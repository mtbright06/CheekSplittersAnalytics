from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.pages import nhl_prop_trends_page as page
from engine.nhl.models import NHLPlayer
from engine.nhl.prop_trends import (
    LAST_10,
    LAST_20,
    LAST_5,
    SEASON,
    NHLPropTrendSummary,
    SAVES,
    SHOTS_ON_GOAL,
)
from engine.nhl.prop_trend_service import NHLPropTrendRow


def test_nhl_prop_trends_all_teams_option_expands_to_all_clubs():
    selected = page._selected_team_abbreviations(
        [page.ALL_TEAMS],
        ["ANA", "BOS", "EDM"],
        ["ANA", "BOS"],
    )

    assert selected == ("ANA", "BOS")


def test_nhl_prop_trends_all_teams_uses_current_slate_not_full_league():
    selected = page._selected_team_abbreviations(
        [page.ALL_TEAMS],
        ["ANA", "BOS", "EDM", "NYR"],
        ["EDM", "NYR"],
    )

    assert selected == ("EDM", "NYR")


def test_nhl_prop_trends_all_teams_no_slate_is_empty_not_league_wide():
    selected = page._selected_team_abbreviations(
        [page.ALL_TEAMS],
        ["ANA", "BOS", "EDM", "NYR"],
        [],
    )

    assert selected == ()


def test_nhl_prop_trends_all_teams_is_available_but_not_default(monkeypatch):
    teams = [
        type("Team", (), {"abbreviation": "ANA"})(),
        type("Team", (), {"abbreviation": "BOS"})(),
    ]
    fake_streamlit = _FakeStreamlit(
        market_label="Shots on Goal",
        selected_line=2.5,
    )
    service = _FakeReadService([
        _row(player_id=1, name="Alpha", market=SHOTS_ON_GOAL)
    ])

    monkeypatch.setattr(page, "st", fake_streamlit)
    monkeypatch.setattr(page, "_load_available_teams", lambda: teams)
    monkeypatch.setattr(page, "_load_current_slate_team_abbreviations", lambda: ("ANA", "BOS"))
    monkeypatch.setattr(page, "render_compact_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(page, "_load_players_for_teams", lambda *args, **kwargs: page.PlayerUniverse(
        players=(_player(1, position="C", team="ANA"),),
    ))
    monkeypatch.setattr(page, "render_data_table", lambda *args, **kwargs: None)

    page.render_nhl_prop_trends(read_service=service)

    assert fake_streamlit.multiselect_calls[0]["options"] == [
        page.ALL_TEAMS,
        "ANA",
        "BOS",
    ]
    assert fake_streamlit.multiselect_calls[0]["default"] == ["ANA"]


def test_nhl_prop_trends_player_search_is_case_insensitive_and_partial():
    rows = [
        _row(player_id=1, name="Leo Carlsson", market=SHOTS_ON_GOAL),
        _row(player_id=2, name="Troy Terry", market=SHOTS_ON_GOAL),
    ]

    filtered = page._filter_rows_by_player_search(rows, "carl")

    assert [row.player_name for row in filtered] == ["Leo Carlsson"]


def test_nhl_prop_trends_empty_player_search_returns_all_rows():
    rows = [
        _row(player_id=1, name="Leo Carlsson", market=SHOTS_ON_GOAL),
        _row(player_id=2, name="Troy Terry", market=SHOTS_ON_GOAL),
    ]

    assert page._filter_rows_by_player_search(rows, "") == rows


def test_nhl_prop_trends_empty_search_result_is_safe(monkeypatch):
    fake_streamlit = _FakeStreamlit(
        market_label="Shots on Goal",
        selected_line=2.5,
        search="missing",
    )
    service = _FakeReadService([
        _row(player_id=1, name="Alpha", market=SHOTS_ON_GOAL)
    ])

    monkeypatch.setattr(page, "st", fake_streamlit)
    monkeypatch.setattr(page, "render_compact_header", lambda *args, **kwargs: None)

    page.render_nhl_prop_trends(
        read_service=service,
        players=[_player(1, position="C")],
    )

    assert fake_streamlit.info_messages == [
        "No NHL prop trend rows match the current filters."
    ]


def test_nhl_prop_trends_dataframe_maps_windows_and_missing_rates():
    frame = page._rows_to_dataframe([
        _row(
            player_id=2,
            name="Beta",
            market=SHOTS_ON_GOAL,
            l5=None,
            l10=0.2,
            l20=0.3,
            season=0.4,
        ),
        _row(
            player_id=1,
            name="Alpha",
            market=SHOTS_ON_GOAL,
            l5=0.8,
            l10=0.7,
            l20=0.6,
            season=0.5,
        ),
    ])

    assert list(frame["Player"]) == ["Alpha", "Beta"]
    assert frame.iloc[0]["L5"] == "80%"
    assert frame.iloc[0]["L10"] == "70%"
    assert frame.iloc[1]["L5"] == "N/A"
    assert frame.iloc[1]["Season"] == "40%"


def test_nhl_prop_trends_dataframe_sorts_by_l10_l5_season_then_name():
    frame = page._rows_to_dataframe([
        _row(
            player_id=4,
            name="Delta",
            market=SHOTS_ON_GOAL,
            l5=0.95,
            l10=None,
            season=0.95,
        ),
        _row(
            player_id=3,
            name="Charlie",
            market=SHOTS_ON_GOAL,
            l5=0.6,
            l10=0.7,
            season=0.9,
        ),
        _row(
            player_id=2,
            name="Bravo",
            market=SHOTS_ON_GOAL,
            l5=0.8,
            l10=0.7,
            season=0.4,
        ),
        _row(
            player_id=1,
            name="Alpha",
            market=SHOTS_ON_GOAL,
            l5=0.8,
            l10=0.7,
            season=0.4,
        ),
    ])

    assert list(frame["Player"]) == [
        "Alpha",
        "Bravo",
        "Charlie",
        "Delta",
    ]
    assert frame.iloc[-1]["L10"] == "N/A"


def test_nhl_prop_trends_page_renders_supplied_sog_rows(monkeypatch):
    fake_streamlit = _FakeStreamlit(
        market_label="Shots on Goal",
        selected_line=2.5,
    )
    service = _FakeReadService([
        _row(player_id=1, name="Alpha", market=SHOTS_ON_GOAL)
    ])
    rendered = {}

    monkeypatch.setattr(page, "st", fake_streamlit)
    monkeypatch.setattr(page, "render_compact_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        page,
        "render_data_table",
        lambda frame, **kwargs: rendered.setdefault("frame", frame),
    )

    page.render_nhl_prop_trends(
        read_service=service,
        players=[_player(1, position="C")],
    )

    assert service.calls == [
        {
            "players": [1],
            "markets": [SHOTS_ON_GOAL],
            "selected_lines": {SHOTS_ON_GOAL: 2.5},
            "season_id": page.current_nhl_season_id(),
            "game_type": "REG",
        }
    ]
    assert rendered["frame"].data.iloc[0]["Player"] == "Alpha"


def test_nhl_prop_trends_page_uses_cached_default_read_service(monkeypatch):
    fake_streamlit = _FakeStreamlit(
        market_label="Shots on Goal",
        selected_line=2.5,
    )
    service = _FakeReadService([
        _row(player_id=1, name="Alpha", market=SHOTS_ON_GOAL)
    ])
    rendered = {}

    monkeypatch.setattr(page, "st", fake_streamlit)
    monkeypatch.setattr(page, "render_compact_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(page, "_get_prop_trend_read_service", lambda: service)
    monkeypatch.setattr(
        page,
        "render_data_table",
        lambda frame, **kwargs: rendered.setdefault("frame", frame),
    )

    page.render_nhl_prop_trends(players=[_player(1, position="C")])

    assert service.calls
    assert rendered["frame"].data.iloc[0]["Player"] == "Alpha"


def test_nhl_prop_trends_saves_market_uses_goalie_universe(monkeypatch):
    team = type("Team", (), {"abbreviation": "EDM"})()
    roster_service = _RosterService([
        _player(1, position="C"),
        _player(30, position="G"),
    ])

    page._load_players_for_teams.clear()
    monkeypatch.setattr(page, "_load_available_teams", lambda: [team])
    monkeypatch.setattr(page, "NHLRosterService", lambda: roster_service)

    universe = page._load_players_for_teams(("EDM",), saves_market=True)

    assert [player.source_player_id for player in universe.players] == [30]


def test_nhl_prop_trends_skater_market_excludes_goalies(monkeypatch):
    team = type("Team", (), {"abbreviation": "EDM"})()
    roster_service = _RosterService([
        _player(1, position="C"),
        _player(30, position="G"),
    ])

    page._load_players_for_teams.clear()
    monkeypatch.setattr(page, "_load_available_teams", lambda: [team])
    monkeypatch.setattr(page, "NHLRosterService", lambda: roster_service)

    universe = page._load_players_for_teams(("EDM",), saves_market=False)

    assert [player.source_player_id for player in universe.players] == [1]


def test_nhl_prop_trends_all_teams_loads_multiple_clubs(monkeypatch):
    teams = [
        type("Team", (), {"abbreviation": "ANA"})(),
        type("Team", (), {"abbreviation": "BOS"})(),
    ]
    roster_service = _RosterService({
        "ANA": [_player(1, position="C", team="ANA")],
        "BOS": [_player(2, position="LW", team="BOS")],
    })

    page._load_players_for_teams.clear()
    monkeypatch.setattr(page, "_load_available_teams", lambda: teams)
    monkeypatch.setattr(page, "NHLRosterService", lambda: roster_service)

    universe = page._load_players_for_teams(("ANA", "BOS"), saves_market=False)

    assert [player.source_player_id for player in universe.players] == [1, 2]


def test_nhl_prop_trends_team_and_search_filters_compose():
    rows = [
        _row(player_id=1, name="Ana Match", market=SHOTS_ON_GOAL, team="ANA"),
        _row(player_id=2, name="Boston Match", market=SHOTS_ON_GOAL, team="BOS"),
    ]

    filtered = page._filter_rows_by_player_search(rows[:1], "match")

    assert [row.team_abbreviation for row in filtered] == ["ANA"]


def test_nhl_prop_trends_concerns_render_without_crashing():
    frame = page._rows_to_dataframe([
        _row(
            player_id=1,
            name="Concerned",
            market=SHOTS_ON_GOAL,
            concerns=("no_game_logs",),
        )
    ])

    assert frame.iloc[0]["Concern"] == "!"
    assert frame.iloc[0]["Season"] == "60%"


def test_nhl_prop_trends_concern_indicator_blank_when_clean():
    frame = page._rows_to_dataframe([
        _row(player_id=1, name="Clean", market=SHOTS_ON_GOAL)
    ])

    assert frame.iloc[0]["Concern"] == ""


def test_nhl_prop_trends_concern_details_preserve_full_text():
    rows = [
        _row(
            player_id=1,
            name="Concerned",
            market=SHOTS_ON_GOAL,
            concerns=("no_game_logs",),
        )
    ]

    assert page._concern_details(rows) == ["Concerned: no_game_logs"]


def test_nhl_prop_trends_missing_hit_rate_style_is_not_zero():
    assert page._format_hit_rate(None) == "N/A"
    assert page._sort_hit_rate(None) < 0


def test_nhl_prop_trends_page_does_not_duplicate_trend_math():
    source = Path("dashboard/pages/nhl_prop_trends_page.py").read_text()

    assert "summarize_prop_trend" not in source
    assert "summarize_prop_windows" not in source
    assert "summarize_prop_lines" not in source
    assert "NHLPropTrendReadService" in source


def test_props_route_uses_nhl_prop_trends_page():
    source = Path("dashboard/app.py").read_text()

    assert "from pages.nhl_prop_trends_page import render_nhl_prop_trends" in source
    assert 'elif page == "Props":' in source
    assert "render_nhl_prop_trends()" in source


def test_props_route_does_not_load_combined_dashboard_card_before_dispatch():
    source = Path("dashboard/app.py").read_text()
    props_branch = source.split('elif page == "Props":', 1)[0]

    assert "dashboard_card = combined_dashboard_card()" in source
    assert "dashboard_card = combined_dashboard_card()" not in source.split(
        "def render_page():",
        1,
    )[0]
    assert props_branch.count("combined_dashboard_card()") == 1


def _row(
    *,
    player_id,
    name,
    market,
    l5=0.8,
    l10=0.7,
    l20=0.65,
    season=0.6,
    concerns=(),
    team="EDM",
):
    return NHLPropTrendRow(
        player_id=player_id,
        player_name=name,
        team_abbreviation=team,
        position="C" if market != SAVES else "G",
        market=market,
        selected_line=2.5,
        last_5=_summary(player_id, market, LAST_5, l5, 5),
        last_10=_summary(player_id, market, LAST_10, l10, 10),
        last_20=_summary(player_id, market, LAST_20, l20, 20),
        season=_summary(player_id, market, SEASON, season, 76),
        concerns=concerns,
    )


def _summary(player_id, market, window, hit_rate, games):
    return NHLPropTrendSummary(
        player_id=player_id,
        market=market,
        line=2.5,
        window=window,
        games_considered=games,
        hits=0,
        misses=0,
        pushes=0,
        hit_rate=hit_rate,
        game_results=(),
    )


def _player(player_id, *, position, team="EDM"):
    return NHLPlayer(
        source_player_id=player_id,
        name=f"Player {player_id}",
        team_abbreviation=team,
        position=position,
        position_code=position,
    )


class _FakeReadService:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def build_rows(self, **kwargs):
        self.calls.append({
            "players": [player.source_player_id for player in kwargs["players"]],
            "markets": kwargs["markets"],
            "selected_lines": kwargs["selected_lines"],
            "season_id": kwargs["season_id"],
            "game_type": kwargs["game_type"],
        })
        return self.rows


class _RosterService:
    def __init__(self, players):
        self.players = players

    def load_team_roster(self, team):
        if isinstance(self.players, dict):
            return list(self.players.get(team.abbreviation, []))
        return list(self.players)


@dataclass
class _Column:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _ColumnConfig:
    @staticmethod
    def TextColumn(label):
        return label


class _FakeStreamlit:
    column_config = _ColumnConfig()

    def __init__(
        self,
        *,
        market_label,
        selected_line,
        search="",
    ):
        self.market_label = market_label
        self.selected_line = selected_line
        self.search = search
        self.info_messages = []
        self.multiselect_calls = []

    def columns(self, spec):
        return [_Column() for _ in spec]

    def selectbox(self, label, options, index=0, key=None):
        return self.market_label

    def number_input(self, *args, **kwargs):
        return self.selected_line

    def multiselect(self, *args, **kwargs):
        self.multiselect_calls.append({
            "options": list(args[1] if len(args) > 1 else kwargs.get("options", [])),
            "default": list(kwargs.get("default", [])),
        })
        return ["EDM"]

    def text_input(self, *args, **kwargs):
        return self.search

    def info(self, message):
        self.info_messages.append(message)

    def caption(self, message):
        pass

    def expander(self, *args, **kwargs):
        return _Column()
