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
from engine.mlb.totals.market import (
    MarketEdge,
    MarketTotal,
    evaluate_market_edge,
    extract_market_total,
)
from engine.mlb.totals.park_factors import (
    ParkFactorResult,
    get_park_factor,
)


@dataclass
class TotalsProjection:
    away: TeamRunProjection
    home: TeamRunProjection
    park: ParkFactorResult
    market: MarketTotal
    market_edge: MarketEdge
    projected_total: float
    confidence: float
    data_quality: str
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
            "market_total": (
                None
                if self.market.total is None
                else round(
                    self.market.total,
                    2,
                )
            ),
            "edge": (
                None
                if self.market_edge.edge is None
                else round(
                    self.market_edge.edge,
                    2,
                )
            ),
            "absolute_edge": (
                None
                if (
                    self.market_edge.absolute_edge
                    is None
                )
                else round(
                    self.market_edge.absolute_edge,
                    2,
                )
            ),
            "direction": (
                self.market_edge.direction
            ),
            "confidence": round(
                self.confidence,
                1,
            ),
            "data_quality": (
                self.data_quality
            ),
            "market_status": (
                self.market_edge.status
            ),
            "recommendation": (
                self.market_edge.recommendation
            ),
            "park": self.park.to_dict(),
            "market": self.market.to_dict(),
            "market_edge": (
                self.market_edge.to_dict()
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
    Totals v1 confidence measures input completeness,
    not wager strength.
    """

    return clamp(
        40.0
        + (
            data_points * 4.0
        ),
        40.0,
        78.0,
    )


def data_quality_label(
    data_points: int,
) -> str:
    if data_points >= 11:
        return "EXCELLENT"

    if data_points >= 8:
        return "GOOD"

    if data_points >= 5:
        return "FAIR"

    return "LIMITED"


def calculate_game_data_points(
    *,
    away_projection: TeamRunProjection,
    home_projection: TeamRunProjection,
    park: ParkFactorResult,
) -> int:
    """
    Count unique game-level model inputs.

    Park is already included in each team projection,
    so one duplicated park point is removed here.
    """

    team_projection_points = (
        away_projection.data_points
        + home_projection.data_points
    )

    duplicated_park_points = (
        1
        if park.available
        else 0
    )

    return max(
        0,
        team_projection_points
        - duplicated_park_points,
    )


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

    park = get_park_factor(
        home_team
    )

    away_projection = project_team_runs(
        team_profile=away_team,
        opposing_pitcher=home_pitcher,
        park=park,
        is_home=False,
    )

    home_projection = project_team_runs(
        team_profile=home_team,
        opposing_pitcher=away_pitcher,
        park=park,
        is_home=True,
    )

    projected_total = (
        away_projection.expected_runs
        + home_projection.expected_runs
    )

    market = extract_market_total(
        game
    )

    market_edge = evaluate_market_edge(
        model_total=projected_total,
        market_total=market,
    )

    data_points = calculate_game_data_points(
        away_projection=away_projection,
        home_projection=home_projection,
        park=park,
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
            f"Projected game total is "
            f"{projected_total:.2f} runs."
        ),
        (
            f"Park factor: "
            f"{park.team} "
            f"{park.factor:.3f} "
            f"({park.source})."
        ),
        (
            f"Projection uses {data_points} "
            f"unique offense, starter and park inputs."
        ),
        (
            "Bullpen, weather and confirmed lineups "
            "are not yet included."
        ),
    ]

    if market.available:
        reasons.append(
            (
                f"Market total is "
                f"{market.total:.2f}; "
                f"model edge is "
                f"{market_edge.edge:+.2f} runs."
            )
        )
    else:
        reasons.append(
            "No sportsbook total was available."
        )

    result = TotalsProjection(
        away=away_projection,
        home=home_projection,
        park=park,
        market=market,
        market_edge=market_edge,
        projected_total=projected_total,
        confidence=confidence,
        data_quality=quality,
        reasons=reasons,
    )

    return result.to_dict()
