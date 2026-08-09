from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

import requests

from engine.nfl.models import (
    NFLDepthChartEntry,
    NFLPlayer,
    NFLPlayerAvailability,
    NFLRosterEntry,
    NFLTeamAvailability,
)
from engine.nfl.players import load_nfl_players
from engine.nfl.rosters import load_nfl_weekly_roster
from engine.nfl.teams import normalize_nfl_abbreviation


DEPTH_CHART_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "depth_charts/depth_charts_{season}.csv"
)
SOURCE = "nflverse_depth_charts"


class NFLDepthChartProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        players: list[NFLPlayer] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._players = players
        self._cache: dict[int, list[dict[str, str]]] = {}

    def load_depth_chart_snapshots(
        self,
        *,
        season: int,
    ) -> list[NFLDepthChartEntry]:
        return normalize_nfl_depth_chart_entries(
            self._load_rows(int(season)),
            players=self._player_index(),
        )

    def get_team_depth_chart_as_of(
        self,
        *,
        season: int,
        team: str,
        as_of: datetime,
    ) -> list[NFLDepthChartEntry]:
        entries = self.load_depth_chart_snapshots(season=season)
        return select_team_depth_chart_as_of(
            entries,
            team=team,
            as_of=as_of,
        )

    def _load_rows(
        self,
        season: int,
    ) -> list[dict[str, str]]:
        if season not in self._cache:
            try:
                response = self._fetcher(
                    DEPTH_CHART_URL.format(season=season),
                    timeout=30,
                    headers={
                        "User-Agent": "SharpStack/1.0 personal analytics",
                    },
                )
                response.raise_for_status()
                self._cache[season] = _csv_rows(response.text)
            except Exception:
                self._cache[season] = []
        return list(self._cache[season])

    def _player_index(self) -> dict[str, NFLPlayer]:
        if self._players is None:
            self._players = load_nfl_players()
        return {
            player.gsis_id: player
            for player in self._players
        }


def normalize_nfl_depth_chart_entries(
    rows: list[dict[str, Any]] | None,
    *,
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> list[NFLDepthChartEntry]:
    player_index = _players_index(players)
    entries = []
    seen = set()
    for row in rows or []:
        entry = nfl_depth_chart_entry_from_provider(
            row,
            players=player_index,
        )
        if entry is None:
            continue
        key = (
            entry.snapshot_time,
            entry.team_abbreviation,
            entry.player_id,
            entry.espn_id,
            entry.position_group,
            entry.position,
            entry.position_slot,
            entry.depth_rank,
        )
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


def nfl_depth_chart_entry_from_provider(
    row: dict[str, Any],
    *,
    players: dict[str, NFLPlayer] | None = None,
) -> NFLDepthChartEntry | None:
    snapshot = _parse_timestamp(row.get("dt"))
    team = normalize_nfl_abbreviation(row.get("team"))
    player_name = _text(row.get("player_name"))
    if snapshot is None or not team or not player_name:
        return None

    gsis_id = _text(row.get("gsis_id"))
    player = players.get(gsis_id) if players and gsis_id else None
    concerns = []
    if not gsis_id:
        concerns.append("depth_chart_gsis_id_missing")
    elif player is None:
        concerns.append("depth_chart_identity_unresolved")

    return NFLDepthChartEntry(
        team_abbreviation=team,
        player_id=gsis_id,
        player_name=player_name,
        player=player,
        espn_id=_text(row.get("espn_id")),
        position_group=_text(row.get("pos_grp")),
        position=_upper(row.get("pos_abb")),
        position_name=_text(row.get("pos_name")),
        position_slot=_optional_int(row.get("pos_slot")),
        depth_rank=_optional_int(row.get("pos_rank")),
        snapshot_time=snapshot,
        concerns=tuple(concerns),
    )


def select_team_depth_chart_as_of(
    entries: list[NFLDepthChartEntry],
    *,
    team: str,
    as_of: datetime,
) -> list[NFLDepthChartEntry]:
    requested_team = normalize_nfl_abbreviation(team)
    query_time = _ensure_utc(as_of)
    team_entries = [
        entry
        for entry in entries
        if entry.team_abbreviation == requested_team
        and entry.snapshot_time <= query_time
    ]
    if not team_entries:
        return []
    latest = max(entry.snapshot_time for entry in team_entries)
    return sorted(
        [
            entry
            for entry in team_entries
            if entry.snapshot_time == latest
        ],
        key=lambda entry: (
            entry.position_group or "",
            entry.position_slot if entry.position_slot is not None else 999,
            entry.depth_rank if entry.depth_rank is not None else 999,
            entry.player_name,
        ),
    )


def build_team_availability_context(
    *,
    team: str,
    depth_chart: list[NFLDepthChartEntry],
    roster_entries: list[NFLRosterEntry] | None = None,
    query_time: datetime | None = None,
) -> NFLTeamAvailability:
    roster_by_player = {
        entry.player_id: entry
        for entry in roster_entries or []
        if entry.player_id
    }
    players = []
    concerns = []
    for entry in depth_chart:
        roster_entry = (
            roster_by_player.get(entry.player_id)
            if entry.player_id
            else None
        )
        player_concerns = list(entry.concerns)
        if entry.player_id and roster_entries is not None and roster_entry is None:
            player_concerns.append("roster_context_missing")
        players.append(
            NFLPlayerAvailability(
                player_id=entry.player_id,
                player=entry.player,
                roster_entry=roster_entry,
                depth_chart_entry=entry,
                injury_status="UNKNOWN",
                gameday_status="UNKNOWN",
                snapshot_time=entry.snapshot_time,
                query_time=query_time,
                concerns=tuple(dict.fromkeys(player_concerns)),
            )
        )
    if not depth_chart:
        concerns.append("depth_chart_unavailable")
    return NFLTeamAvailability(
        team_abbreviation=normalize_nfl_abbreviation(team),
        players=tuple(players),
        snapshot_time=depth_chart[0].snapshot_time if depth_chart else None,
        query_time=query_time,
        concerns=tuple(concerns),
    )


def get_team_availability_as_of(
    *,
    season: int,
    team: str,
    as_of: datetime,
    week: int | None = None,
    depth_provider: NFLDepthChartProvider | None = None,
    roster_entries: list[NFLRosterEntry] | None = None,
) -> NFLTeamAvailability:
    provider = depth_provider or NFLDepthChartProvider()
    depth_chart = provider.get_team_depth_chart_as_of(
        season=season,
        team=team,
        as_of=as_of,
    )
    roster_context = (
        roster_entries
        if roster_entries is not None
        else load_nfl_weekly_roster(
            season=season,
            week=week,
            team=team,
        )
        if week is not None
        else None
    )
    return build_team_availability_context(
        team=team,
        depth_chart=depth_chart,
        roster_entries=roster_context,
        query_time=_ensure_utc(as_of),
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


def _parse_timestamp(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _ensure_utc(parsed)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
