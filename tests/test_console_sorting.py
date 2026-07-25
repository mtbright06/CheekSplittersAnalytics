from types import SimpleNamespace

from reports.console import ConsoleReport


def test_kbo_console_sorts_no_edge_games_by_model_probability():
    games = [
        SimpleNamespace(result=SimpleNamespace(edge=None, model_probability=52.0)),
        SimpleNamespace(result=SimpleNamespace(edge=None, model_probability=58.0)),
        SimpleNamespace(result=SimpleNamespace(edge=None, model_probability=55.0)),
    ]

    ordered = sorted(games, key=ConsoleReport._sort_value, reverse=True)

    assert [game.result.model_probability for game in ordered] == [58.0, 55.0, 52.0]


def test_console_retains_numeric_edge_as_the_sort_value():
    game = SimpleNamespace(result=SimpleNamespace(edge=4.0, model_probability=59.0))

    assert ConsoleReport._sort_value(game) == 4.0


def test_kbo_model_only_recommendations_receive_matching_star_ratings():
    report = ConsoleReport()

    assert report._play_rating(None, "🔥 STRONG PLAY") == "★★★★☆ STRONG PLAY"
    assert report._play_rating(None, "✅ PLAYABLE") == "★★★☆☆ PLAYABLE"
    assert report._play_rating(None, "👀 LEAN") == "★★☆☆☆ LEAN"
    assert report._play_rating(None, "❌ NO PLAY") == "★☆☆☆☆ PASS"
