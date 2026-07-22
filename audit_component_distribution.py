from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

DEFAULT_CARD_PATH = ROOT / "output" / "cards" / "mlb_card.json"
DEFAULT_OUTPUT_PATH = (
    ROOT / "output" / "audit" / "component_distribution.json"
)

COMPONENTS = (
    "offense",
    "starting_pitching",
    "bullpen",
    "market",
    "home_field",
)

# Current SharpScore component weights.
#
# Keep these synchronized with engine/model/sharpscore.py.
COMPONENT_WEIGHTS = {
    "offense": 0.35,
    "starting_pitching": 0.35,
    "bullpen": 0.15,
    "market": 0.10,
    "home_field": 0.05,
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    return payload


def extract_component_values(
    payload: dict[str, Any],
) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {
        component: [] for component in COMPONENTS
    }

    games = payload.get("games", [])
    if not isinstance(games, list):
        raise ValueError("mlb_card.json field 'games' must be a list")

    for game in games:
        if not isinstance(game, dict):
            continue

        model = game.get("model")
        if not isinstance(model, dict):
            continue

        component_scores = model.get("component_scores")
        if not isinstance(component_scores, dict):
            continue

        for side in ("selected", "opponent"):
            side_scores = component_scores.get(side)
            if not isinstance(side_scores, dict):
                continue

            for component in COMPONENTS:
                value = side_scores.get(component)

                if isinstance(value, bool):
                    continue

                if isinstance(value, (int, float)):
                    values[component].append(float(value))

    return values


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("Cannot calculate percentile for an empty list")

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * fraction
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    remainder = position - lower_index

    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]

    return lower_value + ((upper_value - lower_value) * remainder)


def summarize_component(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "standard_deviation": None,
            "minimum": None,
            "q1": None,
            "q3": None,
            "maximum": None,
            "exact_low_clamp_count": 0,
            "exact_high_clamp_count": 0,
            "near_low_count": 0,
            "near_high_count": 0,
            "exact_clamp_pct": 0.0,
            "near_clamp_pct": 0.0,
            "unique_values": 0,
        }

    count = len(values)
    exact_low = sum(value <= 0 for value in values)
    exact_high = sum(value >= 100 for value in values)
    near_low = sum(value <= 5 for value in values)
    near_high = sum(value >= 95 for value in values)

    standard_deviation = (
        statistics.pstdev(values) if count > 1 else 0.0
    )

    return {
        "count": count,
        "mean": round(statistics.fmean(values), 3),
        "median": round(statistics.median(values), 3),
        "standard_deviation": round(standard_deviation, 3),
        "minimum": round(min(values), 3),
        "q1": round(percentile(values, 0.25), 3),
        "q3": round(percentile(values, 0.75), 3),
        "maximum": round(max(values), 3),
        "exact_low_clamp_count": exact_low,
        "exact_high_clamp_count": exact_high,
        "near_low_count": near_low,
        "near_high_count": near_high,
        "exact_clamp_pct": round(
            ((exact_low + exact_high) / count) * 100,
            2,
        ),
        "near_clamp_pct": round(
            ((near_low + near_high) / count) * 100,
            2,
        ),
        "unique_values": len(set(values)),
    }


def summarize_weight_contribution(
    raw_values: list[float],
    weight: float,
) -> dict[str, Any]:
    weighted_values = [
        value * weight
        for value in raw_values
    ]

    if not weighted_values:
        return {
            "weight": weight,
            "count": 0,
            "raw_mean": None,
            "mean_contribution": None,
            "median_contribution": None,
            "standard_deviation": None,
            "minimum_contribution": None,
            "maximum_contribution": None,
            "spread": None,
        }

    return {
        "weight": weight,
        "count": len(weighted_values),
        "raw_mean": round(statistics.fmean(raw_values), 3),
        "mean_contribution": round(
            statistics.fmean(weighted_values),
            3,
        ),
        "median_contribution": round(
            statistics.median(weighted_values),
            3,
        ),
        "standard_deviation": round(
            statistics.pstdev(weighted_values)
            if len(weighted_values) > 1
            else 0.0,
            3,
        ),
        "minimum_contribution": round(
            min(weighted_values),
            3,
        ),
        "maximum_contribution": round(
            max(weighted_values),
            3,
        ),
        "spread": round(
            max(weighted_values) - min(weighted_values),
            3,
        ),
    }


def build_report(
    payload: dict[str, Any],
    card_path: Path,
) -> dict[str, Any]:
    component_values = extract_component_values(payload)

    games = payload.get("games", [])
    game_count = len(games) if isinstance(games, list) else 0

    weight_total = sum(COMPONENT_WEIGHTS.values())

    return {
        "audit": "component_distribution_and_weight_contribution",
        "source_file": str(card_path),
        "source_generated_at": payload.get("generated_at"),
        "sport": payload.get("sport"),
        "version": payload.get("version"),
        "game_count": game_count,
        "team_score_rows_expected": game_count * 2,
        "weight_total": round(weight_total, 3),
        "components": {
            component: summarize_component(values)
            for component, values in component_values.items()
        },
        "weight_contributions": {
            component: summarize_weight_contribution(
                component_values[component],
                COMPONENT_WEIGHTS[component],
            )
            for component in COMPONENTS
        },
    }


def format_number(value: Any) -> str:
    if value is None:
        return "N/A"

    return f"{float(value):.2f}"


def print_component_distribution(
    report: dict[str, Any],
) -> None:
    print()
    print("=" * 112)
    print("SHARPSTACK MLB COMPONENT DISTRIBUTION AUDIT")
    print("=" * 112)
    print(f"Source: {report['source_file']}")
    print(f"Generated at: {report.get('source_generated_at')}")
    print(f"Games: {report['game_count']}")
    print()

    header = (
        f"{'Component':<20}"
        f"{'Count':>7}"
        f"{'Mean':>9}"
        f"{'Std Dev':>10}"
        f"{'Min':>9}"
        f"{'Q1':>9}"
        f"{'Median':>10}"
        f"{'Q3':>9}"
        f"{'Max':>9}"
        f"{'Near Clamp %':>15}"
        f"{'Unique':>9}"
    )

    print(header)
    print("-" * len(header))

    components = report["components"]

    for component in COMPONENTS:
        summary = components[component]

        print(
            f"{component:<20}"
            f"{summary['count']:>7}"
            f"{format_number(summary['mean']):>9}"
            f"{format_number(summary['standard_deviation']):>10}"
            f"{format_number(summary['minimum']):>9}"
            f"{format_number(summary['q1']):>9}"
            f"{format_number(summary['median']):>10}"
            f"{format_number(summary['q3']):>9}"
            f"{format_number(summary['maximum']):>9}"
            f"{summary['near_clamp_pct']:>14.2f}%"
            f"{summary['unique_values']:>9}"
        )

    print()

    for component in COMPONENTS:
        summary = components[component]

        print(
            f"{component}: "
            f"exact clamps="
            f"{summary['exact_low_clamp_count'] + summary['exact_high_clamp_count']}, "
            f"near clamps="
            f"{summary['near_low_count'] + summary['near_high_count']}"
        )


def print_weight_contribution(
    report: dict[str, Any],
) -> None:
    print()
    print("=" * 112)
    print("SHARPSTACK MLB WEIGHT CONTRIBUTION AUDIT")
    print("=" * 112)
    print(
        f"Configured weight total: "
        f"{report['weight_total']:.3f}"
    )

    if report["weight_total"] != 1.0:
        print(
            "WARNING: Component weights do not total 1.000."
        )

    print()

    header = (
        f"{'Component':<20}"
        f"{'Weight':>9}"
        f"{'Raw Mean':>11}"
        f"{'Avg Contribution':>19}"
        f"{'Std Contribution':>19}"
        f"{'Min':>10}"
        f"{'Max':>10}"
        f"{'Spread':>10}"
    )

    print(header)
    print("-" * len(header))

    contributions = report["weight_contributions"]

    for component in COMPONENTS:
        summary = contributions[component]

        print(
            f"{component:<20}"
            f"{summary['weight']:>9.2f}"
            f"{format_number(summary['raw_mean']):>11}"
            f"{format_number(summary['mean_contribution']):>19}"
            f"{format_number(summary['standard_deviation']):>19}"
            f"{format_number(summary['minimum_contribution']):>10}"
            f"{format_number(summary['maximum_contribution']):>10}"
            f"{format_number(summary['spread']):>10}"
        )

    print()
    print("Influence ranking by weighted standard deviation:")

    ranked = sorted(
        contributions.items(),
        key=lambda item: (
            item[1]["standard_deviation"]
            if item[1]["standard_deviation"] is not None
            else -1
        ),
        reverse=True,
    )

    for index, (component, summary) in enumerate(
        ranked,
        start=1,
    ):
        print(
            f"{index}. {component}: "
            f"{format_number(summary['standard_deviation'])}"
        )


def print_report(report: dict[str, Any]) -> None:
    print_component_distribution(report)
    print_weight_contribution(report)


def write_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print()
    print(f"Audit report written: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit MLB SharpScore component distributions and "
            "weighted contributions."
        )
    )

    parser.add_argument(
        "--card",
        type=Path,
        default=DEFAULT_CARD_PATH,
        help=f"Path to MLB card JSON. Default: {DEFAULT_CARD_PATH}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Path for audit JSON output. Default: {DEFAULT_OUTPUT_PATH}",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        payload = load_json(args.card)
        report = build_report(payload, args.card)
        print_report(report)
        write_report(report, args.output)
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())