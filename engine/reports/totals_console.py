from __future__ import annotations

from typing import Any

from engine.mlb.totals.explanation import TotalsExplanation
from engine.mlb.totals.explanation_renderer import (
    render_totals_explanation,
)


DIVIDER = "=" * 72
SECTION = "-" * 72


def _line(label: str, value: str) -> None:
    print(f"{label:<28}{value}")


def print_totals_report(result: dict[str, Any]) -> None:
    park = result["park"]

    print()
    print(DIVIDER)
    print("SharpStack MLB Totals Report")
    print(DIVIDER)

    starter_total = result.get(
        "starter_based_total",
        result["projected_total"],
    )

    bullpen_adjustment = result.get(
        "bullpen_adjustment",
        0.0,
    )

    bullpen = result.get(
        "bullpen",
        {},
    )

    _line(
    "Starter Total",
    f"{starter_total:.2f}",
    )

    _line(
        "Bullpen Adjustment",
        f"{bullpen_adjustment:+.2f}",
    )

    _line(
        "Projected Total",
        f"{result['projected_total']:.2f}",
    )

    if result["market_total"] is not None:

        _line(
            "Market Total",
            f"{result['market_total']:.2f}",
        )

        _line(
            "Edge",
            f"{result['edge']:+.2f}",
        )

        _line(
            "Direction",
            result["direction"],
        )

    else:

        _line(
            "Market",
            "No Line Available",
        )

    _line(
        "Recommendation",
        result["recommendation"],
    )

    _line(
        "Reliability",
        f"{result['confidence']:.1f}%",
    )

    _line(
        "Data Quality",
        result["data_quality"],
    )

    explanation_payload = result.get("explanation")
    explanation = None

    if isinstance(
        explanation_payload,
        TotalsExplanation,
    ):
        explanation = explanation_payload

    elif isinstance(
        explanation_payload,
        dict,
    ):
        explanation = TotalsExplanation.from_dict(
            explanation_payload
        )

    if explanation is not None:
        print()
        print(SECTION)
        print("Explanation")
        print(SECTION)

        print(
            render_totals_explanation(
                explanation,
                include_context=True,
            )
        )

    print()
    print(SECTION)
    print("Expected Runs")
    print(SECTION)

    _line(
        "Away",
        f"{result['away_expected_runs']:.2f}",
    )

    _line(
        "Home",
        f"{result['home_expected_runs']:.2f}",
    )

    print()
    print(SECTION)
    print("Park")
    print(SECTION)

    _line(
        "Home Team",
        park["team"],
    )

    if bullpen:

        print()

    _line(
        "Away Bullpen",
        f"{bullpen.get('away_adjustment',0):+.2f}",
    )

    _line(
        "Home Bullpen",
        f"{bullpen.get('home_adjustment',0):+.2f}",
    )

    _line(
        "Combined",
        f"{bullpen.get('combined_adjustment',0):+.2f}",
    )

    _line(
        "Factor",
        f"{park['factor']:.3f}",
    )

    _line(
        "Source",
        park["source"],
    )

    print()
    print(SECTION)
    print("Model Status")
    print(SECTION)

    print("Included")

    print("  ✓ Offense")
    print("  ✓ Starting Pitchers")
    print("  ✓ Bullpen")
    print("  ✓ Park Factors")
    print("  ✓ Market Comparison")

    print()

    print("Pending")

    print("  • Weather")
    print("  • Confirmed Lineups")

    print()
