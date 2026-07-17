from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.mlb.totals.expected_runs import (
    TeamRunProjection,
    project_team_runs,
)
from engine.mlb.totals.helpers import (
    clamp,
)


@dataclass
class TotalsProjection:
    away: TeamRunProjection
    home: TeamRunProjection
    projected_total: float
    confidence: float
    data_quality: str
    market_status: str
    recommendation: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "away_expected_runs": round(
                self.away.expected_runs,
                2,
            ),
            "home_expected_runs": round(
                self.home.expected_runs,
                2,
            ),
            "projected_total": round(
                self.projected_total,
                2,
            ),
            "confidence": round(
                self.confidence,
                1,
            ),
            "data_quality": self.data_quality,
            "market_status": self.market_status,
            "recommendation": (
                self.recommendation
            ),
            "away_projection": (
                self.away.to_dict()
            ),
            "home_projection": (
                self.home.to_dict()
            ),
            "reasons": self.reasons,
        }


def confidence_from_data_points(
    data_points: int,
) -> float:
    """
    v1 confidence measures input completeness,
    not wager confidence.
    """

    return clamp(
        44.0
        + (
            data_points * 6.0
        ),
        44.0,
        82.0,
    )


def data_quality_label(
    data_points: int,
) -> str:
    if data_points >= 8:
        return "EXCELLENT"

    if data_points >= 6:
        return "GOOD"

    if data_points >= 4:
        return "FAIR"

    return "LIMITED"


def build_totals_projection(
    game: dict[str, Any],
) -> dict[str, Any]:
    teams = game.get(
        "teams",
        {},
    )

    pitching = game.get(
        "pitching",
        {},
    )

    away_team = teams.get(
        "away",
        {},
    )

    home_team = teams.get(
        "home",
        {},
    )

    away_pitcher = pitching.get(
        "away",
        {},
    )

    home_pitcher = pitching.get(
        "home",
        {},
    )

    away_projection = project_team_runs(
        team_profile=away_team,
        opposing_pitcher=home_pitcher,
        is_home=False,
    )

    home_projection = project_team_runs(
        team_profile=home_team,
        opposing_pitcher=away_pitcher,
        is_home=True,
    )

    projected_total = (
        away_projection.expected_runs
        + home_projection.expected_runs
    )

    data_points = (
        away_projection.data_points
        + home_projection.data_points
    )

    confidence = confidence_from_data_points(
        data_points
    )

    quality = data_quality_label(
        data_points
    )

    reasons = [
        (
            f"Projected score: "
            f"{away_projection.team} "
            f"{away_projection.expected_runs:.2f}, "
            f"{home_projection.team} "
            f"{home_projection.expected_runs:.2f}."
        ),
        (
            f"Projection uses {data_points} "
            f"available offense and starter inputs."
        ),
        (
            "Bullpen, park, weather and confirmed "
            "lineups are not yet included in Totals v1."
        ),
    ]

    result = TotalsProjection(
        away=away_projection,
        home=home_projection,
        projected_total=projected_total,
        confidence=confidence,
        data_quality=quality,
        market_status="MODEL_ONLY",
        recommendation="NO MARKET LINE",
        reasons=reasons,
    )

    return result.to_dict()