import requests
from scipy import stats


BASE_URL = "https://statsapi.mlb.com/api/v1"


def fetch_pitcher_stats(person_id):
    if not person_id:
        return {}

    url = f"{BASE_URL}/people/{person_id}/stats"

    params = {
        "stats": "season",
        "group": "pitching",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except Exception:
        return {}

    data = response.json()

    stats = data.get("stats", [])

    if not stats:
        return {}

    splits = stats[0].get("splits", [])

    if not splits:
        return {}

    stat = splits[0].get("stat", {})

    return {
        "record": build_record(stat),
        "era": to_float(stat.get("era")),
        "whip": to_float(stat.get("whip")),
        "ip": innings_to_float(stat.get("inningsPitched")),
        "so": to_int(stat.get("strikeOuts")),
        "bb": to_int(stat.get("baseOnBalls")),
        "hr_allowed": to_int(stat.get("homeRuns")),
        "k_rate": to_float(stat.get("strikeoutsPer9Inn")),
        "bb_rate": to_float(stat.get("walksPer9Inn")),
        "hr9": to_float(stat.get("homeRunsPer9")),
    }


def build_record(stat):
    wins = stat.get("wins")
    losses = stat.get("losses")

    if wins is None or losses is None:
        return None

    return f"{wins}-{losses}"


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
    if value is None:
        return None

    try:
        value = str(value)

        if "." not in value:
            return float(value)

        whole, partial = value.split(".")

        return float(whole) + (float(partial) / 3)
    except Exception:
        return None
