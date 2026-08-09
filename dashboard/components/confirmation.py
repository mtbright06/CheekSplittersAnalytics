from __future__ import annotations

from typing import Any


def hammer_confirmation_label(
    tier: Any,
) -> str:
    """Translate internal Hammer tiers into advisory UI language."""
    labels = {
        "HAMMER": "Exceptional Confirmation",
        "BET": "Strong Confirmation",
        "LEAN": "Moderate Confirmation",
        "WATCH": "Weak Confirmation",
        "PASS": "Minimal Confirmation",
    }

    return labels.get(
        str(tier or "").upper(),
        "Confirmation Unavailable",
    )
