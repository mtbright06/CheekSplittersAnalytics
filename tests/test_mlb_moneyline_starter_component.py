from engine.model.component_scores import (
    offense_score,
    starting_pitcher_breakdown,
    starting_pitcher_score,
)
from engine.model.recommendations import MLB_MONEYLINE_V2_CANDIDATE_TIERS
from engine.model.sharpscore import WEIGHTS, build_sharpscore_decision


BASE_PITCHER = {
    "name": "Sample Starter",
    "ip": 120.0,
    "era": 4.50,
    "whip": 1.35,
    "k_bb_pct": 14.0,
    "hr9": 1.20,
}

BASE_OFFENSE = {
    "runs_per_game": 4.4,
    "ops": 0.710,
    "iso": 0.160,
    "bb_rate": 8.0,
    "k_rate": 22.0,
}


def test_better_pitcher_performance_increases_score():
    strong = starting_pitcher_score(
        {
            **BASE_PITCHER,
            "era": 3.10,
            "whip": 1.05,
            "k_bb_pct": 24.0,
            "hr9": 0.75,
        }
    )
    weak = starting_pitcher_score(
        {
            **BASE_PITCHER,
            "era": 5.60,
            "whip": 1.55,
            "k_bb_pct": 5.0,
            "hr9": 1.75,
        }
    )

    assert strong > 50.0
    assert weak < 50.0
    assert strong > weak


def test_missing_metrics_are_neutral_and_active_metrics_renormalize():
    assert starting_pitcher_score({}) == 50.0
    assert starting_pitcher_score({"name": "Unknown Starter"}) == 50.0

    era_only = starting_pitcher_breakdown(
        {
            "name": "Sample Starter",
            "ip": 120.0,
            "era": 3.20,
        }
    )

    assert era_only["active_subcomponents"] == ["run_prevention"]
    assert era_only["starting_pitching_score"] == era_only["run_prevention"]
    assert "whip" in era_only["missing_inputs"]


def test_overlapping_metrics_do_not_receive_duplicate_authority():
    baseline = starting_pitcher_score(BASE_PITCHER)
    noisy_overlap = starting_pitcher_score(
        {
            **BASE_PITCHER,
            "k_rate": 13.0,
            "bb_rate": 1.0,
            "strike_pct": 70.0,
            "h9": 5.0,
            "pitches_per_inning": 12.0,
            "ground_air_ratio": 2.0,
        }
    )

    assert noisy_overlap == baseline


def test_market_fields_cannot_affect_starter_score():
    baseline = starting_pitcher_score(BASE_PITCHER)
    with_market = starting_pitcher_score(
        {
            **BASE_PITCHER,
            "edge": 25.0,
            "ev": 18.0,
            "odds": 180,
            "model_probability": 0.65,
        }
    )

    assert with_market == baseline


def test_missing_starter_context_is_neutral():
    baseline = starting_pitcher_breakdown(BASE_PITCHER)
    missing_context = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": None,
            "previous_start_ip": None,
            "previous_start_pitch_count": None,
        }
    )

    assert missing_context["starter_quality_score"] == baseline["starter_quality_score"]
    assert missing_context["starter_context_adjustment"] == 0.0
    assert missing_context["starting_pitching_score"] == baseline["starting_pitching_score"]


def test_short_rest_reduces_context_without_changing_quality_score():
    normal = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": 5,
        }
    )
    short = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": 4,
        }
    )

    assert short["starter_quality_score"] == normal["starter_quality_score"]
    assert short["starter_context_adjustment"] == -3.0
    assert short["starting_pitching_score"] < normal["starting_pitching_score"]
    assert "short_rest" in short["starter_context_reasons"]


def test_previous_workload_combined_with_short_rest_is_bounded():
    heavy = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": 4,
            "previous_start_ip": 7.1,
            "previous_start_pitch_count": 112,
        }
    )

    assert heavy["starter_context_adjustment"] == -5.0
    assert "heavy_previous_pitch_count" in heavy["starter_context_reasons"]
    assert "deep_previous_start" in heavy["starter_context_reasons"]


def test_unknown_rest_does_not_create_workload_strength_penalty():
    heavy_unknown_rest = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": None,
            "previous_start_ip": 7.1,
            "previous_start_pitch_count": 112,
        }
    )

    assert heavy_unknown_rest["starter_context_adjustment"] == 0.0
    assert heavy_unknown_rest["starter_context_reasons"] == []


def test_opener_role_risk_reduces_authority_but_keeps_core_quality():
    normal = starting_pitcher_breakdown(BASE_PITCHER)
    opener = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "average_start_ip": 2.4,
            "role_context": "opener_risk",
        }
    )

    assert opener["starter_quality_score"] == normal["starter_quality_score"]
    assert opener["starter_context_adjustment"] == -4.0
    assert "opener_risk" in opener["starter_context_reasons"]


def test_extra_rest_gets_only_modest_positive_context_and_extended_rest_is_neutral():
    extra_rest = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": 7,
        }
    )
    extended_rest = starting_pitcher_breakdown(
        {
            **BASE_PITCHER,
            "days_rest": 9,
        }
    )

    assert extra_rest["starter_context_adjustment"] == 1.0
    assert extended_rest["starter_context_adjustment"] == 0.0


def test_score_remains_bounded():
    extreme = starting_pitcher_score(
        {
            **BASE_PITCHER,
            "era": 0.50,
            "whip": 0.60,
            "k_bb_pct": 45.0,
            "hr9": 0.10,
        }
    )

    assert 0.0 <= extreme <= 100.0


def test_sharpscore_consumes_rebuilt_starter_score_and_breakdown():
    away_pitcher = {
        **BASE_PITCHER,
        "name": "Away Starter",
        "era": 3.20,
        "whip": 1.05,
        "k_bb_pct": 22.0,
        "hr9": 0.85,
    }
    home_pitcher = {
        **BASE_PITCHER,
        "name": "Home Starter",
        "era": 5.10,
        "whip": 1.50,
        "k_bb_pct": 8.0,
        "hr9": 1.55,
    }

    result = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        away_pitcher,
        home_pitcher,
        None,
        None,
    )

    selected = result["model"]["component_scores"]["selected"]
    opponent = result["model"]["component_scores"]["opponent"]

    assert selected["starting_pitching"] == starting_pitcher_score(away_pitcher)
    assert opponent["starting_pitching"] == starting_pitcher_score(home_pitcher)
    assert "starting_pitcher_breakdown" in selected
    assert result["model"]["play"] == "Away Club"


def test_offense_component_remains_unchanged():
    assert offense_score(BASE_OFFENSE) == 50.0


def test_weights_and_thresholds_are_unchanged():
    assert WEIGHTS == {
        "offense": 0.40,
        "starting_pitching": 0.40,
        "bullpen": 0.15,
        "home_field": 0.05,
    }
    assert sum(WEIGHTS.values()) == 1.0
    assert MLB_MONEYLINE_V2_CANDIDATE_TIERS == (
        ("STRONG PLAY", 8.0),
        ("PLAY", 6.0),
        ("PLAYABLE", 3.0),
        ("LEAN", 1.0),
    )


def test_starter_role_uncertainty_reduces_reliability_only_not_selection():
    away = {
        **BASE_PITCHER,
        "name": "Away Starter",
        "era": 3.10,
        "whip": 1.05,
        "k_bb_pct": 24.0,
        "hr9": 0.75,
        "average_start_ip": 2.5,
        "role_context": "opener_risk",
    }
    home = {
        **BASE_PITCHER,
        "name": "Home Starter",
        "era": 5.60,
        "whip": 1.55,
        "k_bb_pct": 5.0,
        "hr9": 1.75,
    }

    result = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        away,
        home,
        None,
        None,
    )

    model = result["model"]
    assert model["play"] == "Away Club"
    assert "starter_role_uncertainty" in model["reliability_breakdown"]["concerns"]
    assert model["reliability_breakdown"]["tier_cap"] == "PLAYABLE"


def test_missing_starter_rest_context_reduces_reliability_not_strength():
    away = {
        **BASE_PITCHER,
        "name": "Away Starter",
        "previous_start_date": None,
        "data_source": "starter_game_log",
    }
    home = {
        **BASE_PITCHER,
        "name": "Home Starter",
        "previous_start_date": "2026-08-01",
        "data_source": "starter_game_log",
    }

    result = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        away,
        home,
        None,
        None,
    )

    assert starting_pitcher_breakdown(away)["starter_context_adjustment"] == 0.0
    assert "missing_starter_rest_context" in result["model"]["reliability_breakdown"]["concerns"]


def test_winner_first_behavior_remains_deterministic():
    away = {
        **BASE_PITCHER,
        "name": "Away Starter",
        "era": 3.10,
        "whip": 1.05,
        "k_bb_pct": 24.0,
        "hr9": 0.75,
    }
    home = {
        **BASE_PITCHER,
        "name": "Home Starter",
        "era": 5.60,
        "whip": 1.55,
        "k_bb_pct": 5.0,
        "hr9": 1.75,
    }

    first = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        away,
        home,
        None,
        None,
    )
    second = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1, "whip": 1.3}},
        dict(away),
        dict(home),
        None,
        None,
    )

    assert first["model"]["play"] == second["model"]["play"] == "Away Club"
