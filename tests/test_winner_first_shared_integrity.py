from pathlib import Path
import sys

from engine.core import MarketQuote, Recommendation, RecommendationRegistry
from engine.core.ranking import model_confidence_score, ranked_recommendations
from engine.core.play_of_day import eligibility_result, select_play_of_day
from engine.decision.hammer_score import HammerInputs, calculate_hammer_score


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.best_bets_workstation import filter_recommendations


def hammer_input(**overrides):
    data = {
        "mlb_model_score": 72.0,
        "mlb_model_probability": 0.58,
        "first5_score": 66.0,
        "bomb_score": 61.0,
        "starter_score": 70.0,
        "offense_score": 68.0,
        "bullpen_score": 62.0,
        "park_score": 55.0,
        "weather_score": 50.0,
        "sample_confidence": 80.0,
        "module_agreement": 2,
        "contradiction_count": 0,
        "real_market_loaded": True,
    }
    data.update(overrides)
    return HammerInputs(**data)


def recommendation(**overrides):
    data = {
        "sport": "BASEBALL",
        "league": "MLB",
        "market": "moneyline",
        "selection": "Favorite",
        "event_id": "1",
        "model_probability": 0.61,
        "hammer_score": 76.0,
        "recommendation": "BET",
        "confidence": "HIGH",
        "pregame_eligible": True,
        "pregame_eligibility_reason": "GAME_NOT_STARTED",
    }
    data.update(overrides)
    return Recommendation(**data)


def test_market_inputs_do_not_change_hammer_score():
    baseline = calculate_hammer_score(hammer_input())
    changed_market = calculate_hammer_score(
        hammer_input(real_market_loaded=False)
    )
    changed_edge = hammer_input()
    changed_edge.market_edge_pct = 50.0
    changed_ev = hammer_input()
    changed_ev.expected_value_pct = 75.0

    assert changed_market["hammer_score"] == baseline["hammer_score"]
    assert changed_market["recommendation"] == baseline["recommendation"]
    assert calculate_hammer_score(changed_edge)["hammer_score"] == baseline["hammer_score"]
    assert calculate_hammer_score(changed_ev)["hammer_score"] == baseline["hammer_score"]
    assert "market_edge" not in baseline["breakdown"]
    assert "expected_value" not in baseline["breakdown"]
    assert baseline["market_status_penalty"] == 0.0


def test_hammer_normalizes_weights_and_remains_bounded():
    full_score = calculate_hammer_score(
        hammer_input(
            mlb_model_score=100.0,
            first5_score=100.0,
            bomb_score=100.0,
            starter_score=100.0,
            offense_score=100.0,
            bullpen_score=100.0,
            park_score=100.0,
            weather_score=100.0,
            sample_confidence=100.0,
            module_agreement=10,
        )
    )
    partial_score = calculate_hammer_score(
        HammerInputs(
            mlb_model_score=80.0,
        )
    )

    assert full_score["base_score"] == 100.0
    assert full_score["hammer_score"] == 100.0
    assert partial_score["base_score"] == 80.0
    assert partial_score["hammer_score"] == 80.0


def test_price_edge_and_ev_do_not_change_recommendation_ranking():
    favorite = recommendation(
        selection="Favorite",
        event_id="favorite",
        model_probability=0.62,
        edge_pct=-12.0,
        expected_value_pct=-18.0,
        market_quote=MarketQuote(sportsbook="A", odds=-220),
    )
    underdog = recommendation(
        selection="Underdog",
        event_id="underdog",
        model_probability=0.54,
        edge_pct=20.0,
        expected_value_pct=35.0,
        market_quote=MarketQuote(sportsbook="B", odds=180),
    )

    registry = RecommendationRegistry([underdog, favorite])

    assert registry.ranked()[0].selection == "Favorite"
    assert registry.to_dict()["recommendations"][0]["selection"] == "Favorite"
    assert registry.to_dict()["recommendations"][0]["edge_pct"] == -12.0


def test_ranking_prefers_explicit_model_confidence_over_hammer_label():
    row = recommendation(
        model_probability=0.60,
        model_win_strength=0.60,
        model_confidence=71.0,
        hammer_confidence="ELITE",
        confidence="ELITE",
        edge_pct=99.0,
        expected_value_pct=99.0,
        market_quote=MarketQuote(sportsbook="A", odds=400),
    )

    assert model_confidence_score(row) == 71.0


def test_ranking_never_uses_edge_ev_or_price_as_confidence():
    baseline = recommendation(
        model_probability=0.60,
        model_win_strength=0.60,
        model_confidence=None,
        hammer_confidence="ELITE",
        confidence="ELITE",
        edge_pct=-50.0,
        expected_value_pct=-50.0,
        market_quote=MarketQuote(sportsbook="A", odds=-500),
    )
    changed_market = recommendation(
        model_probability=0.60,
        model_win_strength=0.60,
        model_confidence=None,
        hammer_confidence="ELITE",
        confidence="ELITE",
        edge_pct=50.0,
        expected_value_pct=50.0,
        market_quote=MarketQuote(sportsbook="B", odds=500),
    )

    assert model_confidence_score(baseline) == 50.0
    assert model_confidence_score(changed_market) == 50.0


def test_registry_order_is_stable_when_only_market_values_change():
    first = recommendation(
        selection="First",
        event_id="first",
        model_probability=0.60,
        edge_pct=-10.0,
        expected_value_pct=-20.0,
        market_quote=MarketQuote(sportsbook="A", odds=-250),
    )
    second = recommendation(
        selection="Second",
        event_id="second",
        model_probability=0.58,
        edge_pct=25.0,
        expected_value_pct=45.0,
        market_quote=MarketQuote(sportsbook="B", odds=210),
    )

    assert RecommendationRegistry([second, first]).ranked()[0].selection == "First"

    first.edge_pct = 40.0
    first.expected_value_pct = 70.0
    first.market_quote = MarketQuote(sportsbook="C", odds=300)
    second.edge_pct = -25.0
    second.expected_value_pct = -40.0
    second.market_quote = MarketQuote(sportsbook="D", odds=-300)

    assert RecommendationRegistry([second, first]).ranked()[0].selection == "First"


def test_play_of_day_does_not_suppress_negative_edge_favorite():
    favorite = recommendation(
        selection="Favorite",
        event_id="favorite",
        model_probability=0.63,
        edge_pct=-8.0,
        expected_value_pct=-10.0,
    )
    underdog = recommendation(
        selection="Underdog",
        event_id="underdog",
        model_probability=0.55,
        edge_pct=18.0,
        expected_value_pct=30.0,
    )

    assert eligibility_result(favorite)[0] is True
    result = select_play_of_day([underdog, favorite])

    assert result.recommendation.selection == "Favorite"


def test_play_of_day_is_unchanged_when_only_market_price_changes():
    first = recommendation(selection="First", event_id="first", model_probability=0.61)
    second = recommendation(selection="Second", event_id="second", model_probability=0.57)

    assert select_play_of_day([second, first]).recommendation.selection == "First"

    first.edge_pct = -50.0
    first.expected_value_pct = -50.0
    first.market_quote = MarketQuote(sportsbook="A", odds=-400)
    second.edge_pct = 50.0
    second.expected_value_pct = 50.0
    second.market_quote = MarketQuote(sportsbook="B", odds=300)

    assert select_play_of_day([second, first]).recommendation.selection == "First"


def test_best_bets_inherits_winner_first_registry_order():
    registry_rows = RecommendationRegistry(
        [
            recommendation(selection="Underdog", event_id="underdog", model_probability=0.53, edge_pct=30.0),
            recommendation(selection="Favorite", event_id="favorite", model_probability=0.60, edge_pct=-15.0),
        ]
    ).to_dict()["recommendations"]

    filtered = filter_recommendations(registry_rows, "MLB", "moneyline")

    assert [row["selection"] for row in filtered] == ["Favorite", "Underdog"]


def test_pregame_eligibility_still_blocks_live_registry_rows():
    registry = RecommendationRegistry(
        [
            recommendation(
                selection="Live Favorite",
                pregame_eligible=False,
                pregame_eligibility_reason="GAME_STARTED",
            )
        ]
    )

    assert registry.ranked() == []


def test_exact_ranking_ties_ignore_uuid_ids():
    older = recommendation(
        selection="Alpha",
        event_id="game-1",
        scheduled_start_at="2026-08-05T17:00:00Z",
        recommendation_id="zzzz",
    )
    later = recommendation(
        selection="Beta",
        event_id="game-2",
        scheduled_start_at="2026-08-05T18:00:00Z",
        recommendation_id="aaaa",
    )

    first = ranked_recommendations([older, later])
    second = ranked_recommendations([
        recommendation(
            selection="Alpha",
            event_id="game-1",
            scheduled_start_at="2026-08-05T17:00:00Z",
            recommendation_id="1111",
        ),
        recommendation(
            selection="Beta",
            event_id="game-2",
            scheduled_start_at="2026-08-05T18:00:00Z",
            recommendation_id="9999",
        ),
    ])

    assert [row.selection for row in first] == ["Beta", "Alpha"]
    assert [row.selection for row in second] == ["Beta", "Alpha"]
