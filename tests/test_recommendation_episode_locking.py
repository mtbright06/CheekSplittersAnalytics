from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

from app.models.recommendation_episode import RecommendationEpisodeStatus
from app.services.recommendation_episode_lock_service import RecommendationEpisodeLockService


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
STREAM_ID = UUID("11111111-1111-1111-1111-111111111111")
EPISODE_ID = UUID("22222222-2222-2222-2222-222222222222")
SNAPSHOT_ID = UUID("33333333-3333-3333-3333-333333333333")


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def first(self):
        return self.value


class _Session:
    def __init__(self, *results):
        self.results = list(results)
        self.flushes = 0

    def execute(self, statement):
        return _ScalarResult(self.results.pop(0))

    def flush(self):
        self.flushes += 1


def stream(*, scheduled_start_at=NOW - timedelta(minutes=1)):
    return SimpleNamespace(id=STREAM_ID, scheduled_start_at=scheduled_start_at)


def episode(*, status=RecommendationEpisodeStatus.ACTIVE.value):
    return SimpleNamespace(
        id=EPISODE_ID,
        status=status,
        canonical_snapshot_id=None,
        locked_at=None,
        closed_at=None,
        closure_reason=None,
    )


def snapshot(*, snapshot_id=SNAPSHOT_ID, minute=-5):
    return SimpleNamespace(
        id=snapshot_id,
        recommendation_time=NOW + timedelta(minutes=minute),
        created_at=NOW + timedelta(minutes=minute),
    )


def result(status):
    return SimpleNamespace(status=status)


def service():
    return RecommendationEpisodeLockService(now_factory=lambda: NOW)


def test_same_selection_episode_locks_once_with_latest_eligible_snapshot():
    active = episode()
    latest = snapshot()
    session = _Session(None, active, latest)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(),
        result=result("FINAL"),
    )

    assert locked.created is True
    assert locked.canonical_snapshot_id == SNAPSHOT_ID
    assert active.status == RecommendationEpisodeStatus.LOCKED.value
    assert active.canonical_snapshot_id == SNAPSHOT_ID
    assert active.locked_at == NOW


def test_post_start_snapshot_is_never_canonical():
    active = episode()
    session = _Session(None, active, None)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(),
        result=result("FINAL"),
    )

    assert locked.locked is False
    assert locked.status == "NO_ELIGIBLE_SNAPSHOT"
    assert active.status == RecommendationEpisodeStatus.ACTIVE.value


def test_no_build_at_first_pitch_locks_retroactively_on_later_run():
    active = episode()
    pregame_snapshot = snapshot(minute=-20)
    session = _Session(None, active, pregame_snapshot)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(scheduled_start_at=NOW - timedelta(hours=3)),
        result=None,
    )

    assert locked.locked is True
    assert active.canonical_snapshot_id == pregame_snapshot.id


def test_no_actionable_episode_means_no_canonical_recommendation():
    session = _Session(None, None)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(),
        result=result("FINAL"),
    )

    assert locked.episode_id is None
    assert locked.status == "NO_ACTIONABLE_EPISODE"


def test_withdrawn_or_superseded_episode_does_not_lock():
    locked_episode = episode(status=RecommendationEpisodeStatus.WITHDRAWN.value)
    locked_episode.canonical_snapshot_id = None
    session = _Session(None, None)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(),
        result=result("FINAL"),
    )

    assert locked.episode_id is None
    assert locked_episode.status == RecommendationEpisodeStatus.WITHDRAWN.value


def test_unverified_game_state_fails_closed_before_start():
    active = episode()
    session = _Session(None, active)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(scheduled_start_at=NOW + timedelta(hours=2)),
        result=result("SCHEDULED"),
    )

    assert locked.locked is False
    assert active.status == RecommendationEpisodeStatus.ACTIVE.value


def test_repeated_lock_call_is_idempotent():
    locked_episode = episode(status=RecommendationEpisodeStatus.LOCKED.value)
    locked_episode.canonical_snapshot_id = SNAPSHOT_ID
    session = _Session(locked_episode)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(),
        result=result("FINAL"),
    )

    assert locked.created is False
    assert locked.canonical_snapshot_id == SNAPSHOT_ID
    assert session.flushes == 0


def test_concurrent_lock_attempt_observes_existing_locked_episode():
    locked_episode = episode(status=RecommendationEpisodeStatus.LOCKED.value)
    locked_episode.canonical_snapshot_id = SNAPSHOT_ID
    session = _Session(locked_episode)

    locked = service().lock_stream_in_session(
        session=session,
        stream=stream(),
        result=result("FINAL"),
    )

    assert locked.status == RecommendationEpisodeStatus.LOCKED.value
    assert locked.created is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
