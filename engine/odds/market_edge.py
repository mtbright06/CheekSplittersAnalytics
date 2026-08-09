from __future__ import annotations

from typing import Any

from engine.odds.implied_probability import (
    implied_probability_to_american,
)
from engine.odds.models import MarketEdge


def safe_float(
    value: Any,
) -> float | None:
    try:
        if value in {
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        }:
            return None

        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_probability_pct(
    value: Any,
) -> float | None:
    """
    Normalize a probability into percentage form.

    Examples:
        0.551 -> 55.1
        55.1  -> 55.1
    """

    probability = safe_float(value)

    if probability is None:
        return None

    if 0 <= probability <= 1:
        probability *= 100

    if probability < 0 or probability > 100:
        return None

    return probability


def expected_roi(
    model_probability: Any,
    american_odds: Any,
) -> float | None:
    probability_pct = normalize_probability_pct(
        model_probability
    )

    odds = safe_float(
        american_odds
    )

    if (
        probability_pct is None
        or odds is None
        or odds == 0
    ):
        return None

    probability = probability_pct / 100

    if odds > 0:
        profit = odds / 100
    else:
        profit = 100 / abs(odds)

    roi = (
        probability * profit
    ) - (
        1 - probability
    )

    return round(
        roi * 100,
        2,
    )


def calculate_market_edge(
    model_probability: Any,
    quote: Any,
) -> MarketEdge:
    model_probability_pct = (
        normalize_probability_pct(
            model_probability
        )
    )

    book_probability_pct = (
        normalize_probability_pct(
            quote.implied_probability
        )
    )

    if (
        model_probability_pct is None
        or book_probability_pct is None
    ):
        edge = None
    else:
        edge = round(
            model_probability_pct
            - book_probability_pct,
            2,
        )

    fair_odds = (
        implied_probability_to_american(
            model_probability_pct
        )
        if model_probability_pct is not None
        else None
    )

    return MarketEdge(
        selection=quote.selection,
        market=quote.market,
        sportsbook=quote.sportsbook,
        american_odds=quote.american_odds,
        book_probability=book_probability_pct,
        model_probability=model_probability_pct,
        edge=edge,
        fair_odds=fair_odds,
        expected_roi=expected_roi(
            model_probability_pct,
            quote.american_odds,
        ),
    )


def market_edge_to_dict(
    edge: MarketEdge,
) -> dict:
    return {
        "selection": edge.selection,
        "market": edge.market,
        "sportsbook": edge.sportsbook,
        "moneyline": edge.american_odds,
        "american_odds": edge.american_odds,
        "book_probability": (
            edge.book_probability
        ),
        "model_probability": (
            edge.model_probability
        ),
        "edge": edge.edge,
        "fair_odds": edge.fair_odds,
        "expected_roi": edge.expected_roi,
    }
