from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.mlb.totals.helpers import (
    clamp,
    first_number,
    safe_float,
)
from engine.model.pitcher_stabilization import (
    stabilize_pitcher_metrics,
)
from engine.mlb.totals.park_factors import (
    ParkFactorResult,
)


LEAGUE_RUNS_PER_TEAM = 4.45
LEAGUE_STARTER_ERA = 4.20
LEAGUE_STARTER_WHIP = 1.30
LEAGUE_HR9 = 1.15

HOME_FIELD_RUN_BONUS = 0.12

# Converts the park multiplier into a per-team run adjustment.
#
# Examples:
# 1.05 -> +0.20 runs
# 0.95 -> -0.20 runs
# 1.18 -> +0.72 runs
PARK_RUN_MULTIPLIER = 4.00


@dataclass
class TeamRunProjection:
    team: str
    expected_runs: float
    baseline_runs: float
    offense_adjustment: float
    starter_adjustment: float
    park_adjustment: float
    park_factor: float
    home_adjustment: float
    data_points: int
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "expected_runs": round(
                self.expected_runs,
                2,
            ),
            "baseline_runs": round(
                self.baseline_runs,
                2,
            ),
            "offense_adjustment": round(
                self.offense_adjustment,
                2,
            ),
            "starter_adjustment": round(
                self.starter_adjustment,
                2,
            ),
            "park_adjustment": round(
                self.park_adjustment,
                2,
            ),
            "park_factor": round(
                self.park_factor,
                3,
            ),
            "home_adjustment": round(
                self.home_adjustment,
                2,
            ),
            "data_points": self.data_points,
            "reasons": self.reasons,
        }


def extract_runs_per_game(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("runs_per_game"),
        offense.get("rpg"),
        offense.get("runs_game"),
        offense.get("runsPerGame"),
        team_profile.get("runs_per_game"),
    )


def extract_ops(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("ops"),
        offense.get("OPS"),
    )


def extract_wrc_plus(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("wrc_plus"),
        offense.get("wrc+"),
        offense.get("wRC+"),
    )


def calculate_offense_adjustment(
    team_profile: dict[str, Any],
) -> tuple[float, int, list[str]]:
    adjustments: list[float] = []
    reasons: list[str] = []

    runs_per_game = extract_runs_per_game(
        team_profile
    )

    if runs_per_game is not None:
        rpg_adjustment = (
            runs_per_game
            - LEAGUE_RUNS_PER_TEAM
        )

        adjustments.append(
            clamp(
                rpg_adjustment,
                -1.25,
                1.25,
            )
        )

        reasons.append(
            f"Offense averages "
            f"{runs_per_game:.2f} runs per game."
        )

    wrc_plus = extract_wrc_plus(
        team_profile
    )

    if wrc_plus is not None:
        wrc_adjustment = (
            (wrc_plus - 100.0)
            / 100.0
        ) * 1.35

        adjustments.append(
            clamp(
                wrc_adjustment,
                -0.80,
                0.80,
            )
        )

        reasons.append(
            f"Offense wRC+ is "
            f"{wrc_plus:.0f}."
        )

    ops = extract_ops(
        team_profile
    )

    if ops is not None:
        ops_adjustment = (
            ops - 0.720
        ) * 4.5

        adjustments.append(
            clamp(
                ops_adjustment,
                -0.65,
                0.65,
            )
        )

        reasons.append(
            f"Offense OPS is "
            f"{ops:.3f}."
        )

    if not adjustments:
        return (
            0.0,
            0,
            [
                "Advanced offense inputs unavailable; "
                "league-average offense used."
            ],
        )

    return (
        sum(adjustments)
        / len(adjustments),
        len(adjustments),
        reasons,
    )


def calculate_starter_adjustment(
    opposing_pitcher: dict[str, Any],
) -> tuple[float, int, list[str]]:
    adjustments: list[float] = []
    reasons: list[str] = []
    pitcher_metrics = dict(opposing_pitcher)
    pitcher_metrics["hr9"] = first_number(
        opposing_pitcher.get("hr9"),
        opposing_pitcher.get("hr_per_9"),
    )
    stabilized_metrics = stabilize_pitcher_metrics(
        pitcher_metrics,
    )

    era = safe_float(
        stabilized_metrics.get("era")
    )

    if era is not None:
        era_adjustment = (
            era
            - LEAGUE_STARTER_ERA
        ) * 0.42

        adjustments.append(
            clamp(
                era_adjustment,
                -1.15,
                1.15,
            )
        )

        reasons.append(
            f"Stabilized opposing starter ERA is "
            f"{era:.2f}."
        )

    whip = safe_float(
        stabilized_metrics.get("whip")
    )

    if whip is not None:
        whip_adjustment = (
            whip
            - LEAGUE_STARTER_WHIP
        ) * 1.35

        adjustments.append(
            clamp(
                whip_adjustment,
                -0.75,
                0.75,
            )
        )

        reasons.append(
            f"Stabilized opposing starter WHIP is "
            f"{whip:.2f}."
        )

    hr9 = safe_float(stabilized_metrics.get("hr9"))

    if hr9 is not None:
        hr_adjustment = (
            hr9
            - LEAGUE_HR9
        ) * 0.45

        adjustments.append(
            clamp(
                hr_adjustment,
                -0.50,
                0.50,
            )
        )

        reasons.append(
            f"Stabilized opposing starter HR/9 is "
            f"{hr9:.2f}."
        )

    if not adjustments:
        return (
            0.0,
            0,
            [
                "Starter metrics unavailable; "
                "league-average starter used."
            ],
        )

    return (
        sum(adjustments)
        / len(adjustments),
        len(adjustments),
        reasons,
    )


def calculate_park_adjustment(
    park: ParkFactorResult,
) -> tuple[float, int, list[str]]:
    adjustment = (
        park.factor - 1.00
    ) * PARK_RUN_MULTIPLIER

    adjustment = clamp(
        adjustment,
        -0.80,
        0.80,
    )

    if not park.available:
        return (
            0.0,
            0,
            [
                "Park factor unavailable; "
                "neutral park used."
            ],
        )

    if adjustment > 0.01:
        description = "run-friendly"
    elif adjustment < -0.01:
        description = "run-suppressing"
    else:
        description = "approximately neutral"

    return (
        adjustment,
        1,
        [
            (
                f"Home park factor is "
                f"{park.factor:.3f} and is "
                f"{description}."
            )
        ],
    )


def project_team_runs(
    *,
    team_profile: dict[str, Any],
    opposing_pitcher: dict[str, Any],
    park: ParkFactorResult,
    is_home: bool,
) -> TeamRunProjection:
    team_name = str(
        team_profile.get("name")
        or team_profile.get("abbreviation")
        or "Unknown Team"
    )

    (
        offense_adjustment,
        offense_points,
        offense_reasons,
    ) = calculate_offense_adjustment(
        team_profile
    )

    (
        starter_adjustment,
        starter_points,
        starter_reasons,
    ) = calculate_starter_adjustment(
        opposing_pitcher
    )

    (
        park_adjustment,
        park_points,
        park_reasons,
    ) = calculate_park_adjustment(
        park
    )

    home_adjustment = (
        HOME_FIELD_RUN_BONUS
        if is_home
        else 0.0
    )

    expected_runs = (
        LEAGUE_RUNS_PER_TEAM
        + offense_adjustment
        + starter_adjustment
        + park_adjustment
        + home_adjustment
    )

    expected_runs = clamp(
        expected_runs,
        2.25,
        7.25,
    )

    reasons = [
        *offense_reasons,
        *starter_reasons,
        *park_reasons,
    ]

    if is_home:
        reasons.append(
            "Home-field run adjustment applied."
        )

    return TeamRunProjection(
        team=team_name,
        expected_runs=expected_runs,
        baseline_runs=LEAGUE_RUNS_PER_TEAM,
        offense_adjustment=offense_adjustment,
        starter_adjustment=starter_adjustment,
        park_adjustment=park_adjustment,
        park_factor=park.factor,
        home_adjustment=home_adjustment,
        data_points=(
            offense_points
            + starter_points
            + park_points
        ),
        reasons=reasons,
    )
