from unittest.mock import patch

from engine.model.component_scores import offense_breakdown, offense_score
from engine.model.recommendations import MLB_MONEYLINE_V2_CANDIDATE_TIERS
from engine.model.sharpscore import build_sharpscore_decision


BASE_OFFENSE = {
    "runs_per_game": 4.4,
    "ops": 0.710,
    "iso": 0.160,
    "hr_per_game": 1.10,
    "bb_rate": 8.0,
    "k_rate": 22.0,
}


def test_offense_score_is_deterministic_and_bounded():
    first = offense_score(BASE_OFFENSE)
    second = offense_score(dict(BASE_OFFENSE))

    assert first == second
    assert 0.0 <= first <= 100.0


def test_retained_inputs_move_score_in_expected_direction():
    strong = offense_score(
        {
            **BASE_OFFENSE,
            "runs_per_game": 5.2,
            "ops": 0.790,
            "iso": 0.210,
            "bb_rate": 10.0,
            "k_rate": 19.0,
        }
    )
    weak = offense_score(
        {
            **BASE_OFFENSE,
            "runs_per_game": 3.6,
            "ops": 0.640,
            "iso": 0.120,
            "bb_rate": 6.5,
            "k_rate": 25.0,
        }
    )

    assert strong > 50.0
    assert weak < 50.0
    assert strong > weak


def test_missing_offense_inputs_fall_back_neutrally_without_dilution():
    assert offense_score({}) == 50.0

    rpg_only = offense_breakdown({"runs_per_game": 5.1})
    rpg_and_missing_noise = offense_breakdown(
        {
            "runs_per_game": 5.1,
            "ops": None,
            "iso": None,
            "bb_rate": None,
            "k_rate": None,
        }
    )

    assert rpg_only["offense_score"] == rpg_and_missing_noise["offense_score"]
    assert rpg_only["active_subcomponents"] == ["run_creation"]


def test_power_does_not_count_iso_and_hr_per_game_as_duplicate_authority():
    with_iso = offense_breakdown(
        {
            **BASE_OFFENSE,
            "iso": 0.210,
            "hr_per_game": 0.65,
        }
    )
    without_iso = offense_breakdown(
        {
            **BASE_OFFENSE,
            "iso": None,
            "hr_per_game": 0.65,
        }
    )

    assert with_iso["power_source"] == "iso"
    assert without_iso["power_source"] == "hr_per_game"
    assert with_iso["power"] > without_iso["power"]


def test_market_fields_cannot_affect_offense_score():
    baseline = offense_score(BASE_OFFENSE)
    with_market = offense_score(
        {
            **BASE_OFFENSE,
            "edge": 25.0,
            "ev": 18.0,
            "odds": 180,
            "model_probability": 0.65,
        }
    )

    assert with_market == baseline


def test_sharpscore_consumes_rebuilt_offense_score_and_breakdown():
    away_offense = {
        **BASE_OFFENSE,
        "runs_per_game": 5.2,
        "ops": 0.790,
    }
    home_offense = {
        **BASE_OFFENSE,
        "runs_per_game": 3.8,
        "ops": 0.660,
    }

    result = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": away_offense, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"offense": home_offense, "bullpen": {"era": 4.1, "whip": 1.3}},
        {"name": "Away Starter", "ip": 80, "era": 4.5, "whip": 1.35},
        {"name": "Home Starter", "ip": 80, "era": 4.5, "whip": 1.35},
        None,
        None,
    )

    selected = result["model"]["component_scores"]["selected"]
    opponent = result["model"]["component_scores"]["opponent"]

    assert selected["offense"] == offense_score(away_offense)
    assert opponent["offense"] == offense_score(home_offense)
    assert "offense_breakdown" in selected
    assert result["model"]["play"] == "Away Club"


def test_recommendation_bands_are_unchanged():
    assert MLB_MONEYLINE_V2_CANDIDATE_TIERS == (
        ("STRONG PLAY", 8.0),
        ("PLAY", 6.0),
        ("PLAYABLE", 3.0),
        ("LEAN", 1.0),
    )


def test_winner_first_logic_unchanged_with_rebuilt_offense():
    neutral_components = {
        "offense": 50.0,
        "starting_pitching": 50.0,
        "bullpen": 50.0,
        "home_field": 50.0,
        "offense_breakdown": offense_breakdown(BASE_OFFENSE),
    }

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[
            (54.0, neutral_components),
            (50.0, neutral_components),
        ],
    ):
        result = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1}},
            {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1}},
            {"name": "Away Starter", "era": 4.5, "whip": 1.35},
            {"name": "Home Starter", "era": 4.5, "whip": 1.35},
            None,
            None,
        )

    assert result["model"]["play"] == "Away Club"


def test_reliability_semantics_are_unchanged():
    full_inputs = build_sharpscore_decision(
        "Away Club",
        "Home Club",
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1}},
        {"offense": BASE_OFFENSE, "bullpen": {"era": 4.1}},
        {"name": "Away Starter", "era": 4.5, "whip": 1.35},
        {"name": "Home Starter", "era": 4.5, "whip": 1.35},
        None,
        None,
    )

    assert full_inputs["model"]["model_reliability"] == 100.0
