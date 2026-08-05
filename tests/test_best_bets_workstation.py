from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.best_bets_workstation import (
    _recommendation_row_html,
    _summary_from_registry,
    _today_card_hero_html,
    _top_play_banner_html,
    filter_recommendations,
)


def registry_item(**overrides):
    item = {
        "league": "MLB",
        "market": "moneyline",
        "selection": "Houston Astros",
        "matchup": "Houston Astros @ Los Angeles Angels",
        "recommendation": "LEAN",
        "actionable": True,
        "real_market_loaded": True,
        "market_quote": {"odds": -126},
        "edge_pct": 88.0,
        "confidence": "HIGH",
        "reasons": ["Model projects Houston Astros at 57.4%."],
    }
    item.update(overrides)
    return item


def test_today_card_hero_uses_registry_counts_and_timestamp():
    summary = {
        "leagues": ["MLB", "KBO"],
        "recommendations": 12,
        "strong_bets": 2,
        "playable": 4,
        "leans": 6,
    }

    html = _today_card_hero_html(summary, "2026-07-29T19:26:52+00:00")

    assert "Today's Card" in html
    assert "<h1>Best Bets</h1>" not in html
    assert "MLB" in html
    assert "12" in html
    assert "Strong Bets" in html
    assert "4" in html
    assert "6" in html
    assert "Updated" in html


def test_best_bets_summary_derives_playable_and_lean_counts_from_registry_rows():
    summary = _summary_from_registry(
        {"summary": {"recommendations": 4, "leagues": ["MLB"]}},
        [
            registry_item(recommendation="BET"),
            registry_item(recommendation="✅ PLAYABLE"),
            registry_item(recommendation="LEAN"),
            registry_item(recommendation="PASS", actionable=False),
        ],
    )

    assert summary["strong_bets"] == 1
    assert summary["playable"] == 1
    assert summary["leans"] == 1


def test_best_bets_filter_preserves_registry_rows_without_reordering():
    rows = [
        registry_item(selection="Astros"),
        registry_item(selection="Over 8.5", market="totals"),
        registry_item(selection="Doosan Bears", league="KBO"),
    ]

    filtered = filter_recommendations(rows, "MLB", "moneyline")

    assert [row["selection"] for row in filtered] == ["Astros"]


def test_best_bets_row_uses_workstation_card_language():
    html = _recommendation_row_html(registry_item(), 1)

    assert "best-bets-row" in html
    assert "Houston Astros" in html
    assert "Moneyline" in html
    assert "LEAN" in html
    assert "Current Odds" in html
    assert "-126" in html
    assert "Edge" in html
    assert "Confidence" in html
    assert "Model projects Houston Astros" in html
    assert "ss-status-pill" in html


def test_top_play_banner_replaces_large_play_of_day_card():
    html = _top_play_banner_html(
        {
            "recommendation": registry_item(
                market="totals",
                selection="OVER 6.5",
                matchup="Atlanta Braves @ New York Mets",
                recommendation="BET",
                hammer_score=90.4,
                market_quote={"odds": -122, "line": 6.5},
                source_signals={"totals_edge_runs": 1.71},
                pregame_eligible=True,
                pregame_eligibility_reason="GAME_NOT_STARTED",
                status="pregame",
            )
        }
    )

    assert "best-bets-top-play" in html
    assert "Today's Top Play" in html
    assert "OVER 6.5" in html
    assert "Atlanta Braves @ New York Mets" in html
    assert "BET" in html
    assert "Hammer 90.4" in html
    assert "Best Price -122" in html
    assert "decision-card" not in html
    assert "play-day-top-row" not in html


def test_top_play_banner_fails_closed_for_non_pregame_top_play():
    html = _top_play_banner_html(
        {
            "reason": "No eligible pregame Top Play is available.",
            "recommendation": registry_item(
                status="live",
                pregame_eligible=False,
                pregame_eligibility_reason="GAME_STARTED",
            ),
        }
    )

    assert "best-bets-top-play--empty" in html
    assert "No eligible pregame Top Play is available." in html
    assert "Houston Astros" not in html
