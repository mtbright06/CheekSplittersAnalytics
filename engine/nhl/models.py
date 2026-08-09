from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class NHLTeam:
    source_team_id: int | None
    full_name: str
    abbreviation: str
    logo_key: str
    conference: str | None = None
    division: str | None = None


@dataclass(frozen=True)
class NHLPlayer:
    source_player_id: int
    name: str
    team_id: int | None = None
    team_abbreviation: str | None = None
    position: str | None = None
    position_code: str | None = None
    position_name: str | None = None
    sweater_number: int | None = None
    shoots_catches: str | None = None
    active: bool = True


@dataclass(frozen=True)
class NHLGoalie:
    source_player_id: int
    name: str
    team_id: int | None = None
    catches: str | None = None
    jersey_number: int | None = None


@dataclass(frozen=True)
class NHLGameSourceState:
    schedule_source: str = "nhl_api_web_schedule"
    roster_context: str = "CURRENT_ROSTER"
    away_roster_state: str = "UNKNOWN"
    home_roster_state: str = "UNKNOWN"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NHLGoalieAssignment:
    status: str = "UNKNOWN"
    player: NHLPlayer | None = None
    source: str | None = None
    retrieved_at: datetime | None = None
    source_timestamp: datetime | None = None
    game_start_time: datetime | None = None
    concerns: tuple[str, ...] = ()


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
    away_roster: tuple[NHLPlayer, ...] = ()
    home_roster: tuple[NHLPlayer, ...] = ()
    away_goalie_status: NHLGoalieAssignment = field(
        default_factory=NHLGoalieAssignment
    )
    home_goalie_status: NHLGoalieAssignment = field(
        default_factory=NHLGoalieAssignment
    )
    source_state: NHLGameSourceState = field(
        default_factory=NHLGameSourceState
    )

    @property
    def away_goalies(self) -> tuple[NHLPlayer, ...]:
        return tuple(
            player
            for player in self.away_roster
            if player.position == "G"
        )

    @property
    def home_goalies(self) -> tuple[NHLPlayer, ...]:
        return tuple(
            player
            for player in self.home_roster
            if player.position == "G"
        )


@dataclass(frozen=True)
class NHLTeamStats:
    team_id: int
    team_name: str
    season_id: int
    situation: str
    games_played: int
    goals_for: int | None = None
    goals_against: int | None = None
    goals_for_per_game: float | None = None
    goals_against_per_game: float | None = None
    shots_for_per_game: float | None = None
    shots_against_per_game: float | None = None
    power_play_pct: float | None = None
    penalty_kill_pct: float | None = None


@dataclass(frozen=True)
class NHLSkaterStats:
    player_id: int
    name: str
    season_id: int
    situation: str
    team_abbreviations: str | None
    position: str | None
    games_played: int
    goals: int | None = None
    assists: int | None = None
    points: int | None = None
    shots: int | None = None
    time_on_ice_per_game: float | None = None
    ev_time_on_ice_per_game: float | None = None
    pp_time_on_ice_per_game: float | None = None
    sh_time_on_ice_per_game: float | None = None


@dataclass(frozen=True)
class NHLGoalieStats:
    player_id: int
    name: str
    season_id: int
    situation: str
    team_abbreviations: str | None
    games_played: int
    games_started: int | None = None
    wins: int | None = None
    losses: int | None = None
    ot_losses: int | None = None
    shots_against: int | None = None
    saves: int | None = None
    goals_against: int | None = None
    save_pct: float | None = None
    goals_against_average: float | None = None
    time_on_ice: int | None = None


@dataclass(frozen=True)
class NHLMoneyPuckTeamStats:
    team_abbreviation: str
    season: int
    situation: str
    games_played: int
    ice_time: float | None = None
    x_goals_for: float | None = None
    x_goals_against: float | None = None
    x_goals_percentage: float | None = None
    shot_attempts_for: float | None = None
    shot_attempts_against: float | None = None
    shots_on_goal_for: float | None = None
    shots_on_goal_against: float | None = None
    goals_for: float | None = None
    goals_against: float | None = None
    high_danger_x_goals_for: float | None = None
    high_danger_x_goals_against: float | None = None
    source: str = "MoneyPuck.com"


@dataclass(frozen=True)
class NHLMoneyPuckSkaterStats:
    player_id: int
    name: str
    team_abbreviation: str
    position: str | None
    season: int
    situation: str
    games_played: int
    ice_time: float | None = None
    shots_on_goal: float | None = None
    shot_attempts: float | None = None
    individual_x_goals: float | None = None
    goals: float | None = None
    points: float | None = None
    on_ice_x_goals_for: float | None = None
    on_ice_x_goals_against: float | None = None
    high_danger_shots: float | None = None
    high_danger_x_goals: float | None = None
    source: str = "MoneyPuck.com"


@dataclass(frozen=True)
class NHLMoneyPuckGoalieStats:
    player_id: int
    name: str
    team_abbreviation: str
    season: int
    situation: str
    games_played: int
    ice_time: float | None = None
    shots_faced: float | None = None
    goals_against: float | None = None
    expected_goals_against: float | None = None
    goals_saved_above_expected: float | None = None
    high_danger_shots_against: float | None = None
    high_danger_x_goals_against: float | None = None
    source: str = "MoneyPuck.com"


@dataclass(frozen=True)
class NHLProfileSourceState:
    official_available: bool = False
    advanced_available: bool = False
    official_source: str | None = None
    advanced_source: str | None = None
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NHLTeamProfile:
    team_id: int | None
    abbreviation: str
    full_name: str
    season_id: int
    moneypuck_season: int
    official: NHLTeamStats | None = None
    advanced: dict[str, NHLMoneyPuckTeamStats] = field(default_factory=dict)
    source_state: NHLProfileSourceState = field(
        default_factory=NHLProfileSourceState
    )


@dataclass(frozen=True)
class NHLSkaterProfile:
    player_id: int
    name: str
    position: str | None
    team_context: str | None
    season_id: int
    moneypuck_season: int
    official: NHLSkaterStats | None = None
    advanced: dict[str, tuple[NHLMoneyPuckSkaterStats, ...]] = field(
        default_factory=dict
    )
    source_state: NHLProfileSourceState = field(
        default_factory=NHLProfileSourceState
    )


@dataclass(frozen=True)
class NHLGoalieProfile:
    player_id: int
    name: str
    team_context: str | None
    season_id: int
    moneypuck_season: int
    official: NHLGoalieStats | None = None
    advanced: dict[str, tuple[NHLMoneyPuckGoalieStats, ...]] = field(
        default_factory=dict
    )
    source_state: NHLProfileSourceState = field(
        default_factory=NHLProfileSourceState
    )
