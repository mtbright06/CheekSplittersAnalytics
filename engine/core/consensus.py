from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in [None, "", "None", "N/A", "-", "--"]:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    low: float = 0.0,
    high: float = 100.0,
) -> float:
    return max(low, min(high, value))


@dataclass
class ConsensusSignal:
    name: str
    supports: bool | None
    score: float | None = None
    weight: float = 1.0
    reason: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self):
        self.name = str(
            self.name or "Unknown"
        ).strip()

        self.score = safe_float(
            self.score
        )

        if self.score is not None:
            self.score = clamp(
                self.score
            )

        self.weight = max(
            safe_float(
                self.weight,
                1.0,
            )
            or 1.0,
            0.0,
        )

    @property
    def available(self) -> bool:
        return self.supports is not None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "supports": self.supports,
            "available": self.available,
            "score": self.score,
            "weight": self.weight,
            "reason": self.reason,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "ConsensusSignal":
        return cls(
            name=data.get(
                "name",
                "Unknown",
            ),
            supports=data.get(
                "supports"
            ),
            score=data.get("score"),
            weight=data.get(
                "weight",
                1.0,
            ),
            reason=data.get(
                "reason"
            ),
            source=data.get(
                "source"
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
        )


@dataclass
class ConsensusResult:
    signals: list[ConsensusSignal]
    support_count: int
    oppose_count: int
    available_count: int
    unavailable_count: int
    support_weight: float
    oppose_weight: float
    agreement_pct: float
    consensus_score: float
    label: str
    reasons: list[str]

    @property
    def unanimous(self) -> bool:
        return (
            self.available_count > 0
            and self.oppose_count == 0
        )

    @property
    def has_consensus(self) -> bool:
        return self.available_count >= 2

    def to_dict(self) -> dict:
        return {
            "support_count": (
                self.support_count
            ),
            "oppose_count": (
                self.oppose_count
            ),
            "available_count": (
                self.available_count
            ),
            "unavailable_count": (
                self.unavailable_count
            ),
            "support_weight": round(
                self.support_weight,
                3,
            ),
            "oppose_weight": round(
                self.oppose_weight,
                3,
            ),
            "agreement_pct": round(
                self.agreement_pct,
                1,
            ),
            "consensus_score": round(
                self.consensus_score,
                1,
            ),
            "label": self.label,
            "unanimous": self.unanimous,
            "has_consensus": (
                self.has_consensus
            ),
            "reasons": self.reasons,
            "signals": [
                signal.to_dict()
                for signal in self.signals
            ],
        }


def label_from_agreement(
    agreement_pct: float,
    available_count: int,
) -> str:
    if available_count <= 0:
        return "NO DATA"

    if available_count == 1:
        return "SINGLE SIGNAL"

    if agreement_pct >= 100:
        return "UNANIMOUS"

    if agreement_pct >= 80:
        return "STRONG"

    if agreement_pct >= 65:
        return "POSITIVE"

    if agreement_pct >= 50:
        return "SPLIT"

    return "NEGATIVE"


def build_consensus(
    signals: list[ConsensusSignal],
) -> ConsensusResult:
    available = [
        signal
        for signal in signals
        if signal.available
        and signal.weight > 0
    ]

    unavailable_count = len(
        signals
    ) - len(available)

    supporting = [
        signal
        for signal in available
        if signal.supports is True
    ]

    opposing = [
        signal
        for signal in available
        if signal.supports is False
    ]

    support_weight = sum(
        signal.weight
        for signal in supporting
    )

    oppose_weight = sum(
        signal.weight
        for signal in opposing
    )

    total_weight = (
        support_weight
        + oppose_weight
    )

    if total_weight <= 0:
        agreement_pct = 0.0
    else:
        agreement_pct = (
            support_weight
            / total_weight
        ) * 100

    scored_signals = [
        signal
        for signal in available
        if signal.score is not None
    ]

    if scored_signals:
        weighted_score_total = sum(
            (
                signal.score
                if signal.supports
                else 100 - signal.score
            )
            * signal.weight
            for signal in scored_signals
        )

        scored_weight = sum(
            signal.weight
            for signal in scored_signals
        )

        base_score = (
            weighted_score_total
            / scored_weight
            if scored_weight > 0
            else agreement_pct
        )
    else:
        base_score = agreement_pct

    sample_bonus = min(
        max(
            len(available) - 1,
            0,
        )
        * 1.5,
        7.5,
    )

    contradiction_penalty = min(
        len(opposing) * 4.0,
        16.0,
    )

    consensus_score = clamp(
        base_score
        + sample_bonus
        - contradiction_penalty
    )

    reasons: list[str] = []

    for signal in supporting:
        if signal.reason:
            reasons.append(
                signal.reason
            )
        else:
            reasons.append(
                f"{signal.name} supports the play."
            )

    for signal in opposing:
        if signal.reason:
            reasons.append(
                signal.reason
            )
        else:
            reasons.append(
                f"{signal.name} opposes the play."
            )

    return ConsensusResult(
        signals=signals,
        support_count=len(
            supporting
        ),
        oppose_count=len(
            opposing
        ),
        available_count=len(
            available
        ),
        unavailable_count=(
            unavailable_count
        ),
        support_weight=(
            support_weight
        ),
        oppose_weight=(
            oppose_weight
        ),
        agreement_pct=(
            agreement_pct
        ),
        consensus_score=(
            consensus_score
        ),
        label=label_from_agreement(
            agreement_pct,
            len(available),
        ),
        reasons=reasons,
    )
