from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from pages.dashboard_page import (  # noqa: E402
    kbo_recommendation_rank,
    rank_kbo_actionable_games,
)


def test_kbo_lean_outranks_higher_confidence_no_play_for_best_bet():
    games = [
        {
            "matchup": {"away": "Hanwha Eagles", "home": "Doosan Bears"},
            "model": {
                "play": "Hanwha Eagles",
                "recommendation": "❌ NO PLAY",
                "model_probability": 50.5,
                "confidence": 72.0,
            },
        },
        {
            "matchup": {"away": "LG Twins", "home": "Kiwoom Heroes"},
            "model": {
                "play": "LG Twins",
                "recommendation": "👀 LEAN",
                "model_probability": 53.2,
                "confidence": 69.0,
            },
        },
    ]

    assert rank_kbo_actionable_games(games)[0]["model"]["play"] == "LG Twins"


def test_kbo_all_no_play_slate_has_no_best_bet_candidate():
    games = [
        {
            "model": {
                "play": "Hanwha Eagles",
                "recommendation": "❌ NO PLAY",
                "model_probability": 50.5,
                "confidence": 72.0,
            },
        },
        {
            "model": {
                "play": "NC Dinos",
                "recommendation": "PASS",
                "model_probability": 49.8,
                "confidence": 80.0,
            },
        },
    ]

    assert rank_kbo_actionable_games(games) == []


def test_kbo_play_and_strong_play_remain_top_ranked():
    assert kbo_recommendation_rank("🔥 STRONG PLAY") > kbo_recommendation_rank("✅ PLAY")
    assert kbo_recommendation_rank("✅ PLAY") > kbo_recommendation_rank("✅ PLAYABLE")
    assert kbo_recommendation_rank("✅ PLAYABLE") > kbo_recommendation_rank("👀 LEAN")
    assert kbo_recommendation_rank("👀 LEAN") > kbo_recommendation_rank("❌ NO PLAY")
