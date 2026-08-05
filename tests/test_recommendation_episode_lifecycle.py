from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import RecommendationEpisode, RecommendationEpisodeStatus, RecommendationStream
from app.services.prediction_snapshot_persistence_service import (
    PredictionSnapshotPersistenceError,
    PredictionSnapshotPersistenceService,
)
from app.services.recommendation_episode_service import RecommendationEpisodeService


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            RecommendationStream.__table__,
            RecommendationEpisode.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def model_version():
    return SimpleNamespace(id=uuid4(), version="1.0.0")


def recommendation():
    return SimpleNamespace(recommendation_episode_id=None)


def snapshot(
    *,
    selection: str,
    recommendation_label: str = "PLAYABLE",
    market: str = "moneyline",
    side: str | None = "HOME",
    market_line: float | None = None,
    confidence: float | None = 77.0,
    hammer: float | None = 41.0,
    projection: float | None = 0.58,
    odds: float | None = -120,
    minute: int = 0,
):
    return SimpleNamespace(
        identity=SimpleNamespace(
            provider_game_id="824646",
            sport="BASEBALL",
            league="MLB",
            market=market,
            selection=selection,
            selection_side=side,
            scheduled_start_at_prediction=NOW + timedelta(hours=7),
        ),
        prediction=SimpleNamespace(
            recommendation=recommendation_label,
            confidence_score=confidence,
            hammer_score=hammer,
            model_probability=projection,
        ),
        market=SimpleNamespace(
            market_line=market_line,
            offered_odds=odds,
        ),
        run=SimpleNamespace(
            build_timestamp=NOW + timedelta(minutes=minute),
            source="sharpstack",
            logical_run_key="logical-run-key",
            logical_build_id="logical-build",
            artifact_fingerprint="artifact-fingerprint",
            artifact_schema_version="prediction_snapshot_v1",
            artifact_pointer=None,
            started_at=NOW,
            model=SimpleNamespace(
                model_name="mlb",
                version="1.0.0",
                git_commit="abc123",
            ),
        ),
        components={},
    )


def episodes(session):
    return (
        session.query(RecommendationEpisode)
        .order_by(RecommendationEpisode.opened_at)
        .all()
    )


def test_moneyline_same_selection_attaches_three_snapshots_to_one_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()
    attached_ids = []

    for minute in range(3):
        rec = recommendation()
        service.process_snapshot(
            session=session,
            model_version=version,
            recommendation=rec,
            snapshot=snapshot(selection="Yankees", minute=minute),
        )
        attached_ids.append(rec.recommendation_episode_id)

    assert session.query(RecommendationEpisode).count() == 1
    assert len(set(attached_ids)) == 1


def test_moneyline_selection_change_supersedes_and_opens_new_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()

    first = recommendation()
    second = recommendation()
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=first,
        snapshot=snapshot(selection="Yankees"),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=second,
        snapshot=snapshot(selection="Red Sox", side="AWAY", minute=1),
    )

    rows = episodes(session)
    assert len(rows) == 2
    assert rows[0].status == RecommendationEpisodeStatus.SUPERSEDED.value
    assert rows[0].superseded_by_episode_id == rows[1].id
    assert rows[1].status == RecommendationEpisodeStatus.ACTIVE.value
    assert first.recommendation_episode_id != second.recommendation_episode_id


def test_totals_line_change_attaches_to_same_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()
    first = recommendation()
    second = recommendation()

    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=first,
        snapshot=snapshot(
            selection="OVER 8.5",
            market="totals",
            side=None,
            market_line=8.5,
        ),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=second,
        snapshot=snapshot(
            selection="OVER 9.5",
            market="totals",
            side=None,
            market_line=9.5,
            minute=1,
        ),
    )

    rows = episodes(session)
    assert len(rows) == 1
    assert rows[0].selection == "OVER"
    assert str(rows[0].market_line) == "9.500"
    assert first.recommendation_episode_id == second.recommendation_episode_id


def test_metadata_changes_do_not_split_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()
    first = recommendation()
    second = recommendation()

    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=first,
        snapshot=snapshot(
            selection="Yankees",
            confidence=64.0,
            hammer=30.1,
            projection=0.53,
            odds=-115,
            market_line=8.5,
        ),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=second,
        snapshot=snapshot(
            selection="Yankees",
            confidence=90.0,
            hammer=48.4,
            projection=0.61,
            odds=-145,
            market_line=9.5,
            minute=1,
        ),
    )

    assert session.query(RecommendationEpisode).count() == 1
    assert first.recommendation_episode_id == second.recommendation_episode_id


def test_totals_side_change_opens_second_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()

    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=recommendation(),
        snapshot=snapshot(selection="OVER 8.5", market="totals", side=None, market_line=8.5),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=recommendation(),
        snapshot=snapshot(
            selection="UNDER 8.5",
            market="totals",
            side=None,
            market_line=8.5,
            minute=1,
        ),
    )

    rows = episodes(session)
    assert [row.selection for row in rows] == ["OVER", "UNDER"]
    assert rows[0].status == RecommendationEpisodeStatus.SUPERSEDED.value
    assert rows[1].status == RecommendationEpisodeStatus.ACTIVE.value


def test_pass_then_actionable_creates_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()
    pass_rec = recommendation()
    play_rec = recommendation()

    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=pass_rec,
        snapshot=snapshot(selection="PASS", recommendation_label="PASS", side=None),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=play_rec,
        snapshot=snapshot(selection="Yankees", minute=1),
    )

    assert session.query(RecommendationEpisode).count() == 1
    assert pass_rec.recommendation_episode_id is None
    assert play_rec.recommendation_episode_id is not None


def test_actionable_then_pass_withdraws_active_episode():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()
    play_rec = recommendation()
    pass_rec = recommendation()

    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=play_rec,
        snapshot=snapshot(selection="Yankees"),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=pass_rec,
        snapshot=snapshot(selection="PASS", recommendation_label="PASS", side=None, minute=1),
    )

    row = session.query(RecommendationEpisode).one()
    assert row.status == RecommendationEpisodeStatus.WITHDRAWN.value
    assert pass_rec.recommendation_episode_id == play_rec.recommendation_episode_id


def test_withdrawn_episode_does_not_reopen_when_same_team_returns():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()
    first = recommendation()
    third = recommendation()

    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=first,
        snapshot=snapshot(selection="Yankees"),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=recommendation(),
        snapshot=snapshot(selection="PASS", recommendation_label="PASS", side=None, minute=1),
    )
    service.process_snapshot(
        session=session,
        model_version=version,
        recommendation=third,
        snapshot=snapshot(selection="Yankees", minute=2),
    )

    rows = episodes(session)
    assert len(rows) == 2
    assert rows[0].status == RecommendationEpisodeStatus.WITHDRAWN.value
    assert rows[1].status == RecommendationEpisodeStatus.ACTIVE.value
    assert first.recommendation_episode_id != third.recommendation_episode_id


def test_ineligible_snapshot_does_not_alter_episodes():
    session = session_factory()
    service = RecommendationEpisodeService()
    rec = recommendation()

    result = service.process_snapshot(
        session=session,
        model_version=model_version(),
        recommendation=rec,
        snapshot=snapshot(selection="Yankees"),
        pregame_eligible=False,
    )

    assert result.action == "skipped_ineligible"
    assert rec.recommendation_episode_id is None
    assert session.query(RecommendationStream).count() == 0
    assert session.query(RecommendationEpisode).count() == 0


def test_episode_attachment_rolls_back_with_transaction_failure():
    session = session_factory()
    service = RecommendationEpisodeService()
    rec = recommendation()

    try:
        with session.begin():
            service.process_snapshot(
                session=session,
                model_version=model_version(),
                recommendation=rec,
                snapshot=snapshot(selection="Yankees"),
            )
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    assert rec.recommendation_episode_id is not None
    assert session.query(RecommendationStream).count() == 0
    assert session.query(RecommendationEpisode).count() == 0


class _TrackedTransaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        self.session.in_transaction = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.session.in_transaction = False
        return False


class _NoExistingRun:
    def scalar_one_or_none(self):
        return None


class _TrackedSession:
    def __init__(self):
        self.in_transaction = False
        self.rollback_called = False
        self.close_called = False

    def begin(self):
        return _TrackedTransaction(self)

    def execute(self, statement):
        return _NoExistingRun()

    def add(self, value):
        return None

    def flush(self):
        return None

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.close_called = True


class _FailingEpisodeService:
    def process_snapshot(self, *, session, model_version, recommendation, snapshot):
        assert session.in_transaction is True
        recommendation.recommendation_episode_id = uuid4()
        raise RuntimeError("force episode attachment failure")


class _PersistenceWithTrackedSnapshot(PredictionSnapshotPersistenceService):
    def _get_or_create_model_version(self, session, run):
        assert session.in_transaction is True
        return SimpleNamespace(id=uuid4(), version="1.0.0")

    def _insert_snapshot(self, session, model_run, model_version, snapshot):
        assert session.in_transaction is True
        return recommendation(), True


def test_persistence_and_episode_attachment_share_one_transaction():
    session = _TrackedSession()
    service = _PersistenceWithTrackedSnapshot(
        session_factory=lambda: session,
        episode_service=_FailingEpisodeService(),
    )
    snap = snapshot(selection="Yankees")

    try:
        service.persist_run(run=snap.run, snapshots=[snap])
    except RuntimeError:
        assert session.rollback_called is True
        assert session.close_called is True
        return

    raise AssertionError("Episode attachment failure did not abort persistence.")


def test_service_preserves_one_active_episode_per_stream():
    session = session_factory()
    service = RecommendationEpisodeService()
    version = model_version()

    for minute, selection, side in [
        (0, "Yankees", "HOME"),
        (1, "Red Sox", "AWAY"),
        (2, "Red Sox", "AWAY"),
    ]:
        service.process_snapshot(
            session=session,
            model_version=version,
            recommendation=recommendation(),
            snapshot=snapshot(selection=selection, side=side, minute=minute),
        )

    active_count = (
        session.query(RecommendationEpisode)
        .filter(RecommendationEpisode.status == RecommendationEpisodeStatus.ACTIVE.value)
        .count()
    )
    assert active_count == 1


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
