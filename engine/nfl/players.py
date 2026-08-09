from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

import requests

from engine.nfl.models import NFLPlayer


PLAYERS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "players/players.csv"
)
SOURCE = "nflverse_players"


class NFLPlayersProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
    ) -> None:
        self._fetcher = fetcher
        self._rows: list[dict[str, str]] | None = None

    def load_players(self) -> list[NFLPlayer]:
        return normalize_nfl_players(self._load_rows())

    def _load_rows(self) -> list[dict[str, str]]:
        if self._rows is None:
            try:
                response = self._fetcher(
                    PLAYERS_URL,
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


def load_nfl_players(
    *,
    raw_rows: list[dict[str, Any]] | None = None,
) -> list[NFLPlayer]:
    if raw_rows is not None:
        return normalize_nfl_players(raw_rows)
    return NFLPlayersProvider().load_players()


def normalize_nfl_players(
    rows: list[dict[str, Any]] | None,
) -> list[NFLPlayer]:
    players = []
    seen = set()
    for row in rows or []:
        player = nfl_player_from_provider(row)
        if player is None or player.gsis_id in seen:
            continue
        seen.add(player.gsis_id)
        players.append(player)
    return players


def nfl_player_from_provider(row: dict[str, Any]) -> NFLPlayer | None:
    gsis_id = _text(row.get("gsis_id") or row.get("player_id"))
    name = _text(row.get("display_name") or row.get("player_name") or row.get("name"))
    if not gsis_id or not name:
        return None
    return NFLPlayer(
        gsis_id=gsis_id,
        name=name,
        position=_upper(row.get("position")),
        position_group=_upper(row.get("position_group")),
        pfr_id=_text(row.get("pfr_id")),
        birth_date=_optional_date(row.get("birth_date")),
        height=_optional_int(row.get("height")),
        weight=_optional_int(row.get("weight")),
    )


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


def _optional_date(value: Any) -> date | None:
    text = _text(value)
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
