from engine.model.pitcher_stabilization import (
    PITCHER_BASELINES,
    stabilize_pitcher_stat,
)


STATIC_OFFENSE_BASELINES = {
    "runs_per_game": 4.4,
    "ops": 0.710,
    "iso": 0.160,
    "hr_per_game": 1.10,
    "bb_minus_k_rate": -14.0,
}

STATIC_BULLPEN_BASELINES = {
    "era": 4.10,
    "whip": 1.30,
}


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def offense_score(offense, *, league_baselines=None):
    return offense_breakdown(
        offense,
        league_baselines=league_baselines,
    )["offense_score"]


def offense_breakdown(offense, *, league_baselines=None):
    offense_baselines = (league_baselines or {}).get("offense", {})
    rpg_average = to_float(
        offense_baselines.get("runs_per_game")
    ) or STATIC_OFFENSE_BASELINES["runs_per_game"]
    ops_average = to_float(
        offense_baselines.get("ops")
    ) or STATIC_OFFENSE_BASELINES["ops"]
    iso_average = to_float(
        offense_baselines.get("iso")
    ) or STATIC_OFFENSE_BASELINES["iso"]
    hrpg_average = to_float(
        offense_baselines.get("hr_per_game")
    ) or STATIC_OFFENSE_BASELINES["hr_per_game"]
    discipline_average = to_float(
        offense_baselines.get("bb_minus_k_rate")
    ) or STATIC_OFFENSE_BASELINES["bb_minus_k_rate"]

    if not offense:
        return {
            "offense_score": 50.0,
            "run_creation": 50.0,
            "power": 50.0,
            "plate_discipline": 50.0,
            "active_subcomponents": [],
            "missing_inputs": [
                "runs_per_game",
                "ops",
                "iso",
                "hr_per_game",
                "bb_rate",
                "k_rate",
            ],
        }

    run_creation_inputs = []
    missing_inputs = []

    rpg = to_float(offense.get("runs_per_game"))
    ops = to_float(offense.get("ops"))
    hrpg = to_float(offense.get("hr_per_game"))
    iso = to_float(offense.get("iso"))
    k_rate = to_float(offense.get("k_rate"))
    bb_rate = to_float(offense.get("bb_rate"))

    if rpg is not None:
        run_creation_inputs.append(
            normalize_metric(rpg, average=rpg_average, half_range=1.0)
        )
    else:
        missing_inputs.append("runs_per_game")

    if ops is not None:
        run_creation_inputs.append(
            normalize_metric(ops, average=ops_average, half_range=0.080)
        )
    else:
        missing_inputs.append("ops")

    run_creation = active_average(run_creation_inputs)

    if iso is not None:
        power = normalize_metric(iso, average=iso_average, half_range=0.040)
        power_source = "iso"
    elif hrpg is not None:
        power = normalize_metric(hrpg, average=hrpg_average, half_range=0.30)
        power_source = "hr_per_game"
        missing_inputs.append("iso")
    else:
        power = None
        power_source = None
        missing_inputs.extend(["iso", "hr_per_game"])

    if bb_rate is not None and k_rate is not None:
        plate_discipline = normalize_metric(
            bb_rate - k_rate,
            average=discipline_average,
            half_range=6.0,
        )
    else:
        plate_discipline = None
        if bb_rate is None:
            missing_inputs.append("bb_rate")
        if k_rate is None:
            missing_inputs.append("k_rate")

    subcomponents = {
        "run_creation": run_creation,
        "power": power,
        "plate_discipline": plate_discipline,
    }
    weights = {
        "run_creation": 0.45,
        "power": 0.30,
        "plate_discipline": 0.25,
    }
    active_weight = sum(
        weight
        for name, weight in weights.items()
        if subcomponents[name] is not None
    )

    if active_weight <= 0:
        score = 50.0
        active_subcomponents = []
    else:
        score = sum(
            subcomponents[name] * weight
            for name, weight in weights.items()
            if subcomponents[name] is not None
        ) / active_weight
        active_subcomponents = [
            name
            for name in weights
            if subcomponents[name] is not None
        ]

    return {
        "offense_score": round(clamp(score), 1),
        "run_creation": (
            round(run_creation, 1)
            if run_creation is not None
            else 50.0
        ),
        "power": round(power, 1) if power is not None else 50.0,
        "power_source": power_source,
        "plate_discipline": (
            round(plate_discipline, 1)
            if plate_discipline is not None
            else 50.0
        ),
        "active_subcomponents": active_subcomponents,
        "missing_inputs": sorted(set(missing_inputs)),
        "baselines": {
            "runs_per_game": round(rpg_average, 3),
            "ops": round(ops_average, 3),
            "iso": round(iso_average, 3),
            "hr_per_game": round(hrpg_average, 3),
            "bb_minus_k_rate": round(discipline_average, 3),
        },
    }


def normalize_metric(value, *, average, half_range):
    return clamp(50 + ((value - average) / half_range) * 20)


def active_average(values):
    active = [
        value
        for value in values
        if value is not None
    ]

    if not active:
        return None

    return sum(active) / len(active)


def to_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def starting_pitcher_score(pitcher, *, league_baselines=None):
    return starting_pitcher_breakdown(
        pitcher,
        league_baselines=league_baselines,
    )["starting_pitching_score"]


def starting_pitcher_breakdown(pitcher, *, league_baselines=None):
    """Build a cleaner starter-quality score from non-duplicative buckets."""
    if not pitcher or pitcher.get("name") == "Unknown Starter":
        return neutral_starting_pitcher_breakdown()

    innings_pitched = pitcher.get("ip")

    if innings_pitched is None or innings_pitched <= 0:
        return neutral_starting_pitcher_breakdown(
            missing_inputs=["ip"],
        )

    starter_baselines = {
        **PITCHER_BASELINES,
        **(
            (league_baselines or {}).get("starter")
            or {}
        ),
    }

    era = stabilize_pitcher_stat(
        observed_value=pitcher.get("era"),
        innings_pitched=innings_pitched,
        league_average=starter_baselines["era"],
    )
    whip = stabilize_pitcher_stat(
        observed_value=pitcher.get("whip"),
        innings_pitched=innings_pitched,
        league_average=starter_baselines["whip"],
    )
    hr9 = stabilize_pitcher_stat(
        observed_value=pitcher.get("hr9"),
        innings_pitched=innings_pitched,
        league_average=starter_baselines["hr9"],
    )
    k_bb_pct = stabilize_pitcher_stat(
        observed_value=pitcher.get("k_bb_pct"),
        innings_pitched=innings_pitched,
        league_average=starter_baselines["k_bb_pct"],
    )

    missing_inputs = []
    subcomponents = {}

    if era is not None:
        subcomponents["run_prevention"] = inverse_metric_score(
            era,
            average=starter_baselines["era"],
            half_range=1.75,
        )
    else:
        missing_inputs.append("era")

    if whip is not None:
        subcomponents["baserunner_control"] = inverse_metric_score(
            whip,
            average=starter_baselines["whip"],
            half_range=0.35,
        )
    else:
        missing_inputs.append("whip")

    if k_bb_pct is not None:
        subcomponents["strikeout_command"] = normalize_metric(
            k_bb_pct,
            average=starter_baselines["k_bb_pct"],
            half_range=12.0,
        )
    else:
        missing_inputs.append("k_bb_pct")

    if hr9 is not None:
        subcomponents["damage_suppression"] = inverse_metric_score(
            hr9,
            average=starter_baselines["hr9"],
            half_range=0.70,
        )
    else:
        missing_inputs.append("hr9")

    weights = {
        "run_prevention": 0.35,
        "baserunner_control": 0.25,
        "strikeout_command": 0.25,
        "damage_suppression": 0.15,
    }
    active_weight = sum(
        weight
        for name, weight in weights.items()
        if name in subcomponents
    )

    if active_weight <= 0:
        return neutral_starting_pitcher_breakdown(
            missing_inputs=missing_inputs,
        )

    base_score = sum(
        subcomponents[name] * weight
        for name, weight in weights.items()
        if name in subcomponents
    ) / active_weight
    context = starter_context_adjustment(pitcher)
    score = base_score + context["adjustment"]

    return {
        "starting_pitching_score": round(clamp(score), 1),
        "starter_quality_score": round(clamp(base_score), 1),
        "starter_context_adjustment": context["adjustment"],
        "starter_context_reasons": context["reasons"],
        "run_prevention": round(
            subcomponents.get("run_prevention", 50.0),
            1,
        ),
        "baserunner_control": round(
            subcomponents.get("baserunner_control", 50.0),
            1,
        ),
        "strikeout_command": round(
            subcomponents.get("strikeout_command", 50.0),
            1,
        ),
        "damage_suppression": round(
            subcomponents.get("damage_suppression", 50.0),
            1,
        ),
        "active_subcomponents": [
            name
            for name in weights
            if name in subcomponents
        ],
        "missing_inputs": sorted(set(missing_inputs)),
        "baselines": {
            "era": round(starter_baselines["era"], 3),
            "whip": round(starter_baselines["whip"], 3),
            "hr9": round(starter_baselines["hr9"], 3),
            "k_bb_pct": round(starter_baselines["k_bb_pct"], 3),
        },
    }


def neutral_starting_pitcher_breakdown(
    *,
    missing_inputs=None,
):
    return {
        "starting_pitching_score": 50.0,
        "starter_quality_score": 50.0,
        "starter_context_adjustment": 0.0,
        "starter_context_reasons": [],
        "run_prevention": 50.0,
        "baserunner_control": 50.0,
        "strikeout_command": 50.0,
        "damage_suppression": 50.0,
        "active_subcomponents": [],
        "missing_inputs": missing_inputs or [],
    }


def starter_context_adjustment(pitcher):
    adjustment = 0.0
    reasons = []

    days_rest = to_float(pitcher.get("days_rest"))
    previous_ip = to_float(pitcher.get("previous_start_ip"))
    previous_pitches = to_float(pitcher.get("previous_start_pitch_count"))
    average_start_ip = to_float(pitcher.get("average_start_ip"))
    role_context = pitcher.get("role_context")

    if days_rest is not None:
        if days_rest <= 4:
            adjustment -= 3.0
            reasons.append("short_rest")
        elif days_rest == 7:
            adjustment += 1.0
            reasons.append("extra_rest")

    if previous_pitches is not None:
        if previous_pitches >= 110 and days_rest is not None and days_rest <= 5:
            adjustment -= 2.0
            reasons.append("heavy_previous_pitch_count")
        elif previous_pitches >= 100 and days_rest is not None and days_rest <= 4:
            adjustment -= 1.5
            reasons.append("elevated_pitch_count_on_short_rest")

    if (
        previous_ip is not None
        and previous_ip >= 7.0
        and days_rest is not None
        and days_rest <= 5
    ):
        adjustment -= 1.0
        reasons.append("deep_previous_start")

    if role_context == "opener_risk":
        adjustment -= 4.0
        reasons.append("opener_risk")
    elif role_context == "short_start_role_risk":
        adjustment -= 2.0
        reasons.append("short_start_role_risk")
    elif role_context == "limited_starting_role":
        adjustment -= 1.0
        reasons.append("limited_starting_role")

    if (
        average_start_ip is not None
        and average_start_ip < 4.0
        and role_context == "established_starter"
    ):
        adjustment -= 1.0
        reasons.append("limited_average_start_length")

    adjustment = round(
        clamp(
            adjustment,
            low=-5.0,
            high=1.5,
        ),
        1,
    )

    return {
        "adjustment": adjustment,
        "reasons": sorted(set(reasons)),
    }


def inverse_metric_score(value, *, average, half_range):
    return normalize_metric(
        average - (value - average),
        average=average,
        half_range=half_range,
    )


def bullpen_score(bullpen, *, league_baselines=None):
    return bullpen_breakdown(
        bullpen,
        league_baselines=league_baselines,
    )["bullpen_score"]


def bullpen_breakdown(bullpen, *, league_baselines=None):
    bullpen_baselines = (league_baselines or {}).get("bullpen", {})
    era_average = to_float(
        bullpen_baselines.get("era")
    ) or STATIC_BULLPEN_BASELINES["era"]
    whip_average = to_float(
        bullpen_baselines.get("whip")
    ) or STATIC_BULLPEN_BASELINES["whip"]

    if not bullpen:
        return neutral_bullpen_breakdown()

    season_era = to_float(
        first_available(
            bullpen,
            "season_era",
            "era",
        )
    )
    season_whip = to_float(
        first_available(
            bullpen,
            "season_whip",
            "whip",
        )
    )
    recent_era = to_float(
        first_available(
            bullpen,
            "last7_era",
            "last_7_era",
        )
    )
    innings_last7 = to_float(
        first_available(
            bullpen,
            "innings_last7",
            "innings_last_7",
        )
    )
    innings_last3 = to_float(
        first_available(
            bullpen,
            "innings_last3",
            "innings_last_3",
        )
    )

    missing_inputs = []
    quality_components = {}

    if season_era is not None:
        quality_components["season_run_prevention"] = inverse_metric_score(
            season_era,
            average=era_average,
            half_range=1.30,
        )
    else:
        missing_inputs.append("season_era")

    if season_whip is not None:
        quality_components["baserunner_control"] = inverse_metric_score(
            season_whip,
            average=whip_average,
            half_range=0.25,
        )
    else:
        missing_inputs.append("season_whip")

    stabilized_recent_era = stabilize_recent_bullpen_era(
        recent_era=recent_era,
        season_era=season_era,
        innings_last7=innings_last7,
    )

    if stabilized_recent_era is not None:
        quality_components["recent_run_prevention"] = inverse_metric_score(
            stabilized_recent_era,
            average=era_average,
            half_range=2.00,
        )
    else:
        missing_inputs.append("last7_era")
        if recent_era is not None and innings_last7 is None:
            missing_inputs.append("innings_last7")

    quality_weights = {
        "season_run_prevention": 0.50,
        "baserunner_control": 0.30,
        "recent_run_prevention": 0.20,
    }
    active_quality_weight = sum(
        weight
        for name, weight in quality_weights.items()
        if name in quality_components
    )

    if active_quality_weight <= 0:
        quality_score = 50.0
        active_subcomponents = []
    else:
        quality_score = sum(
            quality_components[name] * weight
            for name, weight in quality_weights.items()
            if name in quality_components
        ) / active_quality_weight
        active_subcomponents = [
            name
            for name in quality_weights
            if name in quality_components
        ]

    fatigue_penalty = bullpen_fatigue_penalty(innings_last3)
    availability = bullpen_availability_penalty(bullpen)
    availability_penalty = availability["penalty"]
    score = quality_score - fatigue_penalty - availability_penalty

    return {
        "bullpen_score": round(clamp(score), 1),
        "quality_score": round(clamp(quality_score), 1),
        "season_run_prevention": round(
            quality_components.get("season_run_prevention", 50.0),
            1,
        ),
        "baserunner_control": round(
            quality_components.get("baserunner_control", 50.0),
            1,
        ),
        "recent_run_prevention": round(
            quality_components.get("recent_run_prevention", 50.0),
            1,
        ),
        "stabilized_last7_era": (
            round(stabilized_recent_era, 2)
            if stabilized_recent_era is not None
            else None
        ),
        "last7_sample_weight": bullpen_recent_sample_weight(innings_last7),
        "fatigue_penalty": round(fatigue_penalty, 1),
        "availability_penalty": round(availability_penalty, 1),
        "availability_penalty_reasons": availability["reasons"],
        "active_subcomponents": active_subcomponents,
        "missing_inputs": sorted(set(missing_inputs)),
        "baselines": {
            "era": round(era_average, 3),
            "whip": round(whip_average, 3),
        },
    }


def neutral_bullpen_breakdown():
    return {
        "bullpen_score": 50.0,
        "quality_score": 50.0,
        "season_run_prevention": 50.0,
        "baserunner_control": 50.0,
        "recent_run_prevention": 50.0,
        "stabilized_last7_era": None,
        "last7_sample_weight": 0.0,
        "fatigue_penalty": 0.0,
        "availability_penalty": 0.0,
        "availability_penalty_reasons": [],
        "active_subcomponents": [],
        "missing_inputs": [
            "season_era",
            "season_whip",
            "last7_era",
        ],
    }


def bullpen_fatigue_penalty(innings_last3):
    if innings_last3 is None:
        return 0.0

    return clamp(
        (innings_last3 - 6.0) * 0.75,
        low=0.0,
        high=6.0,
    )


def stabilize_recent_bullpen_era(
    *,
    recent_era,
    season_era,
    innings_last7,
):
    if recent_era is None:
        return None

    sample_weight = bullpen_recent_sample_weight(innings_last7)

    if sample_weight <= 0.0:
        return None

    baseline = season_era if season_era is not None else STATIC_BULLPEN_BASELINES["era"]

    return baseline + sample_weight * (recent_era - baseline)


def bullpen_recent_sample_weight(innings_last7):
    if innings_last7 is None:
        return 0.0

    return round(
        innings_last7 / (innings_last7 + 12.0),
        3,
    )


def bullpen_availability_penalty(bullpen):
    penalty = 0.0
    reasons = []

    if bullpen.get("closer_available") is False:
        penalty += 4.0
        reasons.append("closer_unavailable")

    if bullpen.get("setup_available") is False:
        penalty += 2.5
        reasons.append("setup_unavailable")

    ledger_penalty = high_leverage_workload_penalty(
        bullpen.get("evidence_ledger")
    )
    penalty += ledger_penalty["penalty"]
    reasons.extend(ledger_penalty["reasons"])

    return {
        "penalty": round(
            clamp(
                penalty,
                low=0.0,
                high=6.5,
            ),
            1,
        ),
        "reasons": sorted(set(reasons)),
    }


def high_leverage_workload_penalty(evidence_ledger):
    if not isinstance(evidence_ledger, list):
        return {
            "penalty": 0.0,
            "reasons": [],
        }

    closer_concern = False
    setup_concern = False

    for entry in evidence_ledger:
        if not isinstance(entry, dict):
            continue

        availability = entry.get("availability_evidence")
        if not isinstance(availability, dict):
            continue
        if availability.get("status") != "OBSERVED_WORKLOAD_CONCERN":
            continue
        if availability.get("source_quality") != "COMPLETE":
            continue

        role_evidence = entry.get("role_evidence")
        if not isinstance(role_evidence, dict):
            continue

        for candidate in role_evidence.get("candidate_roles", []):
            if not isinstance(candidate, dict):
                continue
            role = candidate.get("role")
            confidence = candidate.get("confidence")
            if role == "CLOSER" and confidence in {"MEDIUM", "HIGH"}:
                closer_concern = True
            elif role == "SETUP" and confidence in {"MEDIUM", "HIGH"}:
                setup_concern = True

    penalty = 0.0
    reasons = []

    if closer_concern:
        penalty += 2.0
        reasons.append("closer_observed_workload_concern")

    if setup_concern:
        penalty += 1.25
        reasons.append("setup_observed_workload_concern")

    return {
        "penalty": penalty,
        "reasons": reasons,
    }


def first_available(mapping, *keys):
    for key in keys:
        value = mapping.get(key)

        if value is not None:
            return value

    return None


def market_score(book_probability, model_probability):
    if book_probability is None or model_probability is None:
        return 50

    edge = model_probability - book_probability

    return round(clamp(50 + edge * 4), 1)


def home_field_score(is_home):
    return 56 if is_home else 50
