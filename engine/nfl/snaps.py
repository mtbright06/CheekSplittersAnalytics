from __future__ import annotations

import csv
import io
from typing import Any

import requests

from engine.nfl.models import NFLPlayer, NFLSnapCount
from engine.nfl.players import load_nfl_players
from engine.nfl.schedule import normalize_game_type
from engine.nfl.teams import normalize_nfl_abbreviation


SNAP_COUNTS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "snap_counts/snap_counts_{season}.csv"
)
SOURCE = "nflverse_snap_counts"


class NFLSnapCountsProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        players: list[NFLPlayer] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._players = players
        self._cache: dict[int, list[dict[str, str]]] = {}

    def load_snap_counts(
        self,
        *,
        season: int,
        week: int | None = None,
        game_type: str | None = None,
        team: str | None = None,
        player_id: str | None = None,
        game_id: str | None = None,
    ) -> list[NFLSnapCount]:
        rows = self._load_rows(int(season))
        return normalize_nfl_snap_counts(
            rows,
            players=self._player_index(),
            season=season,
            week=week,
            game_type=game_type,
            team=team,
            player_id=player_id,
            game_id=game_id,
        )

    def _load_rows(
        self,
        season: int,
    ) -> list[dict[str, str]]:
        if season not in self._cache:
            try:
                response = self._fetcher(
                    SNAP_COUNTS_URL.format(season=season),
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
            player.pfr_id: player
            for player in self._players
            if player.pfr_id
        }


def load_nfl_snap_counts(
    *,
    season: int,
    week: int | None = None,
    game_type: str | None = None,
    team: str | None = None,
    player_id: str | None = None,
    game_id: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> list[NFLSnapCount]:
    if raw_rows is not None:
        return normalize_nfl_snap_counts(
            raw_rows,
            players=_pfr_player_index(players),
            season=season,
            week=week,
            game_type=game_type,
            team=team,
            player_id=player_id,
            game_id=game_id,
        )
    return NFLSnapCountsProvider(
        players=list(players.values()) if isinstance(players, dict) else players,
    ).load_snap_counts(
        season=season,
        week=week,
        game_type=game_type,
        team=team,
        player_id=player_id,
        game_id=game_id,
    )


def normalize_nfl_snap_counts(
    rows: list[dict[str, Any]] | None,
    *,
    players: dict[str, NFLPlayer] | None = None,
    season: int | None = None,
    week: int | None = None,
    game_type: str | None = None,
    team: str | None = None,
    player_id: str | None = None,
    game_id: str | None = None,
) -> list[NFLSnapCount]:
    requested_type = normalize_game_type(game_type) if game_type else None
    requested_team = normalize_nfl_abbreviation(team) if team else None
    snaps = []
    seen = set()
    for row in rows or []:
        snap = nfl_snap_count_from_provider(row, players=players or {})
        if snap is None:
            continue
        if season is not None and snap.season != int(season):
            continue
        if week is not None and snap.week != int(week):
            continue
        if requested_type and snap.game_type != requested_type:
            continue
        if requested_team and snap.team_abbreviation != requested_team:
            continue
        if player_id and snap.player_id != player_id:
            continue
        if game_id and snap.source_game_id != game_id:
            continue
        key = (
            snap.source_game_id,
            snap.team_abbreviation,
            snap.pfr_player_id,
            snap.player_name,
        )
        if key in seen:
            continue
        seen.add(key)
        snaps.append(snap)
    return sorted(
        snaps,
        key=lambda snap: (
            snap.season,
            snap.week,
            snap.source_game_id,
            snap.team_abbreviation,
            snap.player_name,
        ),
    )


def nfl_snap_count_from_provider(
    row: dict[str, Any],
    *,
    players: dict[str, NFLPlayer] | None = None,
) -> NFLSnapCount | None:
    season = _optional_int(row.get("season"))
    week = _optional_int(row.get("week"))
    game_type = normalize_game_type(row.get("game_type"))
    game_id = _text(row.get("game_id"))
    team = normalize_nfl_abbreviation(row.get("team"))
    player_name = _text(row.get("player"))
    if (
        season is None
        or week is None
        or game_type is None
        or not game_id
        or not team
        or not player_name
    ):
        return None

    pfr_id = _text(row.get("pfr_player_id"))
    player = players.get(pfr_id) if players and pfr_id else None
    concerns = []
    if not pfr_id:
        concerns.append("snap_count_pfr_id_missing")
    elif player is None:
        concerns.append("snap_count_identity_unresolved")

    return NFLSnapCount(
        player_id=player.gsis_id if player else None,
        player=player,
        player_name=player_name,
        pfr_player_id=pfr_id,
        team_abbreviation=team,
        opponent_abbreviation=(
            normalize_nfl_abbreviation(row.get("opponent"))
            if row.get("opponent")
            else None
        ),
        season=season,
        week=week,
        game_type=game_type,
        source_game_id=game_id,
        pfr_game_id=_text(row.get("pfr_game_id")),
        position=_upper(row.get("position")),
        offense_snaps=_optional_int(row.get("offense_snaps")),
        offense_pct=_optional_float(row.get("offense_pct")),
        defense_snaps=_optional_int(row.get("defense_snaps")),
        defense_pct=_optional_float(row.get("defense_pct")),
        special_teams_snaps=_optional_int(row.get("st_snaps")),
        special_teams_pct=_optional_float(row.get("st_pct")),
        concerns=tuple(concerns),
    )


def _pfr_player_index(
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None,
) -> dict[str, NFLPlayer]:
    if players is None:
        return {}
    values = players.values() if isinstance(players, dict) else players
    return {
        player.pfr_id: player
        for player in values
        if player.pfr_id
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


def _optional_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
