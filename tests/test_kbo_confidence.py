from engine.confidence import ConfidenceEngine
from models.game import Game
from models.kbo_model import KBOModel


def apply_known_starter(team, name):
    team.pitcher.name = name
    team.pitcher.era = 3.50
    team.pitcher.whip = 1.20
    team.offense.runs_per_game = 4.80


def test_unknown_starter_reduces_confidence():
    known = type("Pitcher", (), {
        "name": "Known Starter",
        "era": 3.50,
        "whip": 1.20,
    })()
    unknown = type("Pitcher", (), {
        "name": "Unknown Starter",
        "era": None,
        "whip": None,
    })()
    offense = type("Offense", (), {
        "runs_per_game": 4.80,
    })()

    known_confidence, _ = ConfidenceEngine.calculate(
        58.0, known, known, offense, offense, True
    )
    unknown_confidence, breakdown = ConfidenceEngine.calculate(
        58.0, known, unknown, offense, offense, True
    )

    assert unknown_confidence < known_confidence
    assert breakdown["starter_certainty"] == -10.0


def test_missing_market_does_not_create_edge_or_play():
    game = Game("Away", "Home")
    apply_known_starter(game.away, "Away Starter")
    apply_known_starter(game.home, "Home Starter")
    game.result = type("Result", (), {
        "model_probability": 58.0,
        "edge": 8.0,
        "recommendation": "🔥 BET",
    })()
    game.odds = {
        "real_market_loaded": False,
        "book_probability": None,
    }

    KBOModel().finalize([game])

    assert game.result.edge == 0.0
    assert game.result.recommendation == "❌ NO PLAY"
    assert game.result.confidence_breakdown["data_quality"] == 16.0


def test_real_market_recomputes_edge_after_enrichment():
    game = Game("Away", "Home")
    apply_known_starter(game.away, "Away Starter")
    apply_known_starter(game.home, "Home Starter")
    game.result = type("Result", (), {
        "model_probability": 58.0,
    })()
    game.odds = {
        "real_market_loaded": True,
        "book_probability": 52.0,
    }

    KBOModel().finalize([game])

    assert game.result.edge == 6.0
    assert game.result.recommendation == "👀 LEAN"
    assert game.result.confidence_breakdown["data_quality"] == 20.0
