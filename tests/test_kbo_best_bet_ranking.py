from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from pages.dashboard_page import (  # noqa: E402
    kbo_selected_team_model_strength,
    kbo_recommendation_rank,
    rank_kbo_games_for_dashboard,
    rank_kbo_actionable_games,
    rank_mlb_games_by_prediction,
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


def test_kbo_dashboard_actionable_tiers_precede_no_play():
    games = [
        {
            "matchup": {"away": "Hanwha Eagles", "home": "Doosan Bears"},
            "model": {
                "play": "Hanwha Eagles",
                "recommendation": "❌ NO PLAY",
                "model_probability": 50.5,
                "confidence": 99.0,
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

    assert rank_kbo_games_for_dashboard(games)[0]["model"]["play"] == "LG Twins"


def test_kbo_dashboard_tier_ladder_order():
    games = [
        {
            "model": {
                "play": "Lean",
                "recommendation": "👀 LEAN",
                "model_probability": 55.0,
                "confidence": 80.0,
            },
        },
        {
            "model": {
                "play": "Playable",
                "recommendation": "✅ PLAYABLE",
                "model_probability": 52.0,
                "confidence": 80.0,
            },
        },
        {
            "model": {
                "play": "Strong",
                "recommendation": "🔥 STRONG PLAY",
                "model_probability": 51.0,
                "confidence": 80.0,
            },
        },
        {
            "model": {
                "play": "Play",
                "recommendation": "✅ PLAY",
                "model_probability": 53.0,
                "confidence": 80.0,
            },
        },
    ]

    assert [game["model"]["play"] for game in rank_kbo_games_for_dashboard(games)] == [
        "Strong",
        "Play",
        "Playable",
        "Lean",
    ]


def test_kbo_dashboard_same_tier_uses_selected_team_strength():
    games = [
        {
            "matchup": {"away": "Away A", "home": "Home A"},
            "model": {
                "play": "Away A",
                "recommendation": "👀 LEAN",
                "model_probability": 52.0,
                "confidence": 95.0,
            },
        },
        {
            "matchup": {"away": "Away B", "home": "Home B"},
            "model": {
                "play": "Away B",
                "recommendation": "👀 LEAN",
                "model_probability": 54.0,
                "confidence": 70.0,
            },
        },
    ]

    assert rank_kbo_games_for_dashboard(games)[0]["model"]["play"] == "Away B"


def test_kbo_dashboard_home_selection_uses_selected_team_perspective():
    home_selection = {
        "matchup": {"away": "Away A", "home": "Home A"},
        "model": {
            "play": "Home A",
            "recommendation": "✅ PLAYABLE",
            "model_probability": 47.0,
            "confidence": 70.0,
        },
    }
    away_selection = {
        "matchup": {"away": "Away B", "home": "Home B"},
        "model": {
            "play": "Away B",
            "recommendation": "✅ PLAYABLE",
            "model_probability": 52.0,
            "confidence": 99.0,
        },
    }

    assert kbo_selected_team_model_strength(home_selection) == 53.0
    assert rank_kbo_games_for_dashboard([away_selection, home_selection])[0] == home_selection


def test_kbo_dashboard_ordering_is_deterministic_for_ties():
    games = [
        {
            "id": "first",
            "matchup": {"away": "Away A", "home": "Home A"},
            "model": {
                "play": "Home A",
                "recommendation": "❌ NO PLAY",
                "model_probability": 49.0,
                "confidence": 72.0,
            },
        },
        {
            "id": "second",
            "matchup": {"away": "Away B", "home": "Home B"},
            "model": {
                "play": "Home B",
                "recommendation": "❌ NO PLAY",
                "model_probability": 49.0,
                "confidence": 72.0,
            },
        },
    ]

    assert [game["id"] for game in rank_kbo_games_for_dashboard(games)] == [
        "first",
        "second",
    ]


def test_mlb_prediction_ordering_unchanged_by_kbo_dashboard_sort():
    games = [
        {"model": {"model_probability": 51.0, "confidence": 99.0}},
        {"model": {"model_probability": 55.0, "confidence": 50.0}},
    ]

    assert rank_mlb_games_by_prediction(games)[0]["model"]["model_probability"] == 55.0
