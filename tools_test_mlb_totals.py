from __future__ import annotations

from typing import Any

from engine.mlb.totals.market import (
    MarketTotal,
    evaluate_market_edge,
)
from engine.mlb.totals.totals_model import (
    build_totals_projection,
)
from engine.reports.totals_console import (
    print_totals_report,
)


def build_test_game() -> dict[str, Any]:
    """
    Build a complete synthetic MLB game for validating
    the bullpen-integrated totals projection engine.

    Seattle is used as the home club so the test confirms
    that a run-suppressing park factor is applied.
    """

    return {
        "market_total": 8.0,
        "teams": {
            "away": {
                "name": "New York Yankees",
                "abbreviation": "NYY",
                "offense": {
                    "runs_per_game": 4.95,
                    "wrc_plus": 112,
                    "ops": 0.748,
                },
            },
            "home": {
                "name": "Seattle Mariners",
                "abbreviation": "SEA",
                "offense": {
                    "runs_per_game": 4.20,
                    "wrc_plus": 98,
                    "ops": 0.708,
                },
            },
        },
        "pitching": {
            "away": {
                "name": "Away Starter",
                "era": 3.85,
                "whip": 1.22,
                "hr9": 1.05,
            },
            "home": {
                "name": "Home Starter",
                "era": 4.60,
                "whip": 1.34,
                "hr9": 1.28,
            },
        },
        "bullpen": {
            "away": {
                "season_era": 3.42,
                "season_whip": 1.18,
                "last7_era": 2.95,
                "innings_last3": 5.2,
                "closer_available": True,
                "setup_available": True,
            },
            "home": {
                "season_era": 4.72,
                "season_whip": 1.41,
                "last7_era": 5.35,
                "innings_last3": 15.1,
                "closer_available": False,
                "setup_available": False,
            },
        },
    }


def build_unknown_park_game() -> dict[str, Any]:
    """
    Build a game with an unrecognized home club to confirm
    that neutral park and bullpen fallbacks behave safely.
    """

    return {
        "teams": {
            "away": {
                "name": "Away Test Club",
                "abbreviation": "NYY",
                "offense": {
                    "runs_per_game": 4.45,
                },
            },
            "home": {
                "name": "Unknown Test Club",
                "abbreviation": "XYZ",
                "offense": {
                    "runs_per_game": 4.45,
                },
            },
        },
        "pitching": {
            "away": {
                "era": 4.20,
            },
            "home": {
                "era": 4.20,
            },
        },
    }


def validate_primary_projection(
    result: dict[str, Any],
) -> None:
    park = result["park"]
    away_projection = result["away_projection"]
    home_projection = result["home_projection"]
    away_bullpen = result["away_bullpen"]
    home_bullpen = result["home_bullpen"]
    bullpen = result["bullpen"]

    assert result["away_expected_runs"] > 0
    assert result["home_expected_runs"] > 0
    assert result["starter_based_total"] > 0
    assert result["projected_total"] > 0

    assert result["starter_based_total"] == round(
        result["away_expected_runs"]
        + result["home_expected_runs"],
        2,
    )

    assert result["projected_total"] == round(
        result["starter_based_total"]
        + result["bullpen_adjustment"],
        2,
    )

    assert result["bullpen_adjustment"] == (
        bullpen["combined_adjustment"]
    )

    assert bullpen["combined_adjustment"] == round(
        bullpen["away_adjustment"]
        + bullpen["home_adjustment"],
        2,
    )

    assert away_bullpen["team"]
    assert home_bullpen["team"]

    assert (
        away_bullpen["total_run_adjustment"]
        == bullpen["away_adjustment"]
    )

    assert (
        home_bullpen["total_run_adjustment"]
        == bullpen["home_adjustment"]
    )

    assert away_bullpen["status"] == "AVAILABLE"
    assert home_bullpen["status"] == "AVAILABLE"
    assert bullpen["status"] == "AVAILABLE"

    assert 0.0 <= bullpen["confidence"] <= 100.0

    assert bullpen["data_quality"] in {
        "LIMITED",
        "FAIR",
        "GOOD",
        "EXCELLENT",
    }

    assert 40.0 <= result["confidence"] <= 78.0

    assert result["data_quality"] in {
        "LIMITED",
        "FAIR",
        "GOOD",
        "EXCELLENT",
    }

    assert result["market_total"] == 8.0
    assert result["market_status"] == "AVAILABLE"

    assert result["edge"] == round(
        result["projected_total"]
        - result["market_total"],
        2,
    )

    assert result["absolute_edge"] == abs(
        result["edge"]
    )

    assert result["direction"] == "OVER"

    assert result["recommendation"] in {
        "LEAN OVER",
        "BET OVER",
        "STRONG BET OVER",
    }

    assert park["team"] == "SEA"
    assert park["factor"] == 0.94
    assert park["source"] == "STATIC_V1"
    assert park["available"] is True

    assert (
        away_projection["park_factor"]
        == park["factor"]
    )

    assert (
        home_projection["park_factor"]
        == park["factor"]
    )

    assert away_projection["park_adjustment"] < 0
    assert home_projection["park_adjustment"] < 0
    assert home_projection["home_adjustment"] > 0


def validate_neutral_fallback() -> None:
    result = build_totals_projection(
        build_unknown_park_game()
    )

    park = result["park"]
    away_bullpen = result["away_bullpen"]
    home_bullpen = result["home_bullpen"]
    bullpen = result["bullpen"]

    assert park["team"] == "UNKNOWN"
    assert park["factor"] == 1.0
    assert park["source"] == "NEUTRAL_FALLBACK"
    assert park["available"] is False

    assert (
        result["away_projection"][
            "park_adjustment"
        ]
        == 0.0
    )

    assert (
        result["home_projection"][
            "park_adjustment"
        ]
        == 0.0
    )

    assert away_bullpen["quality_rating"] == "UNKNOWN"
    assert home_bullpen["quality_rating"] == "UNKNOWN"

    assert away_bullpen["status"] == "PARTIAL"
    assert home_bullpen["status"] == "PARTIAL"
    assert bullpen["status"] == "PARTIAL"

    assert result["bullpen_adjustment"] == 0.0

    assert result["projected_total"] == (
        result["starter_based_total"]
    )


def validate_missing_market() -> None:
    game = build_test_game()

    game.pop(
        "market_total",
        None,
    )

    result = build_totals_projection(
        game
    )

    assert result["market_total"] is None
    assert result["edge"] is None
    assert result["absolute_edge"] is None
    assert result["direction"] == "NONE"
    assert result["market_status"] == "MODEL_ONLY"
    assert result["recommendation"] == "NO MARKET LINE"


def validate_recommendation_thresholds() -> None:
    pass_result = evaluate_market_edge(
        model_total=8.30,
        market_total=MarketTotal(
            total=8.00,
            available=True,
            source="TEST",
        ),
    )

    lean_result = evaluate_market_edge(
        model_total=8.60,
        market_total=MarketTotal(
            total=8.00,
            available=True,
            source="TEST",
        ),
    )

    bet_result = evaluate_market_edge(
        model_total=9.00,
        market_total=MarketTotal(
            total=8.00,
            available=True,
            source="TEST",
        ),
    )

    strong_result = evaluate_market_edge(
        model_total=9.50,
        market_total=MarketTotal(
            total=8.00,
            available=True,
            source="TEST",
        ),
    )

    under_result = evaluate_market_edge(
        model_total=7.20,
        market_total=MarketTotal(
            total=8.00,
            available=True,
            source="TEST",
        ),
    )

    assert pass_result.recommendation == "PASS"
    assert lean_result.recommendation == "LEAN OVER"
    assert bet_result.recommendation == "BET OVER"

    assert (
        strong_result.recommendation
        == "STRONG BET OVER"
    )

    assert under_result.recommendation == "BET UNDER"


def main() -> None:
    result = build_totals_projection(
        build_test_game()
    )

    print_totals_report(
        result
    )

    validate_primary_projection(
        result
    )

    validate_neutral_fallback()
    validate_missing_market()
    validate_recommendation_thresholds()

    print()
    print(
        "Sprint 036 bullpen-integrated totals "
        "validation PASSED."
    )


if __name__ == "__main__":
    main()
