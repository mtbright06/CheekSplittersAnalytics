from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.models.active_recommendation_slot import ActiveRecommendationSlot
from app.services.prediction_snapshot_persistence_service import (
    EVENT_ACTIVATED,
    EVENT_REINSTATED,
    EVENT_SUPERSEDED,
    EVENT_WITHDRAWN,
    REASON_GAME_POSTPONED,
    REASON_MARKET_REFRESH,
    REASON_PASS_REPLACEMENT,
    REASON_REINSTATED,
    REASON_SELECTION_CHANGED,
    PredictionSnapshotPersistenceError,
    PredictionSnapshotPersistenceService,
    WithdrawalRequest,
    supersession_reason,
)
from app.services.prediction_snapshot_service import (
    MarketData,
    PredictionData,
    PredictionIdentity,
    PredictionSnapshot,
    PredictionSnapshotLifecycle,
    SnapshotModelIdentity,
    SupportingEvidence,
)


NOW = datetime(2026, 7, 27, 12, tzinfo=UTC)
MODEL_VERSION_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def build_snapshot(*, selection="Philadelphia Phillies", recommendation="STRONG PLAY", odds=-120):
    lifecycle = PredictionSnapshotLifecycle()
    run = lifecycle.begin_run(
        model=SnapshotModelIdentity("mlb", "1.0", "abc123"),
        logical_build_id="20260727T120000Z",
        artifact_fingerprint="fixture-artifact",
        started_at=NOW,
        build_timestamp=NOW,
    )
    return PredictionSnapshot(
        identity=PredictionIdentity(
            provider_game_id="824414",
            sport="BASEBALL",
            league="MLB",
            market="moneyline",
            selection=selection,
            scheduled_start_at_prediction=NOW + timedelta(hours=2),
        ),
        run=run,
        prediction=PredictionData(recommendation=recommendation),
        market=MarketData(offered_odds=odds),
        supporting_evidence=SupportingEvidence(),
    )


def test_supersession_reason_preserves_selection_model_market_and_pass_evidence():
    prior = SimpleNamespace(
        selection="PHILADELPHIA PHILLIES",
        model_version_id=MODEL_VERSION_ID,
        components={"market": {"offered_odds": -120.0}},
    )
    assert supersession_reason(
        prior,
        build_snapshot(selection="Miami Marlins"),
        MODEL_VERSION_ID,
    ) == REASON_SELECTION_CHANGED
    assert supersession_reason(
        prior,
        build_snapshot(odds=110),
        MODEL_VERSION_ID,
    ) == REASON_MARKET_REFRESH
    assert supersession_reason(
        prior,
        build_snapshot(recommendation="PASS"),
        MODEL_VERSION_ID,
    ) == REASON_PASS_REPLACEMENT


def test_active_slot_has_one_database_identity_per_game_league_market():
    columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in ActiveRecommendationSlot.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("provider_game_id", "league_code", "market_type") in columns


class _FailingTransaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _ScalarResult:
    def scalar_one_or_none(self):
        return None


class _FailingSession:
    def __init__(self):
        self.rolled_back = False
        self.closed = False

    def begin(self):
        return _FailingTransaction()

    def execute(self, statement):
        return _ScalarResult()

    def add(self, value):
        return None

    def flush(self):
        raise SQLAlchemyError("forced transaction failure")

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_partial_persistence_failure_rolls_back_before_any_run_completes():
    session = _FailingSession()
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    snapshot = build_snapshot()

    try:
        service.persist_run(run=snapshot.run, snapshots=[snapshot])
    except PredictionSnapshotPersistenceError:
        assert session.rolled_back is True
        assert session.closed is True
        return
    raise AssertionError("Forced persistence failure did not roll back.")


class _SlotResult:
    def __init__(self, slot):
        self.slot = slot

    def scalar_one_or_none(self):
        return self.slot


class _LifecycleSession:
    def __init__(self, slot, prior):
        self.slot = slot
        self.prior = prior
        self.added = []

    def execute(self, statement):
        return _SlotResult(self.slot)

    def get(self, model, identifier):
        return self.prior

    def add(self, item):
        self.added.append(item)


def test_replacement_records_superseded_and_activated_events_and_updates_slot():
    previous_id = UUID("11111111-1111-1111-1111-111111111111")
    replacement_id = UUID("22222222-2222-2222-2222-222222222222")
    prior = SimpleNamespace(
        selection="PHILADELPHIA PHILLIES",
        model_version_id=MODEL_VERSION_ID,
        components={"market": {"offered_odds": -120.0}},
    )
    slot = SimpleNamespace(active_recommendation_id=previous_id, activated_at=None)
    session = _LifecycleSession(slot, prior)
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    snapshot = build_snapshot(selection="Miami Marlins")
    model_run = SimpleNamespace(id=UUID("33333333-3333-3333-3333-333333333333"), model_version_id=MODEL_VERSION_ID)
    replacement = SimpleNamespace(id=replacement_id)

    assert service._activate_snapshot(session, model_run, replacement, snapshot) == 2
    assert slot.active_recommendation_id == replacement_id
    assert [event.event_type for event in session.added] == [
        EVENT_SUPERSEDED,
        EVENT_ACTIVATED,
    ]


def test_withdrawal_clears_active_slot_and_records_reason():
    previous_id = UUID("11111111-1111-1111-1111-111111111111")
    slot = SimpleNamespace(active_recommendation_id=previous_id, activated_at=NOW)
    session = _LifecycleSession(slot, None)
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    model_run = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        logical_run_key="logical-run",
    )

    assert service._withdraw_slot(
        session,
        model_run,
        WithdrawalRequest("824414", "MLB", "moneyline", REASON_GAME_POSTPONED),
    ) == 1
    assert slot.active_recommendation_id is None
    assert session.added[0].event_type == EVENT_WITHDRAWN
    assert session.added[0].reason == REASON_GAME_POSTPONED


def test_reinstatement_reactivates_a_cleared_slot_with_explicit_reason():
    replacement_id = UUID("22222222-2222-2222-2222-222222222222")
    slot = SimpleNamespace(active_recommendation_id=None, activated_at=None)
    session = _LifecycleSession(slot, None)
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    snapshot = build_snapshot()
    model_run = SimpleNamespace(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        model_version_id=MODEL_VERSION_ID,
    )

    assert service._activate_snapshot(
        session,
        model_run,
        SimpleNamespace(id=replacement_id),
        snapshot,
    ) == 1
    assert slot.active_recommendation_id == replacement_id
    assert session.added[0].event_type == EVENT_REINSTATED
    assert session.added[0].reason == REASON_REINSTATED


class _CompletedRunResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class _ExistingRunSession:
    def __init__(self):
        self.added = []

    def execute(self, statement):
        return _CompletedRunResult([])

    def add(self, value):
        self.added.append(value)


def test_completed_logical_run_retry_is_idempotent_without_new_transitions():
    session = _ExistingRunSession()
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    completed = SimpleNamespace(
        id=UUID("44444444-4444-4444-4444-444444444444"),
        logical_run_key="logical-run",
        status="completed",
        completed_at=NOW,
    )

    result = service._completed_existing_run_or_raise(session, completed)
    assert result.status == "completed"
    assert result.created_snapshot_count == 0
    assert result.lifecycle_event_count == 0
    assert session.added == []


def test_incomplete_logical_run_fails_loudly_instead_of_returning_idempotently():
    session = _ExistingRunSession()
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    incomplete = SimpleNamespace(
        id=UUID("55555555-5555-5555-5555-555555555555"),
        logical_run_key="logical-run",
        status="failed",
        completed_at=None,
    )

    try:
        service._completed_existing_run_or_raise(session, incomplete)
    except PredictionSnapshotPersistenceError:
        assert session.added == []
        return
    raise AssertionError("Incomplete logical run was treated as idempotent.")


def test_simulated_concurrent_completed_run_returns_without_duplicate_events():
    session = _ExistingRunSession()
    service = PredictionSnapshotPersistenceService(session_factory=lambda: session)
    concurrent_winner = SimpleNamespace(
        id=UUID("66666666-6666-6666-6666-666666666666"),
        logical_run_key="logical-run",
        status="completed",
        completed_at=NOW,
    )

    result = service._completed_existing_run_or_raise(session, concurrent_winner)
    assert result.model_run_id == concurrent_winner.id
    assert result.lifecycle_event_count == 0
    assert session.added == []
