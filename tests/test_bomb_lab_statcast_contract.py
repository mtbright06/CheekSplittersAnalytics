import pandas as pd

from engine.bomb_lab.pitcher_attack import build_split_stats
from engine.bomb_lab.statcast_contract import statcast_barrel_flag
from engine.hitters.target_hitters import add_contact_flags


def test_bomb_lab_uses_native_statcast_barrel_classification():
    row = {
        "launch_speed": 96.0,
        "launch_angle": 20.0,
        "launch_speed_angle": 3,
    }

    assert statcast_barrel_flag(row) == 0
    assert statcast_barrel_flag({**row, "launch_speed_angle": 6}) == 1


def test_pitcher_split_stats_do_not_use_old_barrel_approximation():
    df = pd.DataFrame(
        [
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 96.0,
                "launch_angle": 20.0,
                "launch_speed_angle": 3,
                "bb_type": "line_drive",
                "events": "single",
            },
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 100.0,
                "launch_angle": 28.0,
                "launch_speed_angle": 6,
                "bb_type": "fly_ball",
                "events": "home_run",
            },
        ]
    )

    stats = build_split_stats(df, "recent").iloc[0]

    assert stats["recent_barrel_pct"] == 0.5
    assert stats["recent_hard_hit_pct"] == 1.0
    assert stats["recent_hr_per_bbe"] == 0.5


def test_hard_hit_threshold_is_inclusive_at_95_mph():
    df = pd.DataFrame(
        [
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 94.9,
                "launch_angle": 24.0,
                "launch_speed_angle": 5,
                "bb_type": "line_drive",
                "events": "single",
            },
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 95.0,
                "launch_angle": 24.0,
                "launch_speed_angle": 5,
                "bb_type": "line_drive",
                "events": "double",
            },
        ]
    )

    stats = build_split_stats(df, "recent").iloc[0]

    assert stats["recent_hard_hit_pct"] == 0.5


def test_fly_ball_definition_counts_true_fly_balls_only():
    df = pd.DataFrame(
        [
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 90.0,
                "launch_angle": 24.0,
                "launch_speed_angle": 5,
                "bb_type": "fly_ball",
                "events": "flyout",
            },
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 90.0,
                "launch_angle": 10.0,
                "launch_speed_angle": 4,
                "bb_type": "line_drive",
                "events": "single",
            },
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 80.0,
                "launch_angle": 60.0,
                "launch_speed_angle": 3,
                "bb_type": "popup",
                "events": "field_out",
            },
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 90.0,
                "launch_angle": -5.0,
                "launch_speed_angle": 2,
                "bb_type": "ground_ball",
                "events": "groundout",
            },
        ]
    )

    stats = build_split_stats(df, "recent").iloc[0]

    assert stats["recent_fly_ball_pct"] == 0.25
    assert stats["recent_fly_ball_ev"] == 90.0


def test_missing_exit_velocity_is_excluded_from_batted_ball_strength():
    df = pd.DataFrame(
        [
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": None,
                "launch_angle": 28.0,
                "launch_speed_angle": 6,
                "bb_type": "fly_ball",
                "events": "home_run",
            },
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 100.0,
                "launch_angle": 28.0,
                "launch_speed_angle": 6,
                "bb_type": "fly_ball",
                "events": "home_run",
            },
        ]
    )

    stats = build_split_stats(df, "recent").iloc[0]

    assert stats["recent_batted_balls"] == 1
    assert stats["recent_barrel_pct"] == 1.0
    assert stats["recent_hr_per_bbe"] == 1.0


def test_recent_and_season_windows_use_identical_feature_definitions():
    df = pd.DataFrame(
        [
            {
                "pitcher": 1,
                "stand": "R",
                "p_throws": "L",
                "launch_speed": 100.0,
                "launch_angle": 28.0,
                "launch_speed_angle": 6,
                "bb_type": "fly_ball",
                "events": "home_run",
            },
        ]
    )

    recent = build_split_stats(df, "recent").iloc[0]
    season = build_split_stats(df, "season").iloc[0]

    assert recent["recent_barrel_pct"] == season["season_barrel_pct"]
    assert recent["recent_hard_hit_pct"] == season["season_hard_hit_pct"]
    assert recent["recent_fly_ball_pct"] == season["season_fly_ball_pct"]
    assert recent["recent_hr_per_bbe"] == season["season_hr_per_bbe"]


def test_hitter_contact_flags_use_same_native_barrel_contract():
    df = pd.DataFrame(
        [
            {
                "launch_speed": 96.0,
                "launch_angle": 20.0,
                "launch_speed_angle": 3,
                "events": "single",
            },
            {
                "launch_speed": 100.0,
                "launch_angle": 28.0,
                "launch_speed_angle": 6,
                "events": "home_run",
            },
        ]
    )

    flagged = add_contact_flags(df)

    assert flagged["barrel"].tolist() == [0, 1]
    assert flagged["hard_hit"].tolist() == [1, 1]
    assert flagged["is_hr"].tolist() == [0, 1]
