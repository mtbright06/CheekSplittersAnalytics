from pathlib import Path
import sys
from contextlib import nullcontext


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.badges import recommendation_badge_html, recommendation_stars
import components.registry.registry_cards as registry_cards
from components.registry.registry_cards import kbo_model_only_card_html


def kbo_item(recommendation):
    return {
        "league": "KBO",
        "market": "moneyline",
        "selection": "Doosan Bears",
        "matchup": "Samsung Lions @ Doosan Bears",
        "recommendation": recommendation,
        "real_market_loaded": False,
        "hammer_score": 100.0,
        "ranking_score": 100.0,
    }


def test_kbo_model_only_stars_are_derived_from_the_final_recommendation():
    assert recommendation_stars("🔥 STRONG PLAY", model_only=True) == "★★★★★"
    assert recommendation_stars("✅ PLAYABLE", model_only=True) == "★★★★☆"
    assert recommendation_stars("👀 LEAN", model_only=True) == "★★★☆☆"
    assert recommendation_stars("❌ NO PLAY", model_only=True) == "★☆☆☆☆"


def test_kbo_best_bets_card_uses_dashboard_badges_in_the_required_order():
    html = kbo_model_only_card_html(kbo_item("🔥 STRONG PLAY"), 1)

    assert html.index("Doosan Bears") < html.index("Samsung Lions @ Doosan Bears")
    assert "recommendation-badge recommendation-strong" in html
    assert html.index("🔥 STRONG PLAY") < html.index("KBO · Moneyline")
    assert html.index("KBO · Moneyline") < html.index("MODEL ONLY")
    assert "ss-status-pill ss-status-pill--compact ss-status-pill--neutral" in html
    assert "★★★★★" in html
    assert recommendation_badge_html("🔥 STRONG PLAY", model_only=True) in html


def test_real_market_star_display_keeps_the_existing_value():
    assert recommendation_stars("🔥 STRONG PLAY", fallback="★★") == "★★"


def test_shared_badge_preserves_existing_real_market_stars():
    badge = recommendation_badge_html(
        "BET OVER",
        fallback_stars="★★★★",
    )

    assert "BET OVER" in badge
    assert "★★★★" in badge


def test_mlb_moneyline_and_totals_use_the_shared_hero_badge_row(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        registry_cards.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )
    monkeypatch.setattr(registry_cards.st, "expander", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(registry_cards.st, "info", lambda *args, **kwargs: None)

    for market, recommendation, stars in (
        ("moneyline", "✅ PLAYABLE", "★★★★"),
        ("totals", "LEAN OVER", "★★★"),
    ):
        registry_cards.render_registry_card(
            {
                "league": "MLB",
                "market": market,
                "selection": "Minnesota Twins" if market == "moneyline" else "OVER 8.5",
                "matchup": "Detroit Tigers @ Minnesota Twins",
                "recommendation": recommendation,
                "stars": stars,
                "real_market_loaded": True,
                "market_quote": {},
                "reasons": [],
            },
            1,
        )

    assert all("registry-recommendation-row" in html for html in rendered)
    assert all("registry-market-badge" in html for html in rendered)
    assert all("ss-status-pill--accent" in html for html in rendered)
    assert all("REAL MARKET" in html for html in rendered)
    assert "recommendation-playable" in rendered[0]
    assert "★★★★" in rendered[0]
    assert "recommendation-lean" in rendered[1]
    assert "★★★" in rendered[1]


def test_mlb_moneyline_registry_card_shows_the_serialized_market_value_badge(monkeypatch):
    rendered = []
    monkeypatch.setattr(registry_cards.st, "markdown", lambda html, **kwargs: rendered.append(html))
    monkeypatch.setattr(registry_cards.st, "expander", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(registry_cards.st, "info", lambda *args, **kwargs: None)

    registry_cards.render_registry_card(
        {
            "league": "MLB",
            "market": "moneyline",
            "selection": "Washington Nationals",
            "matchup": "Arizona Diamondbacks @ Washington Nationals",
            "recommendation": "✅ STRONG PLAY",
            "market_value_label": "ELITE VALUE",
            "market_value_tone": "elite_value",
            "real_market_loaded": True,
            "market_quote": {},
            "reasons": [],
        },
        1,
    )

    assert "💎 ELITE VALUE" in rendered[0]
    assert "market-value-elite_value" in rendered[0]
