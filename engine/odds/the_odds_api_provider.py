import os
import requests
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from engine.odds.implied_probability import american_to_implied_probability
from engine.odds.odds_models import OddsQuote


load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
SAMPLE_PATH = OUTPUT_DIR / "odds_api_sample.json"

BASE_URL = "https://api.the-odds-api.com/v4/sports"


def get_api_key():
    key = os.getenv("ODDS_API_KEY")

    if not key:
        raise RuntimeError("Missing ODDS_API_KEY in .env")

    return key


def fetch_mlb_moneyline_raw():
    api_key = get_api_key()

    url = f"{BASE_URL}/baseball_mlb/odds"

    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }

    response = requests.get(url, params=params, timeout=30)

    remaining = response.headers.get("x-requests-remaining")
    used = response.headers.get("x-requests-used")
    last = response.headers.get("x-requests-last")

    print("Odds API status:", response.status_code)
    print("Requests remaining:", remaining)
    print("Requests used:", used)
    print("Last request cost:", last)

    response.raise_for_status()

    return response.json()


def save_sample(data):
    OUTPUT_DIR.mkdir(exist_ok=True)

    import json

    with open(SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "provider": "The Odds API",
                "sport": "baseball_mlb",
                "market": "h2h",
                "data": data,
            },
            f,
            indent=2,
        )

    print(f"Saved sample to {SAMPLE_PATH}")


def normalize_team_name(name):
    return (name or "").strip()


def normalize_mlb_moneyline_event(event):
    """
    Converts one The Odds API event into a simple normalized structure.

    We keep all bookmaker outcomes for now because later we may want:
    - best available line
    - consensus line
    - book comparison
    """

    home_team = normalize_team_name(event.get("home_team"))
    away_team = normalize_team_name(event.get("away_team"))

    normalized = {
        "provider": "The Odds API",
        "event_id": event.get("id"),
        "sport_key": event.get("sport_key"),
        "sport_title": event.get("sport_title"),
        "commence_time": event.get("commence_time"),
        "home_team": home_team,
        "away_team": away_team,
        "bookmakers": [],
    }

    for book in event.get("bookmakers", []):
        book_name = book.get("title")
        book_key = book.get("key")
        last_update = book.get("last_update")

        for market in book.get("markets", []):
            if market.get("key") != "h2h":
                continue

            outcomes = []

            for outcome in market.get("outcomes", []):
                team = normalize_team_name(outcome.get("name"))
                price = outcome.get("price")

                outcomes.append(
                    {
                        "team": team,
                        "american_odds": price,
                        "implied_probability": american_to_implied_probability(price),
                    }
                )

            normalized["bookmakers"].append(
                {
                    "sportsbook": book_name,
                    "sportsbook_key": book_key,
                    "last_update": last_update,
                    "market": "Moneyline",
                    "outcomes": outcomes,
                }
            )

    return normalized


def normalize_mlb_moneyline_events(events):
    return [normalize_mlb_moneyline_event(event) for event in events]


def best_available_moneyline(normalized_event, selection):
    """
    For American odds:
    - Higher positive number is better.
    - Less negative number is better.
    So numerically, max() works.
    Example:
    +120 better than +105
    -105 better than -120
    """

    selection = normalize_team_name(selection)

    best = None

    for book in normalized_event.get("bookmakers", []):
        for outcome in book.get("outcomes", []):
            if normalize_team_name(outcome.get("team")) != selection:
                continue

            odds = outcome.get("american_odds")

            if odds is None:
                continue

            if best is None or odds > best["american_odds"]:
                best = {
                    "sportsbook": book.get("sportsbook"),
                    "sportsbook_key": book.get("sportsbook_key"),
                    "selection": selection,
                    "market": "Moneyline",
                    "american_odds": odds,
                    "implied_probability": outcome.get("implied_probability"),
                    "last_update": book.get("last_update"),
                }

    return best


def odds_quote_from_best(normalized_event, selection):
    best = best_available_moneyline(normalized_event, selection)

    if not best:
        return None

    return OddsQuote(
        sport="baseball",
        league="MLB",
        away_team=normalized_event.get("away_team"),
        home_team=normalized_event.get("home_team"),
        market="Moneyline",
        selection=selection,
        american_odds=best.get("american_odds"),
        implied_probability=best.get("implied_probability"),
        sportsbook=best.get("sportsbook"),
        opening_odds=None,
        current_odds=best.get("american_odds"),
        line_movement=None,
        last_updated=best.get("last_update"),
    )
