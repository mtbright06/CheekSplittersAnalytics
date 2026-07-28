from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.models.game_result import GameResult
from app.services.game_result_ingestion_service import (
    GameResultIngestionError,
    GameResultIngestionService,
    GameResultInput,
)


NOW = datetime(2026, 7, 27, 18, tzinfo=UTC)


def result_input(**overrides):
    values = {
        "provider": "mlb_stats_api",
        "league_code": "mlb",
        "provider_game_id": "824414",
        "status": "scheduled",
        "source_status": "Scheduled",
        "source_updated_at": NOW,
        "source_metadata": {"endpoint": "schedule"},
    }
    values.update(overrides)
    return GameResultInput(**values)


class _Transaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _MemorySession:
    def __init__(self):
        self.record = None
        self.add_calls = 0
        self.flush_calls = 0
        self.rolled_back = False
        self.closed = False

    def begin(self):
        return _Transaction()

    def execute(self, statement):
        return _Result(self.record)

    def add(self, value):
        self.add_calls += 1
        self.record = value

    def flush(self):
        self.flush_calls += 1
        if self.record.id is None:
            self.record.id = UUID("11111111-1111-1111-1111-111111111111")

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def service_for(session):
    return GameResultIngestionService(
        session_factory=lambda: session,
        now_factory=lambda: NOW + timedelta(minutes=1),
    )


def test_first_ingestion_creates_authoritative_result_with_revision_one():
    session = _MemorySession()
    outcome = service_for(session).ingest(result_input())

    assert outcome.created is True
    assert outcome.changed is True
    assert outcome.revision == 1
    assert session.add_calls == 1
    assert session.record.league_code == "MLB"
    assert session.record.last_ingested_at == NOW + timedelta(minutes=1)


def test_repeat_ingestion_reuses_same_record_without_revision_change():
    session = _MemorySession()
    service = service_for(session)
    first = service.ingest(result_input())
    repeat = service.ingest(result_input())

    assert repeat.game_result_id == first.game_result_id
    assert repeat.created is False
    assert repeat.changed is False
    assert repeat.revision == 1
    assert session.add_calls == 1


def test_provider_correction_updates_existing_result_and_increments_revision():
    session = _MemorySession()
    service = service_for(session)
    service.ingest(
        result_input(
            status="final",
            away_score=2,
            home_score=3,
            winner_side="home",
        )
    )
    corrected = service.ingest(
        result_input(
            status="final",
            away_score=2,
            home_score=4,
            winner_side="home",
            source_updated_at=NOW + timedelta(minutes=10),
        )
    )

    assert corrected.created is False
    assert corrected.changed is True
    assert corrected.revision == 2
    assert session.record.home_score == 4
    assert session.record.total_score == 6
    assert session.add_calls == 1


def test_status_transitions_are_preserved_on_the_same_authoritative_record():
    session = _MemorySession()
    service = service_for(session)
    service.ingest(result_input(status="scheduled"))
    live = service.ingest(result_input(status="live", source_status="In Progress"))
    final = service.ingest(
        result_input(
            status="final",
            source_status="Final/10",
            away_score=4,
            home_score=5,
            winner_side="home",
            went_extra_innings=True,
            game_completed_at=NOW,
        )
    )

    assert live.revision == 2
    assert final.revision == 3
    assert session.record.status == "FINAL"
    assert session.record.went_extra_innings is True
    assert session.record.total_score == 9


def test_total_score_is_derived_from_final_component_scores():
    session = _MemorySession()
    outcome = service_for(session).ingest(
        result_input(
            status="final",
            away_score=3,
            home_score=2,
            winner_side="away",
        )
    )

    assert outcome.status == "FINAL"
    assert session.record.total_score == 5


def test_final_rejects_an_inconsistent_provider_total():
    session = _MemorySession()

    try:
        service_for(session).ingest(
            result_input(
                status="final",
                away_score=3,
                home_score=2,
                total_score=6,
            )
        )
    except ValueError as exc:
        assert "total_score" in str(exc)
        return
    raise AssertionError("An inconsistent final total was accepted.")


def test_zero_score_and_shutout_finals_keep_a_zero_or_low_derived_total():
    session = _MemorySession()
    service_for(session).ingest(
        result_input(status="final", away_score=0, home_score=0, winner_side="tie")
    )
    assert session.record.total_score == 0

    shutout = service_for(session).ingest(
        result_input(status="final", away_score=0, home_score=5, winner_side="home")
    )
    assert shutout.revision == 2
    assert session.record.total_score == 5


def test_extra_inning_final_derives_the_full_game_total():
    session = _MemorySession()
    service_for(session).ingest(
        result_input(
            status="final",
            away_score=8,
            home_score=7,
            winner_side="away",
            went_extra_innings=True,
        )
    )

    assert session.record.total_score == 15
    assert session.record.went_extra_innings is True


def test_nonfinal_states_allow_no_score_or_paired_partial_scores_only():
    session = _MemorySession()
    service = service_for(session)
    scheduled = service.ingest(result_input(status="scheduled"))
    assert scheduled.status == "SCHEDULED"
    assert session.record.total_score is None

    live = service.ingest(result_input(status="live", away_score=1, home_score=2))
    assert live.status == "LIVE"
    assert session.record.total_score == 3

    try:
        service.ingest(result_input(status="suspended", total_score=3))
    except ValueError as exc:
        assert "total_score requires" in str(exc)
        return
    raise AssertionError("An independent non-final total was accepted.")


def test_postponed_suspended_canceled_and_incomplete_states_are_accepted():
    for status in ("postponed", "suspended", "canceled", "incomplete"):
        session = _MemorySession()
        outcome = service_for(session).ingest(result_input(status=status))
        assert outcome.status == status.upper()


def test_final_requires_paired_scores_and_known_statuses_are_enforced():
    session = _MemorySession()
    service = service_for(session)

    try:
        service.ingest(result_input(status="final", away_score=3))
    except ValueError as exc:
        assert "score" in str(exc)
    else:
        raise AssertionError("FINAL result without paired scores was accepted.")

    try:
        service.ingest(result_input(status="made up"))
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Unknown provider state was accepted as canonical.")


class _FailingSession(_MemorySession):
    def flush(self):
        raise SQLAlchemyError("forced persistence failure")


def test_failure_rolls_back_and_closes_without_reporting_a_saved_result():
    session = _FailingSession()

    try:
        service_for(session).ingest(result_input())
    except GameResultIngestionError:
        assert session.rolled_back is True
        assert session.closed is True
        return
    raise AssertionError("Failed result ingestion did not raise a persistence error.")


def test_model_declares_provider_identity_and_revision_constraints():
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in GameResult.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("provider", "league_code", "provider_game_id") in unique_columns
    assert any(
        "revision >= 1" in str(constraint.sqltext)
        for constraint in GameResult.__table__.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    )
