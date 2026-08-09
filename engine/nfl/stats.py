from __future__ import annotations

import csv
import io
from typing import Any

import requests

from engine.nfl.models import NFLTeamStats
from engine.nfl.schedule import normalize_game_type
from engine.nfl.teams import normalize_nfl_abbreviation


STATS_TEAM_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_team/stats_team_{season_type}_{season}.csv"
)
SOURCE = "nflverse_stats_team"


class NFLTeamStatsProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
    ) -> None:
        self._fetcher = fetcher
        self._cache: dict[tuple[int, str], list[dict[str, str]]] = {}

    def load_team_stats(
        self,
        *,
        season: int,
        season_type: str = "REG",
        team: str | None = None,
    ) -> list[NFLTeamStats]:
        normalized_type = normalize_game_type(season_type)
        if normalized_type is None:
            return []
        rows = self._load_rows(int(season), normalized_type)
        return normalize_nfl_team_stats(
            rows,
            season=season,
            season_type=normalized_type,
            team=team,
        )

    def _load_rows(
        self,
        season: int,
        season_type: str,
    ) -> list[dict[str, str]]:
        key = (season, season_type)
        if key not in self._cache:
            try:
                response = self._fetcher(
                    STATS_TEAM_URL.format(
                        season=season,
                        season_type=season_type.lower(),
                    ),
                    timeout=30,
                    headers={
                        "User-Agent": "SharpStack/1.0 personal analytics",
                    },
                )
                response.raise_for_status()
                self._cache[key] = _csv_rows(response.text)
            except Exception:
                self._cache[key] = []
        return list(self._cache[key])


def load_nfl_team_stats(
    *,
    season: int,
    season_type: str = "REG",
    team: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
) -> list[NFLTeamStats]:
    normalized_type = normalize_game_type(season_type)
    if normalized_type is None:
        return []
    if raw_rows is not None:
        return normalize_nfl_team_stats(
            raw_rows,
            season=season,
            season_type=normalized_type,
            team=team,
        )
    return NFLTeamStatsProvider().load_team_stats(
        season=season,
        season_type=normalized_type,
        team=team,
    )


def normalize_nfl_team_stats(
    rows: list[dict[str, Any]] | None,
    *,
    season: int | None = None,
    season_type: str | None = None,
    team: str | None = None,
) -> list[NFLTeamStats]:
    requested_team = normalize_nfl_abbreviation(team) if team else None
    requested_type = normalize_game_type(season_type) if season_type else None
    stats = []
    seen = set()
    for row in rows or []:
        stat = nfl_team_stats_from_provider(row)
        if stat is None:
            continue
        if season is not None and stat.season != int(season):
            continue
        if requested_type and stat.season_type != requested_type:
            continue
        if requested_team and stat.team_abbreviation != requested_team:
            continue
        key = (
            stat.team_abbreviation,
            stat.season,
            stat.season_type,
        )
        if key in seen:
            continue
        seen.add(key)
        stats.append(stat)
    return sorted(
        stats,
        key=lambda stat: stat.team_abbreviation,
    )


def nfl_team_stats_from_provider(
    row: dict[str, Any],
) -> NFLTeamStats | None:
    season = _optional_int(row.get("season"))
    team = normalize_nfl_abbreviation(row.get("team"))
    season_type = normalize_game_type(row.get("season_type"))
    games = _optional_int(row.get("games"))
    if season is None or not team or season_type is None or games is None:
        return None
    passing_yards = _optional_int(row.get("passing_yards"))
    rushing_yards = _optional_int(row.get("rushing_yards"))
    total_yards = _sum_optional(passing_yards, rushing_yards)
    passing_tds = _optional_int(row.get("passing_tds"))
    rushing_tds = _optional_int(row.get("rushing_tds"))
    interceptions = _optional_int(row.get("passing_interceptions"))
    fumbles_lost = _optional_int(row.get("fumbles_lost_total"))
    return NFLTeamStats(
        team_abbreviation=team,
        season=season,
        season_type=season_type,
        games_played=games,
        passing_yards=passing_yards,
        rushing_yards=rushing_yards,
        total_yards=total_yards,
        yards_per_game=_per_game(total_yards, games),
        passing_touchdowns=passing_tds,
        rushing_touchdowns=rushing_tds,
        offensive_touchdowns=_sum_optional(passing_tds, rushing_tds),
        turnovers=_sum_optional(interceptions, fumbles_lost),
        passing_first_downs=_optional_int(row.get("passing_first_downs")),
        rushing_first_downs=_optional_int(row.get("rushing_first_downs")),
        receiving_first_downs=_optional_int(row.get("receiving_first_downs")),
        defensive_sacks=_optional_float(row.get("def_sacks")),
        defensive_interceptions=_optional_int(row.get("def_interceptions")),
        defensive_forced_fumbles=_optional_int(row.get("def_fumbles_forced")),
        defensive_touchdowns=_optional_int(row.get("def_tds")),
    )


def _csv_rows(text: str) -> list[dict[str, str]]:
    if not text or "<html" in text[:500].lower():
        return []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    return [row for row in reader if isinstance(row, dict)]


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_optional(
    *values: int | None,
) -> int | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _per_game(
    value: int | None,
    games: int,
) -> float | None:
    if value is None or games <= 0:
        return None
    return value / games
