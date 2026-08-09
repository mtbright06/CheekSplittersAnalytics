from unittest.mock import patch

from calculators.bullpen import BullpenCalculator
from calculators.offense import OffenseCalculator
from calculators.recent_form import RecentFormCalculator
from calculators.starting_pitching import StartingPitchingCalculator
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
        team.pitcher.data_source = "starter_profile"
        team.pitcher.starter_confirmed = True
        team.offense.runs_per_game = runs
        team.bullpen.era = 3.85
        team.bullpen.league_era = 3.85
        team.bullpen.source = "LIVE_TEAM_SPLITS"
        team.form.season_runs_per_game = runs
        team.form.recent_runs_per_game = runs
        team.form.recent_games = 10
        team.form.source = "LIVE_TEAM_SPLITS"
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


def test_bullpen_era_advantage_scores_independently():
    game = _known_game()
    game.away.bullpen.era = 3.20
    game.home.bullpen.era = 4.50

    assert BullpenCalculator().score(game, 0) > 0.0

    game.away.bullpen.era = 4.50
    game.home.bullpen.era = 3.20

    assert BullpenCalculator().score(game, 99) < 0.0


def test_recent_form_is_stabilized_scoring_form():
    game = _known_game()
    game.away.form.recent_runs_per_game = 6.0
    game.home.form.recent_runs_per_game = 4.0

    assert RecentFormCalculator().score(game, 0) > 0.0

    game.away.form.recent_runs_per_game = 4.0
    game.home.form.recent_runs_per_game = 6.0

    assert RecentFormCalculator().score(game, 99) < 0.0


def test_recent_form_missing_data_is_neutral():
    game = _known_game()
    game.away.form.recent_runs_per_game = None

    assert RecentFormCalculator().score(game, 0) == 0.0

    game.home.form.recent_runs_per_game = None

    assert RecentFormCalculator().score(game, 0) == 0.0


def test_neutral_kbo_components_do_not_fabricate_strength():
    game = _score([_known_game()])[0]

    assert dict(game.result.signals)["Offense"] == 0.17
    assert dict(game.result.signals)["Bullpen"] == 0.0
    assert dict(game.result.signals)["Recent Form"] == 0.0
    assert game.result.model_probability == 51.3


def test_original_configured_component_weights_are_applied_exactly():
    game = _known_game()
    game.away.pitcher.era = 3.00
    game.home.pitcher.era = 5.25
    game.away.pitcher.whip = 1.10
    game.home.pitcher.whip = 1.60

    scored = _score([game])[0]

    assert scored.result.signals == [
        ("Starting Pitching", 0.32),
        ("Offense", 0.17),
        ("Bullpen", 0.0),
        ("Recent Form", 0.0),
    ]
    assert scored.result.model_probability == 53.9


def test_no_active_weight_normalization_occurs():
    game = _score([_known_game()])[0]

    assert dict(game.result.signals)["Offense"] == 0.17
    assert game.result.model_probability != 52.7


def test_restored_practical_range_and_reachable_tiers():
    model = KBOModel()

    assert (
        StartingPitchingCalculator.WEIGHT
        + OffenseCalculator.WEIGHT
        + BullpenCalculator.WEIGHT
        + RecentFormCalculator.WEIGHT
    ) == 1.0
    assert round(50 + (-1.0 * 8), 1) == 42.0
    assert round(50 + (1.0 * 8), 1) == 58.0
    assert model._model_strength_confidence(58.0) == 100.0
    assert model._model_score_recommendation(52.0) == "👀 LEAN"
    assert model._model_score_recommendation(55.0) == "✅ PLAYABLE"
    assert model._model_score_recommendation(56.5) == "✅ PLAY"
    assert model._model_score_recommendation(56.9) == "✅ PLAY"
    assert model._model_score_recommendation(57.0) == "🔥 STRONG PLAY"
    assert model._model_score_recommendation(58.0) == "🔥 STRONG PLAY"


def test_kbo_strength_and_confidence_aliases_match():
    game = _score([_known_game()])[0]
    finalized = KBOModel().finalize([game])[0]

    assert finalized.result.model_strength == finalized.result.model_probability
    assert finalized.result.model_confidence == finalized.result.confidence
    assert finalized.result.confidence_breakdown["basis"] == "KBO current input reliability"


def test_kbo_strength_is_not_labeled_as_reliability():
    game = _score([_known_game()])[0]
    finalized = KBOModel().finalize([game])[0]

    assert finalized.result.model_strength == 51.3
    assert finalized.result.model_probability == 51.3
    assert finalized.result.model_confidence == finalized.result.confidence
    assert finalized.result.legacy_model_confidence == KBOModel._model_strength_confidence(51.3)


def test_continuous_starter_score_directionality():
    game = _known_game(
        "Away Ace",
        "Home Struggle",
        away_rpg=5.0,
        home_rpg=5.0,
    )
    game.away.pitcher.era = 3.00
    game.away.pitcher.whip = 1.10
    game.away.pitcher.k_rate = 8.0
    game.away.pitcher.bb_rate = 2.0
    game.away.pitcher.hr9 = 0.6
    game.away.pitcher.ip = 90.0
    game.home.pitcher.era = 5.50
    game.home.pitcher.whip = 1.70
    game.home.pitcher.k_rate = 4.0
    game.home.pitcher.bb_rate = 5.0
    game.home.pitcher.hr9 = 1.8
    game.home.pitcher.ip = 90.0

    scored = _score([game])[0]

    assert dict(scored.result.signals)["Starting Pitching"] > 0
    assert scored.result.play == "Away Ace"


def test_continuous_offense_score_directionality():
    away = _score([
        _known_game(
            "Better Offense",
            "Weaker Offense",
            away_rpg=5.4,
            home_rpg=4.3,
        )
    ])[0]
    home = _score([
        _known_game(
            "Weaker Offense",
            "Better Offense",
            away_rpg=4.3,
            home_rpg=5.4,
        )
    ])[0]

    assert dict(away.result.signals)["Offense"] > 0
    assert dict(home.result.signals)["Offense"] < 0


def test_missing_starter_quality_is_neutral_with_reliability_concern():
    game = _known_game(
        "Away",
        "Home",
        away_rpg=5.0,
        home_rpg=5.0,
    )
    game.home.pitcher.name = "Unknown Starter"
    game.home.pitcher.era = None
    game.home.pitcher.whip = None
    game.home.pitcher.starter_confirmed = False

    scored = _score([game])[0]
    finalized = KBOModel().finalize([scored])[0]

    assert finalized.result.model_strength == 50.0
    assert finalized.result.confidence < 100.0


def test_partial_starter_metrics_renormalize_without_fake_values():
    full = _known_game("Full", "Opponent", away_rpg=5.0, home_rpg=5.0)
    partial = _known_game("Partial", "Opponent", away_rpg=5.0, home_rpg=5.0)
    opponent = (full.home, partial.home)
    for home in opponent:
        home.pitcher.era = 4.50
        home.pitcher.whip = 1.40
    full.away.pitcher.era = 3.00
    full.away.pitcher.whip = 1.10
    full.away.pitcher.k_rate = 8.0
    full.away.pitcher.bb_rate = 2.0
    full.away.pitcher.hr9 = 0.6
    partial.away.pitcher.era = 3.00
    partial.away.pitcher.whip = None
    partial.away.pitcher.k_rate = None
    partial.away.pitcher.bb_rate = None
    partial.away.pitcher.hr9 = None

    scored_full, scored_partial = _score([full, partial])

    assert dict(scored_partial.result.signals)["Starting Pitching"] > 0
    assert dict(scored_partial.result.signals)["Starting Pitching"] <= 0.65


def test_dynamic_starter_era_center_changes_center_without_changing_direction():
    game = _known_game("Away", "Home", away_rpg=5.0, home_rpg=5.0)
    game.away.pitcher.era = 4.20
    game.home.pitcher.era = 5.20
    game.away.pitcher.league_era = 4.90
    game.home.pitcher.league_era = 4.90

    scored = _score([game])[0]

    assert dict(scored.result.signals)["Starting Pitching"] > 0
    assert scored.result.play == "Away"


def test_short_rest_reduces_starter_context_without_changing_base_quality_inputs():
    normal = _known_game("Normal", "Opponent", away_rpg=5.0, home_rpg=5.0)
    short = _known_game("Short", "Opponent", away_rpg=5.0, home_rpg=5.0)

    for game in (normal, short):
        game.away.pitcher.era = 3.20
        game.away.pitcher.whip = 1.10
        game.home.pitcher.era = 4.50
        game.home.pitcher.whip = 1.40

    normal.away.pitcher.days_rest = 5
    short.away.pitcher.days_rest = 3

    normal_scored, short_scored = _score([normal, short])

    assert (
        dict(short_scored.result.signals)["Starting Pitching"]
        < dict(normal_scored.result.signals)["Starting Pitching"]
    )


def test_missing_starter_context_is_neutral():
    missing = _known_game("Missing Context", "Opponent", away_rpg=5.0, home_rpg=5.0)
    normal = _known_game("Normal Context", "Opponent", away_rpg=5.0, home_rpg=5.0)

    normal.away.pitcher.days_rest = 5
    missing.away.pitcher.days_rest = None

    missing_scored, normal_scored = _score([missing, normal])

    assert (
        dict(missing_scored.result.signals)["Starting Pitching"]
        == dict(normal_scored.result.signals)["Starting Pitching"]
    )


def test_role_mismatch_reduces_reliability_without_erasing_listed_starter():
    game = _known_game("Opener", "Opponent", away_rpg=5.0, home_rpg=5.0)
    game.game_url = "game"
    game.away.pitcher.role_context = "no_prior_starts"

    finalized = KBOModel().finalize(_score([game]))[0]

    assert finalized.result.play in {"Opener", "Opponent", None}
    assert finalized.result.confidence == 94.0
    assert finalized.result.confidence_breakdown["starter_role"] == -6.0


def test_kbo_score_remains_bounded_and_strong_play_is_reachable():
    game = _known_game("Ceiling", "Floor", away_rpg=5.63, home_rpg=4.23)
    game.away.offense.league_runs_per_game = 4.93
    game.home.offense.league_runs_per_game = 4.93
    game.away.pitcher.era = 2.50
    game.away.pitcher.whip = 1.00
    game.away.pitcher.k_rate = 9.5
    game.away.pitcher.bb_rate = 1.5
    game.away.pitcher.hr9 = 0.3
    game.away.pitcher.ip = 100.0
    game.home.pitcher.era = 6.50
    game.home.pitcher.whip = 1.90
    game.home.pitcher.k_rate = 3.5
    game.home.pitcher.bb_rate = 5.5
    game.home.pitcher.hr9 = 2.0
    game.home.pitcher.ip = 100.0
    game.away.bullpen.era = 2.85
    game.home.bullpen.era = 4.85
    game.away.form.recent_runs_per_game = 8.43
    game.home.form.recent_runs_per_game = 1.43

    finalized = KBOModel().finalize(_score([game]))[0]

    assert finalized.result.model_strength == 58.0
    assert finalized.result.recommendation == "🔥 STRONG PLAY"


def test_dynamic_offense_baseline_replaces_static_center():
    game = _known_game("Away", "Home", away_rpg=5.2, home_rpg=4.8)
    game.away.offense.league_runs_per_game = 5.0
    game.home.offense.league_runs_per_game = 5.0

    scored = _score([game])[0]

    assert dict(scored.result.signals)["Offense"] == 0.09


def test_static_offense_fallback_reduces_reliability_without_changing_strength():
    game = _known_game("Away", "Home", away_rpg=5.2, home_rpg=4.8)
    game.game_url = "game"
    game.away.offense.offense_source = "STATIC_FALLBACK"
    game.home.offense.offense_source = "STATIC_FALLBACK"

    scored = _score([game])[0]
    finalized = KBOModel().finalize([scored])[0]

    assert finalized.result.model_strength > 50.0
    assert finalized.result.confidence == 90.0


def test_missing_active_bullpen_reduces_reliability_without_changing_strength():
    game = _known_game("Away", "Home", away_rpg=5.2, home_rpg=4.8)
    game.game_url = "game"
    game.away.bullpen.era = None
    game.home.bullpen.era = None

    scored = _score([game])[0]
    finalized = KBOModel().finalize([scored])[0]

    assert dict(finalized.result.signals)["Bullpen"] == 0.0
    assert finalized.result.model_strength > 50.0
    assert finalized.result.confidence == 88.0


def test_missing_bullpen_league_baseline_is_neutral_and_reduces_reliability():
    game = _known_game("Away", "Home", away_rpg=5.2, home_rpg=4.8)
    game.game_url = "game"
    game.away.bullpen.league_era = None
    game.home.bullpen.league_era = None

    scored = _score([game])[0]
    finalized = KBOModel().finalize([scored])[0]

    assert dict(finalized.result.signals)["Bullpen"] == 0.0
    assert finalized.result.model_strength > 50.0
    assert finalized.result.confidence == 88.0


def test_missing_recent_form_is_neutral_and_reduces_reliability():
    game = _known_game("Away", "Home", away_rpg=5.2, home_rpg=4.8)
    game.game_url = "game"
    game.away.form.recent_runs_per_game = None
    game.home.form.recent_runs_per_game = None

    scored = _score([game])[0]
    finalized = KBOModel().finalize([scored])[0]

    assert dict(finalized.result.signals)["Recent Form"] == 0.0
    assert finalized.result.model_strength > 50.0
    assert finalized.result.confidence == 94.0


def test_bullpen_changes_strength_without_changing_starter_or_offense():
    strong = _known_game("Strong Bullpen", "Weak Bullpen", away_rpg=5.0, home_rpg=5.0)
    weak = _known_game("Weak Bullpen", "Strong Bullpen", away_rpg=5.0, home_rpg=5.0)
    for game in (strong, weak):
        game.away.pitcher.era = 4.00
        game.home.pitcher.era = 4.00
        game.away.pitcher.whip = 1.30
        game.home.pitcher.whip = 1.30
        game.away.bullpen.league_era = 3.85
        game.home.bullpen.league_era = 3.85

    strong.away.bullpen.era = 2.85
    strong.home.bullpen.era = 4.85
    weak.away.bullpen.era = 4.85
    weak.home.bullpen.era = 2.85

    away_edge, home_edge = _score([strong, weak])

    assert dict(away_edge.result.signals)["Bullpen"] > 0
    assert away_edge.result.play == "Strong Bullpen"
    assert dict(home_edge.result.signals)["Bullpen"] < 0
    assert home_edge.result.play == "Strong Bullpen"


def test_offense_strength_does_not_affect_reliability():
    strong = _known_game("Strong", "Weak", away_rpg=5.6, home_rpg=4.2)
    weak = _known_game("Weak", "Strong", away_rpg=4.2, home_rpg=5.6)
    for game in (strong, weak):
        game.away.offense.offense_source = "LIVE_TEAM_SPLITS"
        game.home.offense.offense_source = "LIVE_TEAM_SPLITS"

    scored = _score([strong, weak])
    finalized = KBOModel().finalize(scored)

    assert finalized[0].result.model_strength != finalized[1].result.model_strength
    assert finalized[0].result.confidence == finalized[1].result.confidence
