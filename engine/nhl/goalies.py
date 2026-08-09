from __future__ import annotations

from typing import Any

from engine.nhl.models import NHLGoalie
from engine.nhl.players import _player_name


def nhl_goalie_from_provider(
    goalie: dict[str, Any],
    *,
    team_id: int | None = None,
) -> NHLGoalie:
    return NHLGoalie(
        source_player_id=int(
            goalie.get("id")
            or goalie.get("playerId")
            or 0
        ),
        name=_player_name(goalie),
        team_id=team_id,
        catches=(
            str(
                goalie.get("catches")
                or goalie.get("shootsCatches")
                or ""
            ).strip()
            or None
        ),
        jersey_number=_optional_int(
            goalie.get("sweaterNumber")
            or goalie.get("jerseyNumber")
        ),
    )


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
