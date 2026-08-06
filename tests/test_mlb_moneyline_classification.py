from types import SimpleNamespace
from unittest.mock import patch

from engine.model.recommendations import (
    market_value_classification,
    mlb_moneyline_conviction_recommendation,
    recommendation,
)
from engine.model.sharpscore import build_sharpscore_decision


def test_mlb_moneyline_conviction_tiers():
    assert mlb_moneyline_conviction_recommendation(63.0, 85.0) == "🔥 CHEEK RIPPER"
    assert mlb_moneyline_conviction_recommendation(59.0, 78.0) == "✅ STRONG PLAY"
    assert mlb_moneyline_conviction_recommendation(56.5, 74.0) == "🟡 PLAYABLE"
    assert mlb_moneyline_conviction_recommendation(52.0, 65.0) == "LEAN"
    assert mlb_moneyline_conviction_recommendation(51.9, 95.0) == "PASS"


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
            {"offense": {}},
            {"offense": {}},
            {"name": "Away Starter"},
            {"name": "Home Starter"},
            quote,
            None,
        )

    model = result["model"]
    assert model["model_win_strength"] == 59.0
    assert model["model_probability"] == 59.0
    assert model["model_win_strength"] == model["model_probability"]
    assert model["model_confidence"] == 85.0
    assert model["confidence"] == model["model_confidence"]
    assert model["recommendation"] == "✅ STRONG PLAY"
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
            {"offense": {}},
            {"offense": {}},
            {"name": "Away Starter"},
            {"name": "Home Starter"},
            None,
            None,
        )

    assert result["model"]["recommendation"] == "✅ STRONG PLAY"
    assert result["model"]["market_value_label"] == "VALUE UNAVAILABLE"


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
