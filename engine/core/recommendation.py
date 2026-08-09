from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from engine.core.pregame_eligibility import PregameEligibilityReason
from engine.core.markets import (
    MarketQuote,
    expected_value,
    probability_edge,
)
from engine.core.scoring import (
    clamp_score,
    confidence_label,
    recommendation_label,
    stars_from_score,
    unit_recommendation,
)


def normalize_probability(
    value: Any,
) -> float | None:
    try:
        if value in [
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        ]:
            return None

        number = float(value)

        if number > 1:
            number = number / 100

        return max(
            0.0,
            min(1.0, number),
        )
    except (TypeError, ValueError):
        return None


def is_actionable_label(
    value: Any,
) -> bool:
    label = str(value or "").upper()

    if not label or "NO PLAY" in label or label == "PASS":
        return False

    return any(
        tier in label
        for tier in (
            "HAMMER",
            "BET",
            "LEAN",
            "PLAYABLE",
            "STRONG PLAY",
            "CHEEK RIPPER",
        )
    )


def is_verified_pregame_recommendation(value: Any) -> bool:
    eligible = getattr(value, "pregame_eligible", None)
    reason = str(getattr(value, "pregame_eligibility_reason", "") or "")

    return (
        eligible is True
        and reason
        in {
            PregameEligibilityReason.GAME_NOT_STARTED.value,
            PregameEligibilityReason.ELIGIBLE.value,
        }
    )


@dataclass
class Recommendation:
    sport: str
    league: str
    market: str
    selection: str

    event_id: str | None = None
    matchup: str | None = None
    event_time: str | None = None
    scheduled_start_at: str | None = None

    model_win_strength: float | None = None
    model_probability: float | None = None
    market_probability: float | None = None

    edge_pct: float | None = None
    expected_value_pct: float | None = None

    hammer_score: float = 0.0
    recommendation: str | None = None
    model_recommendation: str | None = None
    market_value_label: str | None = None
    market_value_tone: str | None = None
    recommendation_explanation: dict[str, Any] = field(
        default_factory=dict
    )
    hammer_tier: str | None = None
    hammer_assessment: str | None = None
    model_confidence: float | None = None
    hammer_confidence: str | None = None
    confidence: str | None = None
    stars: str | None = None
    units: float | None = None

    market_quote: MarketQuote = field(
        default_factory=MarketQuote
    )

    reasons: list[str] = field(
        default_factory=list
    )

    components: dict[str, Any] = field(
        default_factory=dict
    )

    source_signals: dict[str, Any] = field(
        default_factory=dict
    )

    tags: list[str] = field(
        default_factory=list
    )

    status: str = "pregame"
    pregame_eligible: bool | None = None
    pregame_eligibility_reason: str | None = None
    generated_at: str = field(
        default_factory=lambda: (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )

    recommendation_id: str = field(
        default_factory=lambda: (
            uuid4().hex
        )
    )

    def __post_init__(self):
        self.sport = str(
            self.sport or ""
        ).upper()

        self.league = str(
            self.league or ""
        ).upper()

        self.market = str(
            self.market or ""
        ).lower()

        self.selection = str(
            self.selection or ""
        ).strip()

        self.model_win_strength = (
            normalize_probability(
                self.model_win_strength
            )
        )

        self.model_probability = (
            normalize_probability(
                self.model_probability
            )
        )

        if self.model_win_strength is None:
            self.model_win_strength = self.model_probability

        if self.model_probability is None:
            self.model_probability = self.model_win_strength

        self.market_probability = (
            normalize_probability(
                self.market_probability
            )
        )

        self.hammer_score = clamp_score(
            self.hammer_score
        )

        if not isinstance(
            self.market_quote,
            MarketQuote,
        ):
            self.market_quote = (
                MarketQuote.from_dict(
                    self.market_quote
                )
            )

        if (
            self.market_probability is None
            and self.market_quote.no_vig_probability
            is not None
        ):
            self.market_probability = (
                self.market_quote.no_vig_probability
            )

        if (
            self.market_probability is None
            and self.market_quote.implied_probability
            is not None
        ):
            self.market_probability = (
                self.market_quote.implied_probability
            )

        if self.edge_pct is None:
            self.edge_pct = probability_edge(
                self.model_probability,
                self.market_probability,
            )

        if (
            self.expected_value_pct is None
            and self.model_probability
            is not None
            and self.market_quote.odds
            is not None
        ):
            ev = expected_value(
                self.model_probability,
                self.market_quote.odds,
            )

            if ev is not None:
                self.expected_value_pct = round(
                    ev * 100,
                    2,
                )

        real_market_loaded = (
            self.market_quote.has_real_price
        )

        if not self.recommendation:
            self.recommendation = (
                recommendation_label(
                    self.hammer_score,
                    real_market_loaded=(
                        real_market_loaded
                    ),
                )
            )

        if (
            not self.model_recommendation
            and self.league == "MLB"
            and self.market == "moneyline"
        ):
            self.model_recommendation = self.recommendation

        if not self.confidence:
            self.confidence = confidence_label(
                self.hammer_score
            )

        if not self.stars:
            self.stars = stars_from_score(
                self.hammer_score
            )

        if (
            self.units is None
            and not (
                self.league == "MLB"
                and self.market == "moneyline"
                and is_actionable_label(
                    self.model_recommendation
                )
            )
        ):
            self.units = unit_recommendation(
                self.hammer_score,
                real_market_loaded=(
                    real_market_loaded
                ),
            )

        self.reasons = [
            str(reason)
            for reason in self.reasons
            if reason
        ]

        self.tags = list(
            dict.fromkeys(
                str(tag).lower()
                for tag in self.tags
                if tag
            )
        )

    @property
    def real_market_loaded(self) -> bool:
        return self.market_quote.has_real_price

    @property
    def actionable(self) -> bool:
        return is_actionable_label(
            self.recommendation
        )

    @property
    def ranking_score(self) -> float:
        from engine.core.ranking import (
            calculate_ranking_score,
        )

        return calculate_ranking_score(self)

    def to_dict(self) -> dict:
        return {
            "recommendation_id": (
                self.recommendation_id
            ),
            "sport": self.sport,
            "league": self.league,
            "event_id": self.event_id,
            "matchup": self.matchup,
            "event_time": self.event_time,
            "scheduled_start_at": self.scheduled_start_at,
            "market": self.market,
            "selection": self.selection,
            "model_win_strength": (
                self.model_win_strength
            ),
            "model_probability": (
                self.model_probability
            ),
            "market_probability": (
                self.market_probability
            ),
            "edge_pct": self.edge_pct,
            "expected_value_pct": (
                self.expected_value_pct
            ),
            "hammer_score": (
                round(
                    self.hammer_score,
                    1,
                )
            ),
            "ranking_score": (
                self.ranking_score
            ),
            "recommendation": (
                self.recommendation
            ),
            "model_recommendation": (
                self.model_recommendation
            ),
            "market_value_label": self.market_value_label,
            "market_value_tone": self.market_value_tone,
            "recommendation_explanation": (
                self.recommendation_explanation
            ),
            "hammer_tier": self.hammer_tier,
            "hammer_assessment": (
                self.hammer_assessment
            ),
            "model_confidence": self.model_confidence,
            "hammer_confidence": self.hammer_confidence,
            "confidence": self.confidence,
            "stars": self.stars,
            "units": self.units,
            "real_market_loaded": (
                self.real_market_loaded
            ),
            "market_quote": (
                self.market_quote.to_dict()
            ),
            "reasons": self.reasons,
            "components": self.components,
            "source_signals": (
                self.source_signals
            ),
            "tags": self.tags,
            "status": self.status,
            "pregame_eligible": self.pregame_eligible,
            "pregame_eligibility_reason": (
                self.pregame_eligibility_reason
            ),
            "pregame_eligibility": {
                "eligible": self.pregame_eligible,
                "reason": self.pregame_eligibility_reason,
            },
            "generated_at": self.generated_at,
            "actionable": self.actionable,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "Recommendation":
        return cls(
            recommendation_id=data.get(
                "recommendation_id",
                uuid4().hex,
            ),
            sport=data.get("sport", ""),
            league=data.get("league", ""),
            event_id=data.get("event_id"),
            matchup=data.get("matchup"),
            event_time=data.get("event_time"),
            scheduled_start_at=data.get(
                "scheduled_start_at"
            ),
            market=data.get("market", ""),
            selection=data.get(
                "selection",
                "",
            ),
            model_win_strength=(
                data.get("model_win_strength")
            ),
            model_probability=data.get(
                "model_probability"
            ),
            market_probability=data.get(
                "market_probability"
            ),
            edge_pct=data.get("edge_pct"),
            expected_value_pct=data.get(
                "expected_value_pct"
            ),
            hammer_score=data.get(
                "hammer_score",
                0,
            ),
            recommendation=data.get(
                "recommendation"
            ),
            model_recommendation=data.get(
                "model_recommendation"
            ),
            market_value_label=data.get(
                "market_value_label"
            ),
            market_value_tone=data.get(
                "market_value_tone"
            ),
            recommendation_explanation=data.get(
                "recommendation_explanation",
                {},
            ),
            hammer_tier=data.get("hammer_tier"),
            hammer_assessment=data.get(
                "hammer_assessment"
            ),
            model_confidence=data.get(
                "model_confidence"
            ),
            hammer_confidence=data.get(
                "hammer_confidence"
            ),
            confidence=data.get(
                "confidence"
            ),
            stars=data.get("stars"),
            units=data.get("units"),
            market_quote=(
                MarketQuote.from_dict(
                    data.get(
                        "market_quote"
                    )
                )
            ),
            reasons=data.get(
                "reasons",
                [],
            ),
            components=data.get(
                "components",
                {},
            ),
            source_signals=data.get(
                "source_signals",
                {},
            ),
            tags=data.get(
                "tags",
                [],
            ),
            status=data.get(
                "status",
                "pregame",
            ),
            pregame_eligible=data.get(
                "pregame_eligible"
            ),
            pregame_eligibility_reason=data.get(
                "pregame_eligibility_reason"
            ),
            generated_at=data.get(
                "generated_at",
                datetime.now().isoformat(
                    timespec="seconds"
                ),
            ),
        )
