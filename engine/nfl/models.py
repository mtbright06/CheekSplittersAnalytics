from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class NFLTeam:
    abbreviation: str
    full_name: str
    logo_key: str
    conference: str | None = None
    division: str | None = None


@dataclass(frozen=True)
class NFLPlayer:
    gsis_id: str
    name: str
    position: str | None = None
    position_group: str | None = None
    pfr_id: str | None = None
    birth_date: date | None = None
    height: int | None = None
    weight: int | None = None

    @property
    def player_id(self) -> str:
        return self.gsis_id


@dataclass(frozen=True)
class NFLRosterEntry:
    player_id: str | None
    team_abbreviation: str
    season: int
    week: int | None = None
    game_type: str | None = None
    roster_status: str | None = None
    jersey_number: int | None = None
    position: str | None = None
    depth_chart_position: str | None = None
    player: NFLPlayer | None = None


@dataclass(frozen=True)
class NFLDepthChartEntry:
    team_abbreviation: str
    player_id: str | None
    player_name: str
    player: NFLPlayer | None
    espn_id: str | None
    position_group: str | None
    position: str | None
    position_name: str | None
    position_slot: int | None
    depth_rank: int | None
    snapshot_time: datetime
    source: str = "nflverse_depth_charts"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLPlayerAvailability:
    player_id: str | None
    player: NFLPlayer | None = None
    roster_entry: NFLRosterEntry | None = None
    depth_chart_entry: NFLDepthChartEntry | None = None
    injury_status: str = "UNKNOWN"
    gameday_status: str = "UNKNOWN"
    source: str = "nfl_availability_context"
    snapshot_time: datetime | None = None
    query_time: datetime | None = None
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLTeamAvailability:
    team_abbreviation: str
    players: tuple[NFLPlayerAvailability, ...] = ()
    source: str = "nfl_availability_context"
    snapshot_time: datetime | None = None
    query_time: datetime | None = None
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLTeamStats:
    team_abbreviation: str
    season: int
    season_type: str
    games_played: int
    passing_yards: int | None = None
    rushing_yards: int | None = None
    total_yards: int | None = None
    yards_per_game: float | None = None
    passing_touchdowns: int | None = None
    rushing_touchdowns: int | None = None
    offensive_touchdowns: int | None = None
    turnovers: int | None = None
    passing_first_downs: int | None = None
    rushing_first_downs: int | None = None
    receiving_first_downs: int | None = None
    defensive_sacks: float | None = None
    defensive_interceptions: int | None = None
    defensive_forced_fumbles: int | None = None
    defensive_touchdowns: int | None = None
    source: str = "nflverse_stats_team"


@dataclass(frozen=True)
class NFLPlayerStats:
    player_id: str | None
    player: NFLPlayer | None
    player_name: str
    team_abbreviation: str | None
    season: int
    season_type: str
    week: int | None = None
    position: str | None = None
    position_group: str | None = None
    games: int | None = None
    completions: int | None = None
    attempts: int | None = None
    passing_yards: int | None = None
    passing_touchdowns: int | None = None
    interceptions: int | None = None
    sacks_suffered: int | None = None
    carries: int | None = None
    rushing_yards: int | None = None
    rushing_touchdowns: int | None = None
    rushing_first_downs: int | None = None
    targets: int | None = None
    receptions: int | None = None
    receiving_yards: int | None = None
    receiving_touchdowns: int | None = None
    receiving_first_downs: int | None = None
    fumbles: int | None = None
    fumbles_lost: int | None = None
    yards_per_carry: float | None = None
    yards_per_reception: float | None = None
    catch_rate: float | None = None
    defensive_solo_tackles: int | None = None
    defensive_tackles_for_loss: int | None = None
    defensive_sacks: float | None = None
    defensive_qb_hits: int | None = None
    defensive_interceptions: int | None = None
    defensive_passes_defended: int | None = None
    defensive_forced_fumbles: int | None = None
    defensive_touchdowns: int | None = None
    field_goals_made: int | None = None
    field_goals_attempted: int | None = None
    extra_points_made: int | None = None
    extra_points_attempted: int | None = None
    source: str = "nflverse_stats_player"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLSnapCount:
    player_id: str | None
    player: NFLPlayer | None
    player_name: str
    pfr_player_id: str | None
    team_abbreviation: str
    opponent_abbreviation: str | None
    season: int
    week: int
    game_type: str
    source_game_id: str
    pfr_game_id: str | None = None
    position: str | None = None
    offense_snaps: int | None = None
    offense_pct: float | None = None
    defense_snaps: int | None = None
    defense_pct: float | None = None
    special_teams_snaps: int | None = None
    special_teams_pct: float | None = None
    source: str = "nflverse_snap_counts"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLPlay:
    game_id: str
    play_id: int
    drive_id: int | None
    season: int
    season_type: str
    week: int
    home_team: str | None
    away_team: str | None
    possession_team: str | None = None
    defensive_team: str | None = None
    quarter: int | None = None
    clock: str | None = None
    game_seconds_remaining: int | None = None
    down: int | None = None
    yards_to_go: int | None = None
    yardline_100: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    play_type: str | None = None
    description: str | None = None
    yards_gained: int | None = None
    drive_result: str | None = None
    drive_quarter_start: int | None = None
    drive_quarter_end: int | None = None
    drive_start_yard_line: str | None = None
    drive_end_yard_line: str | None = None
    drive_play_count: int | None = None
    first_down: bool | None = None
    touchdown: bool = False
    interception: bool = False
    fumble: bool = False
    fumble_lost: bool = False
    sack: bool = False
    complete_pass: bool | None = None
    incomplete_pass: bool | None = None
    passer_id: str | None = None
    passer: NFLPlayer | None = None
    rusher_id: str | None = None
    rusher: NFLPlayer | None = None
    receiver_id: str | None = None
    receiver: NFLPlayer | None = None
    interceptor_id: str | None = None
    interceptor: NFLPlayer | None = None
    fumbler_id: str | None = None
    fumbler: NFLPlayer | None = None
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLScoringOpportunity:
    game_id: str
    play_id: int
    drive_id: int | None
    season: int
    week: int
    offense_team: str
    defense_team: str | None
    yardline_100: int
    scoring_zones: tuple[str, ...]
    play_type: str
    down: int | None = None
    yards_to_go: int | None = None
    touchdown: bool = False
    passer_id: str | None = None
    passer: NFLPlayer | None = None
    rusher_id: str | None = None
    rusher: NFLPlayer | None = None
    receiver_id: str | None = None
    receiver: NFLPlayer | None = None
    source: str = "nfl_scoring_opportunities"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLDriveContext:
    game_id: str
    drive_id: int
    season: int
    week: int
    game_type: str
    possession_team: str | None
    defensive_team: str | None
    start_quarter: int | None = None
    end_quarter: int | None = None
    start_yard_line: str | None = None
    end_yard_line: str | None = None
    play_count: int | None = None
    drive_result: str | None = None
    play_ids: tuple[int, ...] = ()
    scoring_opportunity_play_ids: tuple[int, ...] = ()
    source: str = "nfl_drive_context"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLPlayerOpportunitySummary:
    player_id: str
    player: NFLPlayer | None
    team_abbreviation: str | None
    season: int
    week: int | None = None
    games_represented: tuple[str, ...] = ()
    red_zone_rush_opportunities: int = 0
    inside_10_rush_opportunities: int = 0
    inside_5_rush_opportunities: int = 0
    red_zone_receiving_opportunities: int = 0
    inside_10_receiving_opportunities: int = 0
    inside_5_receiving_opportunities: int = 0
    rushing_touchdowns_from_qualified_events: int = 0
    receiving_touchdowns_from_qualified_events: int = 0
    source: str = "nfl_opportunity_read_model"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLTeamOpportunitySummary:
    team_abbreviation: str
    season: int
    week: int | None = None
    games_represented: tuple[str, ...] = ()
    scoring_opportunities_20: int = 0
    scoring_opportunities_10: int = 0
    scoring_opportunities_5: int = 0
    rush_opportunities: int = 0
    pass_opportunities: int = 0
    touchdown_opportunities: int = 0
    drive_result_counts: tuple[tuple[str, int], ...] = ()
    source: str = "nfl_opportunity_read_model"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLGame:
    source_game_id: str
    season: int
    week: int
    game_type: str
    game_date: date
    start_time: datetime | None
    away_team: NFLTeam
    home_team: NFLTeam
    game_status: str
    location: str | None = None
    away_score: int | None = None
    home_score: int | None = None
