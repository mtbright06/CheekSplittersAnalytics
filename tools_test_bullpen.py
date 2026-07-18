from engine.mlb.bullpen.bullpen_model import (
    BullpenProjection,
    build_bullpen_projection,
)
from engine.mlb.bullpen.game_adjustment import (
    GameBullpenAdjustment,
    apply_bullpen_adjustment,
    build_game_bullpen_adjustment,
)


def print_projection(
    projection: BullpenProjection,
) -> None:
    print()
    print("=" * 64)
    print(
        f"SHARPSTACK BULLPEN INTELLIGENCE: "
        f"{projection.team}"
    )
    print("=" * 64)

    print()
    print("QUALITY")
    print("-" * 64)
    print(
        f"Rating:                    "
        f"{projection.quality.rating}"
    )
    print(
        f"Quality score:              "
        f"{projection.quality.quality_score:.1f}"
    )
    print(
        f"Season ERA:                 "
        f"{projection.quality.season_era}"
    )
    print(
        f"Season WHIP:                "
        f"{projection.quality.season_whip}"
    )
    print(
        f"Last-7 ERA:                 "
        f"{projection.quality.last7_era}"
    )

    print()
    print("USAGE AND AVAILABILITY")
    print("-" * 64)
    print(
        f"Innings last 3 days:        "
        f"{projection.fatigue.innings_last3:.1f}"
    )
    print(
        f"Fatigue rating:             "
        f"{projection.fatigue.rating}"
    )
    print(
        f"Closer available:           "
        f"{projection.closer_available}"
    )
    print(
        f"Setup reliever available:   "
        f"{projection.setup_available}"
    )

    print()
    print("RUN ADJUSTMENTS")
    print("-" * 64)
    print(
        f"Quality adjustment:         "
        f"{projection.quality_adjustment:+.2f}"
    )
    print(
        f"Fatigue adjustment:         "
        f"{projection.fatigue_adjustment:+.2f}"
    )
    print(
        f"Availability adjustment:    "
        f"{projection.availability_adjustment:+.2f}"
    )
    print(
        f"Total bullpen adjustment:   "
        f"{projection.total_run_adjustment:+.2f}"
    )

    print()
    print("MODEL QUALITY")
    print("-" * 64)
    print(
        f"Confidence:                 "
        f"{projection.confidence:.1f}"
    )
    print(
        f"Data quality:               "
        f"{projection.data_quality}"
    )
    print(
        f"Status:                     "
        f"{projection.status}"
    )


def print_game_adjustment(
    adjustment: GameBullpenAdjustment,
    starter_based_total: float,
) -> None:
    final_total = apply_bullpen_adjustment(
        starter_based_total=starter_based_total,
        bullpen_adjustment=adjustment,
    )

    print()
    print("=" * 64)
    print("SHARPSTACK GAME BULLPEN IMPACT")
    print("=" * 64)

    print()
    print(
        f"Matchup:                    "
        f"{adjustment.away_team} @ "
        f"{adjustment.home_team}"
    )

    print()
    print("BULLPEN ADJUSTMENTS")
    print("-" * 64)
    print(
        f"Away bullpen adjustment:    "
        f"{adjustment.away_adjustment:+.2f}"
    )
    print(
        f"Home bullpen adjustment:    "
        f"{adjustment.home_adjustment:+.2f}"
    )
    print(
        f"Combined adjustment:        "
        f"{adjustment.combined_adjustment:+.2f}"
    )

    print()
    print("TOTALS IMPACT")
    print("-" * 64)
    print(
        f"Starter-based total:        "
        f"{starter_based_total:.2f}"
    )
    print(
        f"Bullpen adjustment:         "
        f"{adjustment.combined_adjustment:+.2f}"
    )
    print(
        f"Final projected total:      "
        f"{final_total:.2f}"
    )

    print()
    print("MODEL QUALITY")
    print("-" * 64)
    print(
        f"Confidence:                 "
        f"{adjustment.confidence:.1f}"
    )
    print(
        f"Data quality:               "
        f"{adjustment.data_quality}"
    )
    print(
        f"Status:                     "
        f"{adjustment.status}"
    )


def validate_projection(
    projection: BullpenProjection,
) -> None:
    assert projection.team
    assert 0.0 <= projection.confidence <= 100.0

    assert (
        -0.75
        <= projection.total_run_adjustment
        <= 1.75
    )


def validate_neutral_fallback() -> None:
    projection = build_bullpen_projection(
        team="TST",
        season_era=None,
        season_whip=None,
        last7_era=None,
        innings_last3=6.0,
    )

    assert projection.quality.rating == "UNKNOWN"
    assert projection.quality.run_adjustment == 0.0
    assert projection.status == "PARTIAL"


def validate_availability_adjustment() -> None:
    fully_available = build_bullpen_projection(
        team="AAA",
        season_era=4.10,
        season_whip=1.30,
        last7_era=4.10,
        innings_last3=7.0,
        closer_available=True,
        setup_available=True,
    )

    unavailable = build_bullpen_projection(
        team="AAA",
        season_era=4.10,
        season_whip=1.30,
        last7_era=4.10,
        innings_last3=7.0,
        closer_available=False,
        setup_available=False,
    )

    assert (
        unavailable.availability_adjustment
        >
        fully_available.availability_adjustment
    )

    assert (
        unavailable.total_run_adjustment
        >
        fully_available.total_run_adjustment
    )


def validate_quality_direction() -> None:
    strong = build_bullpen_projection(
        team="STR",
        season_era=3.10,
        season_whip=1.12,
        last7_era=2.80,
        innings_last3=5.0,
    )

    weak = build_bullpen_projection(
        team="WEK",
        season_era=5.10,
        season_whip=1.48,
        last7_era=5.70,
        innings_last3=5.0,
    )

    assert strong.quality_adjustment < 0.0
    assert weak.quality_adjustment > 0.0

    assert (
        strong.total_run_adjustment
        <
        weak.total_run_adjustment
    )


def validate_game_adjustment(
    adjustment: GameBullpenAdjustment,
    starter_based_total: float,
) -> None:
    expected_combined = round(
        adjustment.away_adjustment
        + adjustment.home_adjustment,
        2,
    )

    expected_combined = max(
        -1.25,
        min(2.50, expected_combined),
    )

    assert (
        adjustment.combined_adjustment
        == expected_combined
    )

    final_total = apply_bullpen_adjustment(
        starter_based_total=starter_based_total,
        bullpen_adjustment=adjustment,
    )

    assert final_total == round(
        starter_based_total
        + adjustment.combined_adjustment,
        2,
    )

    assert 0.0 <= adjustment.confidence <= 100.0


def main() -> None:
    away_bullpen = build_bullpen_projection(
        team="SEA",
        season_era=3.42,
        season_whip=1.18,
        last7_era=2.95,
        innings_last3=5.2,
        closer_available=True,
        setup_available=True,
    )

    home_bullpen = build_bullpen_projection(
        team="NYY",
        season_era=4.72,
        season_whip=1.41,
        last7_era=5.35,
        innings_last3=15.1,
        closer_available=False,
        setup_available=False,
    )

    game_adjustment = build_game_bullpen_adjustment(
        away_bullpen=away_bullpen,
        home_bullpen=home_bullpen,
    )

    starter_based_total = 8.69

    print_projection(away_bullpen)
    print_projection(home_bullpen)

    print_game_adjustment(
        adjustment=game_adjustment,
        starter_based_total=starter_based_total,
    )

    validate_projection(away_bullpen)
    validate_projection(home_bullpen)

    validate_neutral_fallback()
    validate_availability_adjustment()
    validate_quality_direction()

    validate_game_adjustment(
        adjustment=game_adjustment,
        starter_based_total=starter_based_total,
    )

    print()
    print("=" * 64)
    print(
        "PASSED: Team bullpen intelligence and game-level "
        "totals adjustment behaved as expected."
    )
    print("=" * 64)


if __name__ == "__main__":
    main()
