from __future__ import annotations

from engine.nfl.models import NFLPlay, NFLPlayer
from engine.nfl.scoring_opportunities import (
    build_nfl_scoring_opportunities,
    normalize_scoring_opportunities,
)


def test_zone_boundaries_and_yardline_truth():
    opportunities = normalize_scoring_opportunities(
        [
            _play(1, yardline=20),
            _play(2, yardline=21),
            _play(3, yardline=10),
            _play(4, yardline=5),
            _play(5, yardline=None),
        ]
    )

    by_id = {opportunity.play_id: opportunity for opportunity in opportunities}
    assert by_id[1].scoring_zones == ("RED_ZONE",)
    assert 2 not in by_id
    assert by_id[3].scoring_zones == ("RED_ZONE", "INSIDE_10")
    assert by_id[4].scoring_zones == ("RED_ZONE", "INSIDE_10", "INSIDE_5")
    assert 5 not in by_id


def test_rush_pass_receiver_and_touchdown_opportunities_preserve_players():
    passer = _player("00-0001", "Quarterback")
    receiver = _player("00-0002", "Receiver")
    rusher = _player("00-0003", "Runner")
    opportunities = normalize_scoring_opportunities(
        [
            _play(
                10,
                play_type="pass",
                passer_id=passer.gsis_id,
                passer=passer,
                receiver_id=receiver.gsis_id,
                receiver=receiver,
                touchdown=True,
            ),
            _play(
                11,
                play_type="run",
                rusher_id=rusher.gsis_id,
                rusher=rusher,
            ),
        ]
    )

    passing = opportunities[0]
    rushing = opportunities[1]
    assert passing.touchdown is True
    assert passing.passer is passer
    assert passing.receiver is receiver
    assert passing.rusher is None
    assert rushing.rusher is rusher
    assert rushing.passer is None


def test_special_teams_no_play_and_missing_possession_are_excluded():
    opportunities = normalize_scoring_opportunities(
        [
            _play(20, play_type="kickoff"),
            _play(21, play_type="punt"),
            _play(22, play_type="field_goal"),
            _play(23, play_type="extra_point"),
            _play(24, play_type="no_play"),
            _play(25, possession_team=None),
            _play(26, play_type="timeout"),
        ]
    )

    assert opportunities == []


def test_missing_player_identity_preserves_valid_team_event_with_concern():
    opportunity = normalize_scoring_opportunities(
        [_play(30, play_type="run", rusher_id=None)]
    )[0]

    assert opportunity.offense_team == "BUF"
    assert opportunity.rusher_id is None
    assert "rusher_identity_missing" in opportunity.concerns


def test_game_week_identity_and_deterministic_filters():
    plays = [
        _play(40, week=1, possession_team="BUF", defense_team="NYJ", rusher_id="rb1"),
        _play(41, week=1, possession_team="NYJ", defense_team="BUF", receiver_id="wr1"),
        _play(42, week=2, possession_team="BUF", defense_team="MIA", rusher_id="rb2"),
    ]

    by_team = build_nfl_scoring_opportunities(
        season=2025,
        week=1,
        team="NYJ",
        plays=plays,
    )
    by_player = build_nfl_scoring_opportunities(
        season=2025,
        player_id="rb2",
        plays=plays,
    )
    by_zone = build_nfl_scoring_opportunities(
        season=2025,
        scoring_zone="inside_10",
        plays=[
            _play(43, yardline=11),
            _play(44, yardline=10),
        ],
    )

    assert [(opp.game_id, opp.play_id, opp.week) for opp in by_team] == [
        ("2025_01_BUF_NYJ", 40, 1),
        ("2025_01_BUF_NYJ", 41, 1),
    ]
    assert [opp.play_id for opp in by_player] == [42]
    assert [opp.play_id for opp in by_zone] == [44]


def test_empty_input_is_safe():
    assert normalize_scoring_opportunities([]) == []


def _play(
    play_id,
    *,
    game_id="2025_01_BUF_NYJ",
    season=2025,
    week=1,
    yardline=20,
    play_type="run",
    possession_team="BUF",
    defense_team="NYJ",
    touchdown=False,
    passer_id=None,
    passer=None,
    rusher_id="00-0003",
    rusher=None,
    receiver_id=None,
    receiver=None,
):
    return NFLPlay(
        game_id=game_id,
        play_id=play_id,
        drive_id=1,
        season=season,
        season_type="REG",
        week=week,
        home_team="NYJ",
        away_team="BUF",
        possession_team=possession_team,
        defensive_team=defense_team,
        quarter=1,
        clock="12:00",
        down=1,
        yards_to_go=10,
        yardline_100=yardline,
        play_type=play_type,
        yards_gained=2,
        touchdown=touchdown,
        passer_id=passer_id,
        passer=passer,
        rusher_id=rusher_id,
        rusher=rusher,
        receiver_id=receiver_id,
        receiver=receiver,
    )


def _player(gsis_id, name):
    return NFLPlayer(gsis_id=gsis_id, name=name, position="RB", position_group="RB")
