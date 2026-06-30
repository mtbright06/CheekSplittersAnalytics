import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"


def fetch_team_batting_stats(team_id):
    if not team_id:
        return empty_offense()

    url = f"{BASE_URL}/teams/{team_id}/stats"

    params = {
        "stats": "season",
        "group": "hitting",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except Exception:
        return empty_offense()

    data = response.json()
    splits = data.get("stats", [{}])[0].get("splits", [])

    if not splits:
        return empty_offense()

    stat = splits[0].get("stat", {})

    games = to_float(stat.get("gamesPlayed")) or 0
    runs = to_float(stat.get("runs")) or 0
    home_runs = to_float(stat.get("homeRuns")) or 0

    avg = to_float(stat.get("avg"))
    obp = to_float(stat.get("obp"))
    slg = to_float(stat.get("slg"))
    ops = to_float(stat.get("ops"))

    return {
        "runs_per_game": round(runs / games, 2) if games else None,
        "avg": avg,
        "obp": obp,
        "slg": slg,
        "ops": ops,
        "hr": to_int(stat.get("homeRuns")),
        "hr_per_game": round(home_runs / games, 2) if games else None,
        "bb": to_int(stat.get("baseOnBalls")),
        "so": to_int(stat.get("strikeOuts")),
        "bb_rate": rate(stat.get("baseOnBalls"), stat.get("plateAppearances")),
        "k_rate": rate(stat.get("strikeOuts"), stat.get("plateAppearances")),
        "iso": round((slg or 0) - (avg or 0), 3) if slg is not None and avg is not None else None,
        "woba": None,
        "wrc_plus": None,
    }


def empty_offense():
    return {
        "runs_per_game": None,
        "avg": None,
        "obp": None,
        "slg": None,
        "ops": None,
        "hr": None,
        "hr_per_game": None,
        "bb": None,
        "so": None,
        "bb_rate": None,
        "k_rate": None,
        "iso": None,
        "woba": None,
        "wrc_plus": None,
    }


def rate(numerator, denominator):
    n = to_float(numerator)
    d = to_float(denominator)

    if n is None or d in (None, 0):
        return None

    return round((n / d) * 100, 1)


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
