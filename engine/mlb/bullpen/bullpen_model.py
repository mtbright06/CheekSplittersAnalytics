from dataclasses import dataclass

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
    closer_available: bool = True,
    setup_available: bool = True,
) -> BullpenProjection:
    """
    Build one team's bullpen projection.

    The returned total_run_adjustment represents the estimated
    scoring impact attributable to this bullpen.
    """

    fatigue = calculate_fatigue(innings_last3)

    quality = calculate_bullpen_quality(
        season_era=season_era,
        season_whip=season_whip,
        last7_era=last7_era,
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
        -0.50,
        min(0.75, total_run_adjustment),
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
