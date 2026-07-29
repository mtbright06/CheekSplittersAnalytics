from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import UUID

from app.services.daily_persistence_service import DailyPersistenceService
from app.services.prediction_snapshot_persistence_service import PersistedPredictionRun
from engine.adapters.mlb_decision_adapter import adapt_decision
from engine.adapters.mlb_totals_adapter import adapt_mlb_totals_game


RUN_ID = UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 7, 29, 17, 0, tzinfo=UTC)


class _SnapshotPersistence:
    def __init__(self):
        self.calls = []

    def persist_run(self, *, run, snapshots):
        self.calls.append((run, snapshots))
        return PersistedPredictionRun(
            model_run_id=RUN_ID,
            logical_run_key=run.logical_run_key,
            recommendation_ids=(),
            created_snapshot_count=len(snapshots),
            lifecycle_event_count=0,
            status="completed",
        )


class _NoopSession:
    def close(self):
        pass


def test_mlb_totals_adapter_refuses_ineligible_game():
    game = {
        "game_id": "824414",
        "matchup": {"away": "Away", "home": "Home"},
        "commence_time": "2026-07-29T16:00:00Z",
        "scheduled_start_at": "2026-07-29T16:00:00Z",
        "pregame_eligible": False,
        "pregame_eligibility_reason": "GAME_STARTED",
        "odds": {
            "totals": {
                "line": 8.5,
                "available": True,
                "real_market_loaded": True,
                "over_odds": -110,
                "under_odds": -110,
            }
        },
        "totals_model": {
            "selection": "OVER",
            "market_total": 8.5,
            "recommendation": "BET OVER",
            "betting_recommendation": {"recommendation_score": 78},
        },
    }

    assert adapt_mlb_totals_game(game) is None


def test_mlb_moneyline_adapter_refuses_live_row():
    row = {
        "game_pk": "824414",
        "matchup": "Away @ Home",
        "selected_team": "Home",
        "market": "moneyline",
        "is_live": True,
        "recommendation": "BET",
    }

    assert adapt_decision(row) is None


def test_future_totals_row_publishes_scheduled_start():
    game = {
        "game_id": "824414",
        "matchup": {"away": "Away", "home": "Home"},
        "commence_time": "2026-07-29T19:00:00Z",
        "scheduled_start_at": "2026-07-29T19:00:00Z",
        "pregame_eligible": True,
        "pregame_eligibility_reason": "ELIGIBLE",
        "odds": {
            "totals": {
                "line": 8.5,
                "available": True,
                "real_market_loaded": True,
                "sportsbook": "FanDuel",
                "over_odds": -110,
                "under_odds": -110,
                "commence_time": "2026-07-29T19:00:00Z",
            }
        },
        "totals_model": {
            "selection": "OVER",
            "market_total": 8.5,
            "recommendation": "BET OVER",
            "betting_recommendation": {"recommendation": "BET", "recommendation_score": 78},
        },
    }

    recommendation = adapt_mlb_totals_game(game, generated_at=NOW.isoformat())

    assert recommendation is not None
    assert recommendation.scheduled_start_at == "2026-07-29T19:00:00Z"
    assert recommendation.pregame_eligible is True


def test_persistence_skips_new_post_start_pregame_snapshot():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "recommendation_registry.json"
        path.write_text(
            json.dumps(
                {
                    "type": "recommendation_registry",
                    "version": "1.0.0",
                    "generated_at": "2026-07-29T17:00:00Z",
                    "recommendations": [
                        {
                            "event_id": "824414",
                            "sport": "BASEBALL",
                            "league": "MLB",
                            "market": "moneyline",
                            "selection": "HOME",
                            "matchup": "Away @ Home",
                            "scheduled_start_at": "2026-07-29T16:00:00Z",
                            "recommendation": "BET",
                            "market_quote": {},
                            "components": {},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        persistence = _SnapshotPersistence()
        service = DailyPersistenceService(
            session_factory=lambda: _NoopSession(),
            snapshot_persistence=persistence,
            result_ingestion=SimpleNamespace(),
            grading=SimpleNamespace(),
        )

        service.persist_registry(path)

        assert len(persistence.calls) == 1
        assert persistence.calls[0][1] == ()


def test_persistence_skips_time_only_start_and_persists_valid_row():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "recommendation_registry.json"
        path.write_text(
            json.dumps(
                {
                    "type": "recommendation_registry",
                    "version": "1.0.0",
                    "generated_at": "2026-07-29T17:00:00Z",
                    "recommendations": [
                        {
                            "event_id": "bad-kbo",
                            "sport": "BASEBALL",
                            "league": "KBO",
                            "market": "moneyline",
                            "selection": "HOME",
                            "matchup": "Away @ Home",
                            "event_time": "6:30pm",
                            "scheduled_start_at": "6:30pm",
                            "recommendation": "BET",
                            "market_quote": {},
                            "components": {},
                        },
                        {
                            "event_id": "good-mlb",
                            "sport": "BASEBALL",
                            "league": "MLB",
                            "market": "moneyline",
                            "selection": "AWAY",
                            "matchup": "Away @ Home",
                            "scheduled_start_at": "2026-07-29T19:00:00Z",
                            "recommendation": "BET",
                            "market_quote": {},
                            "components": {},
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        persistence = _SnapshotPersistence()
        service = DailyPersistenceService(
            session_factory=lambda: _NoopSession(),
            snapshot_persistence=persistence,
            result_ingestion=SimpleNamespace(),
            grading=SimpleNamespace(),
        )

        service.persist_registry(path)

        assert len(persistence.calls) == 1
        snapshots = persistence.calls[0][1]
        assert len(snapshots) == 1
        assert snapshots[0].identity.provider_game_id == "good-mlb"
