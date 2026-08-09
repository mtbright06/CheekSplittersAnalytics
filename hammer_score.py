from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DECISION_CARD_PATH = (
    ROOT
    / "output"
    / "cards"
    / "decision_card.json"
)


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in [
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        ]:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def load_json(
    path: Path,
) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing decision card: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def audit_decision(
    decision: dict,
) -> None:
    breakdown = decision.get(
        "score_breakdown",
        {},
    )

    if not isinstance(
        breakdown,
        dict,
    ):
        breakdown = {}

    weighted_total = 0.0
    used_weight = 0.0

    print("")
    print("=" * 88)
    print(
        decision.get(
            "matchup",
            "Unknown matchup",
        )
    )
    print(
        f"Selected: "
        f"{decision.get('selected_team', 'Unknown')}"
    )
    print(
        f"Recommendation: "
        f"{decision.get('recommendation', 'Unknown')}"
    )
    print("-" * 88)

    print(
        f"{'Component':<20}"
        f"{'Available':<12}"
        f"{'Score':>10}"
        f"{'Weight':>10}"
        f"{'Contribution':>16}"
        f"{'Share':>10}"
    )
    print("-" * 88)

    available_rows: list[
        tuple[str, float, float, float]
    ] = []

    for name, component in breakdown.items():
        if not isinstance(
            component,
            dict,
        ):
            continue

        available = bool(
            component.get("available")
        )

        score = safe_float(
            component.get("score")
        )

        weight = (
            safe_float(
                component.get("weight"),
                0.0,
            )
            or 0.0
        )

        contribution = (
            safe_float(
                component.get("contribution"),
                0.0,
            )
            or 0.0
        )

        if available:
            weighted_total += contribution
            used_weight += weight

            available_rows.append(
                (
                    name,
                    score or 0.0,
                    weight,
                    contribution,
                )
            )

        print(
            f"{name:<20}"
            f"{str(available):<12}"
            f"{str(score):>10}"
            f"{weight:>10.3f}"
            f"{contribution:>16.2f}"
            f"{'':>10}"
        )

    calculated_base = (
        weighted_total / used_weight
        if used_weight > 0
        else 0.0
    )

    print("")
    print("Weight utilization")
    print(
        f"  Available weight:     "
        f"{used_weight:.3f}"
    )
    print(
        f"  Missing weight:       "
        f"{max(1.0 - used_weight, 0.0):.3f}"
    )
    print(
        f"  Weighted total:       "
        f"{weighted_total:.3f}"
    )

    print("")
    print("Effective contribution after renormalization")

    if available_rows and used_weight > 0:
        effective_rows = []

        for (
            name,
            score,
            weight,
            contribution,
        ) in available_rows:
            effective_weight = (
                weight / used_weight
            )

            effective_rows.append(
                (
                    effective_weight,
                    name,
                    score,
                    contribution,
                )
            )

        effective_rows.sort(
            reverse=True
        )

        for (
            effective_weight,
            name,
            score,
            contribution,
        ) in effective_rows:
            print(
                f"  {name:<20}"
                f"{effective_weight * 100:>6.1f}% "
                f"of base score "
                f"(score {score:.1f})"
            )

    stored_base = (
        safe_float(
            decision.get("base_score"),
            0.0,
        )
        or 0.0
    )

    agreement_bonus = (
        safe_float(
            decision.get(
                "agreement_bonus"
            ),
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

    calculated_final = max(
        0.0,
        min(
            100.0,
            calculated_base
            + agreement_bonus
            - contradiction_penalty
            - market_status_penalty,
        ),
    )

    stored_final = (
        safe_float(
            decision.get(
                "hammer_score"
            ),
            0.0,
        )
        or 0.0
    )

    print("")
    print("Hammer reconstruction")
    print(
        f"  Stored base:          "
        f"{stored_base:.1f}"
    )
    print(
        f"  Calculated base:      "
        f"{calculated_base:.1f}"
    )
    print(
        f"  Agreement bonus:      "
        f"+{agreement_bonus:.1f}"
    )
    print(
        f"  Contradiction penalty:"
        f" -{contradiction_penalty:.1f}"
    )
    print(
        f"  Market-only penalty:  "
        f"-{market_status_penalty:.1f}"
    )
    print(
        f"  Stored Hammer:        "
        f"{stored_final:.1f}"
    )
    print(
        f"  Calculated Hammer:    "
        f"{calculated_final:.1f}"
    )

    base_difference = abs(
        stored_base
        - calculated_base
    )

    final_difference = abs(
        stored_final
        - calculated_final
    )

    print("")
    print("Validation")

    if base_difference <= 0.15:
        print(
            "  PASS: Base score matches."
        )
    else:
        print(
            f"  WARNING: Base mismatch "
            f"({base_difference:.3f})."
        )

    if final_difference <= 0.15:
        print(
            "  PASS: Hammer score matches."
        )
    else:
        print(
            f"  WARNING: Hammer mismatch "
            f"({final_difference:.3f})."
        )

    if used_weight < 0.50:
        print(
            "  WARNING: Fewer than half "
            "of configured component weights "
            "were available."
        )

    if used_weight < 0.75:
        print(
            "  NOTE: Missing inputs caused "
            "the remaining components to receive "
            "larger effective weights."
        )

    if (
        agreement_bonus > 0
        and contradiction_penalty > 0
    ):
        print(
            "  NOTE: Both agreement and "
            "contradiction adjustments were applied."
        )


def main() -> None:
    card = load_json(
        DECISION_CARD_PATH
    )

    decisions = card.get(
        "decisions",
        [],
    )

    if not isinstance(
        decisions,
        list,
    ):
        decisions = []

    print("")
    print("=" * 88)
    print("SharpStack Hammer Calculation Audit")
    print("=" * 88)
    print(
        f"Decision card: "
        f"{DECISION_CARD_PATH}"
    )
    print(
        f"Decisions: "
        f"{len(decisions)}"
    )

    for decision in decisions:
        if isinstance(
            decision,
            dict,
        ):
            audit_decision(
                decision
            )


if __name__ == "__main__":
    main()
