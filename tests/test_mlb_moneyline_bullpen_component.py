from engine.model.component_scores import (
    bullpen_breakdown,
    bullpen_score,
    offense_score,
    starting_pitcher_score,
)
from engine.model.recommendations import MLB_MONEYLINE_V2_CANDIDATE_TIERS
from engine.model.sharpscore import WEIGHTS, build_sharpscore_decision


BASE_OFFENSE = {
    "runs_per_game": 4.4,
    "ops": 0.710,
    "iso": 0.160,
    "bb_rate": 8.0,
    "k_rate": 22.0,
}

BASE_PITCHER = {
    "name": "Sample Starter",
    "ip": 120.0,
    "era": 4.50,
    "whip": 1.35,
    "k_bb_pct": 14.0,
    "hr9": 1.20,
}

BASE_BULLPEN = {
    "season_era": 4.10,
    "season_whip": 1.30,
    "last7_era": 4.10,
    "innings_last7": 12.0,
    "innings_last3": 4.0,
    "closer_available": True,
    "setup_available": True,
}


def test_stronger_bullpen_inputs_increase_score():
    strong = bullpen_score(
        {
            **BASE_BULLPEN,
            "season_era": 3.10,
            "season_whip": 1.08,
            "last7_era": 2.80,
        }
    )
    weak = bullpen_score(
        {
            **BASE_BULLPEN,
            "season_era": 5.20,
            "season_whip": 1.52,
            "last7_era": 5.70,
        }
    )

    assert strong > 50.0
    assert weak < 50.0
    assert strong > weak


def test_missing_data_is_neutral_and_active_inputs_renormalize():
    assert bullpen_score({}) == 50.0

    era_only = bullpen_breakdown({"season_era": 3.40})

    assert era_only["active_subcomponents"] == ["season_run_prevention"]
    assert era_only["bullpen_score"] == era_only["season_run_prevention"]
    assert "season_whip" in era_only["missing_inputs"]


def test_fatigue_and_availability_are_counted_once():
    rested = bullpen_score(BASE_BULLPEN)
    tired = bullpen_score(
        {
            **BASE_BULLPEN,
            "innings_last3": 12.0,
        }
    )
    unavailable = bullpen_score(
        {
            **BASE_BULLPEN,
            "closer_available": False,
            "setup_available": False,
        }
    )

    assert tired == rested - 4.5
    assert unavailable == rested - 6.5


def test_last7_era_is_sample_stabilized():
    tiny_sample = bullpen_breakdown(
        {
            **BASE_BULLPEN,
            "season_era": 3.20,
            "last7_era": 7.20,
            "innings_last7": 2.0,
        }
    )
    larger_sample = bullpen_breakdown(
        {
            **BASE_BULLPEN,
            "season_era": 3.20,
            "last7_era": 7.20,
            "innings_last7": 24.0,
        }
    )

    assert tiny_sample["last7_sample_weight"] < larger_sample["last7_sample_weight"]
    assert tiny_sample["stabilized_last7_era"] < larger_sample["stabilized_last7_era"]
    assert tiny_sample["bullpen_score"] > larger_sample["bullpen_score"]


def test_missing_last7_sample_removes_recent_authority():
    no_sample = bullpen_breakdown(
        {
            **BASE_BULLPEN,
            "last7_era": 0.00,
            "innings_last7": None,
        }
    )
    missing_recent = bullpen_breakdown(
        {
            **BASE_BULLPEN,
            "last7_era": None,
            "innings_last7": None,
        }
    )

    assert no_sample["bullpen_score"] == missing_recent["bullpen_score"]
    assert "innings_last7" in no_sample["missing_inputs"]


def test_score_remains_bounded():
    extreme = bullpen_score(
        {
            **BASE_BULLPEN,
            "season_era": 0.50,
            "season_whip": 0.70,
            "last7_era": 0.00,
        }
    )

    assert 0.0 <= extreme <= 100.0


def test_market_fields_cannot_affect_bullpen_score():
    baseline = bullpen_score(BASE_BULLPEN)
    with_market = bullpen_score(
        {
            **BASE_BULLPEN,
            "edge": 25.0,
            "ev": 18.0,
            "odds": 180,
            "model_probability": 0.65,
        }
    )

    assert with_market == baseline


def test_sharpscore_consumes_rebuilt_bullpen_score_and_breakdown():
    away_bullpen = {
        **BASE_BULLPEN,
        "season_era": 3.20,
        "season_whip": 1.10,
        "last7_era": 2.90,
    }
    home_bullpen = {
        **BASE_BULLPEN,
        "season_era": 5.00,
        "season_whip": 1.48,
        "last7_era": 5.40,
    }

    result = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": away_bullpen},
        {"offense": BASE_OFFENSE, "bullpen": home_bullpen},
        BASE_PITCHER,
        BASE_PITCHER,
        None,
        None,
    )

    selected = result["model"]["component_scores"]["selected"]
    opponent = result["model"]["component_scores"]["opponent"]

    assert selected["bullpen"] == bullpen_score(away_bullpen)
    assert opponent["bullpen"] == bullpen_score(home_bullpen)
    assert "bullpen_breakdown" in selected
    assert result["model"]["play"] == "Away Club"


def test_offense_and_starter_components_remain_unchanged():
    assert offense_score(BASE_OFFENSE) == 50.0
    assert starting_pitcher_score(BASE_PITCHER) == 50.0


def test_weights_and_thresholds_are_unchanged():
    assert WEIGHTS == {
        "offense": 0.42,
        "starting_pitching": 0.38,
        "bullpen": 0.15,
        "home_field": 0.05,
    }
    assert MLB_MONEYLINE_V2_CANDIDATE_TIERS == (
        ("STRONG PLAY", 8.0),
        ("PLAY", 6.0),
        ("PLAYABLE", 3.0),
        ("LEAN", 1.0),
    )


def test_winner_first_behavior_remains_deterministic():
    away_bullpen = {
        **BASE_BULLPEN,
        "season_era": 3.20,
        "season_whip": 1.10,
    }
    home_bullpen = {
        **BASE_BULLPEN,
        "season_era": 5.20,
        "season_whip": 1.55,
    }

    first = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": away_bullpen},
        {"offense": BASE_OFFENSE, "bullpen": home_bullpen},
        BASE_PITCHER,
        BASE_PITCHER,
        None,
        None,
    )
    second = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": dict(away_bullpen)},
        {"offense": BASE_OFFENSE, "bullpen": dict(home_bullpen)},
        BASE_PITCHER,
        BASE_PITCHER,
        None,
        None,
    )

    assert first["model"]["play"] == second["model"]["play"] == "Away Club"
