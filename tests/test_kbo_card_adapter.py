from engine.adapters.kbo_card_adapter import adapt_kbo_card


def test_adapter_accepts_nested_canonical_kbo_card():
    card = {
        "generated_at": "2026-07-23T12:00:00",
        "games": [
            {
                "game_id": "kbo-1",
                "matchup": {"away": "Away Club", "home": "Home Club"},
                "teams": {
                    "away": {"name": "Away Club"},
                    "home": {"name": "Home Club"},
                },
                "model": {
                    "play": "Away Club",
                    "market": "Moneyline",
                    "model_probability": 54.5,
                    "confidence": 42.0,
                    "recommendation": "❌ NO PLAY",
                    "reasons": ["Model-only fixture."],
                },
                "odds": {
                    "sportsbook": "Unavailable",
                    "moneyline": None,
                    "book_probability": None,
                },
            }
        ],
    }

    recommendations = adapt_kbo_card(card)

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.league == "KBO"
    assert recommendation.selection == "Away Club"
    assert recommendation.matchup == "Away Club @ Home Club"
    assert recommendation.model_probability == 0.545
    assert recommendation.real_market_loaded is False
