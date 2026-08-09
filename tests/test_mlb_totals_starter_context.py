from engine.mlb.totals.expected_runs import (
    calculate_starter_context_adjustment,
    project_team_runs,
)
from engine.mlb.totals.park_factors import ParkFactorResult


TEAM = {
    "name": "Test Offense",
    "offense": {
        "runs_per_game": 4.5,
        "ops": 0.720,
        "wrc_plus": 100,
    },
}

BASELINES = {
    "offense": {
        "runs_per_team": 4.5,
    },
    "starter": {
        "era": 4.0,
        "whip": 1.25,
        "hr9": 1.1,
    },
}

PARK = ParkFactorResult(
    team="TST",
    factor=1.0,
    source="TEST",
    available=True,
)


def pitcher(**overrides):
    data = {
        "era": 4.0,
        "whip": 1.25,
        "hr9": 1.1,
        "days_rest": 5,
        "previous_start_ip": 6.0,
        "previous_start_pitch_count": 92,
        "average_start_ip": 5.8,
        "role_context": "established_starter",
    }
    data.update(overrides)
    return data


def projected_runs(opposing_pitcher):
    return project_team_runs(
        team_profile=TEAM,
        opposing_pitcher=opposing_pitcher,
        park=PARK,
        is_home=False,
        league_baselines=BASELINES,
    )


def test_average_starter_normal_context_is_strength_neutral():
    context = calculate_starter_context_adjustment(pitcher())
    projection = projected_runs(pitcher())

    assert context[0] == 0.0
    assert projection.starter_context_adjustment == 0.0
    assert projection.expected_runs == 4.5


def test_short_rest_and_heavy_workload_raise_projected_runs_modestly():
    taxed = pitcher(
        days_rest=3,
        previous_start_ip=7.0,
        previous_start_pitch_count=112,
    )
    context = calculate_starter_context_adjustment(taxed)
    projection = projected_runs(taxed)

    assert context[0] == 0.30
    assert projection.starter_context_adjustment == 0.30
    assert projection.expected_runs == 4.8
    assert "Starter is on very short rest." in projection.reasons
    assert "Starter carried a heavy previous pitch count." in projection.reasons
    assert "Starter worked deep into the previous start." in projection.reasons


def test_unknown_rest_and_workload_remain_strength_neutral():
    unknown = pitcher(
        days_rest=None,
        previous_start_ip=None,
        previous_start_pitch_count=None,
    )
    context = calculate_starter_context_adjustment(unknown)
    projection = projected_runs(unknown)

    assert context[0] == 0.0
    assert projection.starter_context_adjustment == 0.0
    assert projection.expected_runs == 4.5


def test_opener_risk_has_bounded_full_game_authority():
    opener = pitcher(
        role_context="opener_risk",
        average_start_ip=2.0,
    )
    context = calculate_starter_context_adjustment(opener)
    projection = projected_runs(opener)

    assert context[0] == 0.12
    assert projection.starter_context_adjustment == 0.12
    assert projection.expected_runs == 4.62


def test_limited_starter_role_does_not_receive_first5_sized_penalty():
    limited = pitcher(
        role_context="limited_starting_role",
        average_start_ip=3.5,
    )
    context = calculate_starter_context_adjustment(limited)
    projection = projected_runs(limited)

    assert context[0] == 0.05
    assert projection.starter_context_adjustment == 0.05
    assert projection.expected_runs == 4.55


def test_extra_rest_is_tiny_benefit_and_extended_rest_is_neutral():
    extra = calculate_starter_context_adjustment(pitcher(days_rest=7))
    extended = calculate_starter_context_adjustment(pitcher(days_rest=9))

    assert extra[0] == -0.03
    assert extended[0] == 0.0
