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

DIVIDER = "=" * 72
SECTION_DIVIDER = "-" * 72


def build_test_game() -> dict[str, Any]:
    """
    Build a complete synthetic MLB game for validating
    the Totals v1 projection engine.

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
    }


def build_unknown_park_game() -> dict[str, Any]:
    """
    Build a game with an unrecognized home club to confirm
    that the neutral park fallback behaves safely.
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


def print_projection(
    result: dict[str, Any],
) -> None:
    park = result.get(
        "park",
        {},
    )

    away_projection = result.get(
        "away_projection",
        {},
    )

    home_projection = result.get(
        "home_projection",
        {},
    )

    print(DIVIDER)
    print("SharpStack MLB Totals Projection Test")
    print(DIVIDER)

    print(
        "Away expected runs: "
        f"{result['away_expected_runs']:.2f}"
    )

    print(
        "Home expected runs: "
        f"{result['home_expected_runs']:.2f}"
    )

    print(
        "Projected total: "
        f"{result['projected_total']:.2f}"
    )

    print(
    "Market total: "
    f"{result['market_total']:.2f}"
    )

    print(
    "Edge: "
    f"{result['edge']:+.2f}"
    )

    print(
    "Direction: "
    f"{result['direction']}"
    )

    print(
    "Recommendation: "
    f"{result['recommendation']}"
    )

    print(
        "Confidence: "
        f"{result['confidence']:.1f}"
    )

    print(
        "Data quality: "
        f"{result['data_quality']}"
    )

    print(
        "Status: "
        f"{result['market_status']}"
    )

    print(SECTION_DIVIDER)
    print("Park Factor")
    print(SECTION_DIVIDER)

    print(
        "Home park team: "
        f"{park.get('team', 'UNKNOWN')}"
    )

    print(
        "Factor: "
        f"{park.get('factor', 1.0):.3f}"
    )

    print(
        "Source: "
        f"{park.get('source', 'UNKNOWN')}"
    )

    print(
        "Available: "
        f"{park.get('available', False)}"
    )

    print(SECTION_DIVIDER)
    print("Projection Components")
    print(SECTION_DIVIDER)

    print(
        "Away offense adjustment: "
        f"{away_projection.get('offense_adjustment', 0.0):+.2f}"
    )

    print(
        "Away starter adjustment: "
        f"{away_projection.get('starter_adjustment', 0.0):+.2f}"
    )

    print(
        "Away park adjustment: "
        f"{away_projection.get('park_adjustment', 0.0):+.2f}"
    )

    print(
        "Home offense adjustment: "
        f"{home_projection.get('offense_adjustment', 0.0):+.2f}"
    )

    print(
        "Home starter adjustment: "
        f"{home_projection.get('starter_adjustment', 0.0):+.2f}"
    )

    print(
        "Home park adjustment: "
        f"{home_projection.get('park_adjustment', 0.0):+.2f}"
    )

    print(
        "Home-field adjustment: "
        f"{home_projection.get('home_adjustment', 0.0):+.2f}"
    )


def validate_primary_projection(
    result: dict[str, Any],
) -> None:
    park = result["park"]
    away_projection = result[
        "away_projection"
    ]
    home_projection = result[
        "home_projection"
    ]

    assert result["away_expected_runs"] > 0
    assert result["home_expected_runs"] > 0
    assert result["projected_total"] > 0

    assert (
        result["projected_total"]
        == round(
            result["away_expected_runs"]
            + result["home_expected_runs"],
            2,
        )
    )

    assert 40.0 <= result["confidence"] <= 78.0

    assert result["data_quality"] in {
        "LIMITED",
        "FAIR",
        "GOOD",
        "EXCELLENT",
    }

    assert result["market_total"] == 8.0

    assert result["market_status"] == "AVAILABLE"

    assert result["direction"] == "OVER"

    assert result["edge"] == round(
        result["projected_total"]
        - result["market_total"],
        2,
    )

    assert result["recommendation"] == "LEAN OVER"

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

    assert (
        away_projection["park_adjustment"]
        < 0
    )

    assert (
        home_projection["park_adjustment"]
        < 0
    )

    assert (
        home_projection["home_adjustment"]
        > 0
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

    assert (
        result["market_status"]
        == "MODEL_ONLY"
    )

    assert (
        result["recommendation"]
        == "NO MARKET LINE"
    )

def validate_neutral_fallback() -> None:
    fallback_result = build_totals_projection(
        build_unknown_park_game()
    )

    park = fallback_result["park"]

    assert park["team"] == "UNKNOWN"
    assert park["factor"] == 1.0

    assert (
        park["source"]
        == "NEUTRAL_FALLBACK"
    )

    assert park["available"] is False

    assert (
        fallback_result[
            "away_projection"
        ]["park_adjustment"]
        == 0.0
    )

    assert (
        fallback_result[
            "home_projection"
        ]["park_adjustment"]
        == 0.0
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

    assert (
        result["market_status"]
        == "MODEL_ONLY"
    )

    assert (
        result["recommendation"]
        == "NO MARKET LINE"
    )

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

    assert (
        pass_result.recommendation
        == "PASS"
    )

    assert (
        lean_result.recommendation
        == "LEAN OVER"
    )

    assert (
        bet_result.recommendation
        == "BET OVER"
    )

    assert (
        strong_result.recommendation
        == "STRONG BET OVER"
    )

    assert (
        under_result.recommendation
        == "BET UNDER"
    )

def main() -> None:
    game = build_test_game()

    result = build_totals_projection(
        game
    )

    print_totals_report(result)

    validate_primary_projection(
        result
    )

    validate_neutral_fallback()
    validate_missing_market()
    validate_recommendation_thresholds()
    print()
    print("Sprint 035 Totals v1 validation PASSED.")


if __name__ == "__main__":
    main()
