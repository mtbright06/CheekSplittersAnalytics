from __future__ import annotations

from datetime import date

from engine.nfl.models import NFLPlayer, NFLPlayerGameLog, NFLRosterEntry
from engine.nfl.player_game_logs import NFLPlayerGameLogBatch
from engine.nfl.prop_trend_service import NFLPropTrendReadService
from engine.nfl.prop_trends import (
    ANYTIME_TOUCHDOWN,
    PASSING_TOUCHDOWNS,
    PASSING_YARDS,
    RECEIVING_YARDS,
    RECEPTIONS,
    RUSHING_YARDS,
)


def test_bulk_history_supports_players_markets_windows_and_alternate_lines():
    provider = _Provider(
        {
            2025: [_log("p1", "Alpha", season=2025, week=18, passing_yards=240)],
            2026: [
                _log("p1", "Alpha", season=2026, week=1, passing_yards=300),
                _log("p2", "Beta", season=2026, week=1, receiving_yards=100),
            ],
        }
    )
    service = NFLPropTrendReadService(game_log_provider=provider)

    result = service.build_rows(
        roster_entries=[_roster("p1", "Alpha", "QB"), _roster("p2", "Beta", "WR")],
        markets=[PASSING_YARDS, RECEIVING_YARDS],
        selected_lines={PASSING_YARDS: 250.5, RECEIVING_YARDS: 75.5},
        selected_season=2026,
        alternate_lines={PASSING_YARDS: [225.5, 275.5]},
    )

    assert len(result.rows) == 4
    alpha_passing = next(
        row for row in result.rows if row.player_id == "p1" and row.market == PASSING_YARDS
    )
    assert alpha_passing.last_5.games_considered == 2
    assert alpha_passing.season.games_considered == 1
    assert alpha_passing.previous_season.games_considered == 1
    assert set(alpha_passing.alternate_lines) == {225.5, 275.5}
    assert provider.calls == [(2025, {"p1", "p2"}), (2026, {"p1", "p2"})]


def test_pre_week_one_returns_explicit_empty_season_and_previous_recent_history():
    provider = _Provider(
        {2025: [_log("p1", "Alpha", season=2025, week=18, passing_yards=275)]},
        unavailable={2026},
    )
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[_roster("p1", "Alpha", "QB")],
        markets=[PASSING_YARDS],
        selected_lines=250.5,
        selected_season=2026,
    )

    row = result.rows[0]
    assert row.season.games_considered == 0
    assert row.season.hit_rate is None
    assert row.last_5.games_considered == 1
    assert row.previous_season.games_considered == 1
    assert "player_game_logs_source_unavailable:2026" in row.concerns


def test_deterministic_sort_uses_l10_then_games_then_name():
    provider = _Provider(
        {
            2026: [
                _log("p2", "Beta", passing_yards=300),
                _log("p1", "Alpha", passing_yards=300),
                _log("p3", "Gamma", passing_yards=100),
            ]
        }
    )
    entries = [
        _roster("p3", "Gamma", "QB"),
        _roster("p2", "Beta", "QB"),
        _roster("p1", "Alpha", "QB"),
    ]
    service = NFLPropTrendReadService(game_log_provider=provider)

    first = service.build_rows(
        roster_entries=entries,
        markets=[PASSING_YARDS],
        selected_lines=250.5,
        selected_season=2026,
    )
    second = service.build_rows(
        roster_entries=reversed(entries),
        markets=[PASSING_YARDS],
        selected_lines=250.5,
        selected_season=2026,
    )

    assert [row.player_name for row in first.rows] == ["Alpha", "Beta", "Gamma"]
    assert first.rows == second.rows


def test_unresolved_roster_identity_is_skipped_with_board_concern():
    unresolved = NFLRosterEntry(
        player_id="missing",
        player=None,
        team_abbreviation="KC",
        season=2026,
        week=1,
        position="WR",
    )
    result = NFLPropTrendReadService(game_log_provider=_Provider({})).build_rows(
        roster_entries=[unresolved],
        markets=[RECEIVING_YARDS],
        selected_lines=50.5,
        selected_season=2026,
    )

    assert result.rows == ()
    assert result.concerns == ("roster_player_identity_unresolved:missing",)


def test_unsupported_market_is_a_row_concern_not_a_board_failure():
    result = NFLPropTrendReadService(
        game_log_provider=_Provider({2026: [_log("p1", "Alpha")]})
    ).build_rows(
        roster_entries=[_roster("p1", "Alpha", "QB")],
        markets=["NOT_A_MARKET"],
        selected_lines=0.5,
        selected_season=2026,
    )

    assert len(result.rows) == 1
    assert result.rows[0].season.games_considered == 0
    assert "unsupported_market" in result.rows[0].concerns


def test_anytime_touchdown_row_uses_factual_composed_value():
    provider = _Provider(
        {
            2026: [
                _log(
                    "p1",
                    "Alpha",
                    rushing_touchdowns=1,
                    receiving_touchdowns=0,
                    special_teams_touchdowns=1,
                )
            ]
        }
    )
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[_roster("p1", "Alpha", "RB")],
        markets=[ANYTIME_TOUCHDOWN],
        selected_lines=0.5,
        selected_season=2026,
    )

    assert result.rows[0].season.game_results[0].actual_value == 2


def test_usage_filter_excludes_depth_passer_but_keeps_meaningful_qb():
    provider = _Provider({2025: [
        _log("starter", "Starter", passing_yards=300),
        _log("depth", "Depth", passing_yards=20),
    ]})
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[
            _roster("starter", "Starter", "QB"),
            _roster("depth", "Depth", "QB"),
        ],
        markets=[PASSING_YARDS, PASSING_TOUCHDOWNS],
        selected_lines=1.5,
        selected_season=2026,
        require_meaningful_usage=True,
    )

    assert {(row.player_id, row.market) for row in result.rows} == {
        ("starter", PASSING_YARDS),
        ("starter", PASSING_TOUCHDOWNS),
    }


def test_usage_filter_requires_meaningful_rushing_workload():
    provider = _Provider({2025: [
        _log("rb", "Runner", carries=12, rushing_yards=48),
        _log("wr", "Occasional Runner", carries=2, rushing_yards=8),
    ]})
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[_roster("rb", "Runner", "RB"), _roster("wr", "Occasional Runner", "WR")],
        markets=[RUSHING_YARDS],
        selected_lines=49.5,
        selected_season=2026,
        require_meaningful_usage=True,
    )

    assert [row.player_id for row in result.rows] == ["rb"]


def test_usage_filter_requires_meaningful_receiving_workload():
    provider = _Provider({2025: [
        _log("wr", "Receiver", targets=12, receptions=6, receiving_yards=45),
        _log("te", "Depth Tight End", targets=1, receptions=1, receiving_yards=4),
    ]})
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[_roster("wr", "Receiver", "WR"), _roster("te", "Depth Tight End", "TE")],
        markets=[RECEIVING_YARDS, RECEPTIONS],
        selected_lines=3.5,
        selected_season=2026,
        require_meaningful_usage=True,
    )

    assert {row.player_id for row in result.rows} == {"wr"}


def test_usage_filter_excludes_zero_opportunity_anytime_td_depth():
    provider = _Provider({2025: [
        _log("primary", "Primary", carries=8, targets=4),
        _log("depth", "Depth", carries=1, targets=1),
    ]})
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[_roster("primary", "Primary", "RB"), _roster("depth", "Depth", "RB")],
        markets=[ANYTIME_TOUCHDOWN],
        selected_lines=0.5,
        selected_season=2026,
        require_meaningful_usage=True,
    )

    assert [row.player_id for row in result.rows] == ["primary"]


def test_meaningful_sample_with_no_hits_remains_true_zero_percent():
    provider = _Provider({2025: [
        _log("runner", "Runner", carries=12, rushing_yards=0),
    ]})
    result = NFLPropTrendReadService(game_log_provider=provider).build_rows(
        roster_entries=[_roster("runner", "Runner", "RB")],
        markets=[RUSHING_YARDS],
        selected_lines=49.5,
        selected_season=2026,
        require_meaningful_usage=True,
    )

    assert result.rows[0].last_10.games_considered == 1
    assert result.rows[0].last_10.hit_rate == 0.0


def _roster(player_id, name, position):
    player = NFLPlayer(gsis_id=player_id, name=name, position=position)
    return NFLRosterEntry(
        player_id=player_id,
        player=player,
        team_abbreviation="KC",
        season=2026,
        week=1,
        roster_status="ACT",
        position=position,
    )


def _log(
    player_id,
    name,
    *,
    season=2026,
    week=1,
    passing_yards=0,
    passing_touchdowns=0,
    carries=0,
    rushing_yards=0,
    targets=0,
    receptions=0,
    receiving_yards=0,
    rushing_touchdowns=0,
    receiving_touchdowns=0,
    special_teams_touchdowns=0,
):
    return NFLPlayerGameLog(
        player_id=player_id,
        player=None,
        player_name=name,
        game_id=f"{season}_{week:02d}_KC_BUF_{player_id}",
        game_date=date(season, 9, min(week, 28)),
        season=season,
        week=week,
        game_type="REG",
        team_abbreviation="KC",
        opponent_abbreviation="BUF",
        home_away="AWAY",
        passing_yards=passing_yards,
        passing_touchdowns=passing_touchdowns,
        carries=carries,
        rushing_yards=rushing_yards,
        rushing_touchdowns=rushing_touchdowns,
        targets=targets,
        receptions=receptions,
        receiving_yards=receiving_yards,
        receiving_touchdowns=receiving_touchdowns,
        special_teams_touchdowns=special_teams_touchdowns,
    )


class _Provider:
    def __init__(self, logs_by_season, unavailable=()):
        self.logs_by_season = logs_by_season
        self.unavailable = set(unavailable)
        self.calls = []

    def load_player_game_logs(self, *, season, game_type, player_ids):
        selected_ids = set(player_ids)
        self.calls.append((season, selected_ids))
        logs = tuple(
            log
            for log in self.logs_by_season.get(season, ())
            if log.player_id in selected_ids
        )
        concerns = (
            (f"player_game_logs_source_unavailable:{season}",)
            if season in self.unavailable
            else ()
        )
        return NFLPlayerGameLogBatch(
            season=season,
            game_type=game_type,
            game_logs=logs,
            concerns=concerns,
        )
