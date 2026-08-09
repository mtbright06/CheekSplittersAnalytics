from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NHLTeam:
    source_team_id: int
    full_name: str
    abbreviation: str


@dataclass(frozen=True)
class NHLPlayer:
    source_player_id: int
    name: str
    team_id: int | None = None
    position: str | None = None


@dataclass(frozen=True)
class NHLGoalie:
    source_player_id: int
    name: str
    team_id: int | None = None
    catches: str | None = None
    jersey_number: int | None = None


@dataclass(frozen=True)
class NHLGame:
    source_game_id: int
    game_date: datetime
    away_team: NHLTeam
    home_team: NHLTeam
    game_status: str
    venue: str | None = None
    away_goalie: NHLGoalie | None = None
    home_goalie: NHLGoalie | None = None
