from dataclasses import dataclass
from typing import Any


LEAGUE_AVG_ERA = 4.10
LEAGUE_AVG_WHIP = 1.30


def _baseline_value(
    league_baselines: dict[str, Any] | None,
    key: str,
    fallback: float,
) -> float:
    bullpen_baselines = (league_baselines or {}).get("bullpen", {})
    try:
        value = float(bullpen_baselines.get(key))
    except (TypeError, ValueError):
        return fallback
    if value <= 0:
        return fallback
    return value


@dataclass(frozen=True)
class BullpenQualityResult:
    season_era: float | None
    season_whip: float | None
    last7_era: float | None
    stabilized_last7_era: float | None
    last7_sample_weight: float

    quality_score: float
    run_adjustment: float
    rating: str

    available: bool
    source: str


def calculate_bullpen_quality(
    season_era: float | None,
    season_whip: float | None,
    last7_era: float | None,
    innings_last7: float | None = None,
    *,
    league_baselines: dict[str, Any] | None = None,
) -> BullpenQualityResult:
    """
    Evaluate overall bullpen quality.

    A positive run_adjustment means the bullpen is expected to
    increase scoring.

    A negative run_adjustment means the bullpen is expected to
    suppress scoring.
    """

    if season_era is None and season_whip is None:
        return BullpenQualityResult(
            season_era=season_era,
            season_whip=season_whip,
            last7_era=last7_era,
            stabilized_last7_era=None,
            last7_sample_weight=0.0,
            quality_score=50.0,
            run_adjustment=0.0,
            rating="UNKNOWN",
            available=False,
            source="NEUTRAL_FALLBACK",
        )

    league_avg_era = _baseline_value(
        league_baselines,
        "era",
        LEAGUE_AVG_ERA,
    )
    league_avg_whip = _baseline_value(
        league_baselines,
        "whip",
        LEAGUE_AVG_WHIP,
    )

    era = (
        season_era
        if season_era is not None
        else league_avg_era
    )

    whip = (
        season_whip
        if season_whip is not None
        else league_avg_whip
    )

    last7_sample_weight = _recent_sample_weight(
        innings_last7,
    )

    stabilized_recent_era = None
    if last7_era is not None and last7_sample_weight > 0:
        stabilized_recent_era = (
            (last7_era * last7_sample_weight)
            + (era * (1.0 - last7_sample_weight))
        )

    era_component = (
        (league_avg_era - era) / league_avg_era
    )

    whip_component = (
        (league_avg_whip - whip) / league_avg_whip
    )

    recent_component = None
    if stabilized_recent_era is not None:
        recent_component = (
            (league_avg_era - stabilized_recent_era) / league_avg_era
        )

    components = {
        "season_era": era_component,
        "season_whip": whip_component,
        "recent_era": recent_component,
    }
    weights = {
        "season_era": 0.55,
        "season_whip": 0.30,
        "recent_era": 0.15,
    }
    active_weight = sum(
        weight
        for name, weight in weights.items()
        if components[name] is not None
    )
    weighted_quality = sum(
        components[name] * weight
        for name, weight in weights.items()
        if components[name] is not None
    ) / active_weight

    quality_score = 50.0 + (weighted_quality * 100.0)

    quality_score = max(
        0.0,
        min(100.0, quality_score),
    )

    run_adjustment = -weighted_quality * 0.75

    run_adjustment = max(
        -0.45,
        min(0.45, run_adjustment),
    )

    if quality_score >= 65.0:
        rating = "ELITE"
    elif quality_score >= 55.0:
        rating = "STRONG"
    elif quality_score >= 45.0:
        rating = "AVERAGE"
    elif quality_score >= 35.0:
        rating = "WEAK"
    else:
        rating = "POOR"

    return BullpenQualityResult(
        season_era=season_era,
        season_whip=season_whip,
        last7_era=last7_era,
        stabilized_last7_era=(
            round(stabilized_recent_era, 2)
            if stabilized_recent_era is not None
            else None
        ),
        last7_sample_weight=round(last7_sample_weight, 3),
        quality_score=round(quality_score, 1),
        run_adjustment=round(run_adjustment, 2),
        rating=rating,
        available=True,
        source="INPUT_METRICS",
    )


def _recent_sample_weight(
    innings_last7: float | None,
) -> float:
    try:
        innings = float(innings_last7)
    except (TypeError, ValueError):
        return 0.0

    if innings <= 0:
        return 0.0

    return max(
        0.0,
        min(
            0.60,
            innings / 24.0,
        ),
    )
