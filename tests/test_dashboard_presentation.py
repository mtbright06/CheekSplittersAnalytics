from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.pipeline_status import latest_artifact_timestamp
from components.dashboard_metrics import dashboard_metric_values
from components.play_summary import play_summary_state
import components.play_summary as play_summary
import components.cards as cards
from components.kbo.workstation import kbo_workstation_html
from components.bomb_lab.workstation import bomb_workstation_card_html
import components.bomb_lab.workstation as bomb_workstation
import pages.placeholder_pages as placeholder_pages
from pages.best_bets_page import (
    top_market_plays,
)
from pages.dashboard_page import (
    group_recommendations_by_market,
    market_board_title,
    rank_games_by_confidence,
    rank_mlb_games_by_prediction,
)
from components.explorer.recommendation_explorer import decision_for_game
import components.explorer.recommendation_explorer as recommendation_explorer
from components.confirmation import hammer_confirmation_label


def test_model_only_play_uses_preference_language():
    state = play_summary_state(
        market_loaded=False,
        stale=False,
    )

    assert state["heading"] == "Model Preference"
    assert state["badge"] == "MODEL ONLY"
    assert "No bet recommended" in state["market_status"]


def test_actionable_kbo_model_only_status_does_not_say_no_bet_recommended():
    state = play_summary_state(
        market_loaded=False,
        stale=False,
        recommendation="🔥 STRONG PLAY",
    )

    assert state["badge"] == "MODEL ONLY"
    assert state["market_status"] == "Market unavailable · Odds unavailable"


def test_invalid_market_timestamp_is_not_rendered_as_stale_market():
    state = play_summary_state(
        market_loaded=True,
        stale=True,
        freshness_status="FUTURE_TIMESTAMP",
    )

    assert state["badge"] == "MARKET TIMESTAMP INVALID"
    assert state["market_status"] == "Market timestamp unavailable or invalid"


def test_mlb_market_vs_model_is_an_intelligence_tab_after_decision(monkeypatch):
    labels = []
    rendered = []

    class Tab:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        recommendation_explorer.st,
        "tabs",
        lambda values: (labels.extend(values) or [Tab() for _ in values]),
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "_render_overview",
        lambda game: None,
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "_render_moneyline",
        lambda game: None,
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "render_mlb_totals_card",
        lambda game: None,
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "_render_details",
        lambda game, renderer: None,
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "_render_decision",
        lambda game: None,
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "_render_placeholder",
        lambda title, description: None,
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "render_value_meter",
        lambda game: rendered.append(game),
    )
    monkeypatch.setattr(
        recommendation_explorer,
        "render_progress_bar",
        lambda label, value: rendered.append((label, value)),
    )

    game = {"sport": "mlb", "model": {"confidence": 79.5}}
    recommendation_explorer._render_mlb_intelligence_tabs(game, None)

    assert labels[labels.index("Decision") + 1] == "Market vs Model"
    assert rendered == [game, ("Confidence", 79.5)]


def test_kbo_main_card_matches_the_mlb_recommendation_hierarchy(monkeypatch):
    rendered = []

    monkeypatch.setattr(
        play_summary.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )
    monkeypatch.setattr(play_summary, "render_value_meter", lambda game: None)
    monkeypatch.setattr(
        play_summary,
        "render_progress_bar",
        lambda label, value: rendered.append(f"{label}:{value}"),
    )

    play_summary.render_play_summary(
        {
            "sport": "kbo",
            "matchup": {"away": "Samsung Lions", "home": "Doosan Bears"},
            "model": {
                "play": "Doosan Bears",
                "market": "Moneyline",
                "recommendation": "🔥 STRONG PLAY",
                "model_probability": 59.6,
                "confidence": 100.0,
                "edge": None,
            },
            "odds": {"book_probability": None, "moneyline": None},
        }
    )

    assert "KBO Model Recommendation" in rendered[0]
    assert "<div class='play-title'>Doosan Bears</div>" in rendered[0]
    assert "<div class='muted'>Moneyline</div>" in rendered[0]
    assert "<div class='play-title'>🔥 STRONG PLAY</div>" not in rendered[0]
    assert "🔥 STRONG PLAY <span class='recommendation-star-count'>★★★★★</span>" in rendered[0]
    assert "recommendation-badge recommendation-strong" in rendered[0]
    assert "★★★★★" in rendered[0]
    assert "MODEL ONLY</span>" in rendered[0]
    assert "Model Strength" in rendered[0]
    assert "No bet recommended" not in rendered[0]
    assert rendered[1] == "Model Strength:100.0"


def test_kbo_workstation_renderer_uses_existing_payload_without_legacy_stack():
    html = kbo_workstation_html(
        {
            "sport": "kbo",
            "start_time": "6:30pm",
            "venue": "Suwon",
            "matchup": {
                "away": "Hanwha Eagles",
                "home": "KT Wiz",
            },
            "model": {
                "play": "Hanwha Eagles",
                "market": "Moneyline",
                "recommendation": "✅ PLAYABLE",
                "model_probability": 57.6,
                "confidence": 88.4,
                "edge": None,
                "signals": [
                    {"name": "Starting Pitching", "value": 0.7},
                    {"name": "Offense", "value": 0.25},
                ],
                "reasons": [
                    "Starting Pitching +2",
                    "Hanwha Eagles scores more runs per game.",
                ],
            },
            "odds": {
                "sportsbook": "Unavailable",
                "moneyline": None,
                "real_market_loaded": False,
            },
            "pitching": {
                "away": {
                    "name": "Ryu Hyun-jin",
                    "record": "8-2",
                    "era": 3.22,
                    "whip": 1.15,
                    "throws": "L",
                },
                "home": {
                    "name": "So Hyeong-jun",
                    "record": "6-0",
                    "era": 2.95,
                    "whip": 1.30,
                    "throws": "R",
                },
            },
        }
    )

    assert "kbo-workstation-card" in html
    assert "Hanwha Eagles" in html
    assert "KT Wiz" in html
    assert "6:30pm" in html
    assert "Suwon" in html
    assert "✅ PLAYABLE" in html
    assert "MODEL ONLY" in html
    assert "Model Strength" in html
    assert "88.4" in html
    assert "Model Snapshot" in html
    assert "SharpStack Recommendation · Hanwha Eagles" in html
    assert "Source" in html
    assert "Model-only" in html
    assert "Basis" in html
    assert "Contribution" in html
    assert "Pitching Snapshot" in html
    assert "Ryu Hyun-jin" in html
    assert "So Hyeong-jun" in html
    assert "Starting Pitching +2" in html
    assert "kbo-workstation-pick" not in html
    assert "progress-wrap" not in html
    assert "SharpStack Intelligence" not in html


def test_kbo_workstation_quiets_missing_market_values():
    html = kbo_workstation_html(
        {
            "sport": "kbo",
            "matchup": {
                "away": "Samsung Lions",
                "home": "Lotte Giants",
            },
            "model": {
                "play": "Samsung Lions",
                "market": "Moneyline",
                "recommendation": "🔥 STRONG PLAY",
                "model_probability": 59.6,
                "confidence": 100.0,
                "edge": None,
                "signals": [],
                "reasons": [],
            },
            "odds": {
                "real_market_loaded": False,
                "moneyline": None,
                "sportsbook": "Unavailable",
            },
            "pitching": {
                "away": {},
                "home": {},
            },
        }
    )

    assert "Market Data</span><strong>Unavailable</strong>" in html
    assert "Odds</span>" not in html
    assert "Edge</span>" not in html
    assert "kbo-workstation-metric--quiet" in html
    assert "Confidence</span>" not in html


def test_kbo_render_game_swaps_to_workstation_only(monkeypatch):
    calls = []

    monkeypatch.setattr(
        cards,
        "render_kbo_workstation",
        lambda game: calls.append(("workstation", game)),
    )
    monkeypatch.setattr(
        cards,
        "render_matchup_hero",
        lambda *args, **kwargs: calls.append(("hero", args)),
    )
    monkeypatch.setattr(
        cards,
        "render_play_summary",
        lambda *args, **kwargs: calls.append(("summary", args)),
    )
    monkeypatch.setattr(
        cards,
        "render_recommendation_explorer",
        lambda *args, **kwargs: calls.append(("explorer", args)),
    )

    game = {
        "sport": "kbo",
        "matchup": {"away": "Samsung Lions", "home": "Lotte Giants"},
        "model": {},
        "odds": {},
    }

    cards.render_game(game)

    assert calls == [("workstation", game)]


def test_bomb_lab_workstation_uses_existing_payload_without_legacy_tabs():
    html = bomb_workstation_card_html(
        {
            "bomb_score": 84.2,
            "commence_time": "2026-08-01T00:40:00Z",
            "environment": "ELITE",
            "game": "Kansas City Royals @ Colorado Rockies",
            "opponent": "Colorado Rockies",
            "park_factor": 1.25,
            "park_score": 95.0,
            "pitcher": "Michael Wacha",
            "pitcher_risk": 28.2,
            "pitching_team": "Kansas City Royals",
            "recent_barrel_pct": 0.175,
            "recent_batted_balls": 63,
            "recent_hard_hit_pct": 0.27,
            "recent_hr_per_bbe": 0.079,
            "sample_confidence": 95,
            "target_side": "R",
            "tier": "PLAYABLE",
            "top_hitters": [
                {
                    "name": "Hunter Goodman",
                    "position": "C",
                    "bat_side": "R",
                    "team": "Colorado Rockies",
                    "target_score": 83.0,
                    "hr": 30,
                    "barrel_pct": 0.054,
                    "hard_hit_pct": 0.086,
                    "stars": "★★★★☆",
                },
                {
                    "name": "Mickey Moniak",
                    "position": "LF",
                    "bat_side": "L",
                    "team": "Colorado Rockies",
                    "target_score": 77.0,
                    "hr": 17,
                    "stars": "★★★★",
                }
            ],
            "venue": "Coors Field",
            "why": [
                "Recent barrel rate allowed is dangerous.",
                "Park environment boosts home run upside.",
            ],
        }
    )

    assert "bomb-workstation-card" in html
    assert "Colorado Rockies" in html
    assert "Kansas City Royals" in html
    assert "Michael Wacha" in html
    assert "8:40 PM ET" in html
    assert "Coors Field" in html
    assert "SharpStack Bomb Recommendation" in html
    assert "PLAYABLE" in html
    assert "MODEL ONLY" in html
    assert "Bomb Score" in html
    assert "84.2" in html
    assert "HR Confidence" in html
    assert "Hunter Goodman" in html
    assert "RHB · Target Score: 83.0 · Season HR: 30" in html
    assert "Bomb Squad" in html
    assert "bomb-squad-card--active" in html
    assert "Mickey Moniak" in html
    assert "LHB · Target 77 · 17 HR" in html
    assert "Supporting Metrics" in html
    assert "Why We Like Him" in html
    assert "Recent barrel rate allowed is dangerous." in html
    assert "Open" not in html
    assert "Decision Board" not in html
    assert "Metrics Lab" not in html


def test_bomb_lab_live_page_swaps_to_workstation(monkeypatch, tmp_path):
    calls = []
    card_path = tmp_path / "output" / "cards"
    card_path.mkdir(parents=True)
    (card_path / "bomb_lab_card.json").write_text(
        """
{
  "summary": {"pitchers_loaded": 1},
  "pitchers": [{"opponent": "Colorado Rockies", "pitching_team": "Kansas City Royals"}],
  "table": [{"row": 1}]
}
""",
        encoding="utf-8",
    )

    page_file = tmp_path / "dashboard" / "pages" / "placeholder_pages.py"
    page_file.parent.mkdir(parents=True)
    page_file.touch()
    monkeypatch.setattr(placeholder_pages, "Path", lambda _value: page_file)
    monkeypatch.setattr(
        bomb_workstation,
        "render_bomb_lab_workstation",
        lambda summary, pitchers, table: calls.append((summary, pitchers, table)),
    )

    placeholder_pages.render_bomb_lab()

    assert calls == [
        (
            {"pitchers_loaded": 1},
            [{"opponent": "Colorado Rockies", "pitching_team": "Kansas City Royals"}],
            [{"row": 1}],
        )
    ]


def test_mlb_and_kbo_hero_cards_use_the_same_recommendation_badge_mapping(monkeypatch):
    rendered = []

    monkeypatch.setattr(
        play_summary.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )
    monkeypatch.setattr(play_summary, "render_value_meter", lambda game: None)
    monkeypatch.setattr(play_summary, "render_progress_bar", lambda *args: None)

    for sport in ("mlb", "kbo"):
        play_summary.render_play_summary(
            {
                "sport": sport,
                "matchup": {"away": "Away", "home": "Home"},
                "model": {
                    "play": "Home",
                    "market": "Moneyline",
                    "recommendation": "✅ PLAYABLE",
                    "confidence": 60.0,
                    "edge": 5.0 if sport == "mlb" else None,
                },
                "odds": {"book_probability": None, "moneyline": None},
            }
        )

    assert all("recommendation-badge recommendation-playable" in html for html in rendered)


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


def test_mlb_slate_orders_by_model_win_probability_then_confidence():
    games = [
        {"matchup": {"away": "High Probability Pass"}, "model": {"recommendation": "PASS", "model_probability": 60.0, "confidence": 65.0, "edge": -7.0}},
        {"matchup": {"away": "Lower Probability Lean"}, "model": {"recommendation": "LEAN", "model_probability": 54.0, "confidence": 99.0, "edge": 3.0}},
        {"matchup": {"away": "Probability Tie Lower Confidence"}, "model": {"recommendation": "🔥 CHEEK RIPPER", "model_probability": 57.0, "confidence": 55.0, "edge": 15.0}},
        {"matchup": {"away": "Probability Tie Higher Confidence"}, "model": {"recommendation": "PASS", "model_probability": 57.0, "confidence": 80.0, "edge": -9.0}},
    ]

    ranked = rank_mlb_games_by_prediction(games)

    assert [game["matchup"]["away"] for game in ranked] == [
        "High Probability Pass",
        "Probability Tie Higher Confidence",
        "Probability Tie Lower Confidence",
        "Lower Probability Lean",
    ]


def test_mlb_slate_prediction_order_ignores_edge_recommendation_and_hammer():
    games = [
        {"matchup": {"away": "Prediction First"}, "model": {"model_probability": 58.0, "confidence": 60.0, "recommendation": "PASS", "edge": -10.0, "hammer_score": 40.0}},
        {"matchup": {"away": "Value First"}, "model": {"model_probability": 53.0, "confidence": 90.0, "recommendation": "🔥 CHEEK RIPPER", "edge": 20.0, "hammer_score": 99.0}},
    ]

    ranked = rank_mlb_games_by_prediction(games)

    assert [game["matchup"]["away"] for game in ranked] == [
        "Prediction First",
        "Value First",
    ]


def test_mlb_hero_keeps_compact_conviction_and_value_badges_above_the_fold(monkeypatch):
    rendered = []

    monkeypatch.setattr(
        play_summary.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )
    monkeypatch.setattr(play_summary.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(play_summary, "render_value_meter", lambda game: None)
    monkeypatch.setattr(play_summary, "render_progress_bar", lambda *args: None)

    play_summary.render_play_summary(
        {
            "sport": "mlb",
            "matchup": {"away": "Away", "home": "Los Angeles Dodgers"},
            "model": {
                "play": "Los Angeles Dodgers",
                "market": "Moneyline",
                "model_probability": 58.0,
                "confidence": 76.7,
                "edge": -2.78,
                "recommendation": "🟡 PLAYABLE",
                "market_value_label": "MARKET PREMIUM",
                "market_value_tone": "market_premium",
            },
            "odds": {
                "real_market_loaded": True,
                "moneyline": -155,
                "reference_price": -155,
            },
        },
        hammer_score=60.7,
    )

    assert "Model Prediction · Projected Winner" in rendered[0]
    assert "Model Win %</span><strong>58.0%" in rendered[0]
    assert "Model Confidence</span><strong>76.7/100" in rendered[0]
    assert "Model Conviction" in rendered[0]
    assert "🟡 PLAYABLE" in rendered[0]
    assert "Market Value" in rendered[0]
    assert "⚠️ MARKET PREMIUM" in rendered[0]
    assert rendered[0].index("🟡 PLAYABLE") < rendered[0].index("⚠️ MARKET PREMIUM")
    assert "The model supports Los Angeles Dodgers as a bet." not in rendered[0]
    assert "We like the team, but you're paying a premium." not in rendered[0]
    assert "SSRP Edge" not in rendered[0]
    assert "Price meets model value criteria" not in rendered[0]
    assert "Current odds: -155" in rendered[0]
    assert "Reference price: -155" in rendered[0]
    assert "Hammer Score" not in rendered[0]


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


def test_kbo_dashboard_metrics_count_model_strength_labels_and_use_best_score():
    metrics = dashboard_metric_values(
        {
            "sport": "KBO",
            "games": [
                {"model": {"recommendation": "🔥 STRONG PLAY", "model_probability": 59.6, "edge": None, "confidence": 100.0}},
                {"model": {"recommendation": "✅ PLAYABLE", "model_probability": 55.0, "edge": None, "confidence": 73.3}},
                {"model": {"recommendation": "❌ NO PLAY", "model_probability": 49.0, "edge": None, "confidence": 38.4}},
            ],
        }
    )

    assert metrics[1] == ("Playable", 2)
    assert metrics[2] == ("Best Model Score", "59.6")


def test_hammer_tiers_use_advisory_confirmation_language():
    assert hammer_confirmation_label("WATCH") == "Weak Confirmation"
    assert hammer_confirmation_label("LEAN") == "Moderate Confirmation"
    assert hammer_confirmation_label("BET") == "Strong Confirmation"
    assert hammer_confirmation_label("HAMMER") == "Exceptional Confirmation"
