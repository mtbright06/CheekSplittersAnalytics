from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time

from engine.nfl.availability import (
    NFLDepthChartProvider,
    build_team_availability_context,
    select_team_depth_chart_as_of,
)
from engine.nfl.game_builder import build_nfl_games
from engine.nfl.models import (
    NFLDepthChartEntry,
    NFLGame,
    NFLPlayerStats,
    NFLRosterEntry,
    NFLSnapCount,
    NFLTeamAvailability,
    NFLTeamStats,
)
from engine.nfl.player_stats import NFLPlayerStatsProvider
from engine.nfl.rosters import NFLRostersProvider
from engine.nfl.snaps import NFLSnapCountsProvider
from engine.nfl.stats import NFLTeamStatsProvider


@dataclass(frozen=True)
class NFLGameContext:
    game: NFLGame
    away_team_stats: NFLTeamStats | None = None
    home_team_stats: NFLTeamStats | None = None
    away_roster: tuple[NFLRosterEntry, ...] = ()
    home_roster: tuple[NFLRosterEntry, ...] = ()
    away_availability: NFLTeamAvailability | None = None
    home_availability: NFLTeamAvailability | None = None
    away_player_stats: tuple[NFLPlayerStats, ...] = ()
    home_player_stats: tuple[NFLPlayerStats, ...] = ()
    away_prior_snaps: tuple[NFLSnapCount, ...] = ()
    home_prior_snaps: tuple[NFLSnapCount, ...] = ()
    concerns: tuple[str, ...] = ()


class NFLGameContextComposer:
    def __init__(
        self,
        *,
        team_stats_provider: NFLTeamStatsProvider | None = None,
        roster_provider: NFLRostersProvider | None = None,
        depth_chart_provider: NFLDepthChartProvider | None = None,
        player_stats_provider: NFLPlayerStatsProvider | None = None,
        snap_counts_provider: NFLSnapCountsProvider | None = None,
    ) -> None:
        self.team_stats_provider = team_stats_provider or NFLTeamStatsProvider()
        self.roster_provider = roster_provider or NFLRostersProvider()
        self.depth_chart_provider = depth_chart_provider or NFLDepthChartProvider()
        self.player_stats_provider = player_stats_provider or NFLPlayerStatsProvider()
        self.snap_counts_provider = snap_counts_provider or NFLSnapCountsProvider()

    def build_contexts(
        self,
        *,
        games: list[NFLGame],
    ) -> list[NFLGameContext]:
        if not games:
            return []

        team_stats = self._load_by_season_type(self._safe_load_team_stats, games)
        player_stats = self._load_by_season_type(self._safe_load_player_stats, games)
        rosters = self._load_by_season(self._safe_load_weekly_rosters, games)
        depth_charts = self._load_by_season(
            self._safe_load_depth_charts,
            games,
        )
        snaps = self._load_by_season(self._safe_load_snap_counts, games)

        contexts = []
        for game in games:
            contexts.append(
                self._compose_game_context(
                    game,
                    team_stats=team_stats.get((game.season, game.game_type), []),
                    player_stats=player_stats.get((game.season, game.game_type), []),
                    roster_entries=rosters.get(game.season, []),
                    depth_entries=depth_charts.get(game.season, []),
                    snap_counts=snaps.get(game.season, []),
                )
            )
        return contexts

    def _compose_game_context(
        self,
        game: NFLGame,
        *,
        team_stats: list[NFLTeamStats],
        player_stats: list[NFLPlayerStats],
        roster_entries: list[NFLRosterEntry],
        depth_entries: list[NFLDepthChartEntry],
        snap_counts: list[NFLSnapCount],
    ) -> NFLGameContext:
        away = game.away_team.abbreviation
        home = game.home_team.abbreviation
        as_of = _game_query_time(game)
        away_roster = _weekly_roster_for_game(roster_entries, game, away)
        home_roster = _weekly_roster_for_game(roster_entries, game, home)
        away_depth = select_team_depth_chart_as_of(
            depth_entries,
            team=away,
            as_of=as_of,
        )
        home_depth = select_team_depth_chart_as_of(
            depth_entries,
            team=home,
            as_of=as_of,
        )
        away_availability = build_team_availability_context(
            team=away,
            depth_chart=away_depth,
            roster_entries=list(away_roster),
            query_time=as_of,
        )
        home_availability = build_team_availability_context(
            team=home,
            depth_chart=home_depth,
            roster_entries=list(home_roster),
            query_time=as_of,
        )
        away_team_stats = _team_stats_for_game(team_stats, game, away)
        home_team_stats = _team_stats_for_game(team_stats, game, home)
        away_player_stats = _player_stats_for_team(player_stats, game, away)
        home_player_stats = _player_stats_for_team(player_stats, game, home)
        away_prior_snaps = _prior_snaps_for_team(snap_counts, game, away)
        home_prior_snaps = _prior_snaps_for_team(snap_counts, game, home)
        concerns = _context_concerns(
            game=game,
            away_roster=away_roster,
            home_roster=home_roster,
            away_availability=away_availability,
            home_availability=home_availability,
            away_team_stats=away_team_stats,
            home_team_stats=home_team_stats,
            away_player_stats=away_player_stats,
            home_player_stats=home_player_stats,
            snap_counts=snap_counts,
        )
        return NFLGameContext(
            game=game,
            away_team_stats=away_team_stats,
            home_team_stats=home_team_stats,
            away_roster=away_roster,
            home_roster=home_roster,
            away_availability=away_availability,
            home_availability=home_availability,
            away_player_stats=away_player_stats,
            home_player_stats=home_player_stats,
            away_prior_snaps=away_prior_snaps,
            home_prior_snaps=home_prior_snaps,
            concerns=concerns,
        )

    def _safe_load_team_stats(
        self,
        *,
        season: int,
        game_type: str,
    ) -> list[NFLTeamStats]:
        try:
            return self.team_stats_provider.load_team_stats(
                season=season,
                season_type=game_type,
            )
        except Exception:
            return []

    def _safe_load_player_stats(
        self,
        *,
        season: int,
        game_type: str,
    ) -> list[NFLPlayerStats]:
        try:
            return self.player_stats_provider.load_player_stats(
                season=season,
                season_type=game_type,
            )
        except Exception:
            return []

    def _safe_load_weekly_rosters(
        self,
        *,
        season: int,
    ) -> list[NFLRosterEntry]:
        try:
            return self.roster_provider.load_weekly_roster(season=season)
        except Exception:
            return []

    def _safe_load_depth_charts(
        self,
        *,
        season: int,
    ) -> list[NFLDepthChartEntry]:
        try:
            return self.depth_chart_provider.load_depth_chart_snapshots(
                season=season,
            )
        except Exception:
            return []

    def _safe_load_snap_counts(
        self,
        *,
        season: int,
    ) -> list[NFLSnapCount]:
        try:
            return self.snap_counts_provider.load_snap_counts(season=season)
        except Exception:
            return []

    @staticmethod
    def _load_by_season_type(loader, games: list[NFLGame]):
        data = {}
        for season, game_type in sorted(
            {
                (game.season, game.game_type)
                for game in games
            }
        ):
            data[(season, game_type)] = loader(
                season=season,
                game_type=game_type,
            )
        return data

    @staticmethod
    def _load_by_season(loader, games: list[NFLGame]):
        data = {}
        for season in sorted({game.season for game in games}):
            data[season] = loader(season=season)
        return data


def build_nfl_game_contexts(
    *,
    season: int | None = None,
    week: int | None = None,
    game_type: str | None = None,
    target_date=None,
    games: list[NFLGame] | None = None,
    composer: NFLGameContextComposer | None = None,
) -> list[NFLGameContext]:
    selected_games = games
    if selected_games is None:
        selected_games = build_nfl_games(
            season=season,
            week=week,
            game_type=game_type,
            target_date=target_date,
        )
    return (composer or NFLGameContextComposer()).build_contexts(
        games=selected_games,
    )


def _game_query_time(game: NFLGame) -> datetime:
    if game.start_time is not None:
        if game.start_time.tzinfo is None:
            return game.start_time.replace(tzinfo=UTC)
        return game.start_time.astimezone(UTC)
    return datetime.combine(game.game_date, time.min, tzinfo=UTC)


def _weekly_roster_for_game(
    roster_entries: list[NFLRosterEntry],
    game: NFLGame,
    team: str,
) -> tuple[NFLRosterEntry, ...]:
    return tuple(
        entry
        for entry in roster_entries
        if entry.season == game.season
        and entry.week == game.week
        and entry.team_abbreviation == team
    )


def _team_stats_for_game(
    stats: list[NFLTeamStats],
    game: NFLGame,
    team: str,
) -> NFLTeamStats | None:
    for row in stats:
        if (
            row.season == game.season
            and row.season_type == game.game_type
            and row.team_abbreviation == team
        ):
            return row
    return None


def _player_stats_for_team(
    stats: list[NFLPlayerStats],
    game: NFLGame,
    team: str,
) -> tuple[NFLPlayerStats, ...]:
    return tuple(
        row
        for row in stats
        if row.season == game.season
        and row.season_type == game.game_type
        and row.team_abbreviation == team
    )


def _prior_snaps_for_team(
    snaps: list[NFLSnapCount],
    game: NFLGame,
    team: str,
) -> tuple[NFLSnapCount, ...]:
    return tuple(
        row
        for row in snaps
        if row.season == game.season
        and row.game_type == game.game_type
        and row.week < game.week
        and row.team_abbreviation == team
    )


def _context_concerns(
    *,
    game: NFLGame,
    away_roster: tuple[NFLRosterEntry, ...],
    home_roster: tuple[NFLRosterEntry, ...],
    away_availability: NFLTeamAvailability,
    home_availability: NFLTeamAvailability,
    away_team_stats: NFLTeamStats | None,
    home_team_stats: NFLTeamStats | None,
    away_player_stats: tuple[NFLPlayerStats, ...],
    home_player_stats: tuple[NFLPlayerStats, ...],
    snap_counts: list[NFLSnapCount],
) -> tuple[str, ...]:
    concerns = []
    if not away_roster:
        concerns.append("away_weekly_roster_unavailable")
    if not home_roster:
        concerns.append("home_weekly_roster_unavailable")
    if "depth_chart_unavailable" in away_availability.concerns:
        concerns.append("away_depth_chart_unavailable")
    if "depth_chart_unavailable" in home_availability.concerns:
        concerns.append("home_depth_chart_unavailable")
    if away_team_stats is None:
        concerns.append("away_team_stats_unavailable")
    if home_team_stats is None:
        concerns.append("home_team_stats_unavailable")
    if not away_player_stats:
        concerns.append("away_player_stats_unavailable")
    if not home_player_stats:
        concerns.append("home_player_stats_unavailable")
    if not any(
        row.season == game.season and row.game_type == game.game_type
        for row in snap_counts
    ):
        concerns.append("snap_counts_unavailable_for_season")
    return tuple(concerns)
