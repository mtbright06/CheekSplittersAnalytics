from engine.hitters.target_hitters import (
    hitter_hr_ability_score,
    hitter_sample_reliability,
    hr_opportunity_score,
    side_matches,
)


POWER_HITTER = {
    "barrel_pct": 0.12,
    "hard_hit_pct": 0.50,
    "avg_ev": 94.0,
    "hr_vs_lhp": 4,
    "hr_vs_rhp": 12,
    "bbe": 200,
    "pa": 250,
}


WEAK_HITTER = {
    "barrel_pct": 0.02,
    "hard_hit_pct": 0.04,
    "avg_ev": 84.0,
    "hr_vs_lhp": 1,
    "hr_vs_rhp": 1,
    "bbe": 180,
    "pa": 220,
}


def test_hitter_hr_ability_uses_handedness_split():
    assert hitter_hr_ability_score(POWER_HITTER, "R") > hitter_hr_ability_score(
        POWER_HITTER,
        "L",
    )


def test_missing_pitcher_hand_does_not_fabricate_split_power():
    assert hitter_hr_ability_score(POWER_HITTER, None) < hitter_hr_ability_score(
        POWER_HITTER,
        "R",
    )
    reliability = hitter_sample_reliability(POWER_HITTER, None)
    assert "pitcher_hand_missing" in reliability["concerns"]


def test_switch_and_any_side_matching_remains_safe():
    assert side_matches("L", "BOTH") is True
    assert side_matches("R", "ANY") is True
    assert side_matches("L", "R") is False


def test_missing_hitter_sample_reduces_reliability_only():
    reliability = hitter_sample_reliability(
        {
            **POWER_HITTER,
            "bbe": 0,
            "pa": 0,
        },
        "R",
    )

    assert reliability["score"] == 45.0
    assert "hitter_batted_ball_sample_missing" in reliability["concerns"]
    assert "hitter_pa_sample_missing" in reliability["concerns"]


def test_pitcher_hitter_and_park_remain_separate_authority_inputs():
    vulnerable_pitcher_weak_hitter = hr_opportunity_score(
        pitcher_vulnerability=80.0,
        hitter_hr_ability=hitter_hr_ability_score(WEAK_HITTER, "R"),
        environment_score=50.0,
    )
    moderate_pitcher_elite_hitter = hr_opportunity_score(
        pitcher_vulnerability=45.0,
        hitter_hr_ability=hitter_hr_ability_score(POWER_HITTER, "R"),
        environment_score=50.0,
    )

    assert moderate_pitcher_elite_hitter > vulnerable_pitcher_weak_hitter


def test_hitter_hr_ability_centered_scale_has_neutral_meaning():
    average_hitter = {
        "barrel_pct": 0.04,
        "hard_hit_pct": 0.09,
        "avg_ev": 84.0,
        "hr_vs_rhp": 8,
        "hr_vs_lhp": 8,
    }

    assert hitter_hr_ability_score(average_hitter, "R") == 50.0
    assert hitter_hr_ability_score(POWER_HITTER, "R") == 95.0


def test_hr_opportunity_uses_corrected_top_level_weights():
    assert hr_opportunity_score(
        pitcher_vulnerability=80.0,
        hitter_hr_ability=60.0,
        environment_score=40.0,
    ) == 65.0


def test_park_context_cannot_change_hitter_ability():
    ability = hitter_hr_ability_score(POWER_HITTER, "R")

    assert hr_opportunity_score(
        pitcher_vulnerability=50.0,
        hitter_hr_ability=ability,
        environment_score=80.0,
    ) > hr_opportunity_score(
        pitcher_vulnerability=50.0,
        hitter_hr_ability=ability,
        environment_score=40.0,
    )
    assert hitter_hr_ability_score(POWER_HITTER, "R") == ability
