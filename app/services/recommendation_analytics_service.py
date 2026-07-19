from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SettledResult:
    outcome: str
    stake_units: Decimal
    profit_units: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    graded: int
    wins: int
    losses: int
    pushes: int
    voids: int
    decisions: int
    win_percentage: Decimal | None
    stake_units: Decimal
    profit_units: Decimal
    roi_percentage: Decimal | None


def summarize_performance(results: Iterable[SettledResult]) -> PerformanceSummary:
    rows = list(results)
    outcomes = [row.outcome.strip().upper() for row in rows]

    wins = outcomes.count("WIN")
    losses = outcomes.count("LOSS")
    pushes = outcomes.count("PUSH")
    voids = outcomes.count("VOID")
    decisions = wins + losses

    stake_units = sum(
        (row.stake_units for row in rows if row.outcome.strip().upper() != "VOID"),
        Decimal("0"),
    )
    profit_units = sum((row.profit_units for row in rows), Decimal("0"))

    win_percentage = None
    if decisions:
        win_percentage = (
            Decimal(wins) / Decimal(decisions) * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    roi_percentage = None
    if stake_units > 0:
        roi_percentage = (
            profit_units / stake_units * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return PerformanceSummary(
        graded=len(rows),
        wins=wins,
        losses=losses,
        pushes=pushes,
        voids=voids,
        decisions=decisions,
        win_percentage=win_percentage,
        stake_units=stake_units.quantize(Decimal("0.001")),
        profit_units=profit_units.quantize(Decimal("0.0001")),
        roi_percentage=roi_percentage,
    )
