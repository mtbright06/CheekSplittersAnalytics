from __future__ import annotations

from typing import Any


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
        "Confidence",
        f"{result['confidence']:.1f}%",
    )

    _line(
        "Data Quality",
        result["data_quality"],
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
    print("  ✓ Park Factors")
    print("  ✓ Market Comparison")

    print()

    print("Pending")

    print("  • Bullpen")
    print("  • Weather")
    print("  • Confirmed Lineups")

    print()
