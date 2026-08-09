from engine.adapters.mlb_totals_adapter import adapt_mlb_totals_card


def test_actionable_totals_reaches_registry_contract():
    card = {
        "generated_at": "2026-07-23T12:00:00",
        "games": [
            {
                "game_id": "mlb-1",
                "matchup": {"away": "Away Club", "home": "Home Club"},
                "pregame_eligible": True,
                "pregame_eligibility_reason": "GAME_NOT_STARTED",
                "odds": {
                    "totals": {
                        "event_id": "event-1",
                        "real_market_loaded": True,
                        "sportsbook": "FixtureBook",
                        "over_odds": -110,
                        "under_odds": -110,
                    }
                },
                "totals_model": {
                    "recommendation": "LEAN OVER",
                    "selection": "OVER",
                    "market_total": 8.5,
                    "edge": 0.8,
                    "projected_total": 9.3,
                    "reasons": ["Fixture totals reason."],
                    "betting_recommendation": {
                        "recommendation": "LEAN OVER",
                        "recommendation_score": 77.2,
                        "confidence": "MODERATE",
                        "stars": "★★★★",
                    },
                },
            }
        ],
    }

    recommendations = adapt_mlb_totals_card(card)

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.market == "totals"
    assert recommendation.selection == "OVER 8.5"
    assert recommendation.recommendation == "LEAN"
    assert recommendation.actionable is True
    assert recommendation.real_market_loaded is True
    assert recommendation.hammer_score == 77.2


def test_strong_totals_recommendation_remains_strong_in_registry_contract():
    card = {
        "generated_at": "2026-07-23T12:00:00",
        "games": [
            {
                "game_id": "mlb-2",
                "matchup": {"away": "Away Club", "home": "Home Club"},
                "pregame_eligible": True,
                "pregame_eligibility_reason": "GAME_NOT_STARTED",
                "odds": {
                    "totals": {
                        "event_id": "event-2",
                        "real_market_loaded": True,
                        "sportsbook": "FixtureBook",
                        "over_odds": -110,
                        "under_odds": -110,
                    }
                },
                "totals_model": {
                    "recommendation": "STRONG BET OVER",
                    "selection": "OVER",
                    "market_total": 8.5,
                    "projected_total": 10.1,
                    "betting_recommendation": {
                        "recommendation": "STRONG BET OVER",
                        "recommendation_score": 88.0,
                        "confidence": "HIGH",
                        "stars": "★★★★",
                    },
                },
            }
        ],
    }

    recommendations = adapt_mlb_totals_card(card)

    assert recommendations[0].recommendation == "STRONG BET"
