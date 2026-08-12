from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup


class ScheduleParser:
    URL = "https://mykbostats.com/"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }

    TEAM_NAME_MAP = {
        ("Hanwha", "Eagles"): "Hanwha Eagles",
        ("SSG", "Landers"): "SSG Landers",
        ("Kia", "Tigers"): "KIA Tigers",
        ("KIA", "Tigers"): "KIA Tigers",
        ("Doosan", "Bears"): "Doosan Bears",
        ("KT", "Wiz"): "KT Wiz",
        ("Samsung", "Lions"): "Samsung Lions",
        ("LG", "Twins"): "LG Twins",
        ("Lotte", "Giants"): "Lotte Giants",
        ("Kiwoom", "Heroes"): "Kiwoom Heroes",
        ("NC", "Dinos"): "NC Dinos",
    }

    TIME_PATTERN = re.compile(
        r"^\d{1,2}:\d{2}\s*(?:am|pm)?$",
        re.IGNORECASE,
    )

    @classmethod
    def load(cls) -> list[dict[str, Any]]:
        session = requests.Session()

        response = session.get(
            cls.URL,
            headers=cls.HEADERS,
            timeout=15,
        )
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        games: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = str(link.get("href") or "").strip()

            if not href.startswith("/games/"):
                continue

            full_url = f"https://mykbostats.com{href}"

            if full_url in seen_urls:
                continue

            text = link.get_text(
                " ",
                strip=True,
            )

            if "Final" in text:
                continue

            lines = [
                value.strip()
                for value in link.get_text(
                    "\n",
                    strip=True,
                ).splitlines()
                if value.strip()
            ]

            game = cls._parse_game_lines(
                lines=lines,
                href=href,
            )

            if game is None:
                print(
                    "Skipping malformed KBO schedule row:",
                    lines,
                )
                continue

            game["url"] = full_url

            games.append(game)
            seen_urls.add(full_url)

        return games

    @classmethod
    def _parse_game_lines(
        cls,
        lines: list[str],
        href: str,
    ) -> dict[str, Any] | None:
        """
        Current MyKBOStats layout:

        0: away team first word
        1: away team second word
        2: home team first word
        3: home team second word
        4+: optional weather, game time, venue, starter notes
        """

        if len(lines) < 5:
            return None

        away = cls._normalize(
            lines[0],
            lines[1],
        )

        home = cls._normalize(
            lines[2],
            lines[3],
        )

        game_time = None
        venue = None

        for index, value in enumerate(lines[4:], start=4):
            if not cls._looks_like_time(value):
                continue

            game_time = value.strip()
            venue = cls._next_meaningful_token(lines, index + 1)
            break

        if not cls._valid_team_name(away):
            return None

        if not cls._valid_team_name(home):
            return None

        if not game_time:
            print(
                "Unexpected KBO game time:",
                lines[4:] if len(lines) > 4 else lines,
                "for",
                href,
            )

        return {
            "away": away,
            "home": home,
            "time": game_time,
            "venue": venue,
            "game_date": cls._game_date_from_href(href),
        }

    @classmethod
    def _next_meaningful_token(
        cls,
        lines: list[str],
        start_index: int,
    ) -> str | None:
        for value in lines[start_index:]:
            text = str(value or "").strip()
            if not text:
                continue
            if text == "Starters:":
                continue
            return text

        return None

    @staticmethod
    def _game_date_from_href(
        href: str,
    ) -> str | None:
        match = re.search(r"(\d{8})(?:$|[^\d])", str(href or ""))
        if not match:
            return None

        value = match.group(1)
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"

    @classmethod
    def _normalize(
        cls,
        first: str,
        second: str,
    ) -> str:
        first = str(first or "").strip()
        second = str(second or "").strip()

        return cls.TEAM_NAME_MAP.get(
            (first, second),
            f"{first} {second}".strip(),
        )

    @classmethod
    def _valid_team_name(
        cls,
        value: str,
    ) -> bool:
        return value in set(
            cls.TEAM_NAME_MAP.values()
        )

    @classmethod
    def _looks_like_time(
        cls,
        value: str,
    ) -> bool:
        return bool(
            cls.TIME_PATTERN.match(
                str(value or "").strip()
            )
        )
