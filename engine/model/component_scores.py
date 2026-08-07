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
    """
    Build a role-aware starting-pitcher score from stabilized performance
    and underlying skill indicators.

    All observed metrics are regressed toward league-average baselines using
    starter-only innings pitched. Small samples therefore remain close to a
    neutral score while established starter samples receive more influence.
    """
    if not pitcher or pitcher.get("name") == "Unknown Starter":
        return 50

    innings_pitched = pitcher.get("ip")

    if innings_pitched is None or innings_pitched <= 0:
        return 50

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
    k9 = stabilize_pitcher_stat(
        observed_value=pitcher.get("k_rate"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["k9"],
    )
    bb9 = stabilize_pitcher_stat(
        observed_value=pitcher.get("bb_rate"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["bb9"],
    )
    hr9 = stabilize_pitcher_stat(
        observed_value=pitcher.get("hr9"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["hr9"],
    )
    h9 = stabilize_pitcher_stat(
        observed_value=pitcher.get("h9"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["h9"],
    )
    k_bb_pct = stabilize_pitcher_stat(
        observed_value=pitcher.get("k_bb_pct"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["k_bb_pct"],
    )
    strike_pct = stabilize_pitcher_stat(
        observed_value=pitcher.get("strike_pct"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["strike_pct"],
    )
    pitches_per_inning = stabilize_pitcher_stat(
        observed_value=pitcher.get("pitches_per_inning"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["pitches_per_inning"],
    )
    ground_air_ratio = stabilize_pitcher_stat(
        observed_value=pitcher.get("ground_air_ratio"),
        innings_pitched=innings_pitched,
        league_average=PITCHER_BASELINES["ground_air_ratio"],
    )

    score = 50

    # Run prevention: 30% of the practical scoring influence.
    if era is not None:
        score += (
            PITCHER_BASELINES["era"] - era
        ) * 3.0

    if whip is not None:
        score += (
            PITCHER_BASELINES["whip"] - whip
        ) * 10.0

    # Bat-missing and command skills.
    if k9 is not None:
        score += (
            k9 - PITCHER_BASELINES["k9"]
        ) * 1.25

    if bb9 is not None:
        score += (
            PITCHER_BASELINES["bb9"] - bb9
        ) * 1.5

    if k_bb_pct is not None:
        score += (
            k_bb_pct - PITCHER_BASELINES["k_bb_pct"]
        ) * 0.30

    if strike_pct is not None:
        score += (
            strike_pct - PITCHER_BASELINES["strike_pct"]
        ) * 0.35

    # Contact management.
    if hr9 is not None:
        score += (
            PITCHER_BASELINES["hr9"] - hr9
        ) * 4.0

    if h9 is not None:
        score += (
            PITCHER_BASELINES["h9"] - h9
        ) * 0.75

    # Efficiency and batted-ball tendency receive modest influence.
    if pitches_per_inning is not None:
        score += (
            PITCHER_BASELINES["pitches_per_inning"]
            - pitches_per_inning
        ) * 0.40

    if ground_air_ratio is not None:
        ground_ball_edge = clamp(
            ground_air_ratio,
            low=0.50,
            high=2.00,
        )

        score += (
            ground_ball_edge
            - PITCHER_BASELINES["ground_air_ratio"]
        ) * 1.5

    return round(clamp(score), 1)


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
