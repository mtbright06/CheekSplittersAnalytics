from __future__ import annotations

from datetime import date

from engine.nfl.models import NFLPlayerGameLog
from engine.nfl.prop_trends import (
    ANYTIME_TOUCHDOWN,
    HIT,
    LAST_10,
    LAST_20,
    LAST_5,
    MISS,
    PASSING_TOUCHDOWNS,
    PASSING_YARDS,
    PREVIOUS_SEASON,
    PUSH,
    RECEIVING_YARDS,
    RECEPTIONS,
    RUSHING_YARDS,
    SEASON,
    summarize_prop_lines,
    summarize_prop_trend,
    summarize_prop_windows,
)


def test_all_first_release_market_actual_values():
    log = _log(
        passing_yards=275,
        passing_touchdowns=3,
        rushing_yards=42,
        receiving_yards=88,
        receptions=7,
        rushing_touchdowns=1,
        receiving_touchdowns=1,
        special_teams_touchdowns=1,
    )
    expected = {
        PASSING_YARDS: 275,
        PASSING_TOUCHDOWNS: 3,
        RUSHING_YARDS: 42,
        RECEIVING_YARDS: 88,
        RECEPTIONS: 7,
        ANYTIME_TOUCHDOWN: 3,
    }

    for market, actual in expected.items():
        summary = summarize_prop_trend(
            [log], market=market, line=-1, selected_season=2026
        )
        assert summary.game_results[0].actual_value == actual


def test_anytime_touchdown_excludes_passing_defensive_and_fumble_scores():
    log = _log(
        passing_touchdowns=4,
        rushing_touchdowns=0,
        receiving_touchdowns=0,
        special_teams_touchdowns=0,
    )
    summary = summarize_prop_trend(
        [log], market=ANYTIME_TOUCHDOWN, line=0.5, selected_season=2026
    )

    assert summary.game_results[0].actual_value == 0
    assert summary.game_results[0].result == MISS


def test_hit_miss_push_and_push_excluded_from_hit_rate_denominator():
    logs = [
        _log(week=1, passing_yards=251),
        _log(week=2, passing_yards=250),
        _log(week=3, passing_yards=249),
    ]
    summary = summarize_prop_trend(
        logs, market=PASSING_YARDS, line=250, selected_season=2026
    )

    assert [result.result for result in summary.game_results] == [MISS, PUSH, HIT]
    assert summary.hits == 1
    assert summary.misses == 1
    assert summary.pushes == 1
    assert summary.hit_rate == 0.5


def test_recent_windows_cross_seasons_but_season_windows_are_isolated():
    logs = [
        *[_log(season=2025, week=week, passing_yards=200 + week) for week in range(1, 21)],
        *[_log(season=2026, week=week, passing_yards=300 + week) for week in range(1, 4)],
    ]
    windows = summarize_prop_windows(
        logs,
        market=PASSING_YARDS,
        line=250.5,
        selected_season=2026,
    )

    assert windows[LAST_5].games_considered == 5
    assert [result.season for result in windows[LAST_5].game_results] == [2026, 2026, 2026, 2025, 2025]
    assert windows[LAST_10].games_considered == 10
    assert windows[LAST_20].games_considered == 20
    assert {result.season for result in windows[SEASON].game_results} == {2026}
    assert windows[SEASON].games_considered == 3
    assert {result.season for result in windows[PREVIOUS_SEASON].game_results} == {2025}
    assert windows[PREVIOUS_SEASON].games_considered == 20


def test_recent_windows_follow_actual_game_dates_not_input_or_week_order():
    logs = [
        _log(
            season=2025,
            week=18,
            game_date=date(2026, 1, 4),
            passing_yards=180,
        ),
        _log(
            season=2025,
            week=17,
            game_date=date(2026, 1, 11),
            passing_yards=320,
        ),
        _log(
            season=2024,
            week=18,
            game_date=date(2025, 1, 5),
            passing_yards=220,
        ),
    ]
    summary = summarize_prop_trend(
        reversed(logs),
        market=PASSING_YARDS,
        line=250.5,
        selected_season=2026,
        window=LAST_5,
    )

    assert [result.actual_value for result in summary.game_results] == [320, 180, 220]


def test_postseason_never_enters_regular_season_windows():
    logs = [
        _log(season=2025, week=18, game_type="REG", passing_yards=200),
        _log(season=2025, week=19, game_type="POST", passing_yards=500),
    ]
    summary = summarize_prop_trend(
        logs,
        market=PASSING_YARDS,
        line=300.5,
        selected_season=2026,
        window=LAST_5,
    )

    assert summary.games_considered == 1
    assert summary.game_results[0].actual_value == 200


def test_pre_week_one_current_season_is_empty_while_recent_uses_previous_year():
    logs = [_log(season=2025, week=18, passing_yards=280)]
    windows = summarize_prop_windows(
        logs,
        market=PASSING_YARDS,
        line=250.5,
        selected_season=2026,
    )

    assert windows[SEASON].games_considered == 0
    assert windows[SEASON].hit_rate is None
    assert "no_current_season_game_logs" in windows[SEASON].concerns
    assert windows[LAST_5].games_considered == 1
    assert windows[PREVIOUS_SEASON].games_considered == 1


def test_alternate_lines_reuse_logs_and_preserve_pushes():
    summaries = summarize_prop_lines(
        [_log(passing_touchdowns=2)],
        market=PASSING_TOUCHDOWNS,
        lines=[1.5, 2.0, 2.5],
        selected_season=2026,
    )

    assert summaries[1.5].game_results[0].result == HIT
    assert summaries[2.0].game_results[0].result == PUSH
    assert summaries[2.5].game_results[0].result == MISS


def _log(
    *,
    season=2026,
    week=1,
    game_type="REG",
    passing_yards=0,
    passing_touchdowns=0,
    rushing_yards=0,
    rushing_touchdowns=0,
    receiving_yards=0,
    receiving_touchdowns=0,
    receptions=0,
    special_teams_touchdowns=0,
    game_date=None,
):
    return NFLPlayerGameLog(
        player_id="00-0000001",
        player=None,
        player_name="Test Player",
        game_id=f"{season}_{week:02d}_KC_BUF",
        game_date=game_date or date(season, 9, min(week, 28)),
        season=season,
        week=week,
        game_type=game_type,
        team_abbreviation="KC",
        opponent_abbreviation="BUF",
        home_away="AWAY",
        passing_yards=passing_yards,
        passing_touchdowns=passing_touchdowns,
        rushing_yards=rushing_yards,
        rushing_touchdowns=rushing_touchdowns,
        receiving_yards=receiving_yards,
        receiving_touchdowns=receiving_touchdowns,
        receptions=receptions,
        special_teams_touchdowns=special_teams_touchdowns,
    )
