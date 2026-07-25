from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from engine.odds.quote_utils import (
    american_to_implied_probability,
    expected_value_pct,
    is_mock_sportsbook,
    normalize_sportsbook_name,
    quote_freshness,
    safe_float,
)


def quote_to_dict(
    quote: Any,
) -> dict[str, Any]:
    if quote is None:
        return {}

    if isinstance(quote, dict):
        return dict(quote)

    if is_dataclass(quote):
        return asdict(quote)

    if hasattr(quote, "to_dict"):
        result = quote.to_dict()

        if isinstance(result, dict):
            return result

    fields = [
        "sportsbook",
        "book",
        "provider",
        "odds",
        "american_odds",
        "moneyline",
        "line",
        "selection",
        "market",
        "event_id",
        "commence_time",
        "implied_probability",
        "real_market_loaded",
        "stale",
        "quote_updated_at_utc",
        "quote_age_minutes",
        "freshness_status",
        "freshness_reason",
        "updated_at",
        "last_updated",
        "is_live",
        "source",
    ]

    return {
        field: getattr(
            quote,
            field,
            None,
        )
        for field in fields
    }


def extract_sportsbook(
    quote: dict[str, Any],
) -> str:
    return normalize_sportsbook_name(
        quote.get("sportsbook")
        or quote.get("book")
        or quote.get("provider")
    )


def extract_american_odds(
    quote: dict[str, Any],
) -> float | None:
    candidates = [
        quote.get("american_odds"),
        quote.get("odds"),
        quote.get("moneyline"),
        quote.get("price"),
    ]

    for candidate in candidates:
        number = safe_float(candidate)

        if number is not None:
            return number

    return None


def extract_updated_at(
    quote: dict[str, Any],
) -> Any:
    return (
        quote.get("updated_at")
        or quote.get("last_updated")
        or quote.get("timestamp")
    )


def is_real_quote(
    quote: Any,
) -> bool:
    data = quote_to_dict(quote)

    sportsbook = extract_sportsbook(
        data
    )

    odds = extract_american_odds(
        data
    )

    if not sportsbook:
        return False

    if is_mock_sportsbook(sportsbook):
        return False

    return odds is not None


def american_odds_sort_value(
    odds: Any,
) -> float:
    """
    Larger American odds always represent
    the better bettor price.

    +125 is better than +110.
    -105 is better than -120.
    +100 is better than -105.
    """

    number = safe_float(
        odds,
        -999999,
    )

    return number or -999999


def enrich_quote(
    quote: Any,
    *,
    model_probability: float | None = None,
    maximum_age_minutes: float = 20,
) -> dict[str, Any]:
    data = quote_to_dict(quote)

    sportsbook = extract_sportsbook(
        data
    )

    odds = extract_american_odds(
        data
    )

    updated_at = extract_updated_at(
        data
    )

    implied_probability = (
        american_to_implied_probability(
            odds
        )
    )

    edge_pct = None

    if (
        model_probability is not None
        and implied_probability is not None
    ):
        probability = float(
            model_probability
        )

        if probability > 1:
            probability /= 100

        edge_pct = (
            probability
            - implied_probability
        ) * 100

    freshness = quote_freshness(
        updated_at,
        maximum_age_minutes=maximum_age_minutes,
    )

    enriched = {
        **data,
        "sportsbook": sportsbook,
        "american_odds": odds,
        "implied_probability": (
            implied_probability
        ),
        "edge_pct": edge_pct,
        "expected_value_pct": (
            expected_value_pct(
                model_probability,
                odds,
            )
            if model_probability
            is not None
            else None
        ),
        "real_market_loaded": (
            is_real_quote(data)
        ),
        "stale": freshness.stale,
        "quote_updated_at_utc": (
            freshness.updated_at_utc.isoformat()
            if freshness.updated_at_utc
            else None
        ),
        "quote_age_minutes": freshness.age_minutes,
        "freshness_status": freshness.status,
        "freshness_reason": freshness.reason,
    }

    return enriched


def select_best_quote(
    quotes: list[Any],
    *,
    model_probability: float | None = None,
    maximum_age_minutes: float = 20,
    allow_stale: bool = False,
) -> dict[str, Any] | None:
    enriched = [
        enrich_quote(
            quote,
            model_probability=(
                model_probability
            ),
            maximum_age_minutes=(
                maximum_age_minutes
            ),
        )
        for quote in quotes
    ]

    eligible = [
        quote
        for quote in enriched
        if quote.get(
            "real_market_loaded"
        )
    ]

    if not allow_stale:
        eligible = [
            quote
            for quote in eligible
            if quote.get("freshness_status") == "FRESH"
        ]
    else:
        eligible = [
            quote
            for quote in eligible
            if quote.get("freshness_status") in {"FRESH", "STALE"}
        ]

    if not eligible:
        return None

    eligible.sort(
        key=lambda quote: (
            american_odds_sort_value(
                quote.get(
                    "american_odds"
                )
            ),
            quote.get(
                "expected_value_pct"
            )
            if quote.get(
                "expected_value_pct"
            )
            is not None
            else -999999,
        ),
        reverse=True,
    )

    winner = dict(
        eligible[0]
    )

    winner["quotes_compared"] = len(
        eligible
    )

    return winner


def rank_quotes(
    quotes: list[Any],
    *,
    model_probability: float | None = None,
    maximum_age_minutes: float = 20,
    include_mock: bool = False,
) -> list[dict[str, Any]]:
    enriched = [
        enrich_quote(
            quote,
            model_probability=(
                model_probability
            ),
            maximum_age_minutes=(
                maximum_age_minutes
            ),
        )
        for quote in quotes
    ]

    if not include_mock:
        enriched = [
            quote
            for quote in enriched
            if quote.get(
                "real_market_loaded"
            )
        ]

    enriched.sort(
        key=lambda quote: (
            not quote.get("stale"),
            american_odds_sort_value(
                quote.get(
                    "american_odds"
                )
            ),
        ),
        reverse=True,
    )

    return enriched
