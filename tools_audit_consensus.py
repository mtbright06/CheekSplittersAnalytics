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


def signal_adjusted_score(
    signal: dict,
) -> float | None:
    score = safe_float(
        signal.get("score")
    )

    supports = signal.get(
        "supports"
    )

    if score is None:
        return None

    if supports is True:
        return score

    if supports is False:
        return 100.0 - score

    return None


def audit_consensus(
    decision: dict,
) -> None:
    consensus = decision.get(
        "consensus",
        {},
    )

    if not isinstance(
        consensus,
        dict,
    ):
        consensus = {}

    signals = consensus.get(
        "signals",
        [],
    )

    if not isinstance(
        signals,
        list,
    ):
        signals = []

    available = [
        signal
        for signal in signals
        if signal.get("available") is True
        and (
            safe_float(
                signal.get("weight"),
                0.0,
            )
            or 0.0
        )
        > 0
    ]

    scored = [
        signal
        for signal in available
        if signal_adjusted_score(
            signal
        )
        is not None
    ]

    support_weight = (
        safe_float(
            consensus.get(
                "support_weight"
            ),
            0.0,
        )
        or 0.0
    )

    oppose_weight = (
        safe_float(
            consensus.get(
                "oppose_weight"
            ),
            0.0,
        )
        or 0.0
    )

    total_weight = (
        support_weight
        + oppose_weight
    )

    calculated_agreement = (
        support_weight
        / total_weight
        * 100.0
        if total_weight > 0
        else 0.0
    )

    if scored:
        weighted_total = sum(
            (
                signal_adjusted_score(
                    signal
                )
                or 0.0
            )
            * (
                safe_float(
                    signal.get("weight"),
                    1.0,
                )
                or 1.0
            )
            for signal in scored
        )

        scored_weight = sum(
            (
                safe_float(
                    signal.get("weight"),
                    1.0,
                )
                or 1.0
            )
            for signal in scored
        )

        base_score = (
            weighted_total
            / scored_weight
            if scored_weight > 0
            else calculated_agreement
        )
    else:
        base_score = (
            calculated_agreement
        )

    sample_bonus = min(
        max(
            len(available) - 1,
            0,
        )
        * 1.5,
        7.5,
    )

    oppose_count = int(
        safe_float(
            consensus.get(
                "oppose_count"
            ),
            0,
        )
        or 0
    )

    contradiction_penalty = min(
        oppose_count * 4.0,
        16.0,
    )

    calculated_score = max(
        0.0,
        min(
            100.0,
            base_score
            + sample_bonus
            - contradiction_penalty,
        ),
    )

    print("")
    print("=" * 72)
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
    print(
        f"Hammer: "
        f"{safe_float(decision.get('hammer_score'), 0.0):.1f}"
    )
    print("-" * 72)

    print("Signals")

    if not signals:
        print("  No consensus signals.")
    else:
        for signal in signals:
            supports = signal.get(
                "supports"
            )

            if supports is True:
                direction = "SUPPORT"
            elif supports is False:
                direction = "OPPOSE"
            else:
                direction = "UNAVAILABLE"

            score = safe_float(
                signal.get("score")
            )

            adjusted = (
                signal_adjusted_score(
                    signal
                )
            )

            weight = safe_float(
                signal.get("weight"),
                0.0,
            )

            print(
                f"  {signal.get('name', 'Unknown'):<14}"
                f" {direction:<11}"
                f" score={str(score):<6}"
                f" adjusted={str(adjusted):<6}"
                f" weight={weight}"
            )

    print("")
    print("Agreement")
    print(
        f"  Support weight:       "
        f"{support_weight:.3f}"
    )
    print(
        f"  Oppose weight:        "
        f"{oppose_weight:.3f}"
    )
    print(
        f"  Stored agreement:     "
        f"{safe_float(consensus.get('agreement_pct'), 0.0):.1f}"
    )
    print(
        f"  Calculated agreement: "
        f"{calculated_agreement:.1f}"
    )

    print("")
    print("Consensus score")
    print(
        f"  Base score:           "
        f"{base_score:.1f}"
    )
    print(
        f"  Sample bonus:         "
        f"+{sample_bonus:.1f}"
    )
    print(
        f"  Contradiction penalty:"
        f" -{contradiction_penalty:.1f}"
    )
    print(
        f"  Stored score:         "
        f"{safe_float(consensus.get('consensus_score'), 0.0):.1f}"
    )
    print(
        f"  Calculated score:     "
        f"{calculated_score:.1f}"
    )
    print(
        f"  Label:                "
        f"{consensus.get('label', 'Unknown')}"
    )


def main() -> None:
    card = load_json(
        DECISION_CARD_PATH
    )

    decisions = card.get(
        "decisions",
        [],
    )

    if not decisions:
        print(
            "No decisions found."
        )
        return

    print("")
    print("=" * 72)
    print("SharpStack Consensus Calculation Audit")
    print("=" * 72)
    print(
        f"Decision card: "
        f"{DECISION_CARD_PATH}"
    )
    print(
        f"Decisions: "
        f"{len(decisions)}"
    )

    for decision in decisions:
        if not isinstance(
            decision,
            dict,
        ):
            continue

        audit_consensus(
            decision
        )


if __name__ == "__main__":
    main()
