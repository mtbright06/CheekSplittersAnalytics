import os
from typing import Any

import requests
from dotenv import load_dotenv

from engine.odds.implied_probability import (
    american_to_implied_probability,
)
from engine.odds.models import MarketQuote
from engine.odds.odds_cache import write_cache
from engine.odds.provider import OddsProvider


load_dotenv()

BASE_URL = "https://api.the-odds-api.com/v4/sports"


SPORT_KEYS = {
    "MLB": "baseball_mlb",
    "KBO": "baseball_kbo",
}


class TheOddsApiProvider(OddsProvider):
    provider_name = "the_odds_api"

    def __init__(self) -> None:
        self.api_key = os.getenv("ODDS_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "Missing ODDS_API_KEY in .env"
            )

    def get_moneylines(
        self,
        league: str = "MLB",
    ) -> list[MarketQuote]:
        league = self._normalize_league(
            league
        )

        sport_key = SPORT_KEYS[league]

        raw = self._fetch_raw(
            sport_key=sport_key,
            markets="h2h",
        )

        quotes = self._normalize_moneylines(
            events=raw,
            league=league,
        )

        write_cache(
            provider=self.provider_name,
            league=league,
            market="moneyline",
            data=[
                quote.__dict__
                for quote in quotes
            ],
        )

        return quotes

    def get_totals(
        self,
        league: str = "MLB",
    ) -> list[MarketQuote]:
        league = self._normalize_league(
            league
        )

        sport_key = SPORT_KEYS[league]

        raw = self._fetch_raw(
            sport_key=sport_key,
            markets="totals",
        )

        quotes = self._normalize_totals(
            events=raw,
            league=league,
        )

        write_cache(
            provider=self.provider_name,
            league=league,
            market="totals",
            data=[
                quote.__dict__
                for quote in quotes
            ],
        )

        return quotes

    def get_moneylines_and_totals(
        self,
        league: str = "MLB",
    ) -> dict[str, list[MarketQuote]]:
        """
        Fetch moneylines and totals in one API request.

        This method is optional but avoids making two separate
        requests when both markets are needed during a build.
        """

        league = self._normalize_league(
            league
        )

        sport_key = SPORT_KEYS[league]

        raw = self._fetch_raw(
            sport_key=sport_key,
            markets="h2h,totals",
        )

        moneylines = self._normalize_moneylines(
            events=raw,
            league=league,
        )

        totals = self._normalize_totals(
            events=raw,
            league=league,
        )

        write_cache(
            provider=self.provider_name,
            league=league,
            market="moneyline",
            data=[
                quote.__dict__
                for quote in moneylines
            ],
        )

        write_cache(
            provider=self.provider_name,
            league=league,
            market="totals",
            data=[
                quote.__dict__
                for quote in totals
            ],
        )

        return {
            "moneylines": moneylines,
            "totals": totals,
        }

    def _fetch_raw(
        self,
        *,
        sport_key: str,
        markets: str,
    ) -> list[dict[str, Any]]:
        url = (
            f"{BASE_URL}/"
            f"{sport_key}/odds"
        )

        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": markets,
            "oddsFormat": "american",
            "dateFormat": "iso",
        }

        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

        print(
            "Odds API status:",
            response.status_code,
        )
        print(
            "Odds API markets:",
            markets,
        )
        print(
            "Requests remaining:",
            response.headers.get(
                "x-requests-remaining"
            ),
        )
        print(
            "Requests used:",
            response.headers.get(
                "x-requests-used"
            ),
        )
        print(
            "Last request cost:",
            response.headers.get(
                "x-requests-last"
            ),
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(
            payload,
            list,
        ):
            raise RuntimeError(
                "Unexpected Odds API response: "
                "expected a list of events."
            )

        return payload

    def _normalize_moneylines(
        self,
        *,
        events: list[dict[str, Any]],
        league: str,
    ) -> list[MarketQuote]:
        quotes: list[MarketQuote] = []

        for event in events:
            away_team = event.get(
                "away_team"
            )
            home_team = event.get(
                "home_team"
            )
            event_id = event.get("id")
            commence_time = event.get(
                "commence_time"
            )

            if not away_team or not home_team:
                continue

            for book in event.get(
                "bookmakers",
                [],
            ):
                sportsbook = book.get(
                    "title"
                )
                last_updated = book.get(
                    "last_update"
                )

                if not sportsbook:
                    continue

                for market in book.get(
                    "markets",
                    [],
                ):
                    if (
                        market.get("key")
                        != "h2h"
                    ):
                        continue

                    market_updated = (
                        market.get(
                            "last_update"
                        )
                        or last_updated
                    )

                    for outcome in market.get(
                        "outcomes",
                        [],
                    ):
                        odds = self._to_int(
                            outcome.get(
                                "price"
                            )
                        )
                        selection = outcome.get(
                            "name"
                        )

                        if (
                            selection is None
                            or odds is None
                        ):
                            continue

                        quotes.append(
                            MarketQuote(
                                provider=(
                                    self.provider_name
                                ),
                                sportsbook=(
                                    sportsbook
                                ),
                                league=league,
                                market=(
                                    "Moneyline"
                                ),
                                selection=(
                                    str(
                                        selection
                                    )
                                ),
                                away_team=(
                                    str(
                                        away_team
                                    )
                                ),
                                home_team=(
                                    str(
                                        home_team
                                    )
                                ),
                                american_odds=(
                                    odds
                                ),
                                implied_probability=(
                                    american_to_implied_probability(
                                        odds
                                    )
                                ),
                                event_id=(
                                    event_id
                                ),
                                commence_time=(
                                    commence_time
                                ),
                                last_updated=(
                                    market_updated
                                ),
                            )
                        )

        return quotes

    def _normalize_totals(
        self,
        *,
        events: list[dict[str, Any]],
        league: str,
    ) -> list[MarketQuote]:
        quotes: list[MarketQuote] = []

        for event in events:
            away_team = event.get(
                "away_team"
            )
            home_team = event.get(
                "home_team"
            )
            event_id = event.get("id")
            commence_time = event.get(
                "commence_time"
            )

            if not away_team or not home_team:
                continue

            for book in event.get(
                "bookmakers",
                [],
            ):
                sportsbook = book.get(
                    "title"
                )
                last_updated = book.get(
                    "last_update"
                )

                if not sportsbook:
                    continue

                for market in book.get(
                    "markets",
                    [],
                ):
                    if (
                        market.get("key")
                        != "totals"
                    ):
                        continue

                    market_updated = (
                        market.get(
                            "last_update"
                        )
                        or last_updated
                    )

                    for outcome in market.get(
                        "outcomes",
                        [],
                    ):
                        outcome_name = (
                            outcome.get("name")
                        )
                        odds = self._to_int(
                            outcome.get(
                                "price"
                            )
                        )
                        line = self._to_float(
                            outcome.get(
                                "point"
                            )
                        )

                        if (
                            outcome_name is None
                            or odds is None
                            or line is None
                        ):
                            continue

                        normalized_name = (
                            str(
                                outcome_name
                            )
                            .strip()
                            .upper()
                        )

                        if normalized_name not in {
                            "OVER",
                            "UNDER",
                        }:
                            continue

                        quotes.append(
                            MarketQuote(
                                provider=(
                                    self.provider_name
                                ),
                                sportsbook=(
                                    sportsbook
                                ),
                                league=league,
                                market="Total",
                                selection=(
                                    normalized_name
                                ),
                                away_team=(
                                    str(
                                        away_team
                                    )
                                ),
                                home_team=(
                                    str(
                                        home_team
                                    )
                                ),
                                american_odds=(
                                    odds
                                ),
                                implied_probability=(
                                    american_to_implied_probability(
                                        odds
                                    )
                                ),
                                event_id=(
                                    event_id
                                ),
                                commence_time=(
                                    commence_time
                                ),
                                last_updated=(
                                    market_updated
                                ),
                                line=line,
                            )
                        )

        return quotes

    @staticmethod
    def _normalize_league(
        league: str,
    ) -> str:
        normalized = (
            league or "MLB"
        ).strip().upper()

        if normalized not in SPORT_KEYS:
            raise ValueError(
                "Unsupported league for "
                f"The Odds API: {normalized}"
            )

        return normalized

    @staticmethod
    def _to_int(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(
                float(value)
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _to_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None
