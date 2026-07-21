from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from engine.core.ranking import (
    calculate_ranking_score,
)
from engine.core.recommendation import (
    Recommendation,
)
from engine.model import recommendations


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
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


@dataclass
class PlayOfDayResult:
    recommendation: Recommendation | None
    fallback_recommendation: Recommendation | None
    eligible_count: int
    reason: str
    generated_at: str

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "eligible_count": self.eligible_count,
            "reason": self.reason,
            "recommendation": (
                self.recommendation.to_dict()
                if self.recommendation
                else None
            ),
            "fallback_recommendation": (
                self.fallback_recommendation.to_dict()
                if self.fallback_recommendation
                else None
            ),
        }


def consensus_values(
    recommendation: Recommendation,
) -> tuple[float, int, int]:
    source_signals = (
        recommendation.source_signals
        if isinstance(
            recommendation.source_signals,
            dict,
        )
        else {}
    )

    consensus = source_signals.get(
        "consensus",
        {},
    )

    if not isinstance(
        consensus,
        dict,
    ):
        return 0.0, 0, 0

    return (
        safe_float(
            consensus.get(
                "agreement_pct"
            ),
            0.0,
        ),
        int(
            safe_float(
                consensus.get(
                    "support_count"
                ),
                0.0,
            )
        ),
        int(
            safe_float(
                consensus.get(
                    "oppose_count"
                ),
                0.0,
            )
        ),
    )


def eligibility_result(
    recommendation: Recommendation,
    *,
    minimum_hammer_score: float = 74.0,
    require_real_market: bool = False,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not recommendation.actionable:
        reasons.append("Not actionable.")

    if recommendation.hammer_score < minimum_hammer_score:
        reasons.append(
            f"Hammer {recommendation.hammer_score:.1f} "
            f"< {minimum_hammer_score:.1f}"
        )

    if (
        require_real_market
        and not recommendation.real_market_loaded
    ):
        reasons.append("Real market required.")

    if (
        recommendation.edge_pct is not None
        and recommendation.edge_pct < -1
    ):
        reasons.append(
            f"Negative edge ({recommendation.edge_pct:+.1f}%)."
        )

    agreement_pct, _, oppose_count = consensus_values(
        recommendation
    )

    if (
        oppose_count >= 2
        and agreement_pct < 60
    ):
        reasons.append(
            f"Consensus only {agreement_pct:.1f}% "
            f"with {oppose_count} opposing models."
        )

    return len(reasons) == 0, reasons


def is_eligible(
    recommendation: Recommendation,
    *,
    minimum_hammer_score: float = 74.0,
    require_real_market: bool = False,
) -> bool:
    eligible, _ = eligibility_result(
        recommendation,
        minimum_hammer_score=minimum_hammer_score,
        require_real_market=require_real_market,
    )
    return eligible


def select_play_of_day(
    recommendations: list[
        Recommendation
    ],
    *,
    require_real_market: bool = False,
    minimum_hammer_score: float = 74.0,
) -> PlayOfDayResult:

    print("")
    print("=" * 64)
    print("PLAY OF DAY AUDIT")
    print("=" * 64)

    for recommendation in recommendations:
        ok, reasons = eligibility_result(
            recommendation,
            minimum_hammer_score=minimum_hammer_score,
            require_real_market=require_real_market,
        )

        print(
            f"{recommendation.league} | "
            f"{recommendation.market} | "
            f"{recommendation.selection}"
        )

        if ok:
            print(
                f"  ✓ ELIGIBLE "
                f"(Rank {calculate_ranking_score(recommendation):.1f})"
            )
        else:
            for reason in reasons:
                print(f"  ✗ {reason}")

        print("")


    actionable = [
        recommendation
        for recommendation in recommendations
        if recommendation.actionable
    ]

    actionable.sort(
        key=lambda recommendation: (
            calculate_ranking_score(
                recommendation
            ),
            recommendation.hammer_score,
        ),
        reverse=True,
    )

    fallback_recommendation = (
        actionable[0]
        if actionable
        else None
    )

    eligible = [
        recommendation
        for recommendation in recommendations
        if is_eligible(
            recommendation,
            minimum_hammer_score=(
                minimum_hammer_score
            ),
            require_real_market=(
                require_real_market
            ),
        )
    ]

    eligible.sort(
        key=lambda recommendation: (
            calculate_ranking_score(
                recommendation
            ),
            recommendation.hammer_score,
        ),
        reverse=True,
    )

    generated_at = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    if not eligible:
        return PlayOfDayResult(
            recommendation=None,
            fallback_recommendation=(
                fallback_recommendation
            ),
            eligible_count=0,
            reason=(
                "No recommendation met the "
                "Play of the Day requirements. "
                "The fallback recommendation is "
                "the highest-ranked actionable play "
                "and is not an official Play of the Day."
            ),
            generated_at=generated_at,
        )

    winner = eligible[0]

    agreement_pct, support_count, oppose_count = (
        consensus_values(
            winner
        )
    )

    reason_parts = [
        (
            f"Highest eligible ranking score "
            f"({calculate_ranking_score(winner):.1f})."
        ),
        (
            f"Hammer Score "
            f"{winner.hammer_score:.1f}."
        ),
    ]

    if support_count > 0:
        reason_parts.append(
            f"Consensus {support_count} support, "
            f"{oppose_count} oppose "
            f"({agreement_pct:.1f}% agreement)."
        )

    if winner.edge_pct is not None:
        reason_parts.append(
            f"Model edge "
            f"{winner.edge_pct:+.1f}%."
        )

    if winner.expected_value_pct is not None:
        reason_parts.append(
            f"Expected value "
            f"{winner.expected_value_pct:+.1f}%."
        )

    if not winner.real_market_loaded:
        reason_parts.append(
            "Model-only recommendation; "
            "confirm a real sportsbook price "
            "before wagering."
        )

    return PlayOfDayResult(
        recommendation=winner,
        fallback_recommendation=None,
        eligible_count=len(
            eligible
        ),
        reason=" ".join(
            reason_parts
        ),
        generated_at=generated_at,
    )
