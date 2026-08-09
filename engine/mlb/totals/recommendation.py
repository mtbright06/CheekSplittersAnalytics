from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.core.pregame_eligibility import PregameEligibilityReason
from engine.mlb.totals.helpers import clamp


LEAN_SEPARATION = 0.40
BET_SEPARATION = 0.75
STRONG_BET_SEPARATION = 1.25


DATA_QUALITY_SCORES = {
    "EXCELLENT": 95.0,
    "GOOD": 82.0,
    "FAIR": 68.0,
    "LIMITED": 50.0,
}


@dataclass(frozen=True)
class TotalsRecommendation:
    selection: str
    recommendation: str
    recommendation_score: float
    confidence: str
    stars: str
    actionable: bool

    model_separation_score: float
    model_confidence_score: float
    data_quality_score: float
    bullpen_confidence_score: float
    reliability_score: float
    reliability_tier_cap: str
    reliability_concerns: list[str]
    base_recommendation: str
    changed_by_reliability: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection": self.selection,
            "recommendation": self.recommendation,
            "recommendation_score": round(
                self.recommendation_score,
                1,
            ),
            "confidence": self.confidence,
            "reliability": round(
                self.reliability_score,
                1,
            ),
            "reliability_tier_cap": self.reliability_tier_cap,
            "reliability_concerns": self.reliability_concerns,
            "base_recommendation": self.base_recommendation,
            "changed_by_reliability": self.changed_by_reliability,
            "stars": self.stars,
            "actionable": self.actionable,
            "score_components": {
                "model_separation": round(
                    self.model_separation_score,
                    1,
                ),
                "model_confidence": round(
                    self.model_confidence_score,
                    1,
                ),
                "data_quality": round(
                    self.data_quality_score,
                    1,
                ),
                "bullpen_confidence": round(
                    self.bullpen_confidence_score,
                    1,
                ),
                "reliability": round(
                    self.reliability_score,
                    1,
                ),
            },
        }


def score_model_separation(
    model_separation: float | None,
) -> float:
    """
    Translate model distance from the total line into a 0-100 score.

    Examples:
        0.40 runs -> 52
        0.75 runs -> 62.5
        1.25 runs -> 77.5
        2.00 runs -> 100
    """

    if model_separation is None:
        return 0.0

    return clamp(
        40.0 + (model_separation * 30.0),
        0.0,
        100.0,
    )


def score_data_quality(
    data_quality: str,
) -> float:
    return DATA_QUALITY_SCORES.get(
        str(data_quality or "").upper(),
        50.0,
    )


def confidence_label(
    score: float,
) -> str:
    if score >= 88:
        return "VERY HIGH"

    if score >= 78:
        return "HIGH"

    if score >= 68:
        return "MODERATE"

    if score >= 58:
        return "LOW"

    return "PASS"


def stars_from_score(
    score: float,
) -> str:
    if score >= 90:
        return "★★★★★"

    if score >= 82:
        return "★★★★½"

    if score >= 74:
        return "★★★★"

    if score >= 66:
        return "★★★½"

    if score >= 58:
        return "★★★"

    return "★★"


TIER_RANKS = {
    "PASS": 0,
    "LEAN": 1,
    "BET": 2,
    "STRONG BET": 3,
}


def reliability_tier_cap(
    reliability: float,
) -> str:
    if reliability < 55:
        return "PASS"
    if reliability < 70:
        return "LEAN"
    if reliability < 82:
        return "BET"
    return "STRONG BET"


def apply_reliability_cap(
    tier: str,
    cap: str,
) -> str:
    if TIER_RANKS.get(tier, 0) <= TIER_RANKS.get(cap, 3):
        return tier

    for label, rank in TIER_RANKS.items():
        if rank == TIER_RANKS.get(cap, 3):
            return label

    return "PASS"


def tier_from_separation(
    model_separation: float | None,
) -> str:
    if model_separation is None:
        return "PASS"
    if model_separation >= STRONG_BET_SEPARATION:
        return "STRONG BET"
    if model_separation >= BET_SEPARATION:
        return "BET"
    if model_separation >= LEAN_SEPARATION:
        return "LEAN"
    return "PASS"


def recommendation_label(
    *,
    direction: str,
    model_separation: float | None,
    line_available: bool,
    reliability: float,
) -> tuple[str, str, bool]:
    if (
        not line_available
        or model_separation is None
        or direction not in {"OVER", "UNDER"}
    ):
        return (
            "NONE",
            "PASS",
            False,
        )

    selection = direction
    base_tier = tier_from_separation(model_separation)
    final_tier = apply_reliability_cap(
        base_tier,
        reliability_tier_cap(reliability),
    )

    if final_tier == "PASS":
        return (
            selection,
            "PASS",
            False,
        )

    return (
        selection,
        f"{final_tier} {selection}",
        True,
    )


def build_totals_recommendation(
    *,
    direction: str,
    model_separation: float | None = None,
    absolute_edge: float | None = None,
    model_confidence: float,
    data_quality: str,
    bullpen_confidence: float,
    market_payload: dict[str, Any] | None,
    reliability: float | None = None,
    reliability_concerns: list[str] | None = None,
) -> TotalsRecommendation:
    market_payload = market_payload or {}
    if model_separation is None:
        model_separation = absolute_edge

    line_available = bool(
        market_payload.get("available")
        and market_payload.get("line") is not None
    )

    pregame_verified = (
        market_payload.get("pregame_eligible") is True
        and str(
            market_payload.get("pregame_eligibility_reason")
            or ""
        )
        == PregameEligibilityReason.GAME_NOT_STARTED.value
    )

    if not pregame_verified:
        line_available = False
        model_separation = None

    separation_component = score_model_separation(
        model_separation
    )

    reliability_value = clamp(
        model_confidence if reliability is None else reliability,
        0.0,
        100.0,
    )
    reliability_concerns = reliability_concerns or []

    model_component = clamp(
        model_confidence,
        0.0,
        100.0,
    )

    data_component = score_data_quality(
        data_quality
    )

    bullpen_component = clamp(
        bullpen_confidence,
        0.0,
        100.0,
    )

    if not line_available:
        recommendation_score = 0.0
    else:
        # Compatibility/display score only. Official authority is separation
        # tier capped by reliability below.
        recommendation_score = separation_component

    recommendation_score = clamp(
        recommendation_score,
        0.0,
        100.0,
    )

    base_tier = (
        tier_from_separation(model_separation)
        if line_available
        else "PASS"
    )
    cap = reliability_tier_cap(reliability_value)
    final_tier = apply_reliability_cap(
        base_tier,
        cap,
    )

    (
        selection,
        recommendation,
        actionable,
    ) = recommendation_label(
        direction=direction,
        model_separation=model_separation,
        line_available=line_available,
        reliability=reliability_value,
    )

    return TotalsRecommendation(
        selection=selection,
        recommendation=recommendation,
        recommendation_score=recommendation_score,
        confidence=confidence_label(
            recommendation_score
        ),
        stars=stars_from_score(
            recommendation_score
        ),
        actionable=actionable,
        model_separation_score=separation_component,
        model_confidence_score=model_component,
        data_quality_score=data_component,
        bullpen_confidence_score=bullpen_component,
        reliability_score=reliability_value,
        reliability_tier_cap=cap,
        reliability_concerns=reliability_concerns,
        base_recommendation=(
            "PASS"
            if base_tier == "PASS" or direction not in {"OVER", "UNDER"}
            else f"{base_tier} {direction}"
        ),
        changed_by_reliability=final_tier != base_tier,
    )
