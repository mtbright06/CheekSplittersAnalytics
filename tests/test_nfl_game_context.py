from __future__ import annotations

from datetime import UTC, date, datetime

from engine.nfl.game_context import (
    NFLGameContextComposer,
    build_nfl_game_contexts,
)
from engine.nfl.models import (
    NFLDepthChartEntry,
    NFLGame,
    NFLPlayer,
    NFLPlayerStats,
    NFLRosterEntry,
    NFLSnapCount,
    NFLTeam,
    NFLTeamStats,
)


def test_game_context_preserves_away_home_week_and_team_truth():
    game = _game(season=2026, week=2)
    player = _player("00-0001", "Away RB")
    composer = _composer(
        team_stats=[
            _team_stats("BUF", 2026),
            _team_stats("NYJ", 2026),
        ],
        rosters=[
            _roster("BUF", 2026, 2, player=player),
            _roster("NYJ", 2026, 2, player=_player("00-0002", "Home WR")),
            _roster("BUF", 2026, 3, player=_player("00-0003", "Future")),
        ],
        depth=[
            _depth("BUF", "00-0001", "Away RB", datetime(2026, 9, 12, tzinfo=UTC), player=player),
            _depth("NYJ", "00-0002", "Home WR", datetime(2026, 9, 12, tzinfo=UTC)),
        ],
        player_stats=[
            _player_stats("BUF", 2026, player=player),
            _player_stats("NYJ", 2026, player=_player("00-0002", "Home WR")),
        ],
    )

    context = build_nfl_game_contexts(games=[game], composer=composer)[0]

    assert context.game.source_game_id == "2026_02_BUF_NYJ"
    assert context.away_team_stats.team_abbreviation == "BUF"
    assert context.home_team_stats.team_abbreviation == "NYJ"
    assert [entry.week for entry in context.away_roster] == [2]
    assert context.away_roster[0].player is player
    assert context.away_availability.players[0].player is player
    assert context.away_availability.players[0].injury_status == "UNKNOWN"
    assert context.away_availability.players[0].gameday_status == "UNKNOWN"
    assert context.away_player_stats[0].player is player


def test_depth_chart_uses_latest_snapshot_at_or_before_game_start():
    game = _game(season=2026, week=2)
    before = _depth(
        "BUF",
        "00-0001",
        "Before RB",
        datetime(2026, 9, 12, 12, tzinfo=UTC),
    )
    future = _depth(
        "BUF",
        "00-9999",
        "Future RB",
        datetime(2026, 9, 14, 12, tzinfo=UTC),
    )
    composer = _composer(
        rosters=[
            _roster("BUF", 2026, 2),
            _roster("NYJ", 2026, 2),
        ],
        depth=[
            before,
            future,
            _depth("NYJ", "00-0002", "Home WR", datetime(2026, 9, 12, tzinfo=UTC)),
        ],
    )

    context = build_nfl_game_contexts(games=[game], composer=composer)[0]

    assert context.away_availability.snapshot_time == before.snapshot_time
    assert [
        entry.depth_chart_entry.player_name
        for entry in context.away_availability.players
    ] == ["Before RB"]


def test_snap_counts_are_prior_game_context_not_same_or_future_game_projection():
    game = _game(season=2025, week=3)
    composer = _composer(
        rosters=[
            _roster("BUF", 2025, 3),
            _roster("NYJ", 2025, 3),
        ],
        snaps=[
            _snap("BUF", 2025, 1, "2025_01_BUF_MIA"),
            _snap("BUF", 2025, 3, "2025_03_BUF_NYJ"),
            _snap("BUF", 2025, 4, "2025_04_BUF_NE"),
            _snap("NYJ", 2025, 2, "2025_02_NYJ_NE"),
        ],
    )

    context = build_nfl_game_contexts(games=[game], composer=composer)[0]

    assert [snap.source_game_id for snap in context.away_prior_snaps] == [
        "2025_01_BUF_MIA",
    ]
    assert [snap.source_game_id for snap in context.home_prior_snaps] == [
        "2025_02_NYJ_NE",
    ]


def test_2026_context_does_not_fallback_to_2025_stats_or_snaps():
    game = _game(season=2026, week=1)
    composer = _composer(
        team_stats=[
            _team_stats("BUF", 2025),
            _team_stats("NYJ", 2025),
        ],
        player_stats=[
            _player_stats("BUF", 2025),
            _player_stats("NYJ", 2025),
        ],
        rosters=[
            _roster("BUF", 2026, 1),
            _roster("NYJ", 2026, 1),
        ],
        snaps=[
            _snap("BUF", 2025, 17, "2025_17_BUF_NYJ"),
            _snap("NYJ", 2025, 17, "2025_17_BUF_NYJ"),
        ],
    )

    context = build_nfl_game_contexts(games=[game], composer=composer)[0]

    assert context.away_team_stats is None
    assert context.home_team_stats is None
    assert context.away_player_stats == ()
    assert context.home_player_stats == ()
    assert context.away_prior_snaps == ()
    assert context.home_prior_snaps == ()
    assert "snap_counts_unavailable_for_season" in context.concerns


def test_historical_game_does_not_receive_current_roster_membership():
    game = _game(season=2025, week=5)
    composer = _composer(
        rosters=[
            _roster("BUF", 2026, 5),
            _roster("NYJ", 2026, 5),
        ],
    )

    context = build_nfl_game_contexts(games=[game], composer=composer)[0]

    assert context.away_roster == ()
    assert context.home_roster == ()
    assert "away_weekly_roster_unavailable" in context.concerns
    assert "home_weekly_roster_unavailable" in context.concerns


def test_empty_schedule_is_safe():
    assert build_nfl_game_contexts(games=[], composer=_composer()) == []


def test_partial_provider_failure_still_builds_context():
    game = _game(season=2026, week=2)
    composer = _composer(
        team_stats_provider=_FailingTeamStatsProvider(),
        rosters=[
            _roster("BUF", 2026, 2),
            _roster("NYJ", 2026, 2),
        ],
    )

    context = build_nfl_game_contexts(games=[game], composer=composer)[0]

    assert context.game == game
    assert context.away_team_stats is None
    assert context.home_team_stats is None
    assert "away_team_stats_unavailable" in context.concerns
    assert "home_team_stats_unavailable" in context.concerns


def test_bulk_loads_once_per_season_and_game_type():
    games = [
        _game(season=2026, week=1),
        _game(season=2026, week=2, source_game_id="2026_02_BUF_NYJ"),
    ]
    team_provider = _TeamStatsProvider([])
    roster_provider = _RosterProvider([])
    depth_provider = _DepthProvider([])
    player_stats_provider = _PlayerStatsProvider([])
    snaps_provider = _SnapsProvider([])
    composer = NFLGameContextComposer(
        team_stats_provider=team_provider,
        roster_provider=roster_provider,
        depth_chart_provider=depth_provider,
        player_stats_provider=player_stats_provider,
        snap_counts_provider=snaps_provider,
    )

    contexts = build_nfl_game_contexts(games=games, composer=composer)

    assert len(contexts) == 2
    assert team_provider.calls == [(2026, "REG")]
    assert roster_provider.calls == [2026]
    assert depth_provider.calls == [2026]
    assert player_stats_provider.calls == [(2026, "REG")]
    assert snaps_provider.calls == [2026]


def _composer(
    *,
    team_stats=None,
    rosters=None,
    depth=None,
    player_stats=None,
    snaps=None,
    team_stats_provider=None,
):
    return NFLGameContextComposer(
        team_stats_provider=team_stats_provider or _TeamStatsProvider(team_stats or []),
        roster_provider=_RosterProvider(rosters or []),
        depth_chart_provider=_DepthProvider(depth or []),
        player_stats_provider=_PlayerStatsProvider(player_stats or []),
        snap_counts_provider=_SnapsProvider(snaps or []),
    )


class _TeamStatsProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def load_team_stats(self, *, season, season_type="REG", team=None):
        self.calls.append((season, season_type))
        return [
            row
            for row in self.rows
            if row.season == season and row.season_type == season_type
        ]


class _FailingTeamStatsProvider:
    def load_team_stats(self, *, season, season_type="REG", team=None):
        raise RuntimeError("source down")


class _RosterProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def load_weekly_roster(self, *, season, week=None, team=None):
        self.calls.append(season)
        return [row for row in self.rows if row.season == season]


class _DepthProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def load_depth_chart_snapshots(self, *, season):
        self.calls.append(season)
        return self.rows


class _PlayerStatsProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def load_player_stats(self, *, season, season_type="REG", player_id=None, team=None):
        self.calls.append((season, season_type))
        return [
            row
            for row in self.rows
            if row.season == season and row.season_type == season_type
        ]


class _SnapsProvider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def load_snap_counts(
        self,
        *,
        season,
        week=None,
        game_type=None,
        team=None,
        player_id=None,
        game_id=None,
    ):
        self.calls.append(season)
        return [row for row in self.rows if row.season == season]


def _game(
    *,
    season,
    week,
    source_game_id=None,
):
    return NFLGame(
        source_game_id=source_game_id or f"{season}_{week:02d}_BUF_NYJ",
        season=season,
        week=week,
        game_type="REG",
        game_date=date(season, 9, 13),
        start_time=datetime(season, 9, 13, 17, tzinfo=UTC),
        away_team=NFLTeam("BUF", "Buffalo Bills", "buf"),
        home_team=NFLTeam("NYJ", "New York Jets", "nyj"),
        game_status="SCHEDULED",
    )


def _player(gsis_id, name):
    return NFLPlayer(gsis_id=gsis_id, name=name, position="RB", position_group="RB")


def _team_stats(team, season):
    return NFLTeamStats(
        team_abbreviation=team,
        season=season,
        season_type="REG",
        games_played=1,
        passing_yards=250,
    )


def _roster(team, season, week, player=None):
    resolved = player or _player(f"00-{team}-{season}-{week}", f"{team} Player")
    return NFLRosterEntry(
        player_id=resolved.gsis_id,
        team_abbreviation=team,
        season=season,
        week=week,
        game_type="REG",
        roster_status="ACT",
        position=resolved.position,
        player=resolved,
    )


def _depth(team, player_id, name, snapshot_time, player=None):
    return NFLDepthChartEntry(
        team_abbreviation=team,
        player_id=player_id,
        player_name=name,
        player=player,
        espn_id=None,
        position_group="RB",
        position="RB",
        position_name="Running Back",
        position_slot=1,
        depth_rank=1,
        snapshot_time=snapshot_time,
    )


def _player_stats(team, season, player=None):
    resolved = player or _player(f"00-{team}-{season}", f"{team} Player")
    return NFLPlayerStats(
        player_id=resolved.gsis_id,
        player=resolved,
        player_name=resolved.name,
        team_abbreviation=team,
        season=season,
        season_type="REG",
        position=resolved.position,
        games=1,
    )


def _snap(team, season, week, game_id):
    return NFLSnapCount(
        player_id=None,
        player=None,
        player_name=f"{team} Snap Player",
        pfr_player_id=None,
        team_abbreviation=team,
        opponent_abbreviation=None,
        season=season,
        week=week,
        game_type="REG",
        source_game_id=game_id,
        offense_snaps=50,
    )
