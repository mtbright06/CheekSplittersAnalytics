from __future__ import annotations

from datetime import datetime

from engine.nhl.models import NHLPlayerGameLog
from engine.nhl.prop_trends import (
    HIT,
    LAST_10,
    LAST_20,
    LAST_5,
    MISS,
    POINTS,
    PUSH,
    SAVES,
    SEASON,
    SHOTS_ON_GOAL,
    summarize_prop_lines,
    summarize_prop_trend,
    summarize_prop_windows,
)


def test_sog_controlled_examples_and_line_adjustment():
    logs = _logs([5, 4, 4, 3, 2], market="shots_on_goal")

    line_35 = summarize_prop_trend(logs, market=SHOTS_ON_GOAL, line=3.5)
    line_25 = summarize_prop_trend(logs, market="SOG", line=2.5)
    line_15 = summarize_prop_trend(logs, market=SHOTS_ON_GOAL, line=1.5)

    assert (line_35.hits, line_35.misses, line_35.hit_rate) == (3, 2, 0.6)
    assert (line_25.hits, line_25.misses, line_25.hit_rate) == (4, 1, 0.8)
    assert (line_15.hits, line_15.misses, line_15.hit_rate) == (5, 0, 1.0)
    assert [result.actual_value for result in line_35.game_results] == [5, 4, 4, 3, 2]


def test_whole_number_push_and_all_push_denominator():
    summary = summarize_prop_trend(
        _logs([3, 3, 2, 4], market="goals"),
        market="GOALS",
        line=3,
    )
    all_push = summarize_prop_trend(
        _logs([1, 1], market="assists"),
        market="ASSISTS",
        line=1,
    )

    assert (summary.hits, summary.misses, summary.pushes) == (1, 1, 2)
    assert [result.result for result in summary.game_results] == [
        PUSH,
        PUSH,
        MISS,
        HIT,
    ]
    assert summary.hit_rate == 0.5
    assert all_push.hit_rate is None


def test_points_and_saves_markets():
    points = summarize_prop_trend(
        _logs([2, 1, 0], market="points"),
        market=POINTS,
        line=0.5,
    )
    saves = summarize_prop_trend(
        _logs([35, 24, 18], market="saves"),
        market=SAVES,
        line=24.5,
    )

    assert (points.hits, points.misses) == (2, 1)
    assert (saves.hits, saves.misses) == (1, 2)


def test_windows_select_descending_game_dates():
    logs = _logs(list(range(1, 22)), market="shots_on_goal")
    windows = summarize_prop_windows(logs, market=SHOTS_ON_GOAL, line=10.5)

    assert windows[LAST_5].games_considered == 5
    assert windows[LAST_10].games_considered == 10
    assert windows[LAST_20].games_considered == 20
    assert windows[SEASON].games_considered == 21
    assert [result.actual_value for result in windows[LAST_5].game_results] == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_missing_stat_exclusion_invalid_market_empty_history_and_ladder_helper():
    logs = [
        _log(1, shots_on_goal=4),
        _log(2, shots_on_goal=None),
        _log(3, shots_on_goal=2),
    ]
    summary = summarize_prop_trend(logs, market=SHOTS_ON_GOAL, line=2.5)
    unsupported = summarize_prop_trend(logs, market="BLOCKS", line=1.5)
    empty = summarize_prop_trend([], market=SHOTS_ON_GOAL, line=2.5)
    ladder = summarize_prop_lines(
        logs,
        market=SHOTS_ON_GOAL,
        lines=[1.5, 2.5, 3.5],
    )

    assert summary.games_considered == 2
    assert summary.hits == 1
    assert unsupported.game_results == ()
    assert unsupported.concerns == ("unsupported_market",)
    assert empty.hit_rate is None
    assert ladder[1.5].hits == 2
    assert ladder[2.5].hits == 1
    assert ladder[3.5].hits == 1


def test_saves_missing_does_not_count_as_zero():
    summary = summarize_prop_trend(
        [
            _log(1, saves=30),
            _log(2, saves=None),
            _log(3, saves=10),
        ],
        market=SAVES,
        line=20.5,
    )

    assert summary.games_considered == 2
    assert (summary.hits, summary.misses) == (1, 1)


def _logs(values, *, market):
    return [
        _log(index + 1, **{market: value})
        for index, value in enumerate(values)
    ]


def _log(
    index,
    *,
    shots_on_goal=None,
    goals=None,
    assists=None,
    points=None,
    saves=None,
):
    return NHLPlayerGameLog(
        player_id=1,
        player=None,
        game_id=1000 + index,
        game_date=datetime(2024, 4, 30 - index),
        season_id=20232024,
        game_type="REG",
        team_abbreviation="EDM",
        opponent_abbreviation="VAN",
        home_away="HOME",
        goals=goals,
        assists=assists,
        points=points,
        shots_on_goal=shots_on_goal,
        saves=saves,
        shots_against=35 if saves is not None else None,
    )
