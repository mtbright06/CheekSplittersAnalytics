from unittest.mock import patch

from calculators.bullpen import BullpenCalculator
from calculators.offense import OffenseCalculator
from calculators.recent_form import RecentFormCalculator
from calculators.starting_pitching import StartingPitchingCalculator
from engine.kbo_shadow import build_supported_component_shadow
from models.game import Game
from models.kbo_model import KBOModel


def _game():
    game = Game("Away", "Home")
    for team in (game.away, game.home):
        team.pitcher.name = f"{team.name} Starter"
        team.pitcher.era = 3.50
        team.pitcher.whip = 1.20
        team.pitcher.data_source = "starter_profile"
        team.pitcher.starter_confirmed = True
        team.offense.runs_per_game = 5.0
        team.offense.league_runs_per_game = 4.93
        team.bullpen.era = 4.00
        team.bullpen.league_era = 4.00
        team.form.season_runs_per_game = 5.0
        team.form.recent_runs_per_game = 5.0
        team.form.recent_games = 10
    return game


def _score(game):
    with patch("models.kbo_model.PitcherLoader.load"):
        return KBOModel().score([game])[0]


def test_shadow_all_components_present_keeps_configured_weights():
    game = _score(_game())

    shadow = game.result.shadow_model

    assert shadow["available"] is True
    assert shadow["effective_weights"] == {
        "Starting Pitching": 0.55,
        "Offense": 0.3,
        "Bullpen": 0.125,
        "Recent Form": 0.025,
    }


def test_shadow_starter_and_offense_only_renormalize_to_647_353():
    game = _game()
    for team in (game.away, game.home):
        team.bullpen.era = None
        team.bullpen.league_era = None
        team.form.recent_runs_per_game = None
        team.form.recent_games = None

    scored = _score(game)
    shadow = scored.result.shadow_model

    assert shadow["supported_components"] == {
        "Starting Pitching": True,
        "Offense": True,
        "Bullpen": False,
        "Recent Form": False,
    }
    assert shadow["effective_weights"]["Starting Pitching"] == 0.647059
    assert shadow["effective_weights"]["Offense"] == 0.352941


def test_shadow_one_unavailable_component_renormalizes_remaining_weights():
    game = _game()
    for team in (game.away, game.home):
        team.bullpen.era = None
        team.bullpen.league_era = None

    shadow = _score(game).result.shadow_model

    assert shadow["effective_weights"] == {
        "Starting Pitching": 0.628571,
        "Offense": 0.342857,
        "Recent Form": 0.028571,
    }


def test_shadow_starter_only_gets_full_active_authority():
    game = _game()
    for team in (game.away, game.home):
        team.offense.runs_per_game = None
        team.bullpen.era = None
        team.bullpen.league_era = None
        team.form.recent_runs_per_game = None
        team.form.recent_games = None

    shadow = _score(game).result.shadow_model

    assert shadow["effective_weights"] == {
        "Starting Pitching": 1.0,
    }


def test_shadow_no_supported_components_is_neutral_and_unavailable():
    game = _game()
    for team in (game.away, game.home):
        team.pitcher.name = "Unknown Starter"
        team.pitcher.starter_confirmed = False
        team.offense.runs_per_game = None
        team.bullpen.era = None
        team.bullpen.league_era = None
        team.form.recent_runs_per_game = None
        team.form.recent_games = None

    calculators = [
        StartingPitchingCalculator(),
        OffenseCalculator(),
        BullpenCalculator(),
        RecentFormCalculator(),
    ]
    shadow = build_supported_component_shadow(
        game=game,
        index=0,
        calculators=calculators,
        component_scores={
            calculator.NAME: 0.0
            for calculator in calculators
        },
        recommendation_fn=KBOModel._model_score_recommendation,
        selection_fn=KBOModel._selection_from_score,
    )

    assert shadow["available"] is False
    assert shadow["effective_weights"] == {}
    assert shadow["weighted_score"] == 0.0
    assert shadow["model_strength"] == 50.0
    assert shadow["selection"] is None


def test_shadow_unsupported_component_cannot_exert_directional_authority():
    game = _game()
    game.away.bullpen.era = 1.00
    game.home.bullpen.era = 9.00
    for team in (game.away, game.home):
        team.bullpen.league_era = None

    shadow = _score(game).result.shadow_model

    assert shadow["supported_components"]["Bullpen"] is False
    assert "Bullpen" not in shadow["effective_weights"]


def test_shadow_does_not_change_production_output():
    game = _game()
    game.away.offense.runs_per_game = 5.7
    game.home.offense.runs_per_game = 4.2
    for team in (game.away, game.home):
        team.bullpen.era = None
        team.bullpen.league_era = None
        team.form.recent_runs_per_game = None
        team.form.recent_games = None

    scored = _score(game)

    assert scored.result.model_strength == 52.4
    assert scored.result.play == "Away"
    assert scored.result.recommendation == "❌ NO PLAY"
    assert scored.result.shadow_model["model_strength"] != scored.result.model_strength


def test_shadow_home_selection_tiers_from_selected_side_strength():
    game = _game()
    game.away.offense.runs_per_game = 4.2
    game.home.offense.runs_per_game = 5.7
    for team in (game.away, game.home):
        team.bullpen.era = None
        team.bullpen.league_era = None
        team.form.recent_runs_per_game = None
        team.form.recent_games = None

    shadow = _score(game).result.shadow_model

    assert shadow["selection"] == "Home"
    assert shadow["model_strength"] < 50.0
    assert shadow["selected_team_model_strength"] > 52.0
    assert shadow["recommendation"] == "👀 LEAN"


def test_shadow_calculation_is_deterministic():
    first = _score(_game()).result.shadow_model
    second = _score(_game()).result.shadow_model

    assert first == second
