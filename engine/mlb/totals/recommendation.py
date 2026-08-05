from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.core.pregame_eligibility import PregameEligibilityReason
from engine.mlb.totals.helpers import clamp


LEAN_EDGE = 0.40
BET_EDGE = 0.75
STRONG_BET_EDGE = 1.25


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

    edge_score: float
    model_confidence_score: float
    data_quality_score: float
    bullpen_confidence_score: float
    market_quality_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection": self.selection,
            "recommendation": self.recommendation,
            "recommendation_score": round(
                self.recommendation_score,
                1,
            ),
            "confidence": self.confidence,
            "stars": self.stars,
            "actionable": self.actionable,
            "score_components": {
                "edge": round(self.edge_score, 1),
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
                "market_quality": round(
                    self.market_quality_score,
                    1,
                ),
            },
        }


def score_edge(
    absolute_edge: float | None,
) -> float:
    """
    Translate run edge into a 0-100 score.

    Examples:
        0.40 runs -> 52
        0.75 runs -> 62.5
        1.25 runs -> 77.5
        2.00 runs -> 100
    """

    if absolute_edge is None:
        return 0.0

    return clamp(
        40.0 + (absolute_edge * 30.0),
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


def score_market_quality(
    *,
    market_available: bool,
    real_market_loaded: bool,
    stale: bool,
    over_odds: Any = None,
    under_odds: Any = None,
) -> float:
    if not market_available:
        return 0.0

    score = 65.0

    if real_market_loaded:
        score += 20.0

    if over_odds is not None and under_odds is not None:
        score += 10.0

    if stale:
        score -= 25.0
    else:
        score += 5.0

    return clamp(
        score,
        0.0,
        100.0,
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


def recommendation_label(
    *,
    direction: str,
    absolute_edge: float | None,
    recommendation_score: float,
    market_available: bool,
) -> tuple[str, str, bool]:
    if (
        not market_available
        or absolute_edge is None
        or direction not in {"OVER", "UNDER"}
    ):
        return (
            "NONE",
            "PASS",
            False,
        )

    selection = direction

    if (
        absolute_edge >= STRONG_BET_EDGE
        and recommendation_score >= 82
    ):
        return (
            selection,
            f"STRONG BET {selection}",
            True,
        )

    if (
        absolute_edge >= BET_EDGE
        and recommendation_score >= 72
    ):
        return (
            selection,
            f"BET {selection}",
            True,
        )

    if (
        absolute_edge >= LEAN_EDGE
        and recommendation_score >= 64
    ):
        return (
            selection,
            f"LEAN {selection}",
            True,
        )

    return (
        selection,
        "PASS",
        False,
    )


def build_totals_recommendation(
    *,
    direction: str,
    absolute_edge: float | None,
    model_confidence: float,
    data_quality: str,
    bullpen_confidence: float,
    market_payload: dict[str, Any] | None,
) -> TotalsRecommendation:
    market_payload = market_payload or {}

    market_available = bool(
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
        market_available = False
        absolute_edge = None

    edge_component = score_edge(
        absolute_edge
    )

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

    market_component = score_market_quality(
        market_available=market_available,
        real_market_loaded=bool(
            market_payload.get("real_market_loaded")
        ),
        stale=bool(
            market_payload.get("stale", True)
        ),
        over_odds=market_payload.get("over_odds"),
        under_odds=market_payload.get("under_odds"),
    )

    if not market_available:
        recommendation_score = 0.0
    else:
        recommendation_score = (
            edge_component * 0.45
            + model_component * 0.20
            + data_component * 0.15
            + bullpen_component * 0.10
            + market_component * 0.10
        )

    recommendation_score = clamp(
        recommendation_score,
        0.0,
        100.0,
    )

    (
        selection,
        recommendation,
        actionable,
    ) = recommendation_label(
        direction=direction,
        absolute_edge=absolute_edge,
        recommendation_score=recommendation_score,
        market_available=market_available,
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
        edge_score=edge_component,
        model_confidence_score=model_component,
        data_quality_score=data_component,
        bullpen_confidence_score=bullpen_component,
        market_quality_score=market_component,
    )
