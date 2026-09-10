from __future__ import annotations

from datetime import date, datetime, UTC
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pages import nfl_prop_trends_page as page
from engine.nfl.models import NFLGame, NFLPlayer, NFLRosterEntry, NFLTeam
from engine.nfl.prop_trend_service import NFLPropTrendRow
from engine.nfl.prop_trends import (
    ANYTIME_TOUCHDOWN,
    PASSING_YARDS,
    RECEIVING_YARDS,
    NFLPropTrendSummary,
)


def test_nfl_props_route_is_registered_without_replacing_nhl_props():
    app = (ROOT / "dashboard" / "app.py").read_text()
    navigation = (ROOT / "dashboard" / "shell" / "navigation.py").read_text()
    assert 'page == "Props"' in app
    assert 'page == "NFL Props"' in app
    assert 'NavigationItem("NFL Props"' in navigation


def test_matchup_options_and_filtering_are_slate_specific():
    games = (_game("DAL", "PHI", "g1"), _game("KC", "LAC", "g2"))
    options = page._matchup_options(games)
    assert [option.label for option in options] == [
        page.ALL_GAMES, "DAL @ PHI", "KC @ LAC"
    ]
    assert options[0].team_abbreviations == ("DAL", "PHI", "KC", "LAC")
    assert page._games_for_matchup(games, options[2]) == (games[1],)


def test_selected_date_is_passed_to_regular_season_schedule_provider(monkeypatch):
    calls = []

    class Provider:
        def load_schedule(self, **kwargs):
            calls.append(kwargs)
            return [_game("DAL", "PHI", "g1")]

    page._load_slate_games.clear()
    monkeypatch.setattr(page, "_get_schedule_provider", lambda: Provider())
    assert page._load_slate_games("2026-09-10")[0].source_game_id == "g1"
    assert calls == [{"target_date": "2026-09-10", "game_type": "REG"}]


def test_roster_universe_uses_exact_season_week_and_selected_teams(monkeypatch):
    calls = []

    class Provider:
        def load_weekly_roster(self, **kwargs):
            calls.append(kwargs)
            return [_entry("QB"), NFLRosterEntry(
                player_id="other",
                team_abbreviation="DEN",
                season=2026,
                week=1,
                player=NFLPlayer("other", "Other", position="QB"),
                position="QB",
            )]

    page._load_roster_universe.clear()
    monkeypatch.setattr(page, "_get_roster_provider", lambda: Provider())
    universe = page._load_roster_universe(2026, 1, ("KC", "LAC"))
    assert calls == [{"season": 2026, "week": 1}]
    assert [entry.team_abbreviation for entry in universe.entries] == ["KC"]


def test_market_position_filters_exclude_irrelevant_players():
    entries = tuple(_entry(position) for position in ("QB", "RB", "WR", "TE", "K"))
    assert [entry.position for entry in page._eligible_roster_entries(entries, PASSING_YARDS)] == ["QB"]
    assert [entry.position for entry in page._eligible_roster_entries(entries, RECEIVING_YARDS)] == ["RB", "WR", "TE"]
    assert [entry.position for entry in page._eligible_roster_entries(entries, ANYTIME_TOUCHDOWN)] == ["QB", "RB", "WR", "TE"]


def test_player_search_is_case_insensitive_and_partial():
    rows = (_row("Patrick Mahomes"), _row("Travis Kelce", player_id="02"))
    assert page._filter_rows_by_player_search(rows, "MAHO") == (rows[0],)
    assert page._filter_rows_by_player_search(rows, "") == rows


def test_board_maps_opponent_windows_and_missing_season_to_na():
    frame = page._rows_to_dataframe((_row("Alpha", season_rate=None),), {"KC": "LAC"})
    assert frame.iloc[0]["Opponent"] == "LAC"
    assert frame.iloc[0]["L5"] == "80%"
    assert frame.iloc[0]["Season"] == "N/A"
    assert frame.iloc[0]["L10 GP"] == 10


def test_board_uses_research_threshold_terminology():
    source = (ROOT / "dashboard" / "pages" / "nfl_prop_trends_page.py").read_text()
    frame = page._rows_to_dataframe((_row("Alpha"),), {"KC": "LAC"})

    assert '"Threshold"' in source
    assert '"Prop Line"' not in source
    assert '"Detail Line"' not in source
    assert "Threshold" in frame.columns
    assert "Line" not in frame.columns


def test_market_formatting_and_default_mode():
    assert page.PROP_MODES == ('Market Lines', 'Research Threshold')
    assert page._price(105) == '+105'
    assert page._price(-110) == '-110'
    assert page._price(None) == 'N/A'
    from types import SimpleNamespace
    assert page._line(SimpleNamespace(line=249.5)) == '249.5'
    assert page._line(SimpleNamespace(line=None)) == 'Anytime (Yes)'


def test_streamlit_market_board_detail_search_and_research_mode(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from tests import test_nfl_prop_markets as fixtures
    from engine.nfl.prop_trend_service import NFLPropTrendReadService
    from engine.nfl.prop_trends import RUSHING_YARDS
    history = fixtures.History()
    service = NFLPropTrendReadService(game_log_provider=history)
    requests = []

    class Response:
        status_code = 200
        def __init__(self, value): self.value = value
        def json(self): return self.value

    def fetch(url, **kwargs):
        requests.append(url)
        return Response([fixtures.payload()] if url.endswith('/events') else fixtures.payload())

    provider = page.NFLPropMarketProvider(api_key='test', fetcher=fetch, clock=lambda: fixtures.NOW)

    monkeypatch.setattr(page, '_load_slate_games', lambda *_: (fixtures.game(),))
    monkeypatch.setattr(page, '_load_roster_universe', lambda *_: page.RosterUniverse(tuple(fixtures.entries())))
    monkeypatch.setattr(page, '_get_market_provider', lambda: provider)
    monkeypatch.setattr(page, '_get_prop_trend_read_service', lambda: service)
    at = AppTest.from_string('from pages.nfl_prop_trends_page import render_nfl_prop_trends\nrender_nfl_prop_trends()')
    at.run()
    assert not at.exception
    assert at.radio(key='nfl_props_mode').value == 'Market Lines'
    at.selectbox(key='nfl_prop_trends_market').select('Rushing Yards').run()
    assert not at.exception
    frame = at.dataframe[0].value
    assert list(frame['Actual Line']) == ['27.5', '68.5']
    assert list(frame['L10']) == ['100%', '0%']
    assert list(frame['Season']) == ['N/A', 'N/A']
    calls = history.calls
    http_calls = len(requests)
    at.text_input(key='nfl_prop_trends_player_search').set_value('Beta').run()
    assert not at.exception
    assert list(at.dataframe[0].value['Player']) == ['Beta Runner']
    assert at.metric[0].value == '68.5'
    at.number_input(key='nfl_explore_2026_01_NE_SEA_02_RUSHING_YARDS').set_value(40.5).run()
    assert not at.exception
    assert at.metric[0].value == '68.5'
    assert history.calls == calls
    assert len(requests) == http_calls
    at.radio(key='nfl_props_mode').set_value('Research Threshold').run()
    assert not at.exception
    assert at.number_input(key='nfl_prop_trends_threshold_RUSHING_YARDS').label == 'Threshold'


def test_multi_game_controls_preserve_subset_clear_and_date_state(monkeypatch):
    from dataclasses import replace
    from streamlit.testing.v1 import AppTest
    from tests import test_nfl_prop_markets as fixtures

    games = tuple(replace(
        fixtures.game(), source_game_id=f"game-{i}",
        away_team=replace(fixtures.game().away_team, abbreviation=f"A{i}"),
    ) for i in range(3))
    represented = []
    roster_calls = []
    monkeypatch.setattr(page, '_load_slate_games', lambda *_: games)
    monkeypatch.setattr(page, '_load_roster_universe', lambda *args: (
        roster_calls.append(args) or page.RosterUniverse(())
    ))
    monkeypatch.setattr(page, '_get_prop_trend_read_service', lambda: object())
    monkeypatch.setattr(page, '_render_market_board', lambda games, *args, **kwargs: represented.append(
        (tuple(game.source_game_id for game in games), kwargs['refresh'])
    ))
    at = AppTest.from_string('from pages.nfl_prop_trends_page import render_nfl_prop_trends\nrender_nfl_prop_trends()').run()
    assert not at.exception
    assert represented[-1] == (('game-0', 'game-1', 'game-2'), False)
    at.multiselect(key='nfl_props_selected_games').set_value(['game-0', 'game-2']).run()
    assert represented[-1][0] == ('game-0', 'game-2')
    assert at.get('popover')[0].proto.popover.label == 'Games 2/3'
    at.text_input(key='nfl_prop_trends_player_search').set_value('Runner').run()
    at.selectbox(key='nfl_prop_trends_market').select('Rushing Yards').run()
    assert represented[-1][0] == ('game-0', 'game-2')
    at.multiselect(key='nfl_props_selected_games').set_value(['game-1']).run()
    assert represented[-1][0] == ('game-1',)
    at.button(key='nfl_market_refresh').click().run()
    assert represented[-1] == (('game-1',), True)
    calls = len(represented), len(roster_calls)
    at.button(key='nfl_props_games_clear').click().run()
    at.run()
    assert (len(represented), len(roster_calls)) == calls
    assert at.multiselect(key='nfl_props_selected_games').value == []
    assert at.get('popover')[0].proto.popover.label == 'Games 0/3'
    assert 'Select one or more games' in at.info[0].value
    at.button(key='nfl_props_games_all').click().run()
    assert represented[-1][0] == ('game-0', 'game-1', 'game-2')
    at.button(key='nfl_props_games_clear').click().run()
    at.date_input(key='nfl_prop_trends_slate_date').set_value(date(2026, 9, 14)).run()
    assert represented[-1][0] == ('game-0', 'game-1', 'game-2')
    at.radio(key='nfl_props_mode').set_value('Research Threshold').run()
    assert not at.exception
    assert at.multiselect(key='nfl_props_selected_games').value == ['game-0', 'game-1', 'game-2']


def test_nfl_route_smoke_never_executes_other_sport_loaders(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import card_loader
    def forbidden(*args, **kwargs): raise AssertionError('unrelated sport executed')
    monkeypatch.setattr(card_loader, 'combined_dashboard_card', forbidden)
    monkeypatch.setattr(card_loader, 'load_sport_card', forbidden)
    monkeypatch.setattr(page, '_load_slate_games', lambda *_: ())
    monkeypatch.setattr(page, '_load_roster_universe', forbidden)
    at = AppTest.from_file(str(ROOT / 'dashboard/app.py'))
    at.session_state['page'] = 'NFL Props'
    at.run()
    assert not at.exception
    assert any('No NFL regular-season games' in info.value for info in at.info)


def test_board_sort_is_l10_l5_season_then_player_with_missing_last():
    rows = (
        _row("Zulu", player_id="1", l10=None, l5=1.0),
        _row("Bravo", player_id="2", l10=0.8, l5=0.7, season_rate=0.5),
        _row("Alpha", player_id="3", l10=0.8, l5=0.7, season_rate=0.5),
    )
    frame = page._rows_to_dataframe(rows, {"KC": "LAC"})
    assert list(frame["Player"]) == ["Alpha", "Bravo", "Zulu"]


def test_game_detail_uses_engine_result_fields():
    result = type("Result", (), {
        "game_date": date(2025, 12, 1),
        "opponent_abbreviation": "DEN",
        "home_away": "AWAY",
        "actual_value": 276,
        "result": "HIT",
    })()
    frame = page._game_results_to_dataframe((result,))
    assert list(frame.columns) == ["Date", "Opponent", "Home/Away", "Actual", "Result"]
    assert frame.iloc[0].to_dict()["Result"] == "HIT"


def test_page_delegates_trend_math_and_has_no_cross_sport_imports():
    source = (ROOT / "dashboard" / "pages" / "nfl_prop_trends_page.py").read_text()
    assert "summarize_prop" not in source
    assert "build_player_detail(" in source
    assert "engine.nhl" not in source
    assert "engine.kbo" not in source
    assert "engine.mlb" not in source


def test_no_game_branch_precedes_roster_and_trend_loading():
    source = (ROOT / "dashboard" / "pages" / "nfl_prop_trends_page.py").read_text()
    no_games = source.index('if not slate_games:')
    roster = source.index('_load_roster_universe(', no_games)
    trend = source.index('service.build_rows(', no_games)
    assert no_games < roster < trend


def _team(abbreviation: str) -> NFLTeam:
    return NFLTeam(abbreviation, abbreviation, abbreviation.lower())


def _game(away: str, home: str, game_id: str) -> NFLGame:
    return NFLGame(
        source_game_id=game_id,
        season=2026,
        week=1,
        game_type="REG",
        game_date=date(2026, 9, 10),
        start_time=datetime(2026, 9, 10, 20, tzinfo=UTC),
        away_team=_team(away),
        home_team=_team(home),
        game_status="SCHEDULED",
    )


def _entry(position: str) -> NFLRosterEntry:
    player = NFLPlayer(f"id-{position}", f"{position} Player", position=position)
    return NFLRosterEntry(
        player_id=player.gsis_id,
        team_abbreviation="KC",
        season=2026,
        week=1,
        game_type="REG",
        roster_status="ACT",
        position=position,
        player=player,
    )


def _summary(rate: float | None, games: int = 5) -> NFLPropTrendSummary:
    return NFLPropTrendSummary(
        player_id="01",
        market=PASSING_YARDS,
        line=249.5,
        window="LAST_5",
        selected_season=2026,
        games_considered=games if rate is not None else 0,
        hits=0,
        misses=0,
        pushes=0,
        hit_rate=rate,
        game_results=(),
    )


def _row(
    name: str,
    *,
    player_id: str = "01",
    l10: float | None = 0.8,
    l5: float | None = 0.8,
    season_rate: float | None = None,
) -> NFLPropTrendRow:
    return NFLPropTrendRow(
        player_id=player_id,
        player_name=name,
        team_abbreviation="KC",
        position="QB",
        market=PASSING_YARDS,
        selected_line=249.5,
        last_5=_summary(l5),
        last_10=_summary(l10, 10),
        last_20=_summary(0.6, 20),
        season=_summary(season_rate),
        previous_season=_summary(0.55, 17),
        selected_season=2026,
    )
