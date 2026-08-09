from __future__ import annotations

from datetime import date
from typing import Any

import requests

from engine.nhl.models import (
    NHLGoalieStats,
    NHLSkaterStats,
    NHLTeamStats,
)
from engine.nhl.players import normalize_nhl_position


BASE_URL = "https://api.nhle.com/stats/rest/en"
SOURCE = "nhl_stats_rest"
REGULAR_SEASON_GAME_TYPE = 2
SITUATION_ALL = "ALL"


def current_nhl_season_id(
    today: date | None = None,
) -> int:
    current = today or date.today()
    if current.month >= 9:
        start_year = current.year
    else:
        start_year = current.year - 1
    return int(f"{start_year}{start_year + 1}")


class NHLStatsProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
    ) -> None:
        self._fetcher = fetcher
        self._cache: dict[tuple[str, int, int], dict[str, Any]] = {}

    def load_team_stats(
        self,
        *,
        season_id: int | None = None,
        game_type_id: int = REGULAR_SEASON_GAME_TYPE,
    ) -> list[NHLTeamStats]:
        season = season_id or current_nhl_season_id()
        raw = self._fetch_report(
            "team/summary",
            season,
            game_type_id,
        )
        return normalize_team_stats(raw)

    def load_skater_stats(
        self,
        *,
        season_id: int | None = None,
        game_type_id: int = REGULAR_SEASON_GAME_TYPE,
    ) -> list[NHLSkaterStats]:
        season = season_id or current_nhl_season_id()
        summary = self._fetch_report(
            "skater/summary",
            season,
            game_type_id,
        )
        toi = self._fetch_report(
            "skater/timeonice",
            season,
            game_type_id,
        )
        return normalize_skater_stats(
            summary,
            time_on_ice_report=toi,
        )

    def load_goalie_stats(
        self,
        *,
        season_id: int | None = None,
        game_type_id: int = REGULAR_SEASON_GAME_TYPE,
    ) -> list[NHLGoalieStats]:
        season = season_id or current_nhl_season_id()
        raw = self._fetch_report(
            "goalie/summary",
            season,
            game_type_id,
        )
        return normalize_goalie_stats(raw)

    def _fetch_report(
        self,
        report: str,
        season_id: int,
        game_type_id: int,
    ) -> dict[str, Any]:
        key = (
            report,
            season_id,
            game_type_id,
        )
        if key not in self._cache:
            response = self._fetcher(
                f"{BASE_URL}/{report}",
                params={
                    "limit": -1,
                    "start": 0,
                    "cayenneExp": (
                        f"seasonId={season_id} "
                        f"and gameTypeId={game_type_id}"
                    ),
                },
                timeout=30,
            )
            response.raise_for_status()
            self._cache[key] = response.json()
        return self._cache[key]


def normalize_team_stats(
    raw_report: dict[str, Any] | None,
) -> list[NHLTeamStats]:
    rows = _report_rows(raw_report)
    stats = []
    seen = set()
    for row in rows:
        team_id = _optional_int(row.get("teamId"))
        season_id = _optional_int(row.get("seasonId"))
        games_played = _optional_int(row.get("gamesPlayed"))
        if team_id is None or season_id is None or games_played is None:
            continue
        if team_id in seen:
            continue
        seen.add(team_id)
        stats.append(
            NHLTeamStats(
                team_id=team_id,
                team_name=str(row.get("teamFullName") or "").strip(),
                season_id=season_id,
                situation=SITUATION_ALL,
                games_played=games_played,
                goals_for=_optional_int(row.get("goalsFor")),
                goals_against=_optional_int(row.get("goalsAgainst")),
                goals_for_per_game=_optional_float(row.get("goalsForPerGame")),
                goals_against_per_game=_optional_float(
                    row.get("goalsAgainstPerGame")
                ),
                shots_for_per_game=_optional_float(row.get("shotsForPerGame")),
                shots_against_per_game=_optional_float(
                    row.get("shotsAgainstPerGame")
                ),
                power_play_pct=_optional_float(row.get("powerPlayPct")),
                penalty_kill_pct=_optional_float(row.get("penaltyKillPct")),
            )
        )
    return stats


def normalize_skater_stats(
    raw_report: dict[str, Any] | None,
    *,
    time_on_ice_report: dict[str, Any] | None = None,
) -> list[NHLSkaterStats]:
    toi_by_player = {
        row.get("playerId"): row
        for row in _report_rows(time_on_ice_report)
        if row.get("playerId") is not None
    }
    stats = []
    seen = set()
    for row in _report_rows(raw_report):
        player_id = _optional_int(row.get("playerId"))
        season_id = _optional_int(row.get("seasonId"))
        games_played = _optional_int(row.get("gamesPlayed"))
        name = str(row.get("skaterFullName") or "").strip()
        if (
            player_id is None
            or season_id is None
            or games_played is None
            or not name
        ):
            continue
        if player_id in seen:
            continue
        seen.add(player_id)
        toi = toi_by_player.get(player_id, {})
        stats.append(
            NHLSkaterStats(
                player_id=player_id,
                name=name,
                season_id=season_id,
                situation=SITUATION_ALL,
                team_abbreviations=(
                    str(row.get("teamAbbrevs") or "").strip()
                    or None
                ),
                position=normalize_nhl_position(row.get("positionCode")),
                games_played=games_played,
                goals=_optional_int(row.get("goals")),
                assists=_optional_int(row.get("assists")),
                points=_optional_int(row.get("points")),
                shots=_optional_int(row.get("shots")),
                time_on_ice_per_game=_optional_float(
                    row.get("timeOnIcePerGame")
                ),
                ev_time_on_ice_per_game=_optional_float(
                    toi.get("evTimeOnIcePerGame")
                ),
                pp_time_on_ice_per_game=_optional_float(
                    toi.get("ppTimeOnIcePerGame")
                ),
                sh_time_on_ice_per_game=_optional_float(
                    toi.get("shTimeOnIcePerGame")
                ),
            )
        )
    return stats


def normalize_goalie_stats(
    raw_report: dict[str, Any] | None,
) -> list[NHLGoalieStats]:
    stats = []
    seen = set()
    for row in _report_rows(raw_report):
        player_id = _optional_int(row.get("playerId"))
        season_id = _optional_int(row.get("seasonId"))
        games_played = _optional_int(row.get("gamesPlayed"))
        name = str(row.get("goalieFullName") or "").strip()
        if (
            player_id is None
            or season_id is None
            or games_played is None
            or not name
        ):
            continue
        if player_id in seen:
            continue
        seen.add(player_id)
        stats.append(
            NHLGoalieStats(
                player_id=player_id,
                name=name,
                season_id=season_id,
                situation=SITUATION_ALL,
                team_abbreviations=(
                    str(row.get("teamAbbrevs") or "").strip()
                    or None
                ),
                games_played=games_played,
                games_started=_optional_int(row.get("gamesStarted")),
                wins=_optional_int(row.get("wins")),
                losses=_optional_int(row.get("losses")),
                ot_losses=_optional_int(row.get("otLosses")),
                shots_against=_optional_int(row.get("shotsAgainst")),
                saves=_optional_int(row.get("saves")),
                goals_against=_optional_int(row.get("goalsAgainst")),
                save_pct=_optional_float(row.get("savePct")),
                goals_against_average=_optional_float(
                    row.get("goalsAgainstAverage")
                ),
                time_on_ice=_optional_int(row.get("timeOnIce")),
            )
        )
    return stats


def _report_rows(
    raw_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(raw_report, dict):
        return []
    rows = raw_report.get("data")
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict)
    ]


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
