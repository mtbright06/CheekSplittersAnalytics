from __future__ import annotations

from engine.nfl.models import (
    NFLDriveContext,
    NFLPlayer,
    NFLScoringOpportunity,
)
from engine.nfl.opportunity_read_model import (
    summarize_player_opportunities,
    summarize_team_opportunities,
)


def test_player_rush_receiving_cumulative_zone_and_touchdown_counts():
    rb = _player("rb1", "Red Zone Back")
    wr = _player("wr1", "Slot Receiver")
    opportunities = [
        _opportunity(1, zones=("RED_ZONE",), play_type="run", rusher=rb),
        _opportunity(
            2,
            zones=("RED_ZONE", "INSIDE_10", "INSIDE_5"),
            play_type="run",
            rusher=rb,
            touchdown=True,
        ),
        _opportunity(
            3,
            zones=("RED_ZONE", "INSIDE_10"),
            play_type="pass",
            receiver=wr,
            touchdown=True,
        ),
    ]

    summaries = summarize_player_opportunities(opportunities, season=2025)
    by_player = {summary.player_id: summary for summary in summaries}

    assert by_player["rb1"].red_zone_rush_opportunities == 2
    assert by_player["rb1"].inside_10_rush_opportunities == 1
    assert by_player["rb1"].inside_5_rush_opportunities == 1
    assert by_player["rb1"].rushing_touchdowns_from_qualified_events == 1
    assert by_player["wr1"].red_zone_receiving_opportunities == 1
    assert by_player["wr1"].inside_10_receiving_opportunities == 1
    assert by_player["wr1"].inside_5_receiving_opportunities == 0
    assert by_player["wr1"].receiving_touchdowns_from_qualified_events == 1


def test_missing_receiver_does_not_create_receiver_count_but_team_count_remains():
    opportunities = [
        _opportunity(1, play_type="pass", receiver=None),
    ]

    player_summaries = summarize_player_opportunities(opportunities, season=2025)
    team_summary = summarize_team_opportunities(opportunities, season=2025)[0]

    assert player_summaries == []
    assert team_summary.scoring_opportunities_20 == 1
    assert team_summary.pass_opportunities == 1


def test_team_counts_historical_ownership_and_drive_result_counts():
    opportunities = [
        _opportunity(1, offense_team="BUF", play_type="run"),
        _opportunity(
            2,
            offense_team="BUF",
            zones=("RED_ZONE", "INSIDE_10"),
            play_type="pass",
            receiver=_player("wr1", "Receiver"),
            touchdown=True,
        ),
        _opportunity(3, offense_team="NYJ", play_type="run"),
    ]
    drives = [
        _drive(1, "BUF", "Touchdown"),
        _drive(2, "BUF", "Punt"),
        _drive(3, "NYJ", "Turnover"),
    ]

    summaries = summarize_team_opportunities(
        opportunities,
        season=2025,
        drives=drives,
    )
    by_team = {summary.team_abbreviation: summary for summary in summaries}

    assert by_team["BUF"].scoring_opportunities_20 == 2
    assert by_team["BUF"].scoring_opportunities_10 == 1
    assert by_team["BUF"].rush_opportunities == 1
    assert by_team["BUF"].pass_opportunities == 1
    assert by_team["BUF"].touchdown_opportunities == 1
    assert by_team["BUF"].drive_result_counts == (("Punt", 1), ("Touchdown", 1))
    assert by_team["NYJ"].drive_result_counts == (("Turnover", 1),)


def test_week_game_player_team_filters_and_empty_input_are_deterministic():
    rb = _player("rb1", "Back")
    opportunities = [
        _opportunity(1, game_id="game_a", week=1, offense_team="BUF", rusher=rb),
        _opportunity(2, game_id="game_b", week=2, offense_team="BUF", rusher=rb),
        _opportunity(3, game_id="game_b", week=2, offense_team="NYJ", rusher=rb),
    ]

    assert [
        summary.games_represented
        for summary in summarize_player_opportunities(
            opportunities,
            season=2025,
            week=2,
            game_id="game_b",
            team="BUF",
            player_id="rb1",
        )
    ] == [("game_b",)]
    assert summarize_player_opportunities([], season=2025) == []
    assert summarize_team_opportunities([], season=2025) == []


def _opportunity(
    play_id,
    *,
    game_id="2025_01_BUF_NYJ",
    week=1,
    offense_team="BUF",
    defense_team="NYJ",
    zones=("RED_ZONE",),
    play_type="run",
    rusher=None,
    receiver=None,
    touchdown=False,
):
    return NFLScoringOpportunity(
        game_id=game_id,
        play_id=play_id,
        drive_id=1,
        season=2025,
        week=week,
        offense_team=offense_team,
        defense_team=defense_team,
        yardline_100=5 if "INSIDE_5" in zones else 10 if "INSIDE_10" in zones else 20,
        scoring_zones=zones,
        play_type=play_type,
        touchdown=touchdown,
        rusher_id=rusher.gsis_id if rusher else None,
        rusher=rusher,
        receiver_id=receiver.gsis_id if receiver else None,
        receiver=receiver,
    )


def _drive(drive_id, team, result):
    return NFLDriveContext(
        game_id="2025_01_BUF_NYJ",
        drive_id=drive_id,
        season=2025,
        week=1,
        game_type="REG",
        possession_team=team,
        defensive_team="NYJ" if team == "BUF" else "BUF",
        drive_result=result,
        play_ids=(drive_id * 10,),
    )


def _player(gsis_id, name):
    return NFLPlayer(gsis_id=gsis_id, name=name, position="RB", position_group="RB")
