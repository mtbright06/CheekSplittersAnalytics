import requests
from datetime import date

from engine.mlb.constants import MLB_SPORT_ID


BASE_URL = "https://statsapi.mlb.com/api/v1/schedule"


def fetch_mlb_schedule(target_date=None):
    target_date = target_date or date.today().isoformat()

    params = {
        "sportId": MLB_SPORT_ID,
        "date": target_date,
        "hydrate": "probablePitcher",
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    return response.json()
