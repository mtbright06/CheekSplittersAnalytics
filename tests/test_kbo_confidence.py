from engine.confidence import ConfidenceEngine
from models.game import Game
from models.kbo_model import KBOModel


def apply_known_starter(team, name):
    team.pitcher.name = name
    team.pitcher.era = 3.50
    team.pitcher.whip = 1.20
    team.pitcher.data_source = "starter_profile"
    team.pitcher.starter_confirmed = True
    team.offense.runs_per_game = 4.80
    team.bullpen.era = 3.85
    team.bullpen.league_era = 3.85
    team.bullpen.source = "LIVE_TEAM_SPLITS"
    team.form.season_runs_per_game = 4.80
    team.form.recent_runs_per_game = 4.80
    team.form.recent_games = 10
    team.form.source = "LIVE_TEAM_SPLITS"


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


def test_missing_market_uses_the_kbo_model_score_scale_without_an_edge():
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

    assert game.result.edge is None
    assert game.result.recommendation == "🔥 STRONG PLAY"
    assert game.result.confidence == 95.0
    assert game.result.model_confidence == 95.0
    assert game.result.legacy_model_confidence == 100.0
    assert game.result.confidence_breakdown["basis"] == "KBO current input reliability"


def test_no_market_kbo_model_score_recommendation_tiers():
    model = KBOModel()

    assert model._model_score_recommendation(58.0) == "🔥 STRONG PLAY"
    assert model._model_score_recommendation(57.0) == "🔥 STRONG PLAY"
    assert model._model_score_recommendation(56.9) == "✅ PLAY"
    assert model._model_score_recommendation(56.5) == "✅ PLAY"
    assert model._model_score_recommendation(56.4) == "✅ PLAYABLE"
    assert model._model_score_recommendation(55.0) == "✅ PLAYABLE"
    assert model._model_score_recommendation(54.9) == "👀 LEAN"
    assert model._model_score_recommendation(52.0) == "👀 LEAN"
    assert model._model_score_recommendation(51.9) == "❌ NO PLAY"


def test_kbo_model_strength_confidence_uses_the_ordinal_score_range():
    model = KBOModel()

    assert model._model_strength_confidence(58.0) == 100.0
    assert model._model_strength_confidence(55.0) == 81.2
    assert model._model_strength_confidence(99.0) == 100.0
    assert model._model_strength_confidence(0.0) == 0.0


def test_kbo_reliability_is_independent_of_model_score_magnitude():
    model = KBOModel()

    strong = Game("Away", "Home", game_url="game")
    weak = Game("Away", "Home", game_url="game")
    for game in (strong, weak):
        apply_known_starter(game.away, "Away Starter")
        apply_known_starter(game.home, "Home Starter")

    strong.result = type("Result", (), {
        "model_probability": 58.0,
        "model_strength": 58.0,
    })()
    weak.result = type("Result", (), {
        "model_probability": 52.0,
        "model_strength": 52.0,
    })()

    model.finalize([strong, weak])

    assert strong.result.confidence == weak.result.confidence == 100.0
    assert strong.result.legacy_model_confidence != weak.result.legacy_model_confidence


def test_no_inactive_kbo_components_reduce_reliability():
    game = Game("Away", "Home", game_url="game")
    apply_known_starter(game.away, "Away Starter")
    apply_known_starter(game.home, "Home Starter")

    reliability, breakdown = KBOModel._input_reliability(game)

    assert reliability == 100.0
    assert breakdown["inactive_components"] == "No inactive KBO model components."


def test_real_market_preserves_model_conviction_after_enrichment():
    game = Game("Away", "Home")
    apply_known_starter(game.away, "Away Starter")
    apply_known_starter(game.home, "Home Starter")
    game.result = type("Result", (), {
        "model_probability": 58.0,
    })()
    game.odds = {
        "real_market_loaded": True,
        "reference_status": "LOCKED",
        "reference_implied_probability": 52.0,
    }

    KBOModel().finalize([game])

    assert game.result.edge == 6.0
    assert game.result.recommendation == "🔥 STRONG PLAY"
    assert game.result.confidence == 95.0
    assert game.result.legacy_model_confidence == 100.0
    assert game.result.confidence_breakdown["basis"] == "KBO current input reliability"


def test_kbo_recommendation_does_not_change_when_only_market_changes():
    model = KBOModel()

    def finalized_with(reference_probability):
        game = Game("Away", "Home")
        apply_known_starter(game.away, "Away Starter")
        apply_known_starter(game.home, "Home Starter")
        game.result = type("Result", (), {
            "model_probability": 55.0,
        })()
        game.odds = {
            "real_market_loaded": True,
            "reference_status": "LOCKED",
            "reference_implied_probability": reference_probability,
        }
        model.finalize([game])
        return game.result

    cheap = finalized_with(40.0)
    expensive = finalized_with(70.0)

    assert cheap.edge != expensive.edge
    assert cheap.recommendation == expensive.recommendation == "✅ PLAYABLE"
    assert cheap.confidence == expensive.confidence == 95.0
