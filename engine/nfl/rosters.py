from __future__ import annotations

import csv
import io
from typing import Any

import requests

from engine.nfl.models import NFLPlayer, NFLRosterEntry
from engine.nfl.players import load_nfl_players
from engine.nfl.teams import normalize_nfl_abbreviation


ROSTERS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "rosters/roster_{season}.csv"
)
WEEKLY_ROSTERS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "weekly_rosters/roster_weekly_{season}.csv"
)
SOURCE = "nflverse_rosters"


class NFLRostersProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        players: list[NFLPlayer] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._players = players
        self._cache: dict[tuple[str, int], list[dict[str, str]]] = {}

    def load_season_roster(
        self,
        *,
        season: int,
        team: str | None = None,
    ) -> list[NFLRosterEntry]:
        rows = self._load_rows("season", int(season))
        return normalize_nfl_roster_entries(
            rows,
            players=self._player_index(),
            team=team,
        )

    def load_weekly_roster(
        self,
        *,
        season: int,
        week: int | None = None,
        team: str | None = None,
    ) -> list[NFLRosterEntry]:
        rows = self._load_rows("weekly", int(season))
        return normalize_nfl_roster_entries(
            rows,
            players=self._player_index(),
            week=week,
            team=team,
        )

    def _load_rows(
        self,
        kind: str,
        season: int,
    ) -> list[dict[str, str]]:
        key = (kind, season)
        if key not in self._cache:
            template = WEEKLY_ROSTERS_URL if kind == "weekly" else ROSTERS_URL
            try:
                response = self._fetcher(
                    template.format(season=season),
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

    def _player_index(self) -> dict[str, NFLPlayer]:
        if self._players is None:
            self._players = load_nfl_players()
        return {
            player.gsis_id: player
            for player in self._players
        }


def load_nfl_season_roster(
    *,
    season: int,
    team: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> list[NFLRosterEntry]:
    if raw_rows is not None:
        return normalize_nfl_roster_entries(
            raw_rows,
            players=_players_index(players),
            team=team,
        )
    return NFLRostersProvider(
        players=list(players.values()) if isinstance(players, dict) else players,
    ).load_season_roster(
        season=season,
        team=team,
    )


def load_nfl_weekly_roster(
    *,
    season: int,
    week: int | None = None,
    team: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> list[NFLRosterEntry]:
    if raw_rows is not None:
        return normalize_nfl_roster_entries(
            raw_rows,
            players=_players_index(players),
            week=week,
            team=team,
        )
    return NFLRostersProvider(
        players=list(players.values()) if isinstance(players, dict) else players,
    ).load_weekly_roster(
        season=season,
        week=week,
        team=team,
    )


def normalize_nfl_roster_entries(
    rows: list[dict[str, Any]] | None,
    *,
    players: dict[str, NFLPlayer] | None = None,
    week: int | None = None,
    team: str | None = None,
) -> list[NFLRosterEntry]:
    player_index = players or {}
    requested_team = (
        normalize_nfl_abbreviation(team)
        if team
        else None
    )
    entries = []
    seen = set()
    for row in rows or []:
        entry = nfl_roster_entry_from_provider(
            row,
            players=player_index,
        )
        if entry is None:
            continue
        if week is not None and entry.week != int(week):
            continue
        if requested_team and entry.team_abbreviation != requested_team:
            continue
        key = (
            entry.player_id,
            entry.team_abbreviation,
            entry.season,
            entry.week,
            entry.game_type,
            entry.roster_status,
        )
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


def nfl_roster_entry_from_provider(
    row: dict[str, Any],
    *,
    players: dict[str, NFLPlayer] | None = None,
) -> NFLRosterEntry | None:
    season = _optional_int(row.get("season"))
    team = normalize_nfl_abbreviation(row.get("team"))
    if season is None or not team:
        return None
    player_id = _text(row.get("gsis_id") or row.get("player_id"))
    player = players.get(player_id) if players and player_id else None
    return NFLRosterEntry(
        player_id=player_id,
        team_abbreviation=team,
        season=season,
        week=_optional_int(row.get("week")),
        game_type=_text(row.get("game_type")),
        roster_status=_text(row.get("status")),
        jersey_number=_optional_int(row.get("jersey_number")),
        position=_upper(row.get("position")),
        depth_chart_position=_upper(row.get("depth_chart_position")),
        player=player,
    )


def _players_index(
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None,
) -> dict[str, NFLPlayer]:
    if players is None:
        return {}
    if isinstance(players, dict):
        return players
    return {
        player.gsis_id: player
        for player in players
    }


def _csv_rows(text: str) -> list[dict[str, str]]:
    if not text or "<html" in text[:500].lower():
        return []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    return [row for row in reader if isinstance(row, dict)]


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _upper(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None
