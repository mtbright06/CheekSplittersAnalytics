from dataclasses import dataclass


LEAGUE_AVG_ERA = 4.10
LEAGUE_AVG_WHIP = 1.30


@dataclass(frozen=True)
class BullpenQualityResult:
    season_era: float | None
    season_whip: float | None
    last7_era: float | None

    quality_score: float
    run_adjustment: float
    rating: str

    available: bool
    source: str


def calculate_bullpen_quality(
    season_era: float | None,
    season_whip: float | None,
    last7_era: float | None,
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
            quality_score=50.0,
            run_adjustment=0.0,
            rating="UNKNOWN",
            available=False,
            source="NEUTRAL_FALLBACK",
        )

    era = (
        season_era
        if season_era is not None
        else LEAGUE_AVG_ERA
    )

    whip = (
        season_whip
        if season_whip is not None
        else LEAGUE_AVG_WHIP
    )

    recent_era = (
        last7_era
        if last7_era is not None
        else era
    )

    era_component = (
        (LEAGUE_AVG_ERA - era) / LEAGUE_AVG_ERA
    )

    whip_component = (
        (LEAGUE_AVG_WHIP - whip) / LEAGUE_AVG_WHIP
    )

    recent_component = (
        (LEAGUE_AVG_ERA - recent_era) / LEAGUE_AVG_ERA
    )

    weighted_quality = (
        era_component * 0.50
        + whip_component * 0.25
        + recent_component * 0.25
    )

    quality_score = 50.0 + (weighted_quality * 100.0)

    quality_score = max(
        0.0,
        min(100.0, quality_score),
    )

    run_adjustment = -weighted_quality * 0.60

    run_adjustment = max(
    -0.35,
    min(0.35, run_adjustment),
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
        quality_score=round(quality_score, 1),
        run_adjustment=round(run_adjustment, 2),
        rating=rating,
        available=True,
        source="INPUT_METRICS",
    )
