from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import requests

from engine.nhl.models import NHLGame
from engine.nhl.teams import nhl_team_from_provider


BASE_URL = "https://api-web.nhle.com/v1/schedule"
SOURCE = "nhl_api_web_schedule"


STATUS_BY_STATE = {
    "FUT": "SCHEDULED",
    "PRE": "PREGAME",
    "LIVE": "LIVE",
    "CRIT": "LIVE",
    "FINAL": "FINAL",
    "OFF": "FINAL",
    "POST": "POSTPONED",
    "CNCL": "CANCELLED",
}


def fetch_nhl_schedule(
    target_date: str | date | None = None,
) -> dict[str, Any]:
    target_date = _schedule_date(target_date)
    response = requests.get(
        f"{BASE_URL}/{target_date}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def build_nhl_schedule(
    target_date: str | date | None = None,
    *,
    raw_schedule: dict[str, Any] | None = None,
) -> list[NHLGame]:
    target_date = _schedule_date(target_date)
    raw = (
        raw_schedule
        if raw_schedule is not None
        else fetch_nhl_schedule(target_date)
    )
    return normalize_nhl_schedule_for_date(
        raw,
        target_date,
    )


def normalize_nhl_schedule_for_date(
    raw_schedule: dict[str, Any] | None,
    target_date: str | date,
) -> list[NHLGame]:
    requested_date = _schedule_date(target_date)
    if not isinstance(raw_schedule, dict):
        return []

    filtered = {
        **raw_schedule,
        "gameWeek": [
            day
            for day in raw_schedule.get("gameWeek") or []
            if isinstance(day, dict)
            and str(day.get("date") or "") == requested_date
        ],
    }
    return normalize_nhl_schedule(filtered)


def normalize_nhl_schedule(
    raw_schedule: dict[str, Any] | None,
) -> list[NHLGame]:
    if not isinstance(raw_schedule, dict):
        return []

    games: list[NHLGame] = []
    for day in raw_schedule.get("gameWeek") or []:
        if not isinstance(day, dict):
            continue
        for raw_game in day.get("games") or []:
            game = normalize_nhl_game(raw_game)
            if game is not None:
                games.append(game)

    return games


def normalize_nhl_game(
    raw_game: dict[str, Any],
) -> NHLGame | None:
    if not isinstance(raw_game, dict):
        return None

    game_id = _optional_int(raw_game.get("id"))
    away_raw = raw_game.get("awayTeam")
    home_raw = raw_game.get("homeTeam")
    start = _parse_start_time(
        raw_game.get("startTimeUTC")
        or raw_game.get("gameDate")
    )

    if (
        game_id is None
        or not isinstance(away_raw, dict)
        or not isinstance(home_raw, dict)
        or start is None
    ):
        return None

    return NHLGame(
        source_game_id=game_id,
        game_date=start,
        away_team=nhl_team_from_provider(away_raw),
        home_team=nhl_team_from_provider(home_raw),
        game_status=_normalize_status(raw_game),
        venue=_localized_value(raw_game.get("venue")),
    )


def _schedule_date(value: str | date | None) -> str:
    if value is None:
        return date.today().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _parse_start_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_status(raw_game: dict[str, Any]) -> str:
    state = str(
        raw_game.get("gameState")
        or raw_game.get("gameScheduleState")
        or raw_game.get("gameStatus")
        or "UNKNOWN"
    ).strip().upper()
    return STATUS_BY_STATE.get(state, state or "UNKNOWN")


def _localized_value(value: Any) -> str | None:
    if isinstance(value, dict):
        text = value.get("default") or value.get("en")
        return str(text).strip() if text else None
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
