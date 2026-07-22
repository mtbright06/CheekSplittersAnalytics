from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DECISION_CARD_PATH = (
    ROOT
    / "output"
    / "cards"
    / "decision_card.json"
)

COMPONENT_ORDER = [
    "mlb_model",
    "first5",
    "bomb",
    "starter",
    "offense",
    "bullpen",
    "park",
    "weather",
    "market_edge",
    "expected_value",
    "sample_confidence",
]

DISPLAY_NAMES = {
    "mlb_model": "MLB Model",
    "first5": "First 5",
    "bomb": "Bomb Lab",
    "starter": "Starter",
    "offense": "Offense",
    "bullpen": "Bullpen",
    "park": "Park",
    "weather": "Weather",
    "market_edge": "Market Edge",
    "expected_value": "Expected Value",
    "sample_confidence": "Sample Confidence",
}


@dataclass
class SensitivityResult:
    matchup: str
    selected_team: str
    recommendation: str
    original_hammer: float
    component: str
    component_score: float | None
    component_weight: float
    hammer_without: float
    movement: float
    absolute_movement: float
    original_rank: int = 0
    rank_without: int = 0
    rank_change: int = 0


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in {
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        }:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing decision card: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "Decision card root must be a JSON object."
        )

    return payload


def get_breakdown(
    decision: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw = decision.get(
        "score_breakdown",
        {},
    )

    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}

    for name, component in raw.items():
        if isinstance(component, dict):
            result[str(name)] = component

    return result


def component_is_available(
    component: dict[str, Any],
) -> bool:
    if not bool(
        component.get("available")
    ):
        return False

    score = safe_float(
        component.get("score")
    )

    weight = safe_float(
        component.get("weight"),
        0.0,
    )

    return (
        score is not None
        and weight is not None
        and weight > 0.0
    )


def calculate_base_score(
    breakdown: dict[str, dict[str, Any]],
    excluded_component: str | None = None,
) -> tuple[float, float]:
    weighted_total = 0.0
    used_weight = 0.0

    for name, component in breakdown.items():
        if name == excluded_component:
            continue

        if not component_is_available(
            component
        ):
            continue

        score = safe_float(
            component.get("score")
        )

        weight = safe_float(
            component.get("weight"),
            0.0,
        )

        if score is None or weight is None:
            continue

        weighted_total += score * weight
        used_weight += weight

    if used_weight <= 0.0:
        return 0.0, 0.0

    return (
        weighted_total / used_weight,
        used_weight,
    )


def get_adjustments(
    decision: dict[str, Any],
) -> tuple[float, float, float]:
    agreement_bonus = (
        safe_float(
            decision.get("agreement_bonus"),
            0.0,
        )
        or 0.0
    )

    contradiction_penalty = (
        safe_float(
            decision.get(
                "contradiction_penalty"
            ),
            0.0,
        )
        or 0.0
    )

    market_status_penalty = (
        safe_float(
            decision.get(
                "market_status_penalty"
            ),
            0.0,
        )
        or 0.0
    )

    return (
        agreement_bonus,
        contradiction_penalty,
        market_status_penalty,
    )


def calculate_hammer(
    decision: dict[str, Any],
    excluded_component: str | None = None,
) -> tuple[float, float]:
    breakdown = get_breakdown(
        decision
    )

    base_score, used_weight = (
        calculate_base_score(
            breakdown=breakdown,
            excluded_component=excluded_component,
        )
    )

    (
        agreement_bonus,
        contradiction_penalty,
        market_status_penalty,
    ) = get_adjustments(
        decision
    )

    hammer = (
        base_score
        + agreement_bonus
        - contradiction_penalty
        - market_status_penalty
    )

    hammer = max(
        0.0,
        min(
            100.0,
            hammer,
        ),
    )

    return hammer, used_weight


def build_results(
    decisions: list[dict[str, Any]],
) -> list[SensitivityResult]:
    results: list[SensitivityResult] = []

    for decision in decisions:
        matchup = str(
            decision.get(
                "matchup",
                "Unknown matchup",
            )
        )

        selected_team = str(
            decision.get(
                "selected_team",
                "Unknown",
            )
        )

        recommendation = str(
            decision.get(
                "recommendation",
                "Unknown",
            )
        )

        original_hammer = (
            safe_float(
                decision.get("hammer_score"),
                0.0,
            )
            or 0.0
        )

        breakdown = get_breakdown(
            decision
        )

        for component_name in COMPONENT_ORDER:
            component = breakdown.get(
                component_name
            )

            if not isinstance(
                component,
                dict,
            ):
                continue

            if not component_is_available(
                component
            ):
                continue

            component_score = safe_float(
                component.get("score")
            )

            component_weight = (
                safe_float(
                    component.get("weight"),
                    0.0,
                )
                or 0.0
            )

            hammer_without, _ = (
                calculate_hammer(
                    decision=decision,
                    excluded_component=component_name,
                )
            )

            movement = (
                original_hammer
                - hammer_without
            )

            results.append(
                SensitivityResult(
                    matchup=matchup,
                    selected_team=selected_team,
                    recommendation=recommendation,
                    original_hammer=original_hammer,
                    component=component_name,
                    component_score=component_score,
                    component_weight=component_weight,
                    hammer_without=hammer_without,
                    movement=movement,
                    absolute_movement=abs(
                        movement
                    ),
                )
            )

    return results


def calculate_ranks(
    decisions: list[dict[str, Any]],
    results: list[SensitivityResult],
) -> None:
    original_scores: dict[str, float] = {}

    for decision in decisions:
        matchup = str(
            decision.get(
                "matchup",
                "Unknown matchup",
            )
        )

        original_scores[matchup] = (
            safe_float(
                decision.get("hammer_score"),
                0.0,
            )
            or 0.0
        )

    original_order = sorted(
        original_scores,
        key=lambda matchup: (
            -original_scores[matchup],
            matchup,
        ),
    )

    original_ranks = {
        matchup: index
        for index, matchup in enumerate(
            original_order,
            start=1,
        )
    }

    results_by_component: dict[
        str,
        list[SensitivityResult],
    ] = defaultdict(list)

    for result in results:
        results_by_component[
            result.component
        ].append(result)

    for component, component_results in (
        results_by_component.items()
    ):
        without_scores = dict(
            original_scores
        )

        for result in component_results:
            without_scores[
                result.matchup
            ] = result.hammer_without

        without_order = sorted(
            without_scores,
            key=lambda matchup: (
                -without_scores[matchup],
                matchup,
            ),
        )

        without_ranks = {
            matchup: index
            for index, matchup in enumerate(
                without_order,
                start=1,
            )
        }

        for result in component_results:
            result.original_rank = (
                original_ranks[
                    result.matchup
                ]
            )

            result.rank_without = (
                without_ranks[
                    result.matchup
                ]
            )

            result.rank_change = (
                result.rank_without
                - result.original_rank
            )


def print_game_detail(
    decisions: list[dict[str, Any]],
    results: list[SensitivityResult],
) -> None:
    results_by_matchup: dict[
        str,
        list[SensitivityResult],
    ] = defaultdict(list)

    for result in results:
        results_by_matchup[
            result.matchup
        ].append(result)

    for decision in decisions:
        matchup = str(
            decision.get(
                "matchup",
                "Unknown matchup",
            )
        )

        game_results = (
            results_by_matchup.get(
                matchup,
                [],
            )
        )

        if not game_results:
            continue

        original_hammer = (
            safe_float(
                decision.get("hammer_score"),
                0.0,
            )
            or 0.0
        )

        selected_team = str(
            decision.get(
                "selected_team",
                "Unknown",
            )
        )

        recommendation = str(
            decision.get(
                "recommendation",
                "Unknown",
            )
        )

        print("")
        print("=" * 94)
        print(matchup)
        print(
            f"Selected: {selected_team}"
        )
        print(
            f"Recommendation: "
            f"{recommendation}"
        )
        print(
            f"Original Hammer: "
            f"{original_hammer:.1f}"
        )
        print("-" * 94)

        print(
            f"{'Removed component':<22}"
            f"{'Score':>9}"
            f"{'Weight':>10}"
            f"{'Without':>11}"
            f"{'Impact':>11}"
            f"{'Rank':>14}"
        )
        print("-" * 94)

        ordered_results = sorted(
            game_results,
            key=lambda row: (
                -row.absolute_movement,
                row.component,
            ),
        )

        for result in ordered_results:
            display_name = DISPLAY_NAMES.get(
                result.component,
                result.component,
            )

            score_text = (
                f"{result.component_score:.1f}"
                if result.component_score
                is not None
                else "None"
            )

            impact_text = (
                f"{result.movement:+.2f}"
            )

            rank_text = (
                f"{result.original_rank}"
                f"->{result.rank_without}"
            )

            print(
                f"{display_name:<22}"
                f"{score_text:>9}"
                f"{result.component_weight:>10.3f}"
                f"{result.hammer_without:>11.2f}"
                f"{impact_text:>11}"
                f"{rank_text:>14}"
            )


def print_component_summary(
    results: list[SensitivityResult],
) -> None:
    grouped: dict[
        str,
        list[SensitivityResult],
    ] = defaultdict(list)

    for result in results:
        grouped[
            result.component
        ].append(result)

    summary_rows: list[
        tuple[
            float,
            str,
            int,
            float,
            float,
            float,
            float,
            int,
            int,
        ]
    ] = []

    for component_name in COMPONENT_ORDER:
        component_results = grouped.get(
            component_name,
            [],
        )

        if not component_results:
            continue

        count = len(
            component_results
        )

        average_signed = sum(
            row.movement
            for row in component_results
        ) / count

        average_absolute = sum(
            row.absolute_movement
            for row in component_results
        ) / count

        maximum_absolute = max(
            row.absolute_movement
            for row in component_results
        )

        average_score = sum(
            row.component_score or 0.0
            for row in component_results
        ) / count

        rank_changes = sum(
            1
            for row in component_results
            if row.rank_change != 0
        )

        maximum_rank_change = max(
            abs(row.rank_change)
            for row in component_results
        )

        summary_rows.append(
            (
                average_absolute,
                component_name,
                count,
                average_score,
                average_signed,
                average_absolute,
                maximum_absolute,
                rank_changes,
                maximum_rank_change,
            )
        )

    summary_rows.sort(
        reverse=True
    )

    print("")
    print("=" * 104)
    print("Slate-wide Component Influence")
    print("=" * 104)
    print(
        f"{'Component':<22}"
        f"{'Games':>7}"
        f"{'Avg score':>12}"
        f"{'Avg impact':>13}"
        f"{'Avg |impact|':>15}"
        f"{'Max |impact|':>15}"
        f"{'Ranks moved':>13}"
        f"{'Max rank':>10}"
    )
    print("-" * 104)

    for (
        _,
        component_name,
        count,
        average_score,
        average_signed,
        average_absolute,
        maximum_absolute,
        rank_changes,
        maximum_rank_change,
    ) in summary_rows:
        display_name = DISPLAY_NAMES.get(
            component_name,
            component_name,
        )

        print(
            f"{display_name:<22}"
            f"{count:>7}"
            f"{average_score:>12.2f}"
            f"{average_signed:>+13.2f}"
            f"{average_absolute:>15.2f}"
            f"{maximum_absolute:>15.2f}"
            f"{rank_changes:>13}"
            f"{maximum_rank_change:>10}"
        )


def print_targeted_comparison(
    results: list[SensitivityResult],
) -> None:
    grouped: dict[
        str,
        list[SensitivityResult],
    ] = defaultdict(list)

    for result in results:
        grouped[
            result.component
        ].append(result)

    print("")
    print("=" * 94)
    print("First 5 and Bomb Lab Focus")
    print("=" * 94)

    for component_name in [
        "first5",
        "bomb",
    ]:
        rows = grouped.get(
            component_name,
            [],
        )

        display_name = DISPLAY_NAMES[
            component_name
        ]

        if not rows:
            print(
                f"{display_name}: "
                "No available observations."
            )
            continue

        count = len(rows)

        average_score = sum(
            row.component_score or 0.0
            for row in rows
        ) / count

        minimum_score = min(
            row.component_score or 0.0
            for row in rows
        )

        maximum_score = max(
            row.component_score or 0.0
            for row in rows
        )

        score_range = (
            maximum_score
            - minimum_score
        )

        average_absolute = sum(
            row.absolute_movement
            for row in rows
        ) / count

        maximum_absolute = max(
            row.absolute_movement
            for row in rows
        )

        rank_changes = sum(
            1
            for row in rows
            if row.rank_change != 0
        )

        positive_impact = sum(
            1
            for row in rows
            if row.movement > 0.01
        )

        negative_impact = sum(
            1
            for row in rows
            if row.movement < -0.01
        )

        print("")
        print(display_name)
        print(
            f"  Available games:       "
            f"{count}"
        )
        print(
            f"  Average raw score:     "
            f"{average_score:.2f}"
        )
        print(
            f"  Raw score range:       "
            f"{minimum_score:.2f}"
            f" to {maximum_score:.2f}"
            f" ({score_range:.2f})"
        )
        print(
            f"  Average Hammer impact: "
            f"{average_absolute:.2f}"
        )
        print(
            f"  Maximum Hammer impact: "
            f"{maximum_absolute:.2f}"
        )
        print(
            f"  Increased Hammer:      "
            f"{positive_impact}"
        )
        print(
            f"  Decreased Hammer:      "
            f"{negative_impact}"
        )
        print(
            f"  Rankings changed:      "
            f"{rank_changes}"
        )


def main() -> None:
    card = load_json(
        DECISION_CARD_PATH
    )

    raw_decisions = card.get(
        "decisions",
        [],
    )

    if not isinstance(
        raw_decisions,
        list,
    ):
        raw_decisions = []

    decisions = [
        decision
        for decision in raw_decisions
        if isinstance(
            decision,
            dict,
        )
    ]

    results = build_results(
        decisions
    )

    calculate_ranks(
        decisions=decisions,
        results=results,
    )

    print("")
    print("=" * 94)
    print(
        "SharpStack Hammer Component "
        "Sensitivity Audit"
    )
    print("=" * 94)
    print(
        f"Decision card: "
        f"{DECISION_CARD_PATH}"
    )
    print(
        f"Decisions: "
        f"{len(decisions)}"
    )
    print("")
    print(
        "Interpretation: positive impact means "
        "the component raises Hammer."
    )
    print(
        "Negative impact means the component "
        "lowers Hammer."
    )
    print(
        "All production adjustments remain fixed; "
        "only the selected base component is removed."
    )

    print_game_detail(
        decisions=decisions,
        results=results,
    )

    print_component_summary(
        results
    )

    print_targeted_comparison(
        results
    )


if __name__ == "__main__":
    main()
