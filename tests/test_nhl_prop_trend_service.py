from __future__ import annotations

from datetime import datetime
from pathlib import Path

from engine.nhl.models import NHLPlayer, NHLPlayerGameLog
from engine.nhl.prop_trend_service import NHLPropTrendReadService
from engine.nhl.prop_trends import (
    ASSISTS,
    GOALS,
    POINTS,
    SAVES,
    SHOTS_ON_GOAL,
)


def test_service_returns_sog_rows_with_all_windows():
    service = NHLPropTrendReadService(
        game_log_provider=_Provider({1: _logs(1, shots=[5, 4, 3, 2, 1, 0])})
    )

    rows = service.build_rows(
        players=[_player(1)],
        markets=[SHOTS_ON_GOAL],
        selected_lines={SHOTS_ON_GOAL: 2.5},
        season_id=20232024,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.player_id == 1
    assert row.player_name == "Player 1"
    assert row.market == SHOTS_ON_GOAL
    assert row.selected_line == 2.5
    assert row.last_5.games_considered == 5
    assert row.last_10.games_considered == 6
    assert row.last_20.games_considered == 6
    assert row.season.games_considered == 6


def test_service_returns_goals_assists_and_points_rows():
    service = NHLPropTrendReadService(
        game_log_provider=_Provider({
            1: _logs(
                1,
                goals=[1, 0, 1],
                assists=[0, 2, 1],
                points=[1, 2, 2],
            )
        })
    )

    rows = service.build_rows(
        players=[_player(1)],
        markets=[GOALS, ASSISTS, POINTS],
        selected_lines={GOALS: 0.5, ASSISTS: 0.5, POINTS: 1.5},
        season_id=20232024,
    )

    by_market = {row.market: row for row in rows}
    assert by_market[GOALS].season.hits == 2
    assert by_market[ASSISTS].season.hits == 2
    assert by_market[POINTS].season.hits == 2


def test_goalie_saves_use_existing_enriched_logs():
    service = NHLPropTrendReadService(
        game_log_provider=_Provider({30: _logs(30, position="G", saves=[31, 24, 18])})
    )

    row = service.build_rows(
        players=[_player(30, position="G")],
        markets=[SAVES],
        selected_lines={SAVES: 24.5},
        season_id=20232024,
    )[0]

    assert row.market == SAVES
    assert row.season.games_considered == 3
    assert (row.season.hits, row.season.misses) == (1, 2)


def test_multiple_markets_do_not_refetch_player_logs():
    provider = _Provider({
        1: _logs(1, shots=[4, 3], goals=[1, 0], assists=[0, 1], points=[1, 1])
    })
    service = NHLPropTrendReadService(game_log_provider=provider)

    rows = service.build_rows(
        players=[_player(1)],
        markets=[SHOTS_ON_GOAL, GOALS, ASSISTS, POINTS],
        selected_lines={
            SHOTS_ON_GOAL: 2.5,
            GOALS: 0.5,
            ASSISTS: 0.5,
            POINTS: 0.5,
        },
        season_id=20232024,
    )

    assert len(rows) == 4
    assert provider.calls == [(1, 20232024, "REG")]


def test_alternate_lines_do_not_refetch_player_logs():
    provider = _Provider({1: _logs(1, shots=[5, 4, 3, 2])})
    service = NHLPropTrendReadService(game_log_provider=provider)

    row = service.build_rows(
        players=[_player(1)],
        markets=[SHOTS_ON_GOAL],
        selected_lines={SHOTS_ON_GOAL: 2.5},
        alternate_lines={SHOTS_ON_GOAL: [1.5, 3.5]},
        season_id=20232024,
    )[0]

    assert sorted(row.alternate_lines) == [1.5, 3.5]
    assert row.alternate_lines[1.5].hits == 4
    assert row.alternate_lines[3.5].hits == 2
    assert provider.calls == [(1, 20232024, "REG")]


def test_unsupported_market_produces_row_concern_without_board_crash():
    service = NHLPropTrendReadService(
        game_log_provider=_Provider({1: _logs(1, shots=[4, 3])})
    )

    row = service.build_rows(
        players=[_player(1)],
        markets=["BLOCKS"],
        selected_lines={"BLOCKS": 1.5},
        season_id=20232024,
    )[0]

    assert row.market == "BLOCKS"
    assert row.season.games_considered == 0
    assert "unsupported_market" in row.concerns


def test_empty_player_list_returns_empty_rows():
    service = NHLPropTrendReadService(game_log_provider=_Provider({}))

    assert service.build_rows(
        players=[],
        markets=[SHOTS_ON_GOAL],
        selected_lines={SHOTS_ON_GOAL: 2.5},
        season_id=20232024,
    ) == []


def test_provider_failure_is_isolated_as_row_concern():
    service = NHLPropTrendReadService(game_log_provider=_FailingProvider())

    rows = service.build_rows(
        players=[_player(1), _player(2)],
        markets=[SHOTS_ON_GOAL],
        selected_lines={SHOTS_ON_GOAL: 2.5},
        season_id=20232024,
    )

    assert len(rows) == 2
    assert all("game_log_provider_failed" in row.concerns for row in rows)
    assert all(row.season.games_considered == 0 for row in rows)


def test_returned_rows_are_deterministic_and_sorting_ready():
    service = NHLPropTrendReadService(
        game_log_provider=_Provider({
            2: _logs(2, shots=[1, 1, 1]),
            1: _logs(1, shots=[4, 4, 1]),
        })
    )

    rows = service.build_rows(
        players=[_player(2, name="Beta"), _player(1, name="Alpha")],
        markets=[SHOTS_ON_GOAL],
        selected_lines={SHOTS_ON_GOAL: 2.5},
        season_id=20232024,
    )

    assert [row.player_id for row in rows] == [1, 2]
    assert rows[0].sort_hit_rate == 2 / 3
    assert rows[1].sort_hit_rate == 0.0


def test_service_has_no_streamlit_dependency():
    source = Path("engine/nhl/prop_trend_service.py").read_text()

    assert "streamlit" not in source.lower()


class _Provider:
    def __init__(self, logs_by_player):
        self.logs_by_player = logs_by_player
        self.calls = []

    def load_player_game_logs(self, *, player_id, season_id, game_type="REG"):
        self.calls.append((player_id, season_id, game_type))
        return list(self.logs_by_player.get(player_id, ()))


class _FailingProvider:
    def load_player_game_logs(self, **kwargs):
        raise RuntimeError("provider down")


def _player(player_id, name=None, position="C"):
    return NHLPlayer(
        source_player_id=player_id,
        name=name or f"Player {player_id}",
        team_abbreviation="EDM",
        position=position,
        position_code=position,
    )


def _logs(
    player_id,
    *,
    position="C",
    shots=None,
    goals=None,
    assists=None,
    points=None,
    saves=None,
):
    values = {
        "shots_on_goal": shots or [],
        "goals": goals or [],
        "assists": assists or [],
        "points": points or [],
        "saves": saves or [],
    }
    count = max([len(items) for items in values.values()] or [0])
    logs = []
    for index in range(count):
        logs.append(
            NHLPlayerGameLog(
                player_id=player_id,
                player=None,
                game_id=1000 + index,
                game_date=datetime(2024, 4, 30 - index),
                season_id=20232024,
                game_type="REG",
                team_abbreviation="EDM",
                opponent_abbreviation="VAN",
                home_away="HOME",
                position=position,
                goals=_value_at(values["goals"], index),
                assists=_value_at(values["assists"], index),
                points=_value_at(values["points"], index),
                shots_on_goal=_value_at(values["shots_on_goal"], index),
                saves=_value_at(values["saves"], index),
                shots_against=35 if _value_at(values["saves"], index) is not None else None,
            )
        )
    return logs


def _value_at(values, index):
    if index >= len(values):
        return None
    return values[index]
