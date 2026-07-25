from __future__ import annotations


from typing import Any

from engine.core import (
    MarketQuote,
    Recommendation,
)


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in [None, "", "None", "N/A", "-", "--"]:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def build_market_quote(
    row: dict,
) -> MarketQuote:
    real_market_loaded = (
        bool(row.get("real_market_loaded"))
        or row.get("market_status")
        == "REAL MARKET"
        or row.get("market")
        == "REAL MARKET"
    )

    sportsbook = (
        row.get("sportsbook")
        or row.get("book")
    )

    if (
        real_market_loaded
        and not sportsbook
    ):
        sportsbook = "UNKNOWN BOOK"

    return MarketQuote(
        sportsbook=sportsbook,
        odds=row.get("book_odds"),
        line=row.get("market_line"),
        implied_probability=row.get(
            "market_probability"
        ),
        no_vig_probability=row.get(
            "market_no_vig_probability"
        ),
        updated_at=row.get(
            "market_updated_at"
        ),
        is_live=bool(
            row.get("is_live", False)
        ),
        source=(
            "decision_card"
            if real_market_loaded
            else None
        ),
    )

def normalize_market(
    row: dict,
) -> str:
    explicit = row.get(
        "market_type"
    )

    if explicit:
        return str(
            explicit
        ).lower()

    return "moneyline"


def build_tags(
    row: dict,
) -> list[str]:
    tags = [
        "mlb",
        "decision_engine",
    ]

    if row.get("first5_score") is not None:
        tags.append("first5_support")

    if row.get("bomb_score") is not None:
        tags.append("bomb_support")

    if (
        row.get("agreement_count", 0)
        >= 2
    ):
        tags.append("multi_model")

    if (
        row.get("real_market_loaded")
        or row.get("market_status")
        == "REAL MARKET"
        or row.get("market")
        == "REAL MARKET"
    ):
        tags.append("real_market")
    else:
        tags.append("model_only")

    return tags

def adapt_decision(
    row: dict,
    *,
    generated_at: str | None = None,
) -> Recommendation:
    market_quote = build_market_quote(
        row
    )

    model_probability = row.get(
        "model_probability"
    )

    market_probability = (
        row.get("market_probability")
        or market_quote.no_vig_probability
        or market_quote.implied_probability
    )

    event_id = row.get(
        "game_pk"
    )

    if event_id is not None:
        event_id = str(event_id)


    return Recommendation(
        sport="BASEBALL",
        league="MLB",
        event_id=event_id,
        matchup=row.get("matchup"),
        event_time=row.get(
            "commence_time"
        ),
        market=normalize_market(row),
        selection=row.get(
            "selected_team",
            "",
        ),
        model_probability=(
            model_probability
        ),
        market_probability=(
            market_probability
        ),
        edge_pct=row.get(
            "market_edge_pct"
        ),
        expected_value_pct=row.get(
            "expected_value_pct"
        ),
        hammer_score=(
            safe_float(
                row.get("hammer_score"),
                0,
            )
            or 0
        ),
        recommendation=(
            row.get("model_recommendation")
            or row.get("recommendation")
        ),
        model_recommendation=row.get(
            "model_recommendation"
        ),
        market_value_label=row.get(
            "market_value_label"
        ),
        market_value_tone=row.get(
            "market_value_tone"
        ),
        recommendation_explanation=row.get(
            "recommendation_explanation",
            {},
        ),
        hammer_tier=row.get("hammer_tier"),
        hammer_assessment=row.get(
            "hammer_assessment"
        ),
        confidence=row.get(
            "confidence"
        ),
        stars=row.get("stars"),
        units=row.get("units"),
        market_quote=market_quote,
        reasons=row.get(
            "reasons",
            [],
        ),
        components=row.get(
            "score_breakdown",
            {},
        ),

        source_signals={
            **(
                row.get("source_signals", {})
                if isinstance(row.get("source_signals"), dict)
                else {}
            ),
            "consensus": row.get(
                "consensus",
                {},
            ),
         },

        tags=build_tags(row),
        status=(
            "live"
            if row.get("is_live")
            else "pregame"
        ),
        generated_at=(
            generated_at
            or row.get("generated_at")
        ),
    )


def adapt_mlb_decision_card(
    card: dict,
) -> list[Recommendation]:
    generated_at = card.get(
        "generated_at"
    )

    rows = card.get(
        "decisions",
        [],
    )

    recommendations = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        selection = row.get(
            "selected_team"
        )

        if not selection:
            continue

        recommendations.append(
            adapt_decision(
                row,
                generated_at=(
                    generated_at
                ),
            )
        )

    return recommendations
