from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.pipeline_status import latest_artifact_timestamp
from components.dashboard_metrics import dashboard_metric_values
from components.play_summary import play_summary_state
from pages.best_bets_page import (
    top_market_plays,
)
from pages.dashboard_page import (
    group_recommendations_by_market,
    market_board_title,
    rank_games_by_confidence,
)
from components.explorer.recommendation_explorer import decision_for_game


def test_model_only_play_uses_preference_language():
    state = play_summary_state(
        market_loaded=False,
        stale=False,
    )

    assert state["heading"] == "Model Preference"
    assert state["badge"] == "MODEL ONLY"
    assert "No bet recommended" in state["market_status"]


def test_latest_artifact_timestamp_uses_newest_loaded_card():
    card = {
        "generated_at": "2026-07-24T08:00:00",
        "cards": [
            {"generated_at": "2026-07-24T08:15:00"},
            {"generated_at": "2026-07-24T08:20:00"},
        ],
    }

    assert latest_artifact_timestamp(card) == "2026-07-24T08:20:00"


def test_command_board_uses_first_artifact_row_per_market():
    recommendations = [
        {"league": "MLB", "market": "totals", "selection": "First Total"},
        {"league": "MLB", "market": "totals", "selection": "Second Total"},
        {"league": "MLB", "market": "moneyline", "selection": "Moneyline"},
        {"league": "KBO", "market": "moneyline", "selection": "KBO"},
    ]

    grouped = group_recommendations_by_market(recommendations)

    assert list(grouped) == [
        ("MLB", "totals"),
        ("MLB", "moneyline"),
        ("KBO", "moneyline"),
    ]
    assert grouped[("MLB", "totals")][0]["selection"] == "First Total"
    assert market_board_title("MLB", "totals") == "MLB Totals"


def test_best_bets_keeps_top_market_rows_in_registry_order():
    recommendations = [
        {"league": "MLB", "market": "moneyline", "recommendation": "BET", "selection": "A"},
        {"league": "MLB", "market": "moneyline", "recommendation": "LEAN", "selection": "B"},
        {"league": "MLB", "market": "totals", "recommendation": "BET", "selection": "C"},
        {"league": "KBO", "market": "moneyline", "recommendation": "PASS", "selection": "D"},
    ]

    plays = top_market_plays(recommendations, "MLB", "moneyline")

    assert [row["selection"] for row in plays] == ["A", "B"]


def test_mlb_and_kbo_share_confidence_display_order():
    games = [
        {"matchup": {"away": "First"}, "model": {"confidence": 42.0}},
        {"matchup": {"away": "Second"}, "model": {"confidence": 71.0}},
        {"matchup": {"away": "Third"}, "model": {"confidence": 56.0}},
    ]

    ranked = rank_games_by_confidence(games)

    assert [game["matchup"]["away"] for game in ranked] == [
        "Second",
        "Third",
        "First",
    ]


def test_decision_tab_uses_the_matching_canonical_decision_row():
    decision_card = {
        "decisions": [
            {"game_pk": 11, "matchup": "Away A @ Home A"},
            {"game_pk": 22, "matchup": "Away B @ Home B"},
        ]
    }

    match = decision_for_game(
        decision_card,
        {"game_id": 22, "matchup": {"away": "Away B", "home": "Home B"}},
    )

    assert match == (2, decision_card["decisions"][1])


def test_dashboard_metric_values_are_reusable_for_compact_headers():
    metrics = dashboard_metric_values(
        {
            "games": [
                {"model": {"confidence": 60.0, "edge": 6.5}},
                {"model": {"confidence": 80.0, "edge": 2.0}},
            ]
        }
    )

    assert metrics == [
        ("Games", 2),
        ("Playable", 1),
        ("Best Edge", "6.5%"),
        ("Avg Confidence", "70.0"),
    ]
