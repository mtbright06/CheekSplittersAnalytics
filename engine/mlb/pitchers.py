from datetime import date

import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"


def fetch_pitcher_stats(person_id):
    """
    Return a probable pitcher's starter-only MLB profile.

    Game-log appearances where gamesStarted > 0 are aggregated so relief
    appearances do not contaminate starting-pitcher evaluation.

    If game logs are unavailable or the pitcher has no recorded starts,
    fall back to the pitcher's full-season pitching aggregate.
    """
    if not person_id:
        return {}

    starter_profile = fetch_starter_only_profile(person_id)

    if starter_profile:
        return starter_profile

    return fetch_season_pitching_profile(person_id)


def fetch_starter_only_profile(person_id):
    url = f"{BASE_URL}/people/{person_id}/stats"

    params = {
        "stats": "gameLog",
        "group": "pitching",
        "season": date.today().year,
        "gameType": "R",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return {}

    stats_groups = data.get("stats", [])

    if not stats_groups:
        return {}

    splits = stats_groups[0].get("splits", [])

    starter_splits = [
        split
        for split in splits
        if to_int(
            split.get("stat", {}).get("gamesStarted")
        )
        not in (None, 0)
    ]

    if not starter_splits:
        return {}

    return aggregate_starter_splits(starter_splits)


def aggregate_starter_splits(starter_splits):
    totals = {
        "starts": 0,
        "outs": 0,
        "earned_runs": 0,
        "runs": 0,
        "hits": 0,
        "at_bats": 0,
        "so": 0,
        "bb": 0,
        "hbp": 0,
        "hr_allowed": 0,
        "batters_faced": 0,
        "pitches": 0,
        "strikes": 0,
        "ground_outs": 0,
        "air_outs": 0,
        "wins": 0,
        "losses": 0,
    }

    for split in starter_splits:
        stat = split.get("stat", {})

        totals["starts"] += to_int(
            stat.get("gamesStarted")
        ) or 0

        totals["outs"] += extract_outs(stat)

        totals["earned_runs"] += to_int(
            stat.get("earnedRuns")
        ) or 0

        totals["runs"] += to_int(
            stat.get("runs")
        ) or 0

        totals["hits"] += to_int(
            stat.get("hits")
        ) or 0

        totals["at_bats"] += to_int(
            stat.get("atBats")
        ) or 0

        totals["so"] += to_int(
            stat.get("strikeOuts")
        ) or 0

        totals["bb"] += to_int(
            stat.get("baseOnBalls")
        ) or 0

        totals["hbp"] += to_int(
            stat.get("hitBatsmen")
        ) or 0

        totals["hr_allowed"] += to_int(
            stat.get("homeRuns")
        ) or 0

        totals["batters_faced"] += to_int(
            stat.get("battersFaced")
        ) or 0

        totals["pitches"] += to_int(
            stat.get("numberOfPitches")
        ) or 0

        totals["strikes"] += to_int(
            stat.get("strikes")
        ) or 0

        totals["ground_outs"] += to_int(
            stat.get("groundOuts")
        ) or 0

        totals["air_outs"] += to_int(
            stat.get("airOuts")
        ) or 0

        totals["wins"] += to_int(
            stat.get("wins")
        ) or 0

        totals["losses"] += to_int(
            stat.get("losses")
        ) or 0

    innings_pitched = totals["outs"] / 3

    if innings_pitched <= 0:
        return {}

    era = rate_per_nine(
        totals["earned_runs"],
        innings_pitched,
    )

    whip = safe_divide(
        totals["hits"] + totals["bb"],
        innings_pitched,
    )

    k9 = rate_per_nine(
        totals["so"],
        innings_pitched,
    )

    bb9 = rate_per_nine(
        totals["bb"],
        innings_pitched,
    )

    hr9 = rate_per_nine(
        totals["hr_allowed"],
        innings_pitched,
    )

    h9 = rate_per_nine(
        totals["hits"],
        innings_pitched,
    )

    k_bb_pct = percentage(
        totals["so"] - totals["bb"],
        totals["batters_faced"],
    )

    strike_pct = percentage(
        totals["strikes"],
        totals["pitches"],
    )

    pitches_per_inning = safe_divide(
        totals["pitches"],
        innings_pitched,
    )

    ground_air_ratio = safe_divide(
        totals["ground_outs"],
        totals["air_outs"],
    )

    opponent_avg = safe_divide(
        totals["hits"],
        totals["at_bats"],
    )

    return {
        "record": (
            f"{totals['wins']}-{totals['losses']}"
        ),
        "era": rounded(era, 2),
        "whip": rounded(whip, 2),
        "ip": rounded(innings_pitched, 1),
        "starts": totals["starts"],
        "so": totals["so"],
        "bb": totals["bb"],
        "hits": totals["hits"],
        "hbp": totals["hbp"],
        "hr_allowed": totals["hr_allowed"],
        "batters_faced": totals["batters_faced"],
        "k_rate": rounded(k9, 2),
        "bb_rate": rounded(bb9, 2),
        "hr9": rounded(hr9, 2),
        "h9": rounded(h9, 2),
        "k_bb_pct": rounded(k_bb_pct, 1),
        "strike_pct": rounded(strike_pct, 1),
        "pitches_per_inning": rounded(
            pitches_per_inning,
            2,
        ),
        "ground_air_ratio": rounded(
            ground_air_ratio,
            2,
        ),
        "opponent_avg": rounded(
            opponent_avg,
            3,
        ),
        "data_source": "starter_game_log",
    }


def fetch_season_pitching_profile(person_id):
    """
    Safe fallback used when starter-only game logs are unavailable.

    This preserves the previous behavior and dictionary shape.
    """
    url = f"{BASE_URL}/people/{person_id}/stats"

    params = {
        "stats": "season",
        "group": "pitching",
        "season": date.today().year,
        "gameType": "R",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return {}

    stats_groups = data.get("stats", [])

    if not stats_groups:
        return {}

    splits = stats_groups[0].get("splits", [])

    if not splits:
        return {}

    stat = splits[0].get("stat", {})

    innings_pitched = innings_to_float(
        stat.get("inningsPitched")
    )

    strike_pct = percentage(
        stat.get("strikes"),
        stat.get("numberOfPitches"),
    )

    k_bb_pct = percentage(
        subtract_values(
            stat.get("strikeOuts"),
            stat.get("baseOnBalls"),
        ),
        stat.get("battersFaced"),
    )

    return {
        "record": build_record(stat),
        "era": to_float(stat.get("era")),
        "whip": to_float(stat.get("whip")),
        "ip": innings_pitched,
        "starts": to_int(stat.get("gamesStarted")),
        "so": to_int(stat.get("strikeOuts")),
        "bb": to_int(stat.get("baseOnBalls")),
        "hits": to_int(stat.get("hits")),
        "hbp": to_int(stat.get("hitBatsmen")),
        "hr_allowed": to_int(stat.get("homeRuns")),
        "batters_faced": to_int(
            stat.get("battersFaced")
        ),
        "k_rate": to_float(
            stat.get("strikeoutsPer9Inn")
        ),
        "bb_rate": to_float(
            stat.get("walksPer9Inn")
        ),
        "hr9": to_float(
            stat.get("homeRunsPer9")
        ),
        "h9": to_float(
            stat.get("hitsPer9Inn")
        ),
        "k_bb_pct": rounded(k_bb_pct, 1),
        "strike_pct": rounded(strike_pct, 1),
        "pitches_per_inning": to_float(
            stat.get("pitchesPerInning")
        ),
        "ground_air_ratio": to_float(
            stat.get("groundOutsToAirouts")
        ),
        "opponent_avg": to_float(
            stat.get("avg")
        ),
        "data_source": "season_fallback",
    }


def extract_outs(stat):
    outs = to_int(stat.get("outs"))

    if outs is not None:
        return outs

    innings = innings_to_outs(
        stat.get("inningsPitched")
    )

    return innings or 0


def build_record(stat):
    wins = stat.get("wins")
    losses = stat.get("losses")

    if wins is None or losses is None:
        return None

    return f"{wins}-{losses}"


def rate_per_nine(value, innings_pitched):
    numerator = to_float(value)

    if numerator is None:
        return None

    if innings_pitched is None or innings_pitched <= 0:
        return None

    return numerator * 9 / innings_pitched


def percentage(numerator, denominator):
    numerator_value = to_float(numerator)
    denominator_value = to_float(denominator)

    if numerator_value is None:
        return None

    if denominator_value in (None, 0):
        return None

    return (
        numerator_value
        / denominator_value
        * 100
    )


def safe_divide(numerator, denominator):
    numerator_value = to_float(numerator)
    denominator_value = to_float(denominator)

    if numerator_value is None:
        return None

    if denominator_value in (None, 0):
        return None

    return numerator_value / denominator_value


def subtract_values(left, right):
    left_value = to_float(left)
    right_value = to_float(right)

    if left_value is None or right_value is None:
        return None

    return left_value - right_value


def rounded(value, digits):
    if value is None:
        return None

    return round(value, digits)


def to_float(value):
    try:
        if value is None or value == "":
            return None

        return float(value)
    except Exception:
        return None


def to_int(value):
    try:
        if value is None or value == "":
            return None

        return int(value)
    except Exception:
        return None


def innings_to_float(value):
    outs = innings_to_outs(value)

    if outs is None:
        return None

    return outs / 3


def innings_to_outs(value):
    if value is None or value == "":
        return None

    try:
        text = str(value)

        if "." not in text:
            return int(text) * 3

        whole, partial = text.split(".", 1)

        whole_outs = int(whole) * 3
        partial_outs = int(partial)

        if partial_outs not in (0, 1, 2):
            return None

        return whole_outs + partial_outs
    except Exception:
        return None
