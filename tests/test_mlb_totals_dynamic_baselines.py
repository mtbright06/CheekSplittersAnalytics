from engine.mlb.bullpen.quality import calculate_bullpen_quality
from engine.mlb.totals.expected_runs import (
    LEAGUE_RUNS_PER_TEAM,
    calculate_offense_adjustment,
    calculate_starter_adjustment,
    project_team_runs,
)
from engine.mlb.totals.park_factors import ParkFactorResult
from engine.mlb.totals.totals_model import build_totals_league_baselines


def park():
    return ParkFactorResult(
        team="TEST",
        factor=1.0,
        source="test",
        available=True,
    )


def team_profile(runs_per_game=4.45):
    return {
        "id": int(runs_per_game * 100),
        "name": "Test Team",
        "offense": {
            "runs_per_game": runs_per_game,
            "source_quality": "COMPLETE",
        },
        "bullpen": {
            "season_era": 4.0,
            "season_whip": 1.25,
            "source_quality": "COMPLETE",
        },
    }


def starter(era=4.2, whip=1.3, hr9=1.15, ip=100.0):
    return {
        "era": era,
        "whip": whip,
        "hr9": hr9,
        "ip": ip,
    }


def test_dynamic_offense_baseline_recenters_runs_per_team_only():
    league_baselines = {
        "offense": {
            "runs_per_team": 4.8,
            "source": "test",
            "sample_size": 30,
        }
    }

    adjustment, points, _ = calculate_offense_adjustment(
        team_profile(runs_per_game=4.8),
        league_baselines=league_baselines,
    )
    projection = project_team_runs(
        team_profile=team_profile(runs_per_game=4.8),
        opposing_pitcher=starter(),
        park=park(),
        is_home=False,
        league_baselines=league_baselines,
    )

    assert adjustment == 0.0
    assert points == 1
    assert projection.baseline_runs == 4.8
    assert projection.expected_runs > LEAGUE_RUNS_PER_TEAM


def test_dynamic_starter_baselines_recenter_existing_coefficients():
    league_baselines = {
        "starter": {
            "era": 3.9,
            "whip": 1.2,
            "hr9": 1.0,
            "source": "test",
            "sample_size": 30,
        }
    }
    static_adjustment, _, _ = calculate_starter_adjustment(
        starter(era=3.9, whip=1.2, hr9=1.0),
    )
    dynamic_adjustment, _, _ = calculate_starter_adjustment(
        starter(era=3.9, whip=1.2, hr9=1.0),
        league_baselines=league_baselines,
    )
    poor_adjustment, _, _ = calculate_starter_adjustment(
        starter(era=5.0, whip=1.45, hr9=1.5),
        league_baselines=league_baselines,
    )

    assert dynamic_adjustment > static_adjustment
    assert poor_adjustment > dynamic_adjustment


def test_dynamic_bullpen_baselines_recenter_quality():
    league_baselines = {
        "bullpen": {
            "era": 3.8,
            "whip": 1.2,
            "source": "test",
            "sample_size": 30,
        }
    }
    average = calculate_bullpen_quality(
        season_era=3.8,
        season_whip=1.2,
        last7_era=3.8,
        league_baselines=league_baselines,
    )
    poor = calculate_bullpen_quality(
        season_era=5.0,
        season_whip=1.45,
        last7_era=5.0,
        league_baselines=league_baselines,
    )

    assert average.quality_score == 50.0
    assert average.run_adjustment == 0.0
    assert poor.run_adjustment > average.run_adjustment


def test_totals_baseline_builder_requires_minimum_current_sample():
    insufficient = build_totals_league_baselines(
        team_profiles=[
            {**team_profile(4.8), "id": index + 1}
            for index in range(9)
        ],
        starter_profiles=[starter()] * 9,
    )
    sufficient = build_totals_league_baselines(
        team_profiles=[
            {**team_profile(4.8), "id": index + 1}
            for index in range(10)
        ],
        starter_profiles=[starter()] * 10,
    )

    assert "offense" not in insufficient
    assert "starter" not in insufficient
    assert "bullpen" not in insufficient
    assert sufficient["offense"]["runs_per_team"] == 4.8
    assert sufficient["starter"]["era"] == 4.2
    assert sufficient["bullpen"]["era"] == 4.0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
