from engine.bomb_lab.pitcher_attack import (
    bomb_authority_score,
    bomb_reliability,
    pitcher_risk,
    tier,
)


def test_sample_confidence_does_not_create_bomb_score_strength():
    low_reliability = bomb_reliability(0, 0)
    high_reliability = bomb_reliability(60, 180)

    assert low_reliability["score"] != high_reliability["score"]
    assert bomb_authority_score(60.0, 70.0) == bomb_authority_score(60.0, 70.0)


def test_bomb_authority_uses_pitcher_vulnerability_and_park_only():
    assert bomb_authority_score(60.0, 70.0) == 62.0
    assert bomb_authority_score(60.0, 50.0) == 58.0
    assert tier(bomb_authority_score(60.0, 70.0)) == "💣 STRONG"


def test_missing_statcast_samples_reduce_reliability_without_strength():
    reliability = bomb_reliability(0, 0)

    assert reliability["score"] == 35.0
    assert "recent_statcast_sample_missing" in reliability["concerns"]
    assert "season_statcast_sample_missing" in reliability["concerns"]
    assert bomb_authority_score(50.0, 50.0) == 50.0


def test_thin_recent_sample_is_a_reliability_concern_only():
    reliability = bomb_reliability(12, 180)

    assert reliability["score"] == 70.0
    assert reliability["concerns"] == ["recent_statcast_sample_thin"]
    assert "HR probability" in reliability["definition"]


def test_pitcher_vulnerability_scale_rewards_native_barrels():
    ordinary_contact = pitcher_risk(
        hh=0.25,
        barrel=0.04,
        ev=84.0,
        hr_rate=0.03,
        air=0.50,
    )
    dangerous_contact = pitcher_risk(
        hh=0.35,
        barrel=0.12,
        ev=91.0,
        hr_rate=0.06,
        air=0.62,
    )

    assert ordinary_contact == 40.7
    assert dangerous_contact == 93.8


def test_bomb_lab_tier_boundaries_are_reachable():
    assert tier(52.4) == "PASS"
    assert tier(52.5) == "👀 WATCH"
    assert tier(57.4) == "👀 WATCH"
    assert tier(57.5) == "💣 STRONG"
    assert tier(64.9) == "💣 STRONG"
    assert tier(65.0) == "🔥 ELITE"


def test_bomb_lab_reliability_caps_tiers_without_creating_strength():
    assert tier(70.0, reliability=45.0) == "PASS"
    assert tier(70.0, reliability=60.0) == "👀 WATCH"
    assert tier(70.0, reliability=70.0) == "🔥 ELITE"
    assert tier(49.9, reliability=95.0) == "PASS"
