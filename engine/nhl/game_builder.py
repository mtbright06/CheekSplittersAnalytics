from __future__ import annotations

from datetime import date

from engine.nhl.models import NHLGame
from engine.nhl.schedule import build_nhl_schedule


def build_nhl_games(
    target_date: str | date | None = None,
) -> list[NHLGame]:
    return build_nhl_schedule(target_date)
