from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.mlb.totals.helpers import (
    first_number,
)


PASS_EDGE = 0.40
LEAN_EDGE = 0.75
BET_EDGE = 1.25


@dataclass(frozen=True)
class MarketTotal:
    total: float | None
    available: bool
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": (
                None
                if self.total is None
                else round(self.total, 2)
            ),
            "available": self.available,
            "source": self.source,
        }


@dataclass(frozen=True)
class MarketEdge:
    model_total: float
    market_total: float | None
    edge: float | None
    absolute_edge: float | None
    direction: str
    recommendation: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_total": round(
                self.model_total,
                2,
            ),
            "market_total": (
                None
                if self.market_total is None
                else round(
                    self.market_total,
                    2,
                )
            ),
            "edge": (
                None
                if self.edge is None
                else round(
                    self.edge,
                    2,
                )
            ),
            "absolute_edge": (
                None
                if self.absolute_edge is None
                else round(
                    self.absolute_edge,
                    2,
                )
            ),
            "direction": self.direction,
            "recommendation": (
                self.recommendation
            ),
            "status": self.status,
        }


def extract_market_total(
    game: dict[str, Any],
) -> MarketTotal:
    """
    Extract a sportsbook total from the game payload.

    Several possible locations are supported so Totals v1
    can work with current and future provider schemas.
    """

    market = game.get(
        "market",
        {},
    )

    odds = game.get(
        "odds",
        {},
    )

    totals = odds.get(
        "totals",
        {},
    )

    candidates: list[
        tuple[Any, str]
    ] = [
        (
            game.get("market_total"),
            "game.market_total",
        ),
        (
            game.get("total_line"),
            "game.total_line",
        ),
        (
            game.get("game_total"),
            "game.game_total",
        ),
        (
            game.get("over_under"),
            "game.over_under",
        ),
        (
            game.get("ou"),
            "game.ou",
        ),
        (
            market.get("total"),
            "market.total",
        ),
        (
            market.get("line"),
            "market.line",
        ),
        (
            market.get("over_under"),
            "market.over_under",
        ),
        (
            odds.get("total"),
            "odds.total",
        ),
        (
            odds.get("over_under"),
            "odds.over_under",
        ),
        (
            totals.get("line"),
            "odds.totals.line",
        ),
        (
            totals.get("total"),
            "odds.totals.total",
        ),
    ]

    for candidate, source in candidates:
        value = first_number(
            candidate
        )

        if value is None:
            continue

        if value <= 0:
            continue

        return MarketTotal(
            total=value,
            available=True,
            source=source,
        )

    return MarketTotal(
        total=None,
        available=False,
        source="NONE",
    )


def recommendation_from_edge(
    edge: float,
) -> tuple[str, str]:
    """
    Convert signed model edge into direction and label.

    Positive edge:
        model total is above market total -> OVER

    Negative edge:
        model total is below market total -> UNDER
    """

    absolute_edge = abs(
        edge
    )

    if edge > 0:
        direction = "OVER"
    elif edge < 0:
        direction = "UNDER"
    else:
        return (
            "NONE",
            "PASS",
        )

    if absolute_edge < PASS_EDGE:
        recommendation = "PASS"

    elif absolute_edge < LEAN_EDGE:
        recommendation = (
            f"LEAN {direction}"
        )

    elif absolute_edge < BET_EDGE:
        recommendation = (
            f"BET {direction}"
        )

    else:
        recommendation = (
            f"STRONG BET {direction}"
        )

    return (
        direction,
        recommendation,
    )


def evaluate_market_edge(
    *,
    model_total: float,
    market_total: MarketTotal,
) -> MarketEdge:
    """
    Compare the SharpStack projection with the market line.
    """

    if (
        not market_total.available
        or market_total.total is None
    ):
        return MarketEdge(
            model_total=model_total,
            market_total=None,
            edge=None,
            absolute_edge=None,
            direction="NONE",
            recommendation=(
                "NO MARKET LINE"
            ),
            status="MODEL_ONLY",
        )

    edge = (
        model_total
        - market_total.total
    )

    (
        direction,
        recommendation,
    ) = recommendation_from_edge(
        edge
    )

    return MarketEdge(
        model_total=model_total,
        market_total=market_total.total,
        edge=edge,
        absolute_edge=abs(edge),
        direction=direction,
        recommendation=recommendation,
        status="AVAILABLE",
    )
