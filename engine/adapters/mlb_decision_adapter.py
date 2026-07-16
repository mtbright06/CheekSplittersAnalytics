from __future__ import annotations

from engine.core.consensus import (
    ConsensusSignal,
    build_consensus,
)

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
        row.get("market")
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
        row.get("market")
        == "REAL MARKET"
    ):
        tags.append("real_market")
    else:
        tags.append("model_only")

    return tags


def score_supports(
    value: Any,
    threshold: float = 60.0,
) -> bool | None:
    number = safe_float(value)

    if number is None:
        return None

    return number >= threshold


def build_consensus_signals(
    row: dict,
) -> list[ConsensusSignal]:
    signals = [
        ConsensusSignal(
            name="MLB Model",
            supports=score_supports(
                row.get(
                    "mlb_model_score"
                )
                or row.get(
                    "model_score"
                )
                or (
                    safe_float(
                        row.get(
                            "model_probability"
                        )
                    )
                    * 100
                    if safe_float(
                        row.get(
                            "model_probability"
                        )
                    )
                    is not None
                    else None
                ),
            ),
            score=(
                row.get(
                    "mlb_model_score"
                )
                or row.get(
                    "model_score"
                )
            ),
            weight=1.4,
            reason=(
                "MLB model supports "
                "the selected side."
            ),
            source="mlb_model",
        ),
        ConsensusSignal(
            name="First 5",
            supports=score_supports(
                row.get(
                    "first5_score"
                )
            ),
            score=row.get(
                "first5_score"
            ),
            weight=1.0,
            reason=(
                "First 5 model supports "
                "the full-game side."
            ),
            source="first5",
        ),
        ConsensusSignal(
            name="Bomb Lab",
            supports=score_supports(
                row.get(
                    "bomb_score"
                )
            ),
            score=row.get(
                "bomb_score"
            ),
            weight=0.8,
            reason=(
                "Bomb Lab supports "
                "the offense."
            ),
            source="bomb_lab",
        ),
        ConsensusSignal(
            name="Starter",
            supports=score_supports(
                row.get(
                    "starter_score"
                )
            ),
            score=row.get(
                "starter_score"
            ),
            weight=1.2,
            reason=(
                "Starting-pitcher matchup "
                "supports the play."
            ),
            source="starter",
        ),
        ConsensusSignal(
            name="Offense",
            supports=score_supports(
                row.get(
                    "offense_score"
                )
            ),
            score=row.get(
                "offense_score"
            ),
            weight=1.0,
            reason=(
                "Offensive matchup "
                "supports the play."
            ),
            source="offense",
        ),
        ConsensusSignal(
            name="Bullpen",
            supports=score_supports(
                row.get(
                    "bullpen_score"
                )
            ),
            score=row.get(
                "bullpen_score"
            ),
            weight=0.8,
            reason=(
                "Bullpen matchup "
                "supports the play."
            ),
            source="bullpen",
        ),
        ConsensusSignal(
            name="Market Edge",
            supports=(
                safe_float(
                    row.get(
                        "market_edge_pct"
                    )
                )
                > 0
                if safe_float(
                    row.get(
                        "market_edge_pct"
                    )
                )
                is not None
                else None
            ),
            score=(
                50
                + (
                    safe_float(
                        row.get(
                            "market_edge_pct"
                        ),
                        0,
                    )
                    or 0
                )
                * 4
            ),
            weight=1.1,
            reason=(
                "Available market price "
                "shows positive model edge."
            ),
            source="market",
        ),
    ]

    return signals


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

        consensus = build_consensus(
        build_consensus_signals(
            row
        )
    )

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
        recommendation=row.get(
            "recommendation"
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
            **row.get(
                "source_signals",
                {},
            ),
            "consensus": (
                consensus.to_dict()
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
