from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import UUID

from app.services.daily_persistence_service import (
    DailyPersistenceError,
    DailyPersistenceService,
)
from app.services.game_result_ingestion_service import GameResultInput
from app.services.prediction_snapshot_persistence_service import PersistedPredictionRun


SNAPSHOT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
RESULT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
RUN_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


class _Scalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _QueryResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _Scalars(self._values)


class _MatchSession:
    def __init__(self, snapshot_ids):
        self.snapshot_ids = snapshot_ids
        self.closed = False

    def execute(self, statement):
        return _QueryResult(self.snapshot_ids)

    def close(self):
        self.closed = True


class _SnapshotPersistence:
    def __init__(self, *, created=2, error=None):
        self.created = created
        self.error = error
        self.calls = []

    def persist_run(self, *, run, snapshots):
        self.calls.append((run, snapshots))
        if self.error:
            raise self.error
        return PersistedPredictionRun(
            model_run_id=RUN_ID,
            logical_run_key=run.logical_run_key,
            recommendation_ids=(SNAPSHOT_ID,),
            created_snapshot_count=self.created,
            lifecycle_event_count=self.created,
            status="completed",
        )


class _Results:
    def __init__(self, items):
        self.items = items
        self.calls = 0

    def fetch_recent(self, *, days_back):
        self.calls += 1
        return tuple(self.items)


class _ResultIngestion:
    def __init__(self):
        self.inputs = []

    def ingest(self, item):
        self.inputs.append(item)
        return SimpleNamespace(game_result_id=RESULT_ID, changed=True)


class _Grading:
    def __init__(self, *, created=True):
        self.created = created
        self.calls = []

    def grade(self, *, prediction_snapshot_id, game_result_id):
        self.calls.append((prediction_snapshot_id, game_result_id))
        return SimpleNamespace(created=self.created)


def _registry(path: Path, recommendations):
    path.write_text(
        json.dumps(
            {
                "type": "recommendation_registry",
                "version": "1.0.0",
                "generated_at": "2026-07-28T12:00:00Z",
                "recommendations": recommendations,
            }
        ),
        encoding="utf-8",
    )


def _row(*, recommendation="PASS", selection="Washington Nationals", market="moneyline"):
    return {
        "event_id": "824414",
        "sport": "BASEBALL",
        "league": "MLB",
        "market": market,
        "selection": selection,
        "matchup": "Arizona Diamondbacks @ Washington Nationals",
        "event_time": "6:30pm",
        "scheduled_start_at": "2026-07-28T18:30:00Z",
        "recommendation": recommendation,
        "components": {},
    }


def _result_input():
    return GameResultInput(
        provider="mlb_stats_api",
        league_code="MLB",
        provider_game_id="824414",
        status="FINAL",
        away_score=2,
        home_score=4,
        winner_side="HOME",
    )


def test_registry_snapshots_are_persisted_then_matching_results_are_graded():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "recommendation_registry.json"
        _registry(
            path,
            [
                _row(recommendation="CHEEK RIPPER"),
                _row(recommendation="STRONG PLAY"),
                _row(recommendation="PLAYABLE"),
                _row(recommendation="LEAN"),
                _row(recommendation="PASS"),
            ],
        )
        persistence = _SnapshotPersistence()
        ingestion = _ResultIngestion()
        grading = _Grading()
        service = DailyPersistenceService(
            session_factory=lambda: _MatchSession([SNAPSHOT_ID]),
            snapshot_persistence=persistence,
            result_ingestion=ingestion,
            grading=grading,
        )

        summary = service.run(registry_path=path, provider=_Results([_result_input()]))

        assert len(persistence.calls) == 1
        assert len(persistence.calls[0][1]) == 5
        assert {item.prediction.recommendation for item in persistence.calls[0][1]} == {
            "CHEEK RIPPER",
            "PASS",
            "STRONG PLAY",
            "PLAYABLE",
            "LEAN",
        }
        assert ingestion.inputs == [_result_input()]
        assert grading.calls == [(SNAPSHOT_ID, RESULT_ID)]
        assert summary.persisted_snapshots == 2
        assert summary.created_grades == 1
        assert summary.unmatched_results == 0


def test_retry_reuses_existing_snapshots_and_existing_grade_without_duplicate_work():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "recommendation_registry.json"
        _registry(path, [_row()])
        service = DailyPersistenceService(
            session_factory=lambda: _MatchSession([SNAPSHOT_ID]),
            snapshot_persistence=_SnapshotPersistence(created=0),
            result_ingestion=_ResultIngestion(),
            grading=_Grading(created=False),
        )

        summary = service.run(registry_path=path, provider=_Results([_result_input()]))

        assert summary.persisted_snapshots == 0
        assert summary.created_grades == 0
        assert summary.reused_grades == 1


def test_unmatched_authoritative_result_is_visible_in_summary():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "recommendation_registry.json"
        _registry(path, [_row()])
        service = DailyPersistenceService(
            session_factory=lambda: _MatchSession([]),
            snapshot_persistence=_SnapshotPersistence(),
            result_ingestion=_ResultIngestion(),
            grading=_Grading(),
        )

        summary = service.run(registry_path=path, provider=_Results([_result_input()]))

        assert summary.unmatched_results == 1
        assert summary.created_grades == 0


def test_snapshot_persistence_failure_stops_result_polling():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "recommendation_registry.json"
        _registry(path, [_row()])
        provider = _Results([_result_input()])
        service = DailyPersistenceService(
            snapshot_persistence=_SnapshotPersistence(error=DailyPersistenceError("forced failure")),
            result_ingestion=_ResultIngestion(),
            grading=_Grading(),
        )

        try:
            service.run(registry_path=path, provider=provider)
        except DailyPersistenceError:
            assert provider.calls == 0
            return
        raise AssertionError("Result polling continued after prediction persistence failed.")
