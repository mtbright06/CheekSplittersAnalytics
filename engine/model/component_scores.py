from engine.model.pitcher_stabilization import (
    PITCHER_BASELINES,
    stabilize_pitcher_stat,
)


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def offense_score(offense):
    return offense_breakdown(offense)["offense_score"]


def offense_breakdown(offense):
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
            normalize_metric(rpg, average=4.4, half_range=1.0)
        )
    else:
        missing_inputs.append("runs_per_game")

    if ops is not None:
        run_creation_inputs.append(
            normalize_metric(ops, average=0.710, half_range=0.080)
        )
    else:
        missing_inputs.append("ops")

    run_creation = active_average(run_creation_inputs)

    if iso is not None:
        power = normalize_metric(iso, average=0.160, half_range=0.040)
        power_source = "iso"
    elif hrpg is not None:
        power = normalize_metric(hrpg, average=1.10, half_range=0.30)
        power_source = "hr_per_game"
        missing_inputs.append("iso")
    else:
        power = None
        power_source = None
        missing_inputs.extend(["iso", "hr_per_game"])

    if bb_rate is not None and k_rate is not None:
        plate_discipline = normalize_metric(
            bb_rate - k_rate,
            average=-14.0,
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


def starting_pitcher_score(pitcher):
    return starting_pitcher_breakdown(pitcher)["starting_pitching_score"]


def starting_pitcher_breakdown(pitcher):
    """Build a cleaner starter-quality score from non-duplicative buckets."""
    if not pitcher or pitcher.get("name") == "Unknown Starter":
        return neutral_starting_pitcher_breakdown()

    innings_pitched = pitcher.get("ip")

    if innings_pitched is None or innings_pitched <= 0:
        return neutral_starting_pitcher_breakdown(
            missing_inputs=["ip"],
        )

    era = stabilize_pitcher_stat(
        observed_value=pitcher.get("era"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["era"],
    )
    whip = stabilize_pitcher_stat(
        observed_value=pitcher.get("whip"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["whip"],
    )
    hr9 = stabilize_pitcher_stat(
        observed_value=pitcher.get("hr9"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["hr9"],
    )
    k_bb_pct = stabilize_pitcher_stat(
        observed_value=pitcher.get("k_bb_pct"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["k_bb_pct"],
    )

    missing_inputs = []
    subcomponents = {}

    if era is not None:
        subcomponents["run_prevention"] = inverse_metric_score(
            era,
            average=PITCHER_BASELINES["era"],
            half_range=1.75,
        )
    else:
        missing_inputs.append("era")

    if whip is not None:
        subcomponents["baserunner_control"] = inverse_metric_score(
            whip,
            average=PITCHER_BASELINES["whip"],
            half_range=0.35,
        )
    else:
        missing_inputs.append("whip")

    if k_bb_pct is not None:
        subcomponents["strikeout_command"] = normalize_metric(
            k_bb_pct,
            average=PITCHER_BASELINES["k_bb_pct"],
            half_range=12.0,
        )
    else:
        missing_inputs.append("k_bb_pct")

    if hr9 is not None:
        subcomponents["damage_suppression"] = inverse_metric_score(
            hr9,
            average=PITCHER_BASELINES["hr9"],
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

    score = sum(
        subcomponents[name] * weight
        for name, weight in weights.items()
        if name in subcomponents
    ) / active_weight

    return {
        "starting_pitching_score": round(clamp(score), 1),
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
    }


def neutral_starting_pitcher_breakdown(
    *,
    missing_inputs=None,
):
    return {
        "starting_pitching_score": 50.0,
        "run_prevention": 50.0,
        "baserunner_control": 50.0,
        "strikeout_command": 50.0,
        "damage_suppression": 50.0,
        "active_subcomponents": [],
        "missing_inputs": missing_inputs or [],
    }


def inverse_metric_score(value, *, average, half_range):
    return normalize_metric(
        average - (value - average),
        average=average,
        half_range=half_range,
    )


def bullpen_score(bullpen):
    if not bullpen:
        return 50

    era = bullpen.get("era")
    whip = bullpen.get("whip")

    score = 50

    if era is not None:
        score += (4.25 - era) * 5

    if whip is not None:
        score += (1.35 - whip) * 15

    return round(clamp(score), 1)


def market_score(book_probability, model_probability):
    if book_probability is None or model_probability is None:
        return 50

    edge = model_probability - book_probability

    return round(clamp(50 + edge * 4), 1)


def home_field_score(is_home):
    return 56 if is_home else 50
