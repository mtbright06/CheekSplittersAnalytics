from __future__ import annotations

from typing import Any

from engine.nhl.models import NHLPlayer


def nhl_player_from_provider(
    player: dict[str, Any],
    *,
    team_id: int | None = None,
) -> NHLPlayer:
    return NHLPlayer(
        source_player_id=int(
            player.get("id")
            or player.get("playerId")
            or 0
        ),
        name=_player_name(player),
        team_id=team_id,
        position=(
            str(player.get("positionCode") or "").strip()
            or None
        ),
    )


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
