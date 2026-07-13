from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 1.0,
) -> float:
    return max(low, min(high, value))


def american_to_implied_probability(
    odds: Any,
) -> float | None:
    american = safe_float(odds)

    if american is None or american == 0:
        return None

    if american < 0:
        probability = abs(american) / (
            abs(american) + 100
        )
    else:
        probability = 100 / (
            american + 100
        )

    return round(
        clamp(probability),
        6,
    )


def implied_probability_to_american(
    probability: Any,
) -> int | None:
    probability_value = safe_float(probability)

    if (
        probability_value is None
        or probability_value <= 0
        or probability_value >= 1
    ):
        return None

    if probability_value >= 0.5:
        odds = -(
            probability_value
            / (1 - probability_value)
        ) * 100
    else:
        odds = (
            (1 - probability_value)
            / probability_value
        ) * 100

    return int(round(odds))


def american_to_decimal(
    odds: Any,
) -> float | None:
    american = safe_float(odds)

    if american is None or american == 0:
        return None

    if american > 0:
        decimal = 1 + (
            american / 100
        )
    else:
        decimal = 1 + (
            100 / abs(american)
        )

    return round(decimal, 6)


def expected_value(
    model_probability: Any,
    american_odds: Any,
) -> float | None:
    probability = safe_float(model_probability)
    decimal = american_to_decimal(
        american_odds
    )

    if probability is None or decimal is None:
        return None

    if probability > 1:
        probability = probability / 100

    probability = clamp(probability)

    return round(
        (probability * decimal) - 1,
        6,
    )


def probability_edge(
    model_probability: Any,
    market_probability: Any,
) -> float | None:
    model = safe_float(model_probability)
    market = safe_float(market_probability)

    if model is None or market is None:
        return None

    if model > 1:
        model = model / 100

    if market > 1:
        market = market / 100

    return round(
        (model - market) * 100,
        2,
    )


def remove_two_way_vig(
    side_a_odds: Any,
    side_b_odds: Any,
) -> dict[str, float | None]:
    side_a_raw = (
        american_to_implied_probability(
            side_a_odds
        )
    )

    side_b_raw = (
        american_to_implied_probability(
            side_b_odds
        )
    )

    if (
        side_a_raw is None
        or side_b_raw is None
    ):
        return {
            "side_a_raw": side_a_raw,
            "side_b_raw": side_b_raw,
            "side_a_no_vig": None,
            "side_b_no_vig": None,
            "hold": None,
        }

    total = side_a_raw + side_b_raw

    if total <= 0:
        return {
            "side_a_raw": side_a_raw,
            "side_b_raw": side_b_raw,
            "side_a_no_vig": None,
            "side_b_no_vig": None,
            "hold": None,
        }

    return {
        "side_a_raw": round(
            side_a_raw,
            6,
        ),
        "side_b_raw": round(
            side_b_raw,
            6,
        ),
        "side_a_no_vig": round(
            side_a_raw / total,
            6,
        ),
        "side_b_no_vig": round(
            side_b_raw / total,
            6,
        ),
        "hold": round(
            total - 1,
            6,
        ),
    }


@dataclass
class MarketQuote:
    sportsbook: str | None = None
    odds: float | None = None
    line: float | None = None
    implied_probability: float | None = None
    no_vig_probability: float | None = None
    updated_at: str | None = None
    is_live: bool = False
    source: str | None = None

    def __post_init__(self):
        self.odds = safe_float(self.odds)
        self.line = safe_float(self.line)

        self.implied_probability = safe_float(
            self.implied_probability
        )

        self.no_vig_probability = safe_float(
            self.no_vig_probability
        )

        if (
            self.implied_probability is None
            and self.odds is not None
        ):
            self.implied_probability = (
                american_to_implied_probability(
                    self.odds
                )
            )

    @property
    def has_real_price(self) -> bool:
        return (
            self.odds is not None
            and bool(self.sportsbook)
        )

    def to_dict(self) -> dict:
        return {
            "sportsbook": self.sportsbook,
            "odds": self.odds,
            "line": self.line,
            "implied_probability": (
                self.implied_probability
            ),
            "no_vig_probability": (
                self.no_vig_probability
            ),
            "updated_at": self.updated_at,
            "is_live": self.is_live,
            "source": self.source,
            "has_real_price": (
                self.has_real_price
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict | None,
    ) -> "MarketQuote":
        data = data or {}

        return cls(
            sportsbook=data.get("sportsbook"),
            odds=data.get("odds"),
            line=data.get("line"),
            implied_probability=data.get(
                "implied_probability"
            ),
            no_vig_probability=data.get(
                "no_vig_probability"
            ),
            updated_at=data.get("updated_at"),
            is_live=bool(
                data.get("is_live", False)
            ),
            source=data.get("source"),
        )
