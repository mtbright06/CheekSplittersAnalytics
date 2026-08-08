from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean

import requests
from bs4 import BeautifulSoup

from parsers.schedule_parser import ScheduleParser


@dataclass(frozen=True)
class TeamSplitsDataset:
    teams: dict[str, dict]
    league_rpg: float
    league_starting_era: float
    league_bullpen_era: float
    source_url: str
    retrieved_at: str


class TeamSplitsParser:
    URL = "https://mykbostats.com/stats/team_splits"

    TEAM_NAME_MAP = {
        "Kia Tigers": "KIA Tigers",
    }

    REQUIRED_TEAMS = set(ScheduleParser.TEAM_NAME_MAP.values())

    @classmethod
    def load(cls) -> TeamSplitsDataset:
        response = requests.get(
            cls.URL,
            headers=ScheduleParser.HEADERS,
            timeout=15,
        )
        response.raise_for_status()

        return cls.parse(
            response.text,
            retrieved_at=datetime.now().isoformat(timespec="seconds"),
        )

    @classmethod
    def parse(
        cls,
        html: str,
        *,
        retrieved_at: str,
    ) -> TeamSplitsDataset:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")

        if len(tables) < 4:
            raise ValueError("KBO team splits page did not expose expected tables.")

        season = cls._parse_table(tables[0], "Season")
        home = cls._parse_table(tables[1], "Home")
        away = cls._parse_table(tables[2], "Away")
        last_10 = cls._parse_table(tables[3], "Last 10G")

        missing = cls.REQUIRED_TEAMS - set(season)
        extra = set(season) - cls.REQUIRED_TEAMS

        if missing or extra:
            raise ValueError(
                "KBO team splits mapping mismatch: "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )

        teams = {}
        for team, row in season.items():
            teams[team] = {
                "name": team,
                "runs_per_game": row["rpg"],
                "runs_allowed_per_game": row["runs_allowed_per_game"],
                "starting_era": row["starting_era"],
                "bullpen_era": row["bullpen_era"],
                "games": row["games"],
                "last_10_runs_per_game": last_10.get(team, {}).get("rpg"),
                "last_10_runs_allowed_per_game": last_10.get(team, {}).get(
                    "runs_allowed_per_game"
                ),
                "last_10_games": last_10.get(team, {}).get("games"),
                "home_runs_per_game": home.get(team, {}).get("rpg"),
                "away_runs_per_game": away.get(team, {}).get("rpg"),
                "home_games": home.get(team, {}).get("games"),
                "away_games": away.get(team, {}).get("games"),
                "source": "LIVE_TEAM_SPLITS",
                "source_url": cls.URL,
                "retrieved_at": retrieved_at,
                "source_row": row["source_row"],
            }

        return TeamSplitsDataset(
            teams=teams,
            league_rpg=round(
                mean(team["runs_per_game"] for team in teams.values()),
                3,
            ),
            league_starting_era=round(
                mean(team["starting_era"] for team in teams.values()),
                3,
            ),
            league_bullpen_era=round(
                mean(team["bullpen_era"] for team in teams.values()),
                3,
            ),
            source_url=cls.URL,
            retrieved_at=retrieved_at,
        )

    @classmethod
    def _parse_table(cls, table, label: str) -> dict[str, dict]:
        rows = table.find_all("tr")

        if not rows:
            return {}

        headers = [
            cell.get_text(" ", strip=True)
            for cell in rows[0].find_all(["th", "td"])
        ]

        first_header = headers[0] if headers else label
        rpg_index = cls._index(headers, "R/G")
        allowed_index = cls._index(headers, "-R/G")
        games_index = cls._index(headers, "G")
        starting_era_index = cls._index(headers, "ERA_{SP}")
        bullpen_era_index = cls._index(headers, "ERA_{RP}")

        parsed = {}
        for source_row, row in enumerate(rows[1:], start=1):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]

            if len(cells) <= max(
                rpg_index,
                allowed_index,
                games_index,
                starting_era_index,
                bullpen_era_index,
            ):
                continue

            team = cls._normalize_team(cells[0])

            if not team:
                continue

            parsed[team] = {
                "split": first_header,
                "games": cls._to_int(cells[games_index]),
                "rpg": cls._to_float(cells[rpg_index]),
                "runs_allowed_per_game": cls._to_float(cells[allowed_index]),
                "starting_era": cls._to_float(cells[starting_era_index]),
                "bullpen_era": cls._to_float(cells[bullpen_era_index]),
                "source_row": source_row,
            }

        return parsed

    @staticmethod
    def _index(headers: list[str], value: str) -> int:
        try:
            return headers.index(value)
        except ValueError as exc:
            raise ValueError(f"Missing KBO team split column: {value}") from exc

    @classmethod
    def _normalize_team(cls, value: str) -> str | None:
        text = str(value or "").strip()
        return cls.TEAM_NAME_MAP.get(text, text)

    @staticmethod
    def _to_float(value: str) -> float | None:
        if value in (None, ""):
            return None

        try:
            return float(str(value).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _to_int(value: str) -> int | None:
        if value in (None, ""):
            return None

        try:
            return int(float(str(value).replace(",", "")))
        except ValueError:
            return None
