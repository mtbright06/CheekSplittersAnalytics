from engine.contracts.sharpstack_card import normalize_card


def test_normalizer_preserves_canonical_pitcher_and_market_fields():
    card = {
        "sport": "MLB",
        "games": [
            {
                "matchup": {"away": "Away", "home": "Home"},
                "teams": {"away": {}, "home": {}},
                "pitching": {
                    "away": {
                        "name": "Away Starter",
                        "data_source": "game_logs",
                        "starts": 12,
                        "strike_pct": 63.2,
                    },
                    "home": {"name": "Home Starter"},
                },
                "model": {"edge": None, "confidence": 61.0},
                "odds": {
                    "real_market_loaded": False,
                    "stale": True,
                    "event_id": "event-1",
                    "book_probability": None,
                },
            }
        ],
    }

    game = normalize_card(card)["games"][0]

    assert game["pitching"]["away"]["data_source"] == "game_logs"
    assert game["pitching"]["away"]["starts"] == 12
    assert game["pitching"]["away"]["strike_pct"] == 63.2
    assert game["odds"]["real_market_loaded"] is False
    assert game["odds"]["stale"] is True
    assert game["odds"]["event_id"] == "event-1"
    assert game["model"]["edge"] is None
