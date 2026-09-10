"""Factual NFL player game logs from nflverse-data (CC BY 4.0).

Source: https://github.com/nflverse/nflverse-data
License: https://creativecommons.org/licenses/by/4.0/
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable
from time import monotonic

import requests

from engine.nfl.models import NFLGame, NFLPlayer, NFLPlayerGameLog
from engine.nfl.players import load_nfl_players
from engine.nfl.schedule import NFLScheduleProvider, normalize_game_type
from engine.nfl.teams import normalize_nfl_abbreviation


STATS_PLAYER_WEEKLY_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_week_{season}.csv"
)
SOURCE = "nflverse_stats_player_weekly"
REGULAR_SEASON = "REG"


@dataclass(frozen=True)
class NFLPlayerGameLogBatch:
    season: int
    game_type: str
    game_logs: tuple[NFLPlayerGameLog, ...] = ()
    source: str = SOURCE
    concerns: tuple[str, ...] = ()


class NFLPlayerGameLogProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        players: Iterable[NFLPlayer] | None = None,
        schedule_provider: NFLScheduleProvider | None = None,
        cache_ttl: float = 1800,
        clock=monotonic,
    ) -> None:
        self._fetcher = fetcher
        self._players = tuple(players) if players is not None else None
        self._schedule_provider = schedule_provider or NFLScheduleProvider(
            fetcher=fetcher
        )
        self._row_cache: dict[int, tuple[list[dict[str, str]], tuple[str, ...]]] = {}
        self._cache_times = {}
        self._cache_ttl = cache_ttl
        self._clock = clock

    def load_player_game_logs(
        self,
        *,
        season: int,
        game_type: str = REGULAR_SEASON,
        player_ids: Iterable[str] | None = None,
    ) -> NFLPlayerGameLogBatch:
        normalized_type = normalize_game_type(game_type)
        if normalized_type is None:
            return NFLPlayerGameLogBatch(
                season=int(season),
                game_type=str(game_type or "").upper(),
                concerns=("unsupported_game_type",),
            )

        rows, source_concerns = self._load_rows(int(season))
        games = self._schedule_provider.load_schedule(
            season=int(season),
            game_type=normalized_type,
        )
        schedule_concerns = (
            (f"schedule_source_unavailable:{int(season)}",)
            if rows and not games
            else ()
        )
        logs = normalize_nfl_player_game_logs(
            rows,
            games=games,
            players=self._player_index(),
            season=int(season),
            game_type=normalized_type,
            player_ids=player_ids,
        )
        return NFLPlayerGameLogBatch(
            season=int(season),
            game_type=normalized_type,
            game_logs=tuple(logs),
            concerns=tuple(dict.fromkeys(source_concerns + schedule_concerns)),
        )

    def _load_rows(
        self,
        season: int,
    ) -> tuple[list[dict[str, str]], tuple[str, ...]]:
        cached = self._row_cache.get(season)
        if cached is not None and self._clock() - self._cache_times[season] < self._cache_ttl:
            rows, concerns = cached
            return list(rows), concerns

        try:
            response = self._fetcher(
                STATS_PLAYER_WEEKLY_URL.format(season=season),
                timeout=30,
                headers={"User-Agent": "SharpStack/1.0 personal analytics"},
            )
            response.raise_for_status()
            rows = _csv_rows(response.text)
        except Exception:
            return [], (f"player_game_logs_source_unavailable:{season}",)

        if not rows:
            return [], (f"player_game_logs_source_empty:{season}",)
        self._row_cache[season] = (rows, ())
        self._cache_times[season] = self._clock()
        return list(rows), ()

    def _player_index(self) -> dict[str, NFLPlayer]:
        if self._players is None:
            self._players = tuple(load_nfl_players())
        return {player.gsis_id: player for player in self._players}


def load_nfl_player_game_logs(
    *,
    season: int,
    game_type: str = REGULAR_SEASON,
    player_ids: Iterable[str] | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
    games: Iterable[NFLGame] | None = None,
    players: Iterable[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> NFLPlayerGameLogBatch:
    normalized_type = normalize_game_type(game_type)
    if normalized_type is None:
        return NFLPlayerGameLogBatch(
            season=int(season),
            game_type=str(game_type or "").upper(),
            concerns=("unsupported_game_type",),
        )
    if raw_rows is None:
        provider_players = (
            players.values() if isinstance(players, dict) else players
        )
        return NFLPlayerGameLogProvider(players=provider_players).load_player_game_logs(
            season=season,
            game_type=normalized_type,
            player_ids=player_ids,
        )

    return NFLPlayerGameLogBatch(
        season=int(season),
        game_type=normalized_type,
        game_logs=tuple(
            normalize_nfl_player_game_logs(
                raw_rows,
                games=games or (),
                players=_players_index(players),
                season=season,
                game_type=normalized_type,
                player_ids=player_ids,
            )
        ),
    )


def normalize_nfl_player_game_logs(
    rows: Iterable[dict[str, Any]] | None,
    *,
    games: Iterable[NFLGame],
    players: dict[str, NFLPlayer] | None = None,
    season: int | None = None,
    game_type: str = REGULAR_SEASON,
    player_ids: Iterable[str] | None = None,
) -> list[NFLPlayerGameLog]:
    normalized_type = normalize_game_type(game_type)
    if normalized_type is None:
        return []
    requested_ids = set(player_ids) if player_ids is not None else None
    game_index = {game.source_game_id: game for game in games}
    player_index = players or {}
    logs = []
    seen = set()
    for row in rows or ():
        log = nfl_player_game_log_from_provider(
            row,
            games=game_index,
            players=player_index,
        )
        if log is None:
            continue
        if season is not None and log.season != int(season):
            continue
        if log.game_type != normalized_type:
            continue
        if requested_ids is not None and log.player_id not in requested_ids:
            continue
        key = (log.player_id, log.player_name, log.game_id)
        if key in seen:
            continue
        seen.add(key)
        logs.append(log)
    return sorted(
        logs,
        key=lambda log: (
            log.game_date or date.min,
            log.game_id,
            log.player_id or "",
            log.player_name,
        ),
    )


def nfl_player_game_log_from_provider(
    row: dict[str, Any],
    *,
    games: dict[str, NFLGame],
    players: dict[str, NFLPlayer] | None = None,
) -> NFLPlayerGameLog | None:
    season = _optional_int(row.get("season"))
    week = _optional_int(row.get("week"))
    game_type = normalize_game_type(row.get("season_type"))
    game_id = _text(row.get("game_id"))
    player_name = _text(row.get("player_display_name") or row.get("player_name"))
    if season is None or week is None or game_type is None or not game_id or not player_name:
        return None

    player_id = _text(row.get("player_id") or row.get("gsis_id"))
    player = players.get(player_id) if players and player_id else None
    team = _team(row.get("team") or row.get("recent_team"))
    provider_opponent = _team(row.get("opponent_team") or row.get("opponent"))
    game = games.get(game_id)
    concerns = []
    if not player_id:
        concerns.append("player_game_log_gsis_id_missing")
    elif player is None:
        concerns.append("player_game_log_identity_unresolved")

    game_date = None
    home_away = None
    opponent = provider_opponent
    if game is None:
        concerns.append("player_game_log_schedule_join_missing")
    else:
        game_date = game.game_date
        if team == game.away_team.abbreviation:
            home_away = "AWAY"
            opponent = game.home_team.abbreviation
        elif team == game.home_team.abbreviation:
            home_away = "HOME"
            opponent = game.away_team.abbreviation
        else:
            concerns.append("player_game_log_schedule_team_mismatch")
        if provider_opponent and opponent and provider_opponent != opponent:
            concerns.append("player_game_log_opponent_mismatch")

    return NFLPlayerGameLog(
        player_id=player_id,
        player=player,
        player_name=player_name,
        game_id=game_id,
        game_date=game_date,
        season=season,
        week=week,
        game_type=game_type,
        team_abbreviation=team,
        opponent_abbreviation=opponent,
        home_away=home_away,
        position=_upper(row.get("position")),
        passing_yards=_optional_int(row.get("passing_yards")),
        passing_touchdowns=_optional_int(row.get("passing_tds")),
        carries=_optional_int(row.get("carries")),
        rushing_yards=_optional_int(row.get("rushing_yards")),
        rushing_touchdowns=_optional_int(row.get("rushing_tds")),
        targets=_optional_int(row.get("targets")),
        receptions=_optional_int(row.get("receptions")),
        receiving_yards=_optional_int(row.get("receiving_yards")),
        receiving_touchdowns=_optional_int(row.get("receiving_tds")),
        special_teams_touchdowns=_optional_int(row.get("special_teams_tds")),
        concerns=tuple(dict.fromkeys(concerns)),
    )


def _players_index(
    players: Iterable[NFLPlayer] | dict[str, NFLPlayer] | None,
) -> dict[str, NFLPlayer]:
    if players is None:
        return {}
    if isinstance(players, dict):
        return players
    return {player.gsis_id: player for player in players}


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


def _team(value: Any) -> str | None:
    text = _text(value)
    return normalize_nfl_abbreviation(text) if text else None


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
