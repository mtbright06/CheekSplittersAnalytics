from __future__ import annotations

from datetime import date

from engine.nfl.models import NFLGame
from engine.nfl.schedule import load_nfl_schedule


def build_nfl_games(
    *,
    season: int | None = None,
    week: int | None = None,
    game_type: str | None = None,
    target_date: str | date | None = None,
) -> list[NFLGame]:
    return load_nfl_schedule(
        season=season,
        week=week,
        game_type=game_type,
        target_date=target_date,
    )
