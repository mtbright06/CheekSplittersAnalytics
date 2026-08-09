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
                "model": {
                    "edge": None,
                    "confidence": 61.0,
                    "market_value_label": "VALUE UNAVAILABLE",
                    "market_value_tone": "unavailable",
                    "recommendation_explanation": {
                        "schema_version": "mlb_moneyline_v1",
                    },
                },
                "odds": {
                    "real_market_loaded": False,
                    "stale": True,
                    "event_id": "event-1",
                    "book_probability": None,
                    "current_price": -110,
                    "reference_price": -105,
                    "reference_status": "LOCKED",
                    "reference_policy_version": "SSRP_v1",
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
    assert game["odds"]["current_price"] == -110
    assert game["odds"]["reference_price"] == -105
    assert game["odds"]["reference_status"] == "LOCKED"
    assert game["model"]["edge"] is None
    assert game["model"]["market_value_label"] == "VALUE UNAVAILABLE"
    assert game["model"]["market_value_tone"] == "unavailable"
    assert game["model"]["recommendation_explanation"]["schema_version"] == "mlb_moneyline_v1"


def test_normalizer_preserves_kbo_starter_identity_and_source_status():
    game = normalize_card(
        {
            "sport": "KBO",
            "games": [
                {
                    "matchup": {"away": "Away", "home": "Home"},
                    "teams": {"away": {}, "home": {}},
                    "pitching": {
                        "away": {
                            "name": "So Hyeong-jun",
                            "data_source": "starter_profile",
                            "starter_confirmed": True,
                        },
                        "home": {"name": "Unknown Starter"},
                    },
                    "model": {},
                    "odds": {},
                }
            ],
        }
    )["games"][0]

    assert game["pitching"]["away"]["name"] == "So Hyeong-jun"
    assert game["pitching"]["away"]["data_source"] == "starter_profile"
    assert game["pitching"]["away"]["starter_confirmed"] is True
