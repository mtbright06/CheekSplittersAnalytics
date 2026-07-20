from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.mlb.bullpen.bullpen_model import (
    BullpenProjection,
    build_bullpen_projection,
)
from engine.mlb.bullpen.game_adjustment import (
    GameBullpenAdjustment,
    apply_bullpen_adjustment,
    build_game_bullpen_adjustment,
)
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

from engine.mlb.totals.recommendation import (
    TotalsRecommendation,
    build_totals_recommendation,
)
from engine.mlb.totals.explanation import (
    TotalsExplanation,
    build_totals_explanation,
)

@dataclass
class TotalsProjection:
    away: TeamRunProjection
    home: TeamRunProjection

    away_bullpen: BullpenProjection
    home_bullpen: BullpenProjection
    bullpen: GameBullpenAdjustment

    park: ParkFactorResult
    market: MarketTotal
    market_edge: MarketEdge
    recommendation: TotalsRecommendation
    explanation: TotalsExplanation

    starter_based_total: float
    bullpen_adjustment: float
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
            "starter_based_total": round(
                self.starter_based_total,
                2,
            ),
            "bullpen_adjustment": round(
                self.bullpen_adjustment,
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
                if self.market_edge.absolute_edge is None
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

            "selection": (
                self.recommendation.selection
            ),
            "recommendation": (
                self.recommendation.recommendation
            ),
            "recommendation_score": (
                round(
                    self.recommendation.recommendation_score,
                    1,
                )
            ),
            "betting_confidence": (
                self.recommendation.confidence
            ),
            "stars": self.recommendation.stars,
            "actionable": (
                self.recommendation.actionable
            ),

            "park": self.park.to_dict(),
            "market": self.market.to_dict(),
            "market_edge": (
                self.market_edge.to_dict()
            ),

            "betting_recommendation": (
                self.recommendation.to_dict()
            ),
            "explanation": (
                self.explanation.to_dict()
            ),

            "away_projection": (
                self.away.to_dict()
            ),
            "home_projection": (
                self.home.to_dict()
            ),
            "away_bullpen": (
                bullpen_projection_to_dict(
                    self.away_bullpen
                )
            ),
            "home_bullpen": (
                bullpen_projection_to_dict(
                    self.home_bullpen
                )
            ),
            "bullpen": (
                game_bullpen_to_dict(
                    self.bullpen
                )
            ),
            "reasons": self.reasons,
        }


def confidence_from_data_points(
    data_points: int,
) -> float:
    """
    Totals confidence measures input completeness,
    not wager strength.

    The current cap remains 78 so bullpen integration
    does not unexpectedly change the established
    confidence scale during Sprint 036.
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
    Count unique offense, starter and park inputs.

    Park is included in each team projection, so one
    duplicated park point is removed here.

    Bullpen inputs are intentionally tracked separately
    during Sprint 036 so existing confidence behavior
    remains stable.
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

    bullpens = game.get(
        "bullpen",
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

    away_bullpen_profile = bullpens.get(
        "away",
        {},
    )

    home_bullpen_profile = bullpens.get(
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

    starter_based_total = (
        away_projection.expected_runs
        + home_projection.expected_runs
    )

    away_bullpen = build_bullpen_projection_from_profile(
        team=away_projection.team,
        profile=away_bullpen_profile,
    )

    home_bullpen = build_bullpen_projection_from_profile(
        team=home_projection.team,
        profile=home_bullpen_profile,
    )

    bullpen_adjustment = (
        build_game_bullpen_adjustment(
            away_bullpen=away_bullpen,
            home_bullpen=home_bullpen,
        )
    )

    projected_total = apply_bullpen_adjustment(
        starter_based_total=starter_based_total,
        bullpen_adjustment=bullpen_adjustment,
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

    market_payload = (
        game.get("odds", {}).get(
            "totals",
            {},
        )
        if isinstance(
            game.get("odds"),
            dict,
        )
        else {}
    )

    recommendation = build_totals_recommendation(
        direction=market_edge.direction,
        absolute_edge=market_edge.absolute_edge,
        model_confidence=confidence,
        data_quality=quality,
        bullpen_confidence=(
            bullpen_adjustment.confidence
        ),
        market_payload=market_payload,
    )

    reasons = build_projection_reasons(
        away_projection=away_projection,
        home_projection=home_projection,
        starter_based_total=starter_based_total,
        bullpen_adjustment=bullpen_adjustment,
        projected_total=projected_total,
        park=park,
        market=market,
        market_edge=market_edge,
        data_points=data_points,
    )

    explanation = build_totals_explanation(
        away_projection=away_projection,
        home_projection=home_projection,
        starter_based_total=starter_based_total,
        bullpen_adjustment=bullpen_adjustment,
        projected_total=projected_total,
        park=park,
        market=market,
        market_edge=market_edge,
        recommendation=recommendation,
        data_points=data_points,
    )

    result = TotalsProjection(
        away=away_projection,
        home=home_projection,
        away_bullpen=away_bullpen,
        home_bullpen=home_bullpen,
        bullpen=bullpen_adjustment,
        park=park,
        market=market,
        market_edge=market_edge,
        recommendation=recommendation,
        explanation=explanation,
        starter_based_total=starter_based_total,
        bullpen_adjustment=(
            bullpen_adjustment.combined_adjustment
        ),
        projected_total=projected_total,
        confidence=confidence,
        data_quality=quality,
        reasons=reasons,
    )

    return result.to_dict()


def build_bullpen_projection_from_profile(
    *,
    team: str,
    profile: dict[str, Any] | None,
) -> BullpenProjection:
    """
    Convert a game bullpen payload into a BullpenProjection.

    Missing bullpen data produces a neutral fallback rather
    than preventing the totals projection from running.
    """

    profile = profile or {}

    return build_bullpen_projection(
        team=team,
        season_era=to_optional_float(
            profile.get(
                "season_era"
            )
        ),
        season_whip=to_optional_float(
            profile.get(
                "season_whip"
            )
        ),
        last7_era=to_optional_float(
            first_available(
                profile,
                "last7_era",
                "last_7_era",
            )
        ),
        innings_last3=to_float(
            first_available(
                profile,
                "innings_last3",
                "innings_last_3",
            ),
            default=0.0,
        ),
        closer_available=to_bool(
            profile.get(
                "closer_available"
            ),
            default=True,
        ),
        setup_available=to_bool(
            first_available(
                profile,
                "setup_available",
                "setup_reliever_available",
            ),
            default=True,
        ),
    )


def build_projection_reasons(
    *,
    away_projection: TeamRunProjection,
    home_projection: TeamRunProjection,
    starter_based_total: float,
    bullpen_adjustment: GameBullpenAdjustment,
    projected_total: float,
    park: ParkFactorResult,
    market: MarketTotal,
    market_edge: MarketEdge,
    data_points: int,
) -> list[str]:
    reasons = [
        (
            f"Starter-based projected score: "
            f"{away_projection.team} "
            f"{away_projection.expected_runs:.2f}, "
            f"{home_projection.team} "
            f"{home_projection.expected_runs:.2f}."
        ),
        (
            f"Starter-based game total is "
            f"{starter_based_total:.2f} runs."
        ),
        (
            f"Away bullpen adjustment: "
            f"{bullpen_adjustment.away_adjustment:+.2f} runs."
        ),
        (
            f"Home bullpen adjustment: "
            f"{bullpen_adjustment.home_adjustment:+.2f} runs."
        ),
        (
            f"Combined bullpen adjustment: "
            f"{bullpen_adjustment.combined_adjustment:+.2f} runs."
        ),
        (
            f"Final projected game total is "
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
            f"Bullpen data status is "
            f"{bullpen_adjustment.status} with "
            f"{bullpen_adjustment.confidence:.1f} confidence."
        ),
        (
            "Weather and confirmed lineups "
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

    return reasons


def bullpen_projection_to_dict(
    projection: BullpenProjection,
) -> dict[str, Any]:
    return {
        "team": projection.team,
        "quality_rating": (
            projection.quality.rating
        ),
        "quality_score": (
            projection.quality.quality_score
        ),
        "season_era": (
            projection.quality.season_era
        ),
        "season_whip": (
            projection.quality.season_whip
        ),
        "last7_era": (
            projection.quality.last7_era
        ),
        "innings_last3": (
            projection.fatigue.innings_last3
        ),
        "fatigue_rating": (
            projection.fatigue.rating
        ),
        "closer_available": (
            projection.closer_available
        ),
        "setup_available": (
            projection.setup_available
        ),
        "quality_adjustment": (
            projection.quality_adjustment
        ),
        "fatigue_adjustment": (
            projection.fatigue_adjustment
        ),
        "availability_adjustment": (
            projection.availability_adjustment
        ),
        "total_run_adjustment": (
            projection.total_run_adjustment
        ),
        "confidence": (
            projection.confidence
        ),
        "data_quality": (
            projection.data_quality
        ),
        "status": (
            projection.status
        ),
    }


def game_bullpen_to_dict(
    adjustment: GameBullpenAdjustment,
) -> dict[str, Any]:
    return {
        "away_team": (
            adjustment.away_team
        ),
        "home_team": (
            adjustment.home_team
        ),
        "away_adjustment": (
            adjustment.away_adjustment
        ),
        "home_adjustment": (
            adjustment.home_adjustment
        ),
        "combined_adjustment": (
            adjustment.combined_adjustment
        ),
        "confidence": (
            adjustment.confidence
        ),
        "data_quality": (
            adjustment.data_quality
        ),
        "status": (
            adjustment.status
        ),
    }


def first_available(
    mapping: dict[str, Any],
    *keys: str,
) -> Any:
    for key in keys:
        value = mapping.get(
            key
        )

        if value is not None:
            return value

    return None


def to_optional_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def to_float(
    value: Any,
    *,
    default: float,
) -> float:
    parsed = to_optional_float(
        value
    )

    if parsed is None:
        return default

    return parsed


def to_bool(
    value: Any,
    *,
    default: bool,
) -> bool:
    if value is None:
        return default

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        normalized = (
            value.strip().lower()
        )

        if normalized in {
            "true",
            "yes",
            "y",
            "1",
            "available",
        }:
            return True

        if normalized in {
            "false",
            "no",
            "n",
            "0",
            "unavailable",
        }:
            return False

    return bool(
        value
    )
