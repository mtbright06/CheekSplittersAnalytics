from __future__ import annotations

import csv
import io
from typing import Any

import requests

from engine.nfl.models import NFLPlayer, NFLPlayerStats
from engine.nfl.players import load_nfl_players
from engine.nfl.schedule import normalize_game_type
from engine.nfl.teams import normalize_nfl_abbreviation


STATS_PLAYER_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_{season_type}_{season}.csv"
)
SOURCE = "nflverse_stats_player"


class NFLPlayerStatsProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        players: list[NFLPlayer] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._players = players
        self._cache: dict[tuple[int, str], list[dict[str, str]]] = {}

    def load_player_stats(
        self,
        *,
        season: int,
        season_type: str = "REG",
        player_id: str | None = None,
        team: str | None = None,
    ) -> list[NFLPlayerStats]:
        normalized_type = normalize_game_type(season_type)
        if normalized_type is None:
            return []
        rows = self._load_rows(int(season), normalized_type)
        return normalize_nfl_player_stats(
            rows,
            players=self._player_index(),
            season=season,
            season_type=normalized_type,
            player_id=player_id,
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
                    STATS_PLAYER_URL.format(
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

    def _player_index(self) -> dict[str, NFLPlayer]:
        if self._players is None:
            self._players = load_nfl_players()
        return {
            player.gsis_id: player
            for player in self._players
        }


def load_nfl_player_stats(
    *,
    season: int,
    season_type: str = "REG",
    player_id: str | None = None,
    team: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> list[NFLPlayerStats]:
    normalized_type = normalize_game_type(season_type)
    if normalized_type is None:
        return []
    if raw_rows is not None:
        return normalize_nfl_player_stats(
            raw_rows,
            players=_players_index(players),
            season=season,
            season_type=normalized_type,
            player_id=player_id,
            team=team,
        )
    return NFLPlayerStatsProvider(
        players=list(players.values()) if isinstance(players, dict) else players,
    ).load_player_stats(
        season=season,
        season_type=normalized_type,
        player_id=player_id,
        team=team,
    )


def normalize_nfl_player_stats(
    rows: list[dict[str, Any]] | None,
    *,
    players: dict[str, NFLPlayer] | None = None,
    season: int | None = None,
    season_type: str | None = None,
    week: int | None = None,
    player_id: str | None = None,
    team: str | None = None,
) -> list[NFLPlayerStats]:
    requested_type = normalize_game_type(season_type) if season_type else None
    requested_team = normalize_nfl_abbreviation(team) if team else None
    stats = []
    seen = set()
    for row in rows or []:
        stat = nfl_player_stats_from_provider(row, players=players or {})
        if stat is None:
            continue
        if season is not None and stat.season != int(season):
            continue
        if requested_type and stat.season_type != requested_type:
            continue
        if week is not None and stat.week != int(week):
            continue
        if player_id and stat.player_id != player_id:
            continue
        if requested_team and stat.team_abbreviation != requested_team:
            continue
        key = (
            stat.player_id,
            stat.player_name,
            stat.team_abbreviation,
            stat.season,
            stat.season_type,
            stat.week,
        )
        if key in seen:
            continue
        seen.add(key)
        stats.append(stat)
    return sorted(
        stats,
        key=lambda stat: (
            stat.team_abbreviation or "",
            stat.player_name,
            stat.week or 0,
        ),
    )


def nfl_player_stats_from_provider(
    row: dict[str, Any],
    *,
    players: dict[str, NFLPlayer] | None = None,
) -> NFLPlayerStats | None:
    season = _optional_int(row.get("season"))
    season_type = normalize_game_type(row.get("season_type"))
    name = _text(row.get("player_display_name") or row.get("player_name"))
    if season is None or season_type is None or not name:
        return None
    player_id = _text(row.get("player_id") or row.get("gsis_id"))
    player = players.get(player_id) if players and player_id else None
    team = (
        normalize_nfl_abbreviation(row.get("recent_team"))
        if row.get("recent_team")
        else normalize_nfl_abbreviation(row.get("team"))
        if row.get("team")
        else None
    )
    concerns = []
    if not player_id:
        concerns.append("player_stats_gsis_id_missing")
    elif player is None:
        concerns.append("player_stats_identity_unresolved")

    carries = _optional_int(row.get("carries"))
    rushing_yards = _optional_int(row.get("rushing_yards"))
    receptions = _optional_int(row.get("receptions"))
    receiving_yards = _optional_int(row.get("receiving_yards"))
    targets = _optional_int(row.get("targets"))
    interceptions = _optional_int(row.get("passing_interceptions"))
    fumbles_lost_total = _optional_int(row.get("fumbles_lost_total"))
    sack_fumbles_lost = _optional_int(row.get("sack_fumbles_lost"))
    rushing_fumbles_lost = _optional_int(row.get("rushing_fumbles_lost"))
    receiving_fumbles_lost = _optional_int(row.get("receiving_fumbles_lost"))

    return NFLPlayerStats(
        player_id=player_id,
        player=player,
        player_name=name,
        team_abbreviation=team,
        season=season,
        season_type=season_type,
        week=_optional_int(row.get("week")),
        position=_upper(row.get("position")),
        position_group=_upper(row.get("position_group")),
        games=_optional_int(row.get("games")),
        completions=_optional_int(row.get("completions")),
        attempts=_optional_int(row.get("attempts")),
        passing_yards=_optional_int(row.get("passing_yards")),
        passing_touchdowns=_optional_int(row.get("passing_tds")),
        interceptions=interceptions,
        sacks_suffered=_optional_int(row.get("sacks_suffered")),
        carries=carries,
        rushing_yards=rushing_yards,
        rushing_touchdowns=_optional_int(row.get("rushing_tds")),
        rushing_first_downs=_optional_int(row.get("rushing_first_downs")),
        targets=targets,
        receptions=receptions,
        receiving_yards=receiving_yards,
        receiving_touchdowns=_optional_int(row.get("receiving_tds")),
        receiving_first_downs=_optional_int(row.get("receiving_first_downs")),
        fumbles=_optional_int(row.get("fumbles_total")),
        fumbles_lost=(
            fumbles_lost_total
            if fumbles_lost_total is not None
            else _sum_optional(
                sack_fumbles_lost,
                rushing_fumbles_lost,
                receiving_fumbles_lost,
            )
        ),
        yards_per_carry=_ratio(rushing_yards, carries),
        yards_per_reception=_ratio(receiving_yards, receptions),
        catch_rate=_ratio(receptions, targets),
        defensive_solo_tackles=_optional_int(row.get("def_tackles_solo")),
        defensive_tackles_for_loss=_optional_int(row.get("def_tackles_for_loss")),
        defensive_sacks=_optional_float(row.get("def_sacks")),
        defensive_qb_hits=_optional_int(row.get("def_qb_hits")),
        defensive_interceptions=_optional_int(row.get("def_interceptions")),
        defensive_passes_defended=_optional_int(row.get("def_pass_defended")),
        defensive_forced_fumbles=_optional_int(row.get("def_fumbles_forced")),
        defensive_touchdowns=_optional_int(row.get("def_tds")),
        field_goals_made=_optional_int(row.get("fg_made")),
        field_goals_attempted=_optional_int(row.get("fg_att")),
        extra_points_made=_optional_int(row.get("pat_made")),
        extra_points_attempted=_optional_int(row.get("pat_att")),
        concerns=tuple(concerns),
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


def _optional_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_optional(*values: int | None) -> int | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _ratio(
    numerator: int | None,
    denominator: int | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator
