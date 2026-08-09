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


def _baseline_value(
    league_baselines: dict[str, Any] | None,
    section: str,
    key: str,
    fallback: float,
) -> float:
    section_payload = (league_baselines or {}).get(section, {})
    value = safe_float(section_payload.get(key))
    if value is None or value <= 0:
        return fallback
    return value


@dataclass
class TeamRunProjection:
    team: str
    expected_runs: float
    baseline_runs: float
    offense_adjustment: float
    starter_adjustment: float
    starter_context_adjustment: float
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
            "starter_context_adjustment": round(
                self.starter_context_adjustment,
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


def extract_obp(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("obp"),
        offense.get("OBP"),
    )


def extract_slg(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("slg"),
        offense.get("SLG"),
    )


def extract_iso(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("iso"),
        offense.get("ISO"),
    )


def extract_hr_per_game(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    return first_number(
        offense.get("hr_per_game"),
        offense.get("hr_game"),
    )


def extract_discipline(
    team_profile: dict[str, Any],
) -> float | None:
    offense = team_profile.get(
        "offense",
        {},
    )

    bb_rate = first_number(
        offense.get("bb_rate"),
        offense.get("BB%"),
    )
    k_rate = first_number(
        offense.get("k_rate"),
        offense.get("K%"),
    )

    if bb_rate is None or k_rate is None:
        return None

    return bb_rate - k_rate


def _active_weighted_average(
    components: dict[str, float | None],
    weights: dict[str, float],
) -> tuple[float | None, list[str]]:
    active = [
        name
        for name in weights
        if components.get(name) is not None
    ]

    active_weight = sum(weights[name] for name in active)

    if active_weight <= 0:
        return None, []

    return (
        sum(
            components[name] * weights[name]
            for name in active
            if components[name] is not None
        ) / active_weight,
        active,
    )


def calculate_offense_adjustment(
    team_profile: dict[str, Any],
    *,
    league_baselines: dict[str, Any] | None = None,
) -> tuple[float, int, list[str]]:
    components: dict[str, float | None] = {
        "realized_scoring": None,
        "skill": None,
    }
    reasons: list[str] = []
    league_runs_per_team = _baseline_value(
        league_baselines,
        "offense",
        "runs_per_team",
        LEAGUE_RUNS_PER_TEAM,
    )
    league_obp = _baseline_value(
        league_baselines,
        "offense",
        "obp",
        0.320,
    )
    league_slg = _baseline_value(
        league_baselines,
        "offense",
        "slg",
        0.400,
    )
    league_ops = _baseline_value(
        league_baselines,
        "offense",
        "ops",
        0.720,
    )
    league_iso = _baseline_value(
        league_baselines,
        "offense",
        "iso",
        0.160,
    )
    league_hr_per_game = _baseline_value(
        league_baselines,
        "offense",
        "hr_per_game",
        1.10,
    )
    league_discipline = _baseline_value(
        league_baselines,
        "offense",
        "bb_minus_k_rate",
        -14.0,
    )

    runs_per_game = extract_runs_per_game(
        team_profile
    )

    if runs_per_game is not None:
        rpg_adjustment = (
            runs_per_game
            - league_runs_per_team
        )

        components["realized_scoring"] = clamp(
            rpg_adjustment,
            -1.10,
            1.10,
        )

        reasons.append(
            f"Offense averages "
            f"{runs_per_game:.2f} runs per game."
        )

    obp = extract_obp(
        team_profile
    )
    iso = extract_iso(
        team_profile
    )
    hr_per_game = extract_hr_per_game(
        team_profile
    )
    discipline = extract_discipline(
        team_profile
    )

    skill_components: dict[str, float | None] = {
        "on_base": None,
        "power": None,
        "discipline": None,
        "ops_fallback": None,
    }

    if obp is not None:
        skill_components["on_base"] = clamp(
            (obp - league_obp) * 9.0,
            -0.55,
            0.55,
        )
        reasons.append(
            f"Offense OBP is "
            f"{obp:.3f}."
        )

    if iso is not None:
        skill_components["power"] = clamp(
            (iso - league_iso) * 5.0,
            -0.45,
            0.45,
        )
        reasons.append(
            f"Offense ISO is "
            f"{iso:.3f}."
        )
    elif hr_per_game is not None:
        skill_components["power"] = clamp(
            (hr_per_game - league_hr_per_game) * 0.90,
            -0.45,
            0.45,
        )
        reasons.append(
            f"Offense hits "
            f"{hr_per_game:.2f} HR per game."
        )
    else:
        slg = extract_slg(
            team_profile
        )
        if slg is not None:
            skill_components["power"] = clamp(
                (slg - league_slg) * 4.0,
                -0.45,
                0.45,
            )
            reasons.append(
                f"Offense SLG is "
                f"{slg:.3f}."
            )

    if discipline is not None:
        skill_components["discipline"] = clamp(
            (discipline - league_discipline) * 0.04,
            -0.25,
            0.25,
        )
        reasons.append(
            f"Offense BB-K rate is "
            f"{discipline:.1f} percentage points."
        )

    if all(
        skill_components[name] is None
        for name in ("on_base", "power", "discipline")
    ):
        ops = extract_ops(
            team_profile
        )
        if ops is not None:
            skill_components["ops_fallback"] = clamp(
                (ops - league_ops) * 4.5,
                -0.65,
                0.65,
            )
            reasons.append(
                f"Offense OPS fallback is "
                f"{ops:.3f}."
            )

    skill_adjustment, active_skill_inputs = _active_weighted_average(
        skill_components,
        {
            "on_base": 0.45,
            "power": 0.35,
            "discipline": 0.20,
            "ops_fallback": 1.00,
        },
    )

    if skill_adjustment is not None:
        components["skill"] = clamp(
            skill_adjustment,
            -0.55,
            0.55,
        )
        reasons.append(
            "Offense skill composite uses "
            f"{', '.join(active_skill_inputs)}."
        )

    offense_adjustment, active_inputs = _active_weighted_average(
        components,
        {
            "realized_scoring": 0.60,
            "skill": 0.40,
        },
    )

    if offense_adjustment is None:
        return (
            0.0,
            0,
            [
                "Advanced offense inputs unavailable; "
                "league-average offense used."
            ],
        )

    return (
        clamp(
            offense_adjustment,
            -1.00,
            1.00,
        ),
        len(active_inputs),
        reasons,
    )


def calculate_starter_adjustment(
    opposing_pitcher: dict[str, Any],
    *,
    league_baselines: dict[str, Any] | None = None,
) -> tuple[float, int, list[str]]:
    adjustments: list[float] = []
    reasons: list[str] = []
    league_starter_era = _baseline_value(
        league_baselines,
        "starter",
        "era",
        LEAGUE_STARTER_ERA,
    )
    league_starter_whip = _baseline_value(
        league_baselines,
        "starter",
        "whip",
        LEAGUE_STARTER_WHIP,
    )
    league_starter_hr9 = _baseline_value(
        league_baselines,
        "starter",
        "hr9",
        LEAGUE_HR9,
    )
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
            - league_starter_era
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
            - league_starter_whip
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
            - league_starter_hr9
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


def calculate_starter_context_adjustment(
    opposing_pitcher: dict[str, Any],
) -> tuple[float, int, list[str]]:
    """
    Estimate today's starter-condition impact in full-game runs.

    This is intentionally smaller than First 5 because full-game totals
    already include an explicit bullpen run adjustment. Role risk here
    represents transfer uncertainty, not a claim that more bullpen innings
    are automatically worse.
    """

    adjustment = 0.0
    reasons: list[str] = []
    data_points = 0

    days_rest = safe_float(opposing_pitcher.get("days_rest"))
    previous_ip = safe_float(opposing_pitcher.get("previous_start_ip"))
    previous_pitches = safe_float(
        opposing_pitcher.get("previous_start_pitch_count")
    )
    average_start_ip = safe_float(opposing_pitcher.get("average_start_ip"))
    role_context = opposing_pitcher.get("role_context")

    if days_rest is not None:
        data_points += 1
        if days_rest <= 3:
            adjustment += 0.15
            reasons.append("Starter is on very short rest.")
        elif days_rest == 4:
            adjustment += 0.08
            reasons.append("Starter is on short rest.")
        elif days_rest == 7:
            adjustment -= 0.03
            reasons.append("Starter has one extra rest day.")

    if previous_pitches is not None and days_rest is not None:
        data_points += 1
        if previous_pitches >= 110 and days_rest <= 5:
            adjustment += 0.10
            reasons.append("Starter carried a heavy previous pitch count.")
        elif previous_pitches >= 100 and days_rest <= 4:
            adjustment += 0.06
            reasons.append("Starter had elevated workload on short rest.")

    if (
        previous_ip is not None
        and previous_ip >= 7.0
        and days_rest is not None
        and days_rest <= 5
    ):
        data_points += 1
        adjustment += 0.05
        reasons.append("Starter worked deep into the previous start.")

    if role_context in {
        "opener_risk",
        "short_start_role_risk",
        "limited_starting_role",
        "established_starter",
    }:
        data_points += 1

    if role_context == "opener_risk":
        adjustment += 0.12
        reasons.append("Starter role carries opener risk.")
    elif role_context == "short_start_role_risk":
        adjustment += 0.08
        reasons.append("Starter role carries short-start risk.")
    elif role_context == "limited_starting_role":
        adjustment += 0.05
        reasons.append("Starter role has limited-start evidence.")

    if (
        average_start_ip is not None
        and average_start_ip < 4.0
        and role_context == "established_starter"
    ):
        data_points += 1
        adjustment += 0.05
        reasons.append("Starter has limited average start length.")

    adjustment = clamp(
        adjustment,
        -0.05,
        0.30,
    )

    return (
        adjustment,
        data_points,
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
    league_baselines: dict[str, Any] | None = None,
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
        team_profile,
        league_baselines=league_baselines,
    )

    (
        starter_adjustment,
        starter_points,
        starter_reasons,
    ) = calculate_starter_adjustment(
        opposing_pitcher,
        league_baselines=league_baselines,
    )

    (
        starter_context_adjustment,
        starter_context_points,
        starter_context_reasons,
    ) = calculate_starter_context_adjustment(
        opposing_pitcher,
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
    league_runs_per_team = _baseline_value(
        league_baselines,
        "offense",
        "runs_per_team",
        LEAGUE_RUNS_PER_TEAM,
    )

    expected_runs = (
        league_runs_per_team
        + offense_adjustment
        + starter_adjustment
        + starter_context_adjustment
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
        *starter_context_reasons,
        *park_reasons,
    ]

    if is_home:
        reasons.append(
            "Home-field run adjustment applied."
        )

    return TeamRunProjection(
        team=team_name,
        expected_runs=expected_runs,
        baseline_runs=league_runs_per_team,
        offense_adjustment=offense_adjustment,
        starter_adjustment=starter_adjustment,
        starter_context_adjustment=starter_context_adjustment,
        park_adjustment=park_adjustment,
        park_factor=park.factor,
        home_adjustment=home_adjustment,
        data_points=(
            offense_points
            + starter_points
            + starter_context_points
            + park_points
        ),
        reasons=reasons,
    )
