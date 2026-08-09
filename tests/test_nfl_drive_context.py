from __future__ import annotations

from engine.nfl.drive_context import (
    build_nfl_drive_contexts,
    normalize_drive_contexts,
)
from engine.nfl.models import NFLPlay, NFLScoringOpportunity


def test_drive_identity_possession_result_and_ordering_are_preserved():
    contexts = normalize_drive_contexts(
        [
            _play(140, drive=1, play_type="run"),
            _play(40, drive=1, play_type="kickoff"),
            _play(90, drive=1, play_type="pass"),
            _play(200, drive=2, possession_team="NYJ", defense_team="BUF", result="Punt"),
        ]
    )

    first = contexts[0]
    assert (first.game_id, first.drive_id) == ("2025_01_BUF_NYJ", 1)
    assert first.season == 2025
    assert first.week == 1
    assert first.game_type == "REG"
    assert first.possession_team == "BUF"
    assert first.defensive_team == "NYJ"
    assert first.start_quarter == 1
    assert first.end_quarter == 1
    assert first.start_yard_line == "BUF 25"
    assert first.end_yard_line == "NYJ 1"
    assert first.play_count == 3
    assert first.drive_result == "Touchdown"
    assert first.play_ids == (40, 90, 140)
    assert contexts[1].drive_result == "Punt"


def test_game_drive_play_association_and_identity_correction():
    context = normalize_drive_contexts(
        [
            _play(100, drive=1, game_id="2025_01_BUF_NYJ"),
            _play(100, drive=2, game_id="2025_01_BUF_NYJ", result="Field goal"),
        ]
    )

    assert [(drive.drive_id, drive.play_ids) for drive in context] == [
        (1, (100,)),
        (2, (100,)),
    ]


def test_scoring_opportunity_association_uses_game_drive_play_identity():
    plays = [
        _play(100, drive=1),
        _play(100, drive=2, result="Field goal"),
        _play(150, drive=2, result="Field goal"),
    ]
    opportunities = [
        NFLScoringOpportunity(
            game_id="2025_01_BUF_NYJ",
            play_id=100,
            drive_id=2,
            season=2025,
            week=1,
            offense_team="BUF",
            defense_team="NYJ",
            yardline_100=10,
            scoring_zones=("RED_ZONE", "INSIDE_10"),
            play_type="run",
        )
    ]

    contexts = normalize_drive_contexts(
        plays,
        scoring_opportunities=opportunities,
    )

    assert contexts[0].scoring_opportunity_play_ids == ()
    assert contexts[1].scoring_opportunity_play_ids == (100,)


def test_missing_drive_and_empty_input_are_safe():
    assert normalize_drive_contexts([_play(100, drive=None)]) == []
    assert normalize_drive_contexts([]) == []


def test_halftime_game_end_turnover_and_field_goal_results_are_factual_strings():
    contexts = normalize_drive_contexts(
        [
            _play(100, drive=1, result="End of half"),
            _play(200, drive=2, result="End of game"),
            _play(300, drive=3, result="Turnover"),
            _play(400, drive=4, result="Field goal"),
        ]
    )

    assert [context.drive_result for context in contexts] == [
        "End of half",
        "End of game",
        "Turnover",
        "Field goal",
    ]


def test_deterministic_filtering_by_game_week_and_team():
    contexts = build_nfl_drive_contexts(
        season=2025,
        week=1,
        team="NYJ",
        plays=[
            _play(100, drive=1, week=1),
            _play(200, drive=2, week=1, possession_team="MIA", defense_team="NE"),
            _play(300, drive=3, week=2),
        ],
    )

    assert [(context.drive_id, context.possession_team) for context in contexts] == [
        (1, "BUF"),
    ]


def _play(
    play_id,
    *,
    drive,
    game_id="2025_01_BUF_NYJ",
    season=2025,
    week=1,
    possession_team="BUF",
    defense_team="NYJ",
    play_type="run",
    result="Touchdown",
):
    return NFLPlay(
        game_id=game_id,
        play_id=play_id,
        drive_id=drive,
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
        yardline_100=20,
        play_type=play_type,
        yards_gained=3,
        drive_result=result,
        drive_quarter_start=1,
        drive_quarter_end=1,
        drive_start_yard_line="BUF 25",
        drive_end_yard_line="NYJ 1",
        drive_play_count=3,
    )
