from dataclasses import dataclass

from engine.mlb.bullpen.bullpen_model import (
    BullpenProjection,
)


MAX_GAME_BULLPEN_ADJUSTMENT = 2.50
MIN_GAME_BULLPEN_ADJUSTMENT = -1.25


@dataclass(frozen=True)
class GameBullpenAdjustment:
    away_team: str
    home_team: str

    away_bullpen: BullpenProjection
    home_bullpen: BullpenProjection

    away_adjustment: float
    home_adjustment: float
    combined_adjustment: float

    confidence: float
    data_quality: str
    status: str


def build_game_bullpen_adjustment(
    away_bullpen: BullpenProjection,
    home_bullpen: BullpenProjection,
) -> GameBullpenAdjustment:
    """
    Combine both team bullpen projections into one game-level
    projected-run adjustment.

    Positive adjustment:
        Raises the projected game total.

    Negative adjustment:
        Lowers the projected game total.
    """

    away_adjustment = (
        away_bullpen.total_run_adjustment
    )

    home_adjustment = (
        home_bullpen.total_run_adjustment
    )

    combined_adjustment = (
        away_adjustment
        + home_adjustment
    )

    combined_adjustment = max(
        MIN_GAME_BULLPEN_ADJUSTMENT,
        min(
            MAX_GAME_BULLPEN_ADJUSTMENT,
            combined_adjustment,
        ),
    )

    confidence = _calculate_game_confidence(
        away_bullpen=away_bullpen,
        home_bullpen=home_bullpen,
    )

    data_quality = _get_data_quality(
        confidence,
    )

    status = _get_status(
        away_bullpen=away_bullpen,
        home_bullpen=home_bullpen,
    )

    return GameBullpenAdjustment(
        away_team=away_bullpen.team,
        home_team=home_bullpen.team,
        away_bullpen=away_bullpen,
        home_bullpen=home_bullpen,
        away_adjustment=round(
            away_adjustment,
            2,
        ),
        home_adjustment=round(
            home_adjustment,
            2,
        ),
        combined_adjustment=round(
            combined_adjustment,
            2,
        ),
        confidence=confidence,
        data_quality=data_quality,
        status=status,
    )


def apply_bullpen_adjustment(
    starter_based_total: float,
    bullpen_adjustment: GameBullpenAdjustment,
) -> float:
    """
    Apply the game bullpen adjustment to a starter-based
    projected total.
    """

    adjusted_total = (
        starter_based_total
        + bullpen_adjustment.combined_adjustment
    )

    return round(
        max(0.0, adjusted_total),
        2,
    )


def _calculate_game_confidence(
    away_bullpen: BullpenProjection,
    home_bullpen: BullpenProjection,
) -> float:
    confidence = (
        away_bullpen.confidence
        + home_bullpen.confidence
    ) / 2.0

    return round(
        max(0.0, min(100.0, confidence)),
        1,
    )


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


def _get_status(
    away_bullpen: BullpenProjection,
    home_bullpen: BullpenProjection,
) -> str:
    if (
        away_bullpen.status == "AVAILABLE"
        and home_bullpen.status == "AVAILABLE"
    ):
        return "AVAILABLE"

    if (
        away_bullpen.status == "PARTIAL"
        or home_bullpen.status == "PARTIAL"
    ):
        return "PARTIAL"

    return "UNAVAILABLE"
