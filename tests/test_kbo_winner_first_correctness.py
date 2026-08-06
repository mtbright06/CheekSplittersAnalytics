from unittest.mock import patch

from calculators.bullpen import BullpenCalculator
from calculators.recent_form import RecentFormCalculator
from models.game import Game
from models.kbo_model import KBOModel


def _known_game(
    away="Away",
    home="Home",
    *,
    away_rpg=5.0,
    home_rpg=4.0,
):
    game = Game(away, home)
    for team, runs in (
        (game.away, away_rpg),
        (game.home, home_rpg),
    ):
        team.pitcher.name = f"{team.name} Starter"
        team.pitcher.era = 3.50
        team.pitcher.whip = 1.20
        team.offense.runs_per_game = runs
    return game


def _score(games):
    with patch("models.kbo_model.PitcherLoader.load"):
        return KBOModel().score(games)


def test_row_order_cannot_change_kbo_selection():
    first = _known_game("Away First", "Home First")
    second = _known_game("Away Second", "Home Second")

    scored = _score([first, second])

    assert scored[0].result.play == "Away First"
    assert scored[1].result.play == "Away Second"


def test_model_score_direction_determines_selected_team():
    away_advantage = _known_game(
        "Away Better",
        "Home Worse",
        away_rpg=5.2,
        home_rpg=4.8,
    )
    home_advantage = _known_game(
        "Away Worse",
        "Home Better",
        away_rpg=4.7,
        home_rpg=5.1,
    )

    scored = _score([away_advantage, home_advantage])

    assert scored[0].result.model_probability > 50.0
    assert scored[0].result.play == "Away Better"
    assert scored[1].result.model_probability < 50.0
    assert scored[1].result.play == "Home Better"


def test_zero_kbo_score_is_neutral_no_play():
    game = _known_game(
        "Away Even",
        "Home Even",
        away_rpg=5.0,
        home_rpg=5.0,
    )

    scored = _score([game])[0]
    finalized = KBOModel().finalize([scored])[0]

    assert finalized.result.model_probability == 50.0
    assert finalized.result.model_strength == 50.0
    assert finalized.result.play is None
    assert finalized.result.recommendation == "❌ NO PLAY"


def test_bullpen_and_recent_form_are_neutral():
    assert BullpenCalculator().score(_known_game(), 0) == 0.0
    assert BullpenCalculator().score(_known_game(), 99) == 0.0
    assert RecentFormCalculator().score(_known_game(), 0) == 0.0
    assert RecentFormCalculator().score(_known_game(), 99) == 0.0


def test_neutral_kbo_components_do_not_fabricate_strength():
    game = _score([_known_game()])[0]

    assert dict(game.result.signals)["Offense"] == 0.25
    assert dict(game.result.signals)["Bullpen"] == 0.0
    assert dict(game.result.signals)["Recent Form"] == 0.0
    assert game.result.model_probability == 52.0


def test_original_configured_component_weights_are_applied_exactly():
    game = _known_game()
    game.away.pitcher.era = 3.00
    game.home.pitcher.era = 5.25
    game.away.pitcher.whip = 1.10
    game.home.pitcher.whip = 1.60

    scored = _score([game])[0]

    assert scored.result.signals == [
        ("Starting Pitching", 0.70),
        ("Offense", 0.25),
        ("Bullpen", 0.0),
        ("Recent Form", 0.0),
    ]
    assert scored.result.model_probability == 57.6


def test_no_active_weight_normalization_occurs():
    game = _score([_known_game()])[0]

    assert dict(game.result.signals)["Offense"] == round(1 * 0.25, 2)
    assert game.result.model_probability != 53.4


def test_restored_practical_range_and_reachable_tiers():
    model = KBOModel()

    assert round(50 + (-0.95 * 8), 1) == 42.4
    assert round(50 + (0.95 * 8), 1) == 57.6
    assert model._model_strength_confidence(57.6) == 88.4
    assert model._model_score_recommendation(52.0) == "👀 LEAN"
    assert model._model_score_recommendation(55.0) == "✅ PLAYABLE"
    assert model._model_score_recommendation(57.6) == "✅ PLAYABLE"
    assert model._model_score_recommendation(58.0) == "🔥 STRONG PLAY"


def test_kbo_strength_and_confidence_aliases_match():
    game = _score([_known_game()])[0]
    finalized = KBOModel().finalize([game])[0]

    assert finalized.result.model_strength == finalized.result.model_probability
    assert finalized.result.model_confidence == finalized.result.confidence
