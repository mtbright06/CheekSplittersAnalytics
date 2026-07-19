from decimal import Decimal

import pytest

from app.services.recommendation_analytics_service import (
    SettledResult,
    summarize_performance,
)
from app.services.recommendation_grading_service import (
    RecommendationGradingValidationError,
    calculate_profit_units,
)


def test_positive_american_odds_profit() -> None:
    assert calculate_profit_units(
        outcome="WIN",
        american_odds=150,
        stake_units=Decimal("1"),
    ) == Decimal("1.5000")


def test_negative_american_odds_profit() -> None:
    assert calculate_profit_units(
        outcome="WIN",
        american_odds=-120,
        stake_units=Decimal("1"),
    ) == Decimal("0.8333")


def test_loss_push_and_void_profit() -> None:
    assert calculate_profit_units(
        outcome="LOSS", american_odds=-110, stake_units="2"
    ) == Decimal("-2.0000")
    assert calculate_profit_units(
        outcome="PUSH", american_odds=None, stake_units="1"
    ) == Decimal("0.0000")
    assert calculate_profit_units(
        outcome="VOID", american_odds=None, stake_units="1"
    ) == Decimal("0.0000")


def test_win_requires_odds() -> None:
    with pytest.raises(RecommendationGradingValidationError):
        calculate_profit_units(outcome="WIN", american_odds=None)


def test_performance_summary() -> None:
    summary = summarize_performance(
        [
            SettledResult("WIN", Decimal("1"), Decimal("1.5000")),
            SettledResult("WIN", Decimal("1"), Decimal("0.8333")),
            SettledResult("LOSS", Decimal("1"), Decimal("-1.0000")),
            SettledResult("PUSH", Decimal("1"), Decimal("0.0000")),
            SettledResult("VOID", Decimal("1"), Decimal("0.0000")),
        ]
    )

    assert summary.graded == 5
    assert summary.wins == 2
    assert summary.losses == 1
    assert summary.pushes == 1
    assert summary.voids == 1
    assert summary.decisions == 3
    assert summary.win_percentage == Decimal("66.67")
    assert summary.stake_units == Decimal("4.000")
    assert summary.profit_units == Decimal("1.3333")
    assert summary.roi_percentage == Decimal("33.33")
