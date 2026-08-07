from engine.adapters.mlb_decision_adapter import adapt_mlb_decision_card
from engine.core.play_of_day import eligibility_result
from engine.model.confidence import calculate_confidence


def test_mlb_model_recommendation_remains_authoritative_over_hammer():
    card = {
        "generated_at": "2026-07-24T12:00:00",
        "decisions": [
            {
                "game_pk": 1,
                "matchup": "Away Club @ Home Club",
                "selected_team": "Away Club",
                "market": "REAL MARKET",
                "pregame_eligible": True,
                "pregame_eligibility_reason": "GAME_NOT_STARTED",
                "book_odds": 120,
                "model_win_strength": 0.556,
                "model_probability": 0.556,
                "model_confidence": 82.0,
                "hammer_confidence": "MODERATE",
                "market_edge_pct": 10.76,
                "hammer_score": 64.6,
                "recommendation": "🔥 CHEEK RIPPER",
                "model_recommendation": "🔥 CHEEK RIPPER",
                "market_value_label": "MARKET PREMIUM",
                "market_value_tone": "market_premium",
                "recommendation_explanation": {
                    "schema_version": "mlb_moneyline_v1",
                },
                "hammer_tier": "WATCH",
                "hammer_assessment": "Below validation threshold / Moderate confirmation",
            }
        ],
    }

    recommendation = adapt_mlb_decision_card(card)[0]

    assert recommendation.recommendation == "🔥 CHEEK RIPPER"
    assert recommendation.model_recommendation == "🔥 CHEEK RIPPER"
    assert recommendation.market_value_label == "MARKET PREMIUM"
    assert recommendation.market_value_tone == "market_premium"
    assert recommendation.recommendation_explanation["schema_version"] == "mlb_moneyline_v1"
    assert recommendation.hammer_tier == "WATCH"
    assert recommendation.model_win_strength == recommendation.model_probability
    assert recommendation.model_confidence == 82.0
    assert recommendation.hammer_confidence == "MODERATE"
    assert recommendation.confidence == "MODERATE"
    assert recommendation.components["model_confidence"] == 82.0
    assert recommendation.components["hammer_confidence"] == "MODERATE"
    assert recommendation.actionable is True
    assert recommendation.units is None
    assert eligibility_result(recommendation)[0] is True


def test_mlb_pass_remains_non_actionable_with_hammer_context():
    card = {
        "decisions": [
            {
                "game_pk": 2,
                "matchup": "Away Club @ Home Club",
                "selected_team": "Home Club",
                "market": "REAL MARKET",
                "pregame_eligible": True,
                "pregame_eligibility_reason": "GAME_NOT_STARTED",
                "book_odds": -110,
                "hammer_score": 72.0,
                "recommendation": "PASS",
                "model_recommendation": "PASS",
                "hammer_tier": "LEAN",
            }
        ]
    }

    recommendation = adapt_mlb_decision_card(card)[0]

    assert recommendation.recommendation == "PASS"
    assert recommendation.actionable is False


def test_mlb_v2_official_recommendation_overrides_v1_shadow():
    card = {
        "decisions": [
            {
                "game_pk": 4,
                "matchup": "Away Club @ Home Club",
                "selected_team": "Away Club",
                "market": "REAL MARKET",
                "pregame_eligible": True,
                "pregame_eligibility_reason": "GAME_NOT_STARTED",
                "book_odds": -110,
                "model_win_strength": 0.51,
                "model_probability": 0.51,
                "model_confidence": 60.0,
                "hammer_confidence": "PASS",
                "hammer_score": 0.0,
                "hammer_tier": "PASS",
                "recommendation": "PLAY",
                "model_recommendation": "PLAY",
                "v1_shadow_recommendation": "PASS",
                "v1_shadow_tier": "PASS",
            }
        ]
    }

    recommendation = adapt_mlb_decision_card(card)[0]

    assert recommendation.recommendation == "PLAY"
    assert recommendation.model_recommendation == "PLAY"
    assert recommendation.components["v1_shadow_recommendation"] == "PASS"
    assert recommendation.hammer_tier == "PASS"
    assert recommendation.actionable is True


def test_mlb_confidence_ignores_market_probability():
    away_pitcher = {"name": "Away Starter", "era": 3.2, "whip": 1.1}
    home_pitcher = {"name": "Home Starter", "era": 4.2, "whip": 1.3}
    away_offense = {"ops": .760}
    home_offense = {"ops": .720}

    no_market = calculate_confidence(
        8.0,
        away_pitcher,
        home_pitcher,
        {},
        away_offense,
        home_offense,
    )
    with_market = calculate_confidence(
        8.0,
        away_pitcher,
        home_pitcher,
        {"book_probability": 0.64},
        away_offense,
        home_offense,
    )

    assert with_market == no_market


def test_model_confidence_and_hammer_confidence_remain_distinct():
    card = {
        "decisions": [
            {
                "game_pk": 3,
                "matchup": "Away Club @ Home Club",
                "selected_team": "Home Club",
                "market": "REAL MARKET",
                "pregame_eligible": True,
                "pregame_eligibility_reason": "GAME_NOT_STARTED",
                "book_odds": -110,
                "model_win_strength": 0.59,
                "model_probability": 0.59,
                "model_confidence": 78.0,
                "hammer_confidence": "LOW",
                "hammer_score": 58.0,
                "recommendation": "✅ STRONG PLAY",
                "model_recommendation": "✅ STRONG PLAY",
            }
        ]
    }

    recommendation = adapt_mlb_decision_card(card)[0]

    assert recommendation.recommendation == "✅ STRONG PLAY"
    assert recommendation.model_win_strength == 0.59
    assert recommendation.model_probability == 0.59
    assert recommendation.model_confidence == 78.0
    assert recommendation.hammer_confidence == "LOW"
    assert recommendation.confidence == "LOW"
