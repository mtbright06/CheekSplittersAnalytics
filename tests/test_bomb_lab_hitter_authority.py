from unittest.mock import patch

from engine.hitters.target_hitters import (
    attach_target_hitters_to_pitchers,
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


def test_bomb_squad_display_order_uses_descending_target_score():
    hitters = [
        {
            "batter_id": 1,
            "name": "Higher Opportunity",
            "position": "OF",
            "bat_side": "L",
            "pa": 200,
            "bbe": 150,
            "hard_hit_pct": 0.09,
            "barrel_pct": 0.04,
            "avg_ev": 84.0,
            "hr": 10,
            "hr_vs_lhp": 0,
            "hr_vs_rhp": 1,
        },
        {
            "batter_id": 2,
            "name": "Higher Target",
            "position": "OF",
            "bat_side": "R",
            "pa": 200,
            "bbe": 150,
            "hard_hit_pct": 0.09,
            "barrel_pct": 0.04,
            "avg_ev": 84.0,
            "hr": 10,
            "hr_vs_lhp": 0,
            "hr_vs_rhp": 20,
        },
    ]

    with (
        patch(
            "engine.hitters.target_hitters.fetch_active_roster",
            lambda team_id: [{"player_id": 1}, {"player_id": 2}],
        ),
        patch(
            "engine.hitters.target_hitters.build_hitter_profiles",
            lambda **kwargs: hitters,
        ),
    ):
        [item] = attach_target_hitters_to_pitchers(
            [
                {
                    "opponent": "Test Team",
                    "opponent_team_id": 1,
                    "opponent_abbr": "TST",
                    "target_side": "R",
                    "pitcher_throw": "R",
                    "bomb_score": 50.0,
                    "pitcher_vulnerability": 80.0,
                    "environment_score": 50.0,
                    "bomb_reliability": 95.0,
                }
            ],
            season_statcast_df=object(),
        )

    target_scores = [hitter["target_score"] for hitter in item["top_hitters"]]

    assert target_scores == sorted(target_scores, reverse=True)
    assert item["recommended_hitter"] == item["top_hitters"][0]["name"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
