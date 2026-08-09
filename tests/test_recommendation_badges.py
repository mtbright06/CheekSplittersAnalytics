from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.badges import (
    market_value_badge_html,
    recommendation_badge_class,
)


def test_recommendation_badges_use_the_shared_color_hierarchy():
    assert "recommendation-strong" in recommendation_badge_class("🔥 STRONG PLAY")
    assert "recommendation-playable" in recommendation_badge_class("✅ PLAYABLE")
    assert "recommendation-lean" in recommendation_badge_class("👀 LEAN")
    assert "recommendation-neutral" in recommendation_badge_class("❌ NO PLAY")
    assert "recommendation-neutral" in recommendation_badge_class("PASS")


def test_recommendation_badge_css_is_larger_and_allows_footer_wrapping():
    styles = (DASHBOARD / "styles.py").read_text()

    assert ".recommendation-badge" in styles
    assert "font-size: 15px" in styles
    assert "padding: 7px 14px" in styles
    assert "flex-wrap: wrap" in styles


def test_market_value_badges_use_the_serialized_tone_mapping():
    cases = {
        "elite_value": ("💎", "ELITE VALUE"),
        "strong_value": ("💰", "STRONG VALUE"),
        "positive_value": ("📈", "POSITIVE VALUE"),
        "fair_price": ("➖", "FAIR PRICE"),
        "market_premium": ("⚠️", "MARKET PREMIUM"),
        "heavy_premium": ("🚫", "HEAVY PREMIUM"),
        "unavailable": ("VALUE UNAVAILABLE", "VALUE UNAVAILABLE"),
    }

    for tone, (icon, label) in cases.items():
        html = market_value_badge_html(label, tone)
        assert icon in html
        assert label in html
        assert f"market-value-{tone}" in html
