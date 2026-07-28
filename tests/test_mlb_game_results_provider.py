from __future__ import annotations

from app.providers.mlb_game_results import MLBGameResultProvider


def _game(*, game_pk=824414, status="Final", abstract="Final", away=2, home=4):
    return {
        "gamePk": game_pk,
        "gameType": "R",
        "gameDate": "2026-07-27T23:10:00Z",
        "doubleHeader": "N",
        "status": {
            "abstractGameState": abstract,
            "detailedState": status,
            "codedGameState": "F",
        },
        "teams": {"away": {"score": away}, "home": {"score": home}},
        "linescore": {"currentInning": 10},
    }


def test_final_game_is_normalized_for_existing_ingestion_service():
    payload = {"dates": [{"games": [_game()]}]}
    result = tuple(MLBGameResultProvider._normalize_games(payload))[0]

    assert result.provider == "mlb_stats_api"
    assert result.league_code == "MLB"
    assert result.provider_game_id == "824414"
    assert result.status == "FINAL"
    assert result.away_score == 2
    assert result.home_score == 4
    assert result.winner_side == "HOME"
    assert result.went_extra_innings is True
    assert result.source_metadata["endpoint"] == "statsapi_schedule"


def test_nonfinal_and_canceled_games_keep_truth_incomplete_or_voidable():
    payload = {
        "dates": [
            {
                "games": [
                    _game(game_pk=1, status="In Progress", abstract="Live", away=1, home=0),
                    _game(game_pk=2, status="Canceled", abstract="Preview", away=None, home=None),
                ]
            }
        ]
    }
    live, canceled = tuple(MLBGameResultProvider._normalize_games(payload))

    assert live.status == "LIVE"
    assert live.winner_side is None
    assert canceled.status == "CANCELED"
    assert canceled.away_score is None
    assert canceled.home_score is None


def test_provider_status_variants_preserve_postponed_and_canceled_truth():
    payload = {
        "dates": [
            {
                "games": [
                    _game(game_pk=3, status="Postponed (Rain)", abstract="Preview", away=None, home=None),
                    _game(game_pk=4, status="Cancelled (Weather)", abstract="Preview", away=None, home=None),
                ]
            }
        ]
    }
    postponed, canceled = tuple(MLBGameResultProvider._normalize_games(payload))

    assert postponed.status == "POSTPONED"
    assert canceled.status == "CANCELED"


def test_missing_provider_game_id_is_not_normalized():
    assert MLBGameResultProvider._normalize_game({"status": {}}) is None
