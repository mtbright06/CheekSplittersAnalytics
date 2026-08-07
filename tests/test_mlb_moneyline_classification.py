from types import SimpleNamespace
from unittest.mock import patch

from engine.model.recommendations import (
    market_value_classification,
    mlb_moneyline_conviction_recommendation,
    mlb_moneyline_v2_candidate_recommendation,
    mlb_moneyline_v2_recommendation,
    recommendation,
)
from engine.model.sharpscore import (
    build_sharpscore_decision,
    mlb_moneyline_v2_reliability,
)


COMPLETE_AWAY_PROFILE = {
    "offense": {"ops": .750},
    "bullpen": {"season_era": 3.8},
}
COMPLETE_HOME_PROFILE = {
    "offense": {"ops": .700},
    "bullpen": {"season_era": 4.2},
}
COMPLETE_AWAY_PITCHER = {
    "name": "Away Starter",
    "era": 3.0,
    "whip": 1.1,
}
COMPLETE_HOME_PITCHER = {
    "name": "Home Starter",
    "era": 4.0,
    "whip": 1.3,
}


def test_mlb_moneyline_conviction_tiers():
    assert mlb_moneyline_conviction_recommendation(63.0, 85.0) == "🔥 CHEEK RIPPER"
    assert mlb_moneyline_conviction_recommendation(59.0, 78.0) == "✅ STRONG PLAY"
    assert mlb_moneyline_conviction_recommendation(56.5, 74.0) == "🟡 PLAYABLE"
    assert mlb_moneyline_conviction_recommendation(52.0, 65.0) == "LEAN"
    assert mlb_moneyline_conviction_recommendation(51.9, 95.0) == "PASS"


def test_mlb_moneyline_v2_uses_sharpscore_gap_as_authority():
    assert mlb_moneyline_v2_recommendation(17.4)["recommendation"] == "STRONG PLAY"
    assert mlb_moneyline_v2_recommendation(12.0)["recommendation"] == "PLAY"
    assert mlb_moneyline_v2_recommendation(8.7)["recommendation"] == "PLAYABLE"
    assert mlb_moneyline_v2_recommendation(2.6)["recommendation"] == "LEAN"
    assert mlb_moneyline_v2_recommendation(2.5)["recommendation"] == "PASS"


def test_mlb_moneyline_v2_reliability_caps_but_does_not_promote():
    result = mlb_moneyline_v2_recommendation(
        17.4,
        {
            "tier_cap": "PLAYABLE",
            "concerns": ["unknown_starter"],
        },
    )

    assert result["base_recommendation"] == "STRONG PLAY"
    assert result["recommendation"] == "PLAYABLE"
    assert result["changed_by_reliability"] is True


def test_mlb_moneyline_v2_candidate_gap_bands_are_exact():
    assert mlb_moneyline_v2_candidate_recommendation(0.9)["recommendation"] == "PASS"
    assert mlb_moneyline_v2_candidate_recommendation(1.0)["recommendation"] == "LEAN"
    assert mlb_moneyline_v2_candidate_recommendation(2.9)["recommendation"] == "LEAN"
    assert mlb_moneyline_v2_candidate_recommendation(3.0)["recommendation"] == "PLAYABLE"
    assert mlb_moneyline_v2_candidate_recommendation(5.9)["recommendation"] == "PLAYABLE"
    assert mlb_moneyline_v2_candidate_recommendation(6.0)["recommendation"] == "PLAY"
    assert mlb_moneyline_v2_candidate_recommendation(7.9)["recommendation"] == "PLAY"
    assert mlb_moneyline_v2_candidate_recommendation(8.0)["recommendation"] == "STRONG PLAY"


def test_mlb_moneyline_v2_candidate_reliability_caps_only_downward():
    capped = mlb_moneyline_v2_candidate_recommendation(
        8.0,
        {"tier_cap": "PLAYABLE", "concerns": ["unknown_starter"]},
    )
    weak = mlb_moneyline_v2_candidate_recommendation(
        0.9,
        {"tier_cap": "STRONG PLAY", "concerns": []},
    )

    assert capped["base_recommendation"] == "STRONG PLAY"
    assert capped["recommendation"] == "PLAYABLE"
    assert capped["changed_by_reliability"] is True
    assert weak["recommendation"] == "PASS"


def test_mlb_conviction_falls_to_the_next_qualified_tier():
    assert mlb_moneyline_conviction_recommendation(63.0, 80.0) == "✅ STRONG PLAY"
    assert mlb_moneyline_conviction_recommendation(63.0, 73.0) == "LEAN"
    assert mlb_moneyline_conviction_recommendation(63.0, 64.9) == "PASS"


def test_mlb_conviction_does_not_accept_or_depend_on_market_edge():
    # The conviction function intentionally has no edge input: negative and
    # missing SSRP values cannot lower an otherwise qualifying tier.
    assert mlb_moneyline_conviction_recommendation(59.0, 78.0) == "✅ STRONG PLAY"
    assert mlb_moneyline_conviction_recommendation(59.0, 78.0) == "✅ STRONG PLAY"


def test_non_mlb_legacy_recommendation_behavior_is_unchanged():
    assert recommendation(10.0, 70.0) == "🔥 CHEEK RIPPER"
    assert recommendation(6.99, 99.0) == "🟡 PLAYABLE"
    assert recommendation(None, 99.0) == "PASS"


def test_market_value_boundaries():
    expected = {
        7.0: ("ELITE VALUE", "elite_value"),
        4.0: ("STRONG VALUE", "strong_value"),
        1.0: ("POSITIVE VALUE", "positive_value"),
        0.0: ("FAIR PRICE", "fair_price"),
        -0.99: ("FAIR PRICE", "fair_price"),
        -1.0: ("MARKET PREMIUM", "market_premium"),
        -5.0: ("HEAVY PREMIUM", "heavy_premium"),
        None: ("VALUE UNAVAILABLE", "unavailable"),
        float("nan"): ("VALUE UNAVAILABLE", "unavailable"),
    }

    for edge, value in expected.items():
        assert market_value_classification(edge) == value


def test_sharpscore_serializes_conviction_and_market_value_separately():
    components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}
    quote = SimpleNamespace(
        selection="Away Club",
        market="Moneyline",
        sportsbook="FanDuel",
        american_odds=-186,
        implied_probability=0.65,
    )

    with (
        patch(
            "engine.model.sharpscore.calculate_team_score",
            side_effect=[(62.0, components), (50.0, components)],
        ),
        patch(
            "engine.model.sharpscore.calculate_confidence",
            return_value=(85.0, {}),
        ),
    ):
        result = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            COMPLETE_AWAY_PROFILE,
            COMPLETE_HOME_PROFILE,
            COMPLETE_AWAY_PITCHER,
            COMPLETE_HOME_PITCHER,
            quote,
            None,
        )

    model = result["model"]
    assert model["model_win_strength"] == 59.0
    assert model["model_probability"] == 59.0
    assert model["model_win_strength"] == model["model_probability"]
    assert model["model_strength"] == 12.0
    assert model["model_confidence"] == 100.0
    assert model["model_reliability"] == 100.0
    assert model["confidence"] == model["model_confidence"]
    assert model["legacy_model_confidence"] == 85.0
    assert model["legacy_confidence"] == 85.0
    assert model["recommendation"] == "STRONG PLAY"
    assert model["model_recommendation"] == "STRONG PLAY"
    assert model["v1_shadow_recommendation"] == "✅ STRONG PLAY"
    assert model["market_value_label"] == "HEAVY PREMIUM"
    assert result["market_edge"]["edge"] == -6.0
    assert result["market_edge"]["market_value_tone"] == "heavy_premium"


def test_sharpscore_keeps_strong_conviction_when_edge_is_missing():
    components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}

    with (
        patch(
            "engine.model.sharpscore.calculate_team_score",
            side_effect=[(62.0, components), (50.0, components)],
        ),
        patch(
            "engine.model.sharpscore.calculate_confidence",
            return_value=(85.0, {}),
        ),
    ):
        result = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            COMPLETE_AWAY_PROFILE,
            COMPLETE_HOME_PROFILE,
            COMPLETE_AWAY_PITCHER,
            COMPLETE_HOME_PITCHER,
            None,
            None,
        )

    assert result["model"]["recommendation"] == "STRONG PLAY"
    assert result["model"]["v1_shadow_recommendation"] == "✅ STRONG PLAY"
    assert result["model"]["market_value_label"] == "VALUE UNAVAILABLE"


def test_mlb_reliability_is_current_input_quality_not_sharpscore_gap():
    full_reliability = mlb_moneyline_v2_reliability(
        away_offense=COMPLETE_AWAY_PROFILE["offense"],
        home_offense=COMPLETE_HOME_PROFILE["offense"],
        away_pitcher=COMPLETE_AWAY_PITCHER,
        home_pitcher=COMPLETE_HOME_PITCHER,
        away_bullpen=COMPLETE_AWAY_PROFILE["bullpen"],
        home_bullpen=COMPLETE_HOME_PROFILE["bullpen"],
    )
    missing_bullpen = mlb_moneyline_v2_reliability(
        away_offense=COMPLETE_AWAY_PROFILE["offense"],
        home_offense=COMPLETE_HOME_PROFILE["offense"],
        away_pitcher=COMPLETE_AWAY_PITCHER,
        home_pitcher=COMPLETE_HOME_PITCHER,
        away_bullpen={},
        home_bullpen={},
    )
    missing_starter = mlb_moneyline_v2_reliability(
        away_offense=COMPLETE_AWAY_PROFILE["offense"],
        home_offense=COMPLETE_HOME_PROFILE["offense"],
        away_pitcher={"name": "Unknown Starter"},
        home_pitcher=COMPLETE_HOME_PITCHER,
        away_bullpen=COMPLETE_AWAY_PROFILE["bullpen"],
        home_bullpen=COMPLETE_HOME_PROFILE["bullpen"],
    )

    assert full_reliability["score"] == 100.0
    assert full_reliability["tier_cap"] == "STRONG PLAY"
    assert missing_bullpen["score"] == 90.0
    assert missing_bullpen["tier_cap"] == "PLAYABLE"
    assert missing_starter["score"] == 55.0
    assert missing_starter["tier_cap"] == "LEAN"


def test_mlb_reliability_aliases_do_not_change_with_sharpscore_gap():
    components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[(54.0, components), (50.0, components)],
    ):
        modest = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            COMPLETE_AWAY_PROFILE,
            COMPLETE_HOME_PROFILE,
            COMPLETE_AWAY_PITCHER,
            COMPLETE_HOME_PITCHER,
            None,
            None,
        )

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[(62.0, components), (50.0, components)],
    ):
        strong = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            COMPLETE_AWAY_PROFILE,
            COMPLETE_HOME_PROFILE,
            COMPLETE_AWAY_PITCHER,
            COMPLETE_HOME_PITCHER,
            None,
            None,
        )

    assert modest["model"]["model_strength"] == 4.0
    assert strong["model"]["model_strength"] == 12.0
    assert modest["model"]["model_confidence"] == strong["model"]["model_confidence"]
    assert modest["model"]["confidence"] == strong["model"]["confidence"]
    assert modest["model"]["model_reliability"] == strong["model"]["model_reliability"]


def test_sharpscore_promotes_v2_candidate_and_preserves_v1_shadow():
    components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}

    with (
        patch(
            "engine.model.sharpscore.calculate_team_score",
            side_effect=[(58.7, components), (50.0, components)],
        ),
        patch(
            "engine.model.sharpscore.calculate_confidence",
            return_value=(73.9, {}),
        ),
    ):
        result = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": {"ops": .750}, "bullpen": {"season_era": 3.8}},
            {"offense": {"ops": .700}, "bullpen": {"season_era": 4.2}},
            {"name": "Away Starter", "era": 3.0, "whip": 1.1},
            {"name": "Home Starter", "era": 4.0, "whip": 1.3},
            None,
            None,
        )

    model = result["model"]
    assert model["recommendation"] == "STRONG PLAY"
    assert model["model_recommendation"] == "STRONG PLAY"
    assert model["v1_shadow_recommendation"] == "LEAN"
    assert model["v2_recommendation"] == "PLAYABLE"
    assert model["v2_authority"]["authoritative_signal"] == "sharpscore_gap"
    assert model["v2_authority"]["sharpscore_gap"] == 8.7
    assert model["v2_candidate_recommendation"] == "STRONG PLAY"
    assert model["v2_candidate_authority"]["sharpscore_gap"] == 8.7


def test_mlb_moneyline_v2_candidate_ignores_odds_edge_and_market_probability():
    components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}
    bad_price = SimpleNamespace(
        selection="Away Club",
        market="Moneyline",
        sportsbook="FanDuel",
        american_odds=-240,
        implied_probability=0.70,
    )
    good_price = SimpleNamespace(
        selection="Away Club",
        market="Moneyline",
        sportsbook="FanDuel",
        american_odds=180,
        implied_probability=0.35,
    )

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[(58.7, components), (50.0, components)],
    ):
        expensive = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": {"ops": .750}, "bullpen": {"season_era": 3.8}},
            {"offense": {"ops": .700}, "bullpen": {"season_era": 4.2}},
            {"name": "Away Starter", "era": 3.0, "whip": 1.1},
            {"name": "Home Starter", "era": 4.0, "whip": 1.3},
            bad_price,
            None,
        )

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[(58.7, components), (50.0, components)],
    ):
        cheap = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": {"ops": .750}, "bullpen": {"season_era": 3.8}},
            {"offense": {"ops": .700}, "bullpen": {"season_era": 4.2}},
            {"name": "Away Starter", "era": 3.0, "whip": 1.1},
            {"name": "Home Starter", "era": 4.0, "whip": 1.3},
            good_price,
            None,
        )

    assert expensive["model"]["v2_recommendation"] == cheap["model"]["v2_recommendation"]
    assert expensive["model"]["v2_authority"] == cheap["model"]["v2_authority"]
    assert (
        expensive["model"]["v2_candidate_recommendation"]
        == cheap["model"]["v2_candidate_recommendation"]
    )
    assert (
        expensive["model"]["v2_candidate_authority"]
        == cheap["model"]["v2_candidate_authority"]
    )


def test_mlb_moneyline_v2_candidate_ignores_strength_confidence_hammer_edge_ev():
    baseline = mlb_moneyline_v2_candidate_recommendation(
        6.0,
        {"tier_cap": "STRONG PLAY"},
    )
    changed_context = mlb_moneyline_v2_candidate_recommendation(
        6.0,
        {
            "tier_cap": "STRONG PLAY",
            "model_win_strength": 50.0,
            "model_confidence": 35.0,
            "hammer_score": 0.0,
            "edge": -20.0,
            "ev": -25.0,
            "odds": 300,
        },
    )

    assert baseline["recommendation"] == "PLAY"
    assert changed_context["recommendation"] == "PLAY"


def test_mlb_moneyline_v2_candidate_preserves_winner_first_side_selection():
    away_components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}
    home_components = {"offense": 50, "starting_pitching": 50, "bullpen": 50, "home_field": 56}

    with (
        patch(
            "engine.model.sharpscore.calculate_team_score",
            side_effect=[(58.0, away_components), (50.0, home_components)],
        ),
        patch(
            "engine.model.sharpscore.calculate_confidence",
            return_value=(95.0, {}),
        ),
    ):
        result = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": {"ops": .750}, "bullpen": {"season_era": 3.8}},
            {"offense": {"ops": .700}, "bullpen": {"season_era": 4.2}},
            {"name": "Away Starter", "era": 3.0, "whip": 1.1},
            {"name": "Home Starter", "era": 4.0, "whip": 1.3},
            None,
            None,
        )

    assert result["model"]["play"] == "Away Club"
    assert result["model"]["v2_candidate_recommendation"] == "STRONG PLAY"


def test_model_win_strength_and_confidence_ignore_odds_changes():
    components = {"offense": 60, "starting_pitching": 60, "bullpen": 60, "home_field": 50}
    away_quote = SimpleNamespace(
        selection="Away Club",
        market="Moneyline",
        sportsbook="FanDuel",
        american_odds=-110,
        implied_probability=0.52,
    )
    alternate_quote = SimpleNamespace(
        selection="Away Club",
        market="Moneyline",
        sportsbook="FanDuel",
        american_odds=240,
        implied_probability=0.29,
    )

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[(62.0, components), (50.0, components)],
    ):
        baseline = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": {"ops": .750}},
            {"offense": {"ops": .700}},
            {"name": "Away Starter", "era": 3.0, "whip": 1.1},
            {"name": "Home Starter", "era": 4.0, "whip": 1.3},
            away_quote,
            None,
        )

    with patch(
        "engine.model.sharpscore.calculate_team_score",
        side_effect=[(62.0, components), (50.0, components)],
    ):
        changed_odds = build_sharpscore_decision(
            "Away Club",
            "Home Club",
            {"offense": {"ops": .750}},
            {"offense": {"ops": .700}},
            {"name": "Away Starter", "era": 3.0, "whip": 1.1},
            {"name": "Home Starter", "era": 4.0, "whip": 1.3},
            alternate_quote,
            None,
        )

    assert baseline["model"]["model_win_strength"] == changed_odds["model"]["model_win_strength"]
    assert baseline["model"]["model_probability"] == changed_odds["model"]["model_probability"]
    assert baseline["model"]["model_confidence"] == changed_odds["model"]["model_confidence"]
    assert baseline["model"]["confidence"] == changed_odds["model"]["confidence"]
