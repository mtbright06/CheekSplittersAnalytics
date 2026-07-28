from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import event

from app.models.recommendation_grade import (
    RecommendationGrade,
    _reject_grade_mutation,
)
from app.services.prediction_snapshot_grading_service import (
    GRADE_LOSS,
    GRADE_PENDING,
    GRADE_PUSH,
    GRADE_UNGRADEABLE,
    GRADE_VOID,
    GRADE_WIN,
    PredictionSnapshotGradingError,
    PredictionSnapshotGradingService,
    determine_grade_status,
)


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
SNAPSHOT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RESULT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def snapshot(*, market="MONEYLINE", selection="HOME", market_line=None, selection_side=None):
    return SimpleNamespace(
        id=SNAPSHOT_ID,
        market_type=market,
        selection=selection,
        market_line=market_line,
        components={
            "identity": {"selection_side": selection_side}
        } if selection_side else {},
    )


def result(*, status="FINAL", winner_side="HOME", total_score=9, revision=1):
    return SimpleNamespace(
        id=RESULT_ID,
        status=status,
        winner_side=winner_side,
        total_score=total_score,
        revision=revision,
    )


def test_moneyline_win_and_loss_use_home_away_result_truth():
    final = result(winner_side="HOME")
    assert determine_grade_status(snapshot(selection="HOME"), final) == GRADE_WIN
    assert determine_grade_status(snapshot(selection="AWAY"), final) == GRADE_LOSS


def test_display_team_moneyline_selection_uses_snapshot_time_side_mapping():
    assert determine_grade_status(
        snapshot(selection="Washington Nationals", selection_side="HOME"),
        result(winner_side="HOME"),
    ) == GRADE_WIN


def test_totals_over_under_and_push_use_immutable_market_line():
    final = result(total_score=10)
    assert determine_grade_status(
        snapshot(market="TOTAL", selection="OVER 9.5", market_line=Decimal("9.5")),
        final,
    ) == GRADE_WIN
    assert determine_grade_status(
        snapshot(market="TOTAL", selection="UNDER", market_line=Decimal("10.5")),
        final,
    ) == GRADE_WIN
    assert determine_grade_status(
        snapshot(market="TOTAL", selection="OVER", market_line=Decimal("10")),
        final,
    ) == GRADE_PUSH


def test_postponed_or_canceled_directional_predictions_are_void():
    assert determine_grade_status(snapshot(), result(status="POSTPONED")) == GRADE_VOID
    assert determine_grade_status(snapshot(), result(status="CANCELED")) == GRADE_VOID


def test_nonfinal_result_stays_pending():
    assert determine_grade_status(snapshot(), result(status="LIVE")) == GRADE_PENDING
    assert determine_grade_status(snapshot(), result(status="SUSPENDED")) == GRADE_PENDING


def test_prediction_without_selection_is_ungradeable_not_loss():
    assert determine_grade_status(snapshot(selection="NONE"), result()) == GRADE_UNGRADEABLE
    assert determine_grade_status(snapshot(selection=""), result()) == GRADE_UNGRADEABLE


def test_pass_recommendation_is_irrelevant_when_snapshot_has_directional_selection():
    pass_snapshot = snapshot(selection="HOME")
    pass_snapshot.recommendation = "PASS"
    assert determine_grade_status(pass_snapshot, result(winner_side="HOME")) == GRADE_WIN


def test_missing_total_line_or_noncanonical_selection_is_ungradeable():
    assert determine_grade_status(
        snapshot(market="TOTAL", selection="OVER", market_line=None),
        result(),
    ) == GRADE_UNGRADEABLE
    assert determine_grade_status(snapshot(selection="Phillies"), result()) == GRADE_UNGRADEABLE


class _Transaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _MemorySession:
    def __init__(self, snapshot_value, result_value):
        self.snapshot_value = snapshot_value
        self.result_value = result_value
        self.existing_grade = None
        self.add_calls = 0
        self.rolled_back = False
        self.closed = False

    def begin(self):
        return _Transaction()

    def get(self, model, identifier):
        if model.__name__ == "Recommendation":
            return self.snapshot_value
        if model.__name__ == "GameResult":
            return self.result_value
        return None

    def execute(self, statement):
        return _ScalarResult(self.existing_grade)

    def add(self, value):
        self.add_calls += 1
        self.existing_grade = value

    def flush(self):
        if self.existing_grade.id is None:
            self.existing_grade.id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _service(session):
    return PredictionSnapshotGradingService(
        session_factory=lambda: session,
        now_factory=lambda: NOW,
    )


def test_grade_persists_once_per_snapshot_result_revision_and_grading_version():
    session = _MemorySession(snapshot(), result())
    service = _service(session)

    first = service.grade(
        prediction_snapshot_id=SNAPSHOT_ID,
        game_result_id=RESULT_ID,
    )
    repeat = service.grade(
        prediction_snapshot_id=SNAPSHOT_ID,
        game_result_id=RESULT_ID,
    )

    assert first.created is True
    assert first.grade_status == GRADE_WIN
    assert first.grading_version == 1
    assert repeat.created is False
    assert repeat.grade_id == first.grade_id
    assert session.add_calls == 1


def test_grading_version_is_metadata_not_parallel_grade_identity():
    session = _MemorySession(snapshot(), result())
    service = _service(session)
    service.grade(prediction_snapshot_id=SNAPSHOT_ID, game_result_id=RESULT_ID)

    version_two = service.grade(
        prediction_snapshot_id=SNAPSHOT_ID,
        game_result_id=RESULT_ID,
        grading_version=2,
    )

    assert version_two.created is False
    assert version_two.grading_version == 1
    assert session.add_calls == 1


def test_corrected_game_result_revision_creates_a_new_immutable_grade():
    session = _MemorySession(snapshot(), result(revision=1))
    service = _service(session)
    service.grade(prediction_snapshot_id=SNAPSHOT_ID, game_result_id=RESULT_ID)

    session.existing_grade = None
    session.result_value.revision = 2
    session.result_value.winner_side = "AWAY"
    corrected = service.grade(
        prediction_snapshot_id=SNAPSHOT_ID,
        game_result_id=RESULT_ID,
    )

    assert corrected.created is True
    assert corrected.game_result_revision == 2
    assert corrected.grade_status == GRADE_LOSS
    assert session.add_calls == 2


class _FailingSession(_MemorySession):
    def flush(self):
        raise SQLAlchemyError("forced failure")


def test_persistence_failure_rolls_back_without_a_partial_grade():
    session = _FailingSession(snapshot(), result())
    try:
        _service(session).grade(
            prediction_snapshot_id=SNAPSHOT_ID,
            game_result_id=RESULT_ID,
        )
    except PredictionSnapshotGradingError:
        assert session.rolled_back is True
        assert session.closed is True
        return
    raise AssertionError("A failed grade write did not roll back.")


def test_model_declares_immutable_evaluation_identity_and_grade_versions():
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in RecommendationGrade.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert (
        "prediction_snapshot_id",
        "game_result_id",
        "game_result_revision",
    ) in unique_columns
    assert "grade_status" in RecommendationGrade.__table__.columns
    assert "recommendation_tier" not in RecommendationGrade.__table__.columns
    assert event.contains(
        RecommendationGrade,
        "before_update",
        _reject_grade_mutation,
    )
