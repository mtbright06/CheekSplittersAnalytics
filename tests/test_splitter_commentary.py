from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.commentary import (
    LEAN_MESSAGES,
    NO_PLAY_MESSAGES,
    PLAYABLE_MESSAGES,
    STRONG_PLAY_MESSAGES,
    message_pool_for_recommendation,
    splitter_commentary,
)


def test_each_recommendation_tier_uses_only_its_matching_message_pool():
    tiers = [
        ("🔥 STRONG PLAY", STRONG_PLAY_MESSAGES),
        ("✅ PLAYABLE", PLAYABLE_MESSAGES),
        ("👀 LEAN", LEAN_MESSAGES),
        ("❌ NO PLAY", NO_PLAY_MESSAGES),
        ("PASS", NO_PLAY_MESSAGES),
    ]

    for recommendation, expected_pool in tiers:
        assert message_pool_for_recommendation(recommendation) is expected_pool
        for _ in range(10):
            assert splitter_commentary(
                {"model": {"recommendation": recommendation}}
            ) in expected_pool


def test_mlb_and_kbo_recommendations_share_the_same_tier_mapping():
    recommendation = "✅ PLAYABLE"

    assert splitter_commentary(
        {"sport": "mlb", "model": {"recommendation": recommendation}}
    ) in PLAYABLE_MESSAGES
    assert splitter_commentary(
        {"sport": "kbo", "model": {"recommendation": recommendation}}
    ) in PLAYABLE_MESSAGES
