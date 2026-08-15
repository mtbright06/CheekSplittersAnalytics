from __future__ import annotations

from datetime import UTC, datetime

from app.providers.kbo_game_results import KBOGameResultProvider
from app.services.prediction_snapshot_grading_service import (
    GRADE_LOSS,
    GRADE_WIN,
    determine_grade_status,
)
from engine.adapters.kbo_card_adapter import adapt_kbo_card
from engine.core import RecommendationRegistry


def _kbo_game(
    *,
    game_id="https://mykbostats.com/games/13809-LG-vs-Kiwoom-20260812",
    game_date="2026-08-12",
    start_time="7:00pm",
    away="LG Twins",
    home="Kiwoom Heroes",
    play="LG Twins",
    recommendation="👀 LEAN",
    model_strength=53.2,
):
    return {
        "sport": "kbo",
        "game_id": game_id,
        "game_date": game_date,
        "start_time": start_time,
        "matchup": {
            "away": away,
            "home": home,
        },
        "teams": {
            "away": {"name": away},
            "home": {"name": home},
        },
        "model": {
            "market": "Moneyline",
            "play": play,
            "recommendation": recommendation,
            "model_strength": model_strength,
            "model_probability": model_strength,
            "model_reliability": 69.0,
            "model_confidence": 69.0,
            "confidence": 69.0,
            "weighted_score": 0.40395,
            "component_scores": {
                "Starting Pitching": 0.345,
                "Offense": 0.714,
                "Bullpen": 0.0,
                "Recent Form": 0.0,
            },
            "configured_weights": {
                "Starting Pitching": 0.55,
                "Offense": 0.3,
                "Bullpen": 0.125,
                "Recent Form": 0.025,
            },
            "confidence_breakdown": {
                "basis": "KBO current input reliability",
                "bullpen": -12.0,
            },
            "shadow_model": {
                "available": True,
                "supported_components": {
                    "Starting Pitching": True,
                    "Offense": True,
                    "Bullpen": False,
                    "Recent Form": False,
                },
                "effective_weights": {
                    "Starting Pitching": 0.647059,
                    "Offense": 0.352941,
                },
                "component_scores": {
                    "Starting Pitching": 0.345,
                    "Offense": 0.714,
                    "Bullpen": 0.0,
                    "Recent Form": 0.0,
                },
                "weighted_score": 0.475235,
                "model_strength": 53.8,
                "selection": play,
                "recommendation": recommendation,
                "concerns": [
                    "Bullpen unsupported; authority omitted from shadow calculation.",
                ],
            },
        },
        "odds": {},
    }


def _card(games):
    return {
        "sport": "KBO",
        "version": "test",
        "generated_at": "2026-08-11T12:00:00Z",
        "games": games,
    }


def test_kbo_game_date_and_time_become_kst_scheduled_start():
    recommendation = adapt_kbo_card(_card([_kbo_game()]))[0]

    assert recommendation.scheduled_start_at == "2026-08-12T10:00:00Z"
    assert recommendation.pregame_eligible is True
    assert recommendation.pregame_eligibility_reason == "GAME_NOT_STARTED"


def test_kbo_kst_date_boundary_preserves_source_game_date():
    recommendation = adapt_kbo_card(
        _card([
            _kbo_game(
                game_date="2026-08-12",
                start_time="12:30am",
            )
        ])
    )[0]

    assert recommendation.scheduled_start_at == "2026-08-11T15:30:00Z"
    assert recommendation.components["identity"]["game_date"] == "2026-08-12"


def test_kbo_current_five_game_style_card_publishes_to_registry():
    games = [
        _kbo_game(game_id=f"https://mykbostats.com/games/1380{i}-A-vs-B-20260812")
        for i in range(5)
    ]
    registry = RecommendationRegistry(adapt_kbo_card(_card(games)))

    assert len(registry.all()) == 5
    assert all(item.league == "KBO" for item in registry.all())


def test_kbo_production_components_and_selected_strength_survive_registry_row():
    recommendation = adapt_kbo_card(_card([_kbo_game()]))[0]
    payload = recommendation.to_dict()

    production = payload["components"]["production"]
    assert production["component_scores"]["Offense"] == 0.714
    assert production["configured_weights"]["Starting Pitching"] == 0.55
    assert production["weighted_score"] == 0.40395
    assert production["raw_model_strength"] == 53.2
    assert production["selected_team_model_strength"] == 53.2
    assert production["selection"] == "LG Twins"
    assert production["recommendation"] == "👀 LEAN"
    assert production["reliability"] == 69.0
    assert production["reliability_breakdown"]["bullpen"] == -12.0


def test_kbo_home_selection_selected_strength_uses_home_perspective():
    recommendation = adapt_kbo_card(
        _card([
            _kbo_game(
                away="Samsung Lions",
                home="KIA Tigers",
                play="KIA Tigers",
                model_strength=48.1,
                recommendation="❌ NO PLAY",
            )
        ])
    )[0]

    assert (
        recommendation.components["production"]["selected_team_model_strength"]
        == 51.9
    )


def test_kbo_shadow_metadata_survives_as_non_authoritative():
    recommendation = adapt_kbo_card(_card([_kbo_game()]))[0]

    shadow = recommendation.to_dict()["components"]["shadow_model"]
    assert shadow["authoritative"] is False
    assert shadow["effective_weights"]["Starting Pitching"] == 0.647059
    assert shadow["selection"] == "LG Twins"
    assert shadow["recommendation"] == "👀 LEAN"
    assert shadow["selected_team_model_strength"] == 53.8


def test_kbo_no_play_publishes_observation_without_becoming_actionable():
    recommendation = adapt_kbo_card(
        _card([
            _kbo_game(
                recommendation="❌ NO PLAY",
                model_strength=50.5,
            )
        ])
    )[0]

    assert recommendation.recommendation == "❌ NO PLAY"
    assert recommendation.actionable is False


def test_kbo_result_provider_normalizes_final_score_and_identity():
    html = """
    <a href="/games/13809-LG-vs-Kiwoom-20260812">
      <span>LG</span><span>Twins</span><span>Kiwoom</span><span>Heroes</span>
      <span>6</span><span>4</span><span>Final</span>
    </a>
    """

    result = tuple(KBOGameResultProvider._normalize_home(html))[0]

    assert result.provider == "mykbostats"
    assert result.league_code == "KBO"
    assert result.provider_game_id == (
        "https://mykbostats.com/games/13809-LG-vs-Kiwoom-20260812"
    )
    assert result.status == "FINAL"
    assert result.away_score == 6
    assert result.home_score == 4
    assert result.winner_side == "AWAY"


def test_kbo_production_moneyline_win_and_loss_use_generic_grading():
    win_snapshot = type(
        "Snapshot",
        (),
        {
            "market_type": "MONEYLINE",
            "selection": "LG Twins",
            "market_line": None,
            "components": {"identity": {"selection_side": "AWAY"}},
        },
    )()
    loss_snapshot = type(
        "Snapshot",
        (),
        {
            "market_type": "MONEYLINE",
            "selection": "Kiwoom Heroes",
            "market_line": None,
            "components": {"identity": {"selection_side": "HOME"}},
        },
    )()
    result = type(
        "Result",
        (),
        {
            "status": "FINAL",
            "winner_side": "AWAY",
            "total_score": 10,
            "revision": 1,
        },
    )()

    assert determine_grade_status(win_snapshot, result) == GRADE_WIN
    assert determine_grade_status(loss_snapshot, result) == GRADE_LOSS


def test_kbo_prediction_payload_is_immutable_rebuild_evidence():
    first = adapt_kbo_card(_card([_kbo_game(model_strength=53.2)]))[0].to_dict()
    later = adapt_kbo_card(_card([_kbo_game(model_strength=55.0)]))[0].to_dict()

    assert first["components"]["production"]["raw_model_strength"] == 53.2
    assert later["components"]["production"]["raw_model_strength"] == 55.0
    assert first["components"]["production"]["raw_model_strength"] != later[
        "components"
    ]["production"]["raw_model_strength"]
    datetime.fromisoformat(
        first["scheduled_start_at"].replace("Z", "+00:00")
    ).astimezone(UTC)
