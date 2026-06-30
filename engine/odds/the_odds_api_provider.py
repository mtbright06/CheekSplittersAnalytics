import os
import requests
from pathlib import Path

from dotenv import load_dotenv

from engine.odds.implied_probability import american_to_implied_probability
from engine.odds.models import MarketQuote
from engine.odds.odds_cache import write_cache
from engine.odds.provider import OddsProvider


load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://api.the-odds-api.com/v4/sports"


SPORT_KEYS = {
    "MLB": "baseball_mlb",
}


class TheOddsApiProvider(OddsProvider):
    provider_name = "the_odds_api"

    def __init__(self):
        self.api_key = os.getenv("ODDS_API_KEY")

        if not self.api_key:
            raise RuntimeError("Missing ODDS_API_KEY in .env")

    def get_moneylines(self, league="MLB"):
        league = league.upper()
        sport_key = SPORT_KEYS.get(league)

        if not sport_key:
            raise ValueError(f"Unsupported league for The Odds API: {league}")

        raw = self._fetch_raw(sport_key)
        quotes = self._normalize_moneylines(raw, league)

        write_cache(
            provider=self.provider_name,
            league=league,
            market="moneyline",
            data=[quote.__dict__ for quote in quotes],
        )

        return quotes

    def _fetch_raw(self, sport_key):
        url = f"{BASE_URL}/{sport_key}/odds"

        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
            "dateFormat": "iso",
        }

        response = requests.get(url, params=params, timeout=30)

        print("Odds API status:", response.status_code)
        print("Requests remaining:", response.headers.get("x-requests-remaining"))
        print("Requests used:", response.headers.get("x-requests-used"))
        print("Last request cost:", response.headers.get("x-requests-last"))

        response.raise_for_status()

        return response.json()

    def _normalize_moneylines(self, events, league):
        quotes = []

        for event in events:
            away_team = event.get("away_team")
            home_team = event.get("home_team")
            event_id = event.get("id")
            commence_time = event.get("commence_time")

            for book in event.get("bookmakers", []):
                sportsbook = book.get("title")
                last_updated = book.get("last_update")

                for market in book.get("markets", []):
                    if market.get("key") != "h2h":
                        continue

                    for outcome in market.get("outcomes", []):
                        odds = outcome.get("price")
                        selection = outcome.get("name")

                        quotes.append(
                            MarketQuote(
                                provider=self.provider_name,
                                sportsbook=sportsbook,
                                league=league,
                                market="Moneyline",
                                selection=selection,
                                away_team=away_team,
                                home_team=home_team,
                                american_odds=odds,
                                implied_probability=american_to_implied_probability(odds),
                                event_id=event_id,
                                commence_time=commence_time,
                                last_updated=last_updated,
                            )
                        )

        return quotes
