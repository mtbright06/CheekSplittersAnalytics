from dataclasses import dataclass
from typing import Any

from engine.mlb.bullpen.fatigue import (
    FatigueResult,
    calculate_fatigue,
)
from engine.mlb.bullpen.quality import (
    BullpenQualityResult,
    calculate_bullpen_quality,
)


CLOSER_UNAVAILABLE_ADJUSTMENT = 0.08
SETUP_UNAVAILABLE_ADJUSTMENT = 0.05


@dataclass(frozen=True)
class BullpenProjection:
    team: str

    fatigue: FatigueResult
    quality: BullpenQualityResult

    closer_available: bool
    setup_available: bool

    quality_adjustment: float
    fatigue_adjustment: float
    availability_adjustment: float
    total_run_adjustment: float

    confidence: float
    data_quality: str
    status: str


def build_bullpen_projection(
    team: str,
    season_era: float | None,
    season_whip: float | None,
    last7_era: float | None,
    innings_last3: float,
    innings_last7: float | None = None,
    innings_last5: float | None = None,
    evidence_ledger: list[dict[str, Any]] | None = None,
    closer_available: bool = True,
    setup_available: bool = True,
    league_baselines: dict[str, Any] | None = None,
) -> BullpenProjection:
    """
    Build one team's bullpen projection.

    The returned total_run_adjustment represents the estimated
    scoring impact attributable to this bullpen.
    """

    high_leverage_concerns = _high_leverage_workload_concerns(
        evidence_ledger or []
    )

    fatigue = calculate_fatigue(
        innings_last3,
        innings_last5=innings_last5,
        high_leverage_concerns=high_leverage_concerns,
    )

    quality = calculate_bullpen_quality(
        season_era=season_era,
        season_whip=season_whip,
        last7_era=last7_era,
        innings_last7=innings_last7,
        league_baselines=league_baselines,
    )

    availability_adjustment = 0.0

    if not closer_available:
        availability_adjustment += (
            CLOSER_UNAVAILABLE_ADJUSTMENT
        )

    if not setup_available:
        availability_adjustment += (
            SETUP_UNAVAILABLE_ADJUSTMENT
        )

    quality_adjustment = quality.run_adjustment
    fatigue_adjustment = fatigue.fatigue_score

    total_run_adjustment = (
        quality_adjustment
        + fatigue_adjustment
        + availability_adjustment
    )

    total_run_adjustment = max(
        -0.55,
        min(0.85, total_run_adjustment),
    )

    confidence = _calculate_confidence(
        quality=quality,
        closer_available=closer_available,
        setup_available=setup_available,
    )

    data_quality = _get_data_quality(confidence)

    status = (
        "AVAILABLE"
        if quality.available
        else "PARTIAL"
    )

    return BullpenProjection(
        team=team.upper(),
        fatigue=fatigue,
        quality=quality,
        closer_available=closer_available,
        setup_available=setup_available,
        quality_adjustment=round(
            quality_adjustment,
            2,
        ),
        fatigue_adjustment=round(
            fatigue_adjustment,
            2,
        ),
        availability_adjustment=round(
            availability_adjustment,
            2,
        ),
        total_run_adjustment=round(
            total_run_adjustment,
            2,
        ),
        confidence=confidence,
        data_quality=data_quality,
        status=status,
    )


def _calculate_confidence(
    quality: BullpenQualityResult,
    closer_available: bool,
    setup_available: bool,
) -> float:
    confidence = 45.0

    if quality.season_era is not None:
        confidence += 18.0

    if quality.season_whip is not None:
        confidence += 15.0

    if quality.last7_era is not None:
        confidence += 12.0

    if quality.available:
        confidence += 5.0

    if not closer_available:
        confidence -= 2.0

    if not setup_available:
        confidence -= 2.0

    confidence = max(
        0.0,
        min(100.0, confidence),
    )

    return round(confidence, 1)


def _get_data_quality(
    confidence: float,
) -> str:
    if confidence >= 90.0:
        return "EXCELLENT"

    if confidence >= 75.0:
        return "GOOD"

    if confidence >= 55.0:
        return "FAIR"

    return "LIMITED"


def _high_leverage_workload_concerns(
    evidence_ledger: list[dict[str, Any]],
) -> int:
    concerns = 0

    for entry in evidence_ledger:
        availability = entry.get("availability_evidence")
        if not isinstance(availability, dict):
            continue

        if availability.get("status") != "OBSERVED_WORKLOAD_CONCERN":
            continue

        if availability.get("confidence") != "HIGH":
            continue

        role = _primary_role(entry)
        if role in {"CLOSER", "SETUP", "GAME_FINISHER"}:
            concerns += 1

    return concerns


def _primary_role(
    entry: dict[str, Any],
) -> str | None:
    role_evidence = entry.get("role_evidence")
    if not isinstance(role_evidence, dict):
        return None

    candidates = role_evidence.get("candidate_roles")
    if not isinstance(candidates, list) or not candidates:
        return None

    first = candidates[0]
    if not isinstance(first, dict):
        return None

    return first.get("role")
