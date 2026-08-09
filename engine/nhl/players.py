from __future__ import annotations

from typing import Any

import requests

from engine.nhl.models import NHLPlayer
from engine.nhl.teams import (
    normalize_nhl_abbreviation,
)


ROSTER_URL = "https://api-web.nhle.com/v1/roster"
POSITION_NAMES = {
    "C": "Center",
    "L": "Left Wing",
    "LW": "Left Wing",
    "R": "Right Wing",
    "RW": "Right Wing",
    "D": "Defense",
    "G": "Goalie",
}


def nhl_player_from_provider(
    player: dict[str, Any],
    *,
    team_id: int | None = None,
    team_abbreviation: str | None = None,
) -> NHLPlayer:
    position = normalize_nhl_position(
        player.get("positionCode")
    )
    return NHLPlayer(
        source_player_id=int(
            player.get("id")
            or player.get("playerId")
            or 0
        ),
        name=_player_name(player),
        team_id=team_id,
        team_abbreviation=(
            normalize_nhl_abbreviation(team_abbreviation)
            or None
        ),
        position=position,
        position_code=(
            str(player.get("positionCode") or "").strip().upper()
            or None
        ),
        position_name=POSITION_NAMES.get(position or ""),
        sweater_number=_optional_int(player.get("sweaterNumber")),
        shoots_catches=(
            str(player.get("shootsCatches") or "").strip().upper()
            or None
        ),
        active=True,
    )


def fetch_team_roster(
    team_abbreviation: str,
) -> dict[str, Any]:
    abbreviation = normalize_nhl_abbreviation(team_abbreviation)
    response = requests.get(
        f"{ROSTER_URL}/{abbreviation}/current",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def load_team_roster(
    team,
    *,
    raw_roster: dict[str, Any] | None = None,
    fetcher=fetch_team_roster,
) -> list[NHLPlayer]:
    team_abbreviation = normalize_nhl_abbreviation(
        getattr(team, "abbreviation", team)
    )
    if not team_abbreviation:
        return []

    team_id = getattr(team, "source_team_id", None)

    try:
        raw = (
            raw_roster
            if raw_roster is not None
            else fetcher(team_abbreviation)
        )
    except Exception:
        return []

    return normalize_team_roster(
        raw,
        team_id=team_id,
        team_abbreviation=team_abbreviation,
    )


def normalize_team_roster(
    raw_roster: dict[str, Any] | None,
    *,
    team_id: int | None = None,
    team_abbreviation: str | None = None,
) -> list[NHLPlayer]:
    if not isinstance(raw_roster, dict):
        return []

    players: list[NHLPlayer] = []
    seen = set()
    for group in ("forwards", "defensemen", "goalies"):
        entries = raw_roster.get(group) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            player = normalize_roster_player(
                entry,
                team_id=team_id,
                team_abbreviation=team_abbreviation,
            )
            if player is None or player.source_player_id in seen:
                continue
            seen.add(player.source_player_id)
            players.append(player)

    return players


def normalize_roster_player(
    player: dict[str, Any],
    *,
    team_id: int | None = None,
    team_abbreviation: str | None = None,
) -> NHLPlayer | None:
    if not isinstance(player, dict):
        return None

    player_id = _optional_int(
        player.get("id")
        or player.get("playerId")
    )
    name = _player_name(player)
    position = normalize_nhl_position(
        player.get("positionCode")
    )
    if player_id is None or not name or position is None:
        return None

    return nhl_player_from_provider(
        {
            **player,
            "id": player_id,
        },
        team_id=team_id,
        team_abbreviation=team_abbreviation,
    )


def load_all_nhl_rosters(
    teams: list,
    *,
    fetcher=fetch_team_roster,
) -> dict[str, list[NHLPlayer]]:
    service = NHLRosterService(fetcher=fetcher)
    return {
        normalize_nhl_abbreviation(getattr(team, "abbreviation", team)): (
            service.load_team_roster(team)
        )
        for team in teams
    }


class NHLRosterService:
    def __init__(self, *, fetcher=fetch_team_roster) -> None:
        self._fetcher = fetcher
        self._cache: dict[str, list[NHLPlayer]] = {}

    def load_team_roster(
        self,
        team,
        *,
        refresh: bool = False,
    ) -> list[NHLPlayer]:
        abbreviation = normalize_nhl_abbreviation(
            getattr(team, "abbreviation", team)
        )
        if not abbreviation:
            return []
        if not refresh and abbreviation in self._cache:
            return list(self._cache[abbreviation])

        roster = load_team_roster(
            team,
            fetcher=self._fetcher,
        )
        self._cache[abbreviation] = roster
        return list(roster)


def normalize_nhl_position(value: Any) -> str | None:
    code = str(value or "").strip().upper()
    if code == "L":
        return "LW"
    if code == "R":
        return "RW"
    if code in {"C", "LW", "RW", "D", "G"}:
        return code
    if code == "F":
        return "F"
    return None


def _player_name(player: dict[str, Any]) -> str:
    name = player.get("name")
    if isinstance(name, dict):
        display = name.get("default") or name.get("en")
        if display:
            return str(display).strip()

    first = _localized_value(player.get("firstName"))
    last = _localized_value(player.get("lastName"))
    return (
        f"{first} {last}".strip()
        or str(player.get("fullName") or "").strip()
    )


def _localized_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(
            value.get("default")
            or value.get("en")
            or ""
        ).strip()
    return str(value or "").strip()


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
