from __future__ import annotations

import csv
import io
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import requests

from engine.nfl.models import NFLGame
from engine.nfl.teams import nfl_team_from_abbreviation


SCHEDULE_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "schedules/games.csv"
)
SOURCE = "nflverse_schedules"
NFL_SCHEDULE_TZ = ZoneInfo("America/New_York")

GAME_TYPE_ALIASES = {
    "PRE": "PRE",
    "REG": "REG",
    "POST": "POST",
    "WC": "POST",
    "DIV": "POST",
    "CON": "POST",
    "SB": "POST",
}


class NFLScheduleProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
    ) -> None:
        self._fetcher = fetcher
        self._rows: list[dict[str, str]] | None = None

    def load_schedule(
        self,
        *,
        season: int | None = None,
        week: int | None = None,
        game_type: str | None = None,
        target_date: str | date | None = None,
    ) -> list[NFLGame]:
        rows = self._load_rows()
        return normalize_nfl_schedule(
            rows,
            season=season,
            week=week,
            game_type=game_type,
            target_date=target_date,
        )

    def _load_rows(self) -> list[dict[str, str]]:
        if self._rows is None:
            try:
                response = self._fetcher(
                    SCHEDULE_URL,
                    timeout=30,
                    headers={
                        "User-Agent": "SharpStack/1.0 personal analytics",
                    },
                )
                response.raise_for_status()
                self._rows = _csv_rows(response.text)
            except Exception:
                self._rows = []
        return list(self._rows)


def load_nfl_schedule(
    *,
    season: int | None = None,
    week: int | None = None,
    game_type: str | None = None,
    target_date: str | date | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
) -> list[NFLGame]:
    if raw_rows is not None:
        return normalize_nfl_schedule(
            raw_rows,
            season=season,
            week=week,
            game_type=game_type,
            target_date=target_date,
        )
    return NFLScheduleProvider().load_schedule(
        season=season,
        week=week,
        game_type=game_type,
        target_date=target_date,
    )


def normalize_nfl_schedule(
    rows: list[dict[str, Any]] | None,
    *,
    season: int | None = None,
    week: int | None = None,
    game_type: str | None = None,
    target_date: str | date | None = None,
) -> list[NFLGame]:
    requested_type = (
        normalize_game_type(game_type)
        if game_type
        else None
    )
    requested_date = _parse_date(target_date) if target_date else None
    games = []
    for row in rows or []:
        game = normalize_nfl_game(row)
        if game is None:
            continue
        if season is not None and game.season != int(season):
            continue
        if week is not None and game.week != int(week):
            continue
        if requested_type and game.game_type != requested_type:
            continue
        if requested_date and game.game_date != requested_date:
            continue
        games.append(game)
    return sorted(
        games,
        key=lambda game: (
            game.game_date,
            game.start_time or datetime.combine(
                game.game_date,
                time.min,
                tzinfo=NFL_SCHEDULE_TZ,
            ),
            game.source_game_id,
        ),
    )


def normalize_nfl_game(
    row: dict[str, Any],
) -> NFLGame | None:
    if not isinstance(row, dict):
        return None
    season = _optional_int(row.get("season"))
    week = _optional_int(row.get("week"))
    game_id = str(row.get("game_id") or "").strip()
    game_date = _parse_date(row.get("gameday"))
    game_type = normalize_game_type(row.get("game_type"))
    away = str(row.get("away_team") or "").strip()
    home = str(row.get("home_team") or "").strip()
    if (
        season is None
        or week is None
        or not game_id
        or game_date is None
        or game_type is None
        or not away
        or not home
    ):
        return None

    return NFLGame(
        source_game_id=game_id,
        season=season,
        week=week,
        game_type=game_type,
        game_date=game_date,
        start_time=_parse_start_time(
            row.get("gameday"),
            row.get("gametime"),
        ),
        away_team=nfl_team_from_abbreviation(away),
        home_team=nfl_team_from_abbreviation(home),
        game_status=_game_status(row),
        location=(
            str(row.get("location") or "").strip()
            or None
        ),
        away_score=_optional_int(row.get("away_score")),
        home_score=_optional_int(row.get("home_score")),
    )


def normalize_game_type(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    return GAME_TYPE_ALIASES.get(raw)


def _game_status(row: dict[str, Any]) -> str:
    result = _optional_int(row.get("result"))
    away_score = _optional_int(row.get("away_score"))
    home_score = _optional_int(row.get("home_score"))
    if result is not None or (away_score is not None and home_score is not None):
        return "FINAL"
    if _parse_date(row.get("gameday")) is not None:
        return "SCHEDULED"
    return "UNKNOWN"


def _parse_start_time(
    gameday: Any,
    gametime: Any,
) -> datetime | None:
    game_date = _parse_date(gameday)
    if game_date is None:
        return None
    text_time = str(gametime or "").strip()
    if not text_time:
        return datetime.combine(game_date, time.min, tzinfo=NFL_SCHEDULE_TZ)
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed_time = datetime.strptime(text_time, fmt).time()
            return datetime.combine(game_date, parsed_time, tzinfo=NFL_SCHEDULE_TZ)
        except ValueError:
            continue
    return datetime.combine(game_date, time.min, tzinfo=NFL_SCHEDULE_TZ)


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _csv_rows(text: str) -> list[dict[str, str]]:
    if not text or "<html" in text[:500].lower():
        return []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    return [
        row
        for row in reader
        if isinstance(row, dict)
    ]
