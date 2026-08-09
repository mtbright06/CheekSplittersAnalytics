from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.models.recommendation_episode import RecommendationEpisodeStatus
from app.services.canonical_recommendation_grading_service import (
    CanonicalRecommendationGradingError,
    CanonicalRecommendationGradingService,
)
from app.services.prediction_snapshot_grading_service import (
    GRADE_LOSS,
    GRADE_PENDING,
    GRADE_PUSH,
    GRADE_VOID,
    GRADE_WIN,
)


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
EPISODE_ID = UUID("11111111-1111-1111-1111-111111111111")
SNAPSHOT_ID = UUID("22222222-2222-2222-2222-222222222222")
RESULT_ID = UUID("33333333-3333-3333-3333-333333333333")
GRADE_ID = UUID("44444444-4444-4444-4444-444444444444")


class _Transaction:
    def __init__(self, session):
        self.session = session
        self.status = None
        self.added_count = 0

    def __enter__(self):
        self.status = self.session.episode.status if self.session.episode else None
        self.added_count = len(self.session.added)
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            if self.session.current_episode is not None:
                self.session.current_episode.status = self.status
            del self.session.added[self.added_count:]
        return False


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, episode, game_result, existing=None):
        self.episode = episode
        self.game_result = game_result
        self.existing = existing
        self.added = []
        self.current_episode = episode
        self.closed = False
        self.rolled_back = False

    def begin(self):
        return _Transaction(self)

    def get(self, model, identifier):
        if model.__name__ == "GameResult":
            return self.game_result
        return None

    def execute(self, statement):
        if self.episode is not None:
            value = self.episode
            self.current_episode = value
            self.episode = None
            return _ScalarResult(value)
        return _ScalarResult(self.existing)

    def add(self, value):
        self.added.append(value)
        self.existing = value

    def flush(self):
        if self.added and self.added[-1].id is None:
            self.added[-1].id = GRADE_ID

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class _FailingSession(_Session):
    def flush(self):
        raise SQLAlchemyError("forced failure")


def snapshot(*, market="MONEYLINE", selection="HOME", market_line=None, side=None):
    return SimpleNamespace(
        id=SNAPSHOT_ID,
        market_type=market,
        selection=selection,
        market_line=market_line,
        components={"identity": {"selection_side": side}} if side else {},
    )


def episode(*, status=RecommendationEpisodeStatus.LOCKED.value, canonical=None):
    canonical_snapshot = canonical or snapshot()
    return SimpleNamespace(
        id=EPISODE_ID,
        status=status,
        canonical_snapshot_id=canonical_snapshot.id if canonical_snapshot else None,
        canonical_snapshot=canonical_snapshot,
    )


def result(*, status="FINAL", winner_side="HOME", total_score=9, revision=1):
    return SimpleNamespace(
        id=RESULT_ID,
        status=status,
        winner_side=winner_side,
        total_score=total_score,
        revision=revision,
    )


def existing_grade():
    return SimpleNamespace(
        id=GRADE_ID,
        recommendation_episode_id=EPISODE_ID,
        canonical_snapshot_id=SNAPSHOT_ID,
        game_result_id=RESULT_ID,
        game_result_revision=1,
        grade_status=GRADE_WIN,
        grading_version=1,
    )


def service(session):
    return CanonicalRecommendationGradingService(
        session_factory=lambda: session,
        now_factory=lambda: NOW,
    )


def test_moneyline_canonical_episode_grades_once():
    session = _Session(episode(), result())

    saved = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert saved.created is True
    assert saved.grade_status == GRADE_WIN
    assert session.added[0].recommendation_episode_id == EPISODE_ID
    assert session.existing is session.added[0]
    assert session.added[0].id == GRADE_ID


def test_totals_canonical_episode_uses_canonical_snapshot_line():
    canonical = snapshot(market="TOTALS", selection="OVER 8.5", market_line=Decimal("8.5"))
    session = _Session(episode(canonical=canonical), result(total_score=9))

    saved = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert saved.grade_status == GRADE_WIN


def test_totals_push_is_handled_correctly():
    canonical = snapshot(market="TOTALS", selection="UNDER", market_line=Decimal("9"))
    session = _Session(episode(canonical=canonical), result(total_score=9))

    saved = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert saved.grade_status == GRADE_PUSH


def test_canceled_game_becomes_void_without_canonical_grade_row():
    row = episode()
    session = _Session(row, result(status="CANCELED"))

    saved = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert saved.grade_status == GRADE_VOID
    assert saved.created is False
    assert row.status == RecommendationEpisodeStatus.VOID.value
    assert session.added == []


def test_suspended_game_remains_pending():
    session = _Session(episode(), result(status="SUSPENDED"))

    saved = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert saved.grade_status == GRADE_PENDING
    assert saved.created is False
    assert session.added == []


def test_superseded_or_withdrawn_episodes_never_receive_grades():
    for status in [
        RecommendationEpisodeStatus.SUPERSEDED.value,
        RecommendationEpisodeStatus.WITHDRAWN.value,
        RecommendationEpisodeStatus.ACTIVE.value,
    ]:
        session = _Session(episode(status=status), result())
        saved = service(session).grade_episode(
            recommendation_episode_id=EPISODE_ID,
            game_result_id=RESULT_ID,
        )
        assert saved.grade_status == GRADE_PENDING
        assert session.added == []


def test_repeated_grade_call_reuses_existing_canonical_grade():
    session = _Session(episode(), result(), existing=existing_grade())

    saved = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert saved.created is False
    assert saved.grade_id == GRADE_ID
    assert session.added == []


def test_only_one_grade_exists_per_episode_by_service_lookup():
    session = _Session(episode(), result(), existing=existing_grade())

    first_lookup = service(session).grade_episode(
        recommendation_episode_id=EPISODE_ID,
        game_result_id=RESULT_ID,
    )

    assert first_lookup.grade_id == GRADE_ID
    assert session.existing.id == GRADE_ID


def test_transaction_rollback_leaves_no_partial_grade_or_state_transition():
    row = episode(canonical=snapshot(selection="AWAY"))
    session = _FailingSession(row, result())

    try:
        service(session).grade_episode(
            recommendation_episode_id=EPISODE_ID,
            game_result_id=RESULT_ID,
        )
    except CanonicalRecommendationGradingError:
        assert session.rolled_back is True
        assert session.closed is True
        assert row.status == RecommendationEpisodeStatus.LOCKED.value
        assert session.added == []
        return

    raise AssertionError("Forced canonical grade failure did not roll back.")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
