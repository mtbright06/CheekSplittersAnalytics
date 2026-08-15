from __future__ import annotations

from typing import Any

from calculators.bullpen import BullpenCalculator
from calculators.offense import OffenseCalculator
from calculators.recent_form import RecentFormCalculator
from calculators.starting_pitching import StartingPitchingCalculator


def build_supported_component_shadow(
    *,
    game: Any,
    index: int,
    calculators: list[Any],
    component_scores: dict[str, float],
    recommendation_fn,
    selection_fn,
) -> dict[str, Any]:
    configured_weights = {
        calculator.NAME: float(calculator.WEIGHT)
        for calculator in calculators
    }
    supported = {
        calculator.NAME: _component_supported(calculator, game)
        for calculator in calculators
    }

    active_weight = sum(
        weight
        for name, weight in configured_weights.items()
        if supported.get(name)
    )

    if active_weight <= 0:
        return {
            "available": False,
            "concerns": ["No supported KBO shadow components available."],
            "configured_weights": configured_weights,
            "supported_components": supported,
            "effective_weights": {},
            "component_scores": component_scores,
            "weighted_score": 0.0,
            "model_strength": 50.0,
            "selected_team_model_strength": None,
            "selection": None,
            "recommendation": recommendation_fn(50.0),
        }

    effective_weights = {
        name: round(weight / active_weight, 6)
        for name, weight in configured_weights.items()
        if supported.get(name)
    }
    weighted_score = sum(
        component_scores[name] * effective_weights[name]
        for name in effective_weights
    )
    model_strength = round(
        50 + (weighted_score * 8),
        1,
    )
    selection = selection_fn(weighted_score, game)
    selected_team_model_strength = _selected_side_strength(
        model_strength,
        selection,
    )

    return {
        "available": True,
        "concerns": _unsupported_concerns(supported),
        "configured_weights": configured_weights,
        "supported_components": supported,
        "effective_weights": effective_weights,
        "component_scores": component_scores,
        "weighted_score": round(weighted_score, 6),
        "model_strength": model_strength,
        "selected_team_model_strength": selected_team_model_strength,
        "selection": selection,
        "recommendation": recommendation_fn(
            selected_team_model_strength
            if selected_team_model_strength is not None
            else 50.0
        ),
    }


def _component_supported(
    calculator: Any,
    game: Any,
) -> bool:
    if isinstance(calculator, StartingPitchingCalculator):
        return (
            _starter_supported(game.away.pitcher)
            and _starter_supported(game.home.pitcher)
        )

    if isinstance(calculator, OffenseCalculator):
        return (
            game.away.offense.runs_per_game is not None
            and game.home.offense.runs_per_game is not None
        )

    if isinstance(calculator, BullpenCalculator):
        return (
            game.away.bullpen.era is not None
            and game.away.bullpen.league_era is not None
            and game.home.bullpen.era is not None
            and game.home.bullpen.league_era is not None
        )

    if isinstance(calculator, RecentFormCalculator):
        return not (
            calculator._missing_form(game.away.form)
            or calculator._missing_form(game.home.form)
        )

    return False


def _starter_supported(pitcher: Any) -> bool:
    return (
        pitcher.name is not None
        and pitcher.name != "Unknown Starter"
        and getattr(pitcher, "starter_confirmed", False) is True
        and pitcher.era is not None
        and pitcher.whip is not None
    )


def _unsupported_concerns(
    supported: dict[str, bool],
) -> list[str]:
    return [
        f"{name} unsupported; authority omitted from shadow calculation."
        for name, is_supported in supported.items()
        if not is_supported
    ]


def _selected_side_strength(
    raw_model_strength: float,
    selection: Any,
) -> float | None:
    if not selection:
        return None

    return round(
        50.0 + abs(float(raw_model_strength) - 50.0),
        1,
    )
