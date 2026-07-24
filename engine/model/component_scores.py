from engine.model.pitcher_stabilization import (
    PITCHER_BASELINES,
    stabilize_pitcher_stat,
)


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def offense_score(offense):
    score = 50

    if not offense:
        return score

    rpg = offense.get("runs_per_game")
    ops = offense.get("ops")
    hrpg = offense.get("hr_per_game")
    iso = offense.get("iso")
    k_rate = offense.get("k_rate")
    bb_rate = offense.get("bb_rate")

    if rpg is not None:
        score += (rpg - 4.4) * 7

    if ops is not None:
        score += (ops - 0.710) * 120

    if hrpg is not None:
        score += (hrpg - 1.1) * 8

    if iso is not None:
        score += (iso - 0.160) * 90

    if k_rate is not None:
        score -= (k_rate - 22.0) * 0.6

    if bb_rate is not None:
        score += (bb_rate - 8.0) * 0.8

    return round(clamp(score), 1)


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
