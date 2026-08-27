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
    assert rendered["frame"].iloc[0]["Player"] == "Alpha"


def test_nhl_prop_trends_saves_market_uses_goalie_universe(monkeypatch):
    team = type("Team", (), {"abbreviation": "EDM"})()
    roster_service = _RosterService([
        _player(1, position="C"),
        _player(30, position="G"),
    ])

    page._load_players_for_teams.clear()
    monkeypatch.setattr(page, "_load_available_teams", lambda: [team])
    monkeypatch.setattr(page, "NHLRosterService", lambda: roster_service)

    players = page._load_players_for_teams(("EDM",), saves_market=True)

    assert [player.source_player_id for player in players] == [30]


def test_nhl_prop_trends_skater_market_excludes_goalies(monkeypatch):
    team = type("Team", (), {"abbreviation": "EDM"})()
    roster_service = _RosterService([
        _player(1, position="C"),
        _player(30, position="G"),
    ])

    page._load_players_for_teams.clear()
    monkeypatch.setattr(page, "_load_available_teams", lambda: [team])
    monkeypatch.setattr(page, "NHLRosterService", lambda: roster_service)

    players = page._load_players_for_teams(("EDM",), saves_market=False)

    assert [player.source_player_id for player in players] == [1]


def test_nhl_prop_trends_concerns_render_without_crashing():
    frame = page._rows_to_dataframe([
        _row(
            player_id=1,
            name="Concerned",
            market=SHOTS_ON_GOAL,
            concerns=("no_game_logs",),
        )
    ])

    assert frame.iloc[0]["Concerns"] == "no_game_logs"
    assert frame.iloc[0]["Season"] == "60%"


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
):
    return NHLPropTrendRow(
        player_id=player_id,
        player_name=name,
        team_abbreviation="EDM",
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


def _player(player_id, *, position):
    return NHLPlayer(
        source_player_id=player_id,
        name=f"Player {player_id}",
        team_abbreviation="EDM",
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

    def __init__(self, *, market_label, selected_line):
        self.market_label = market_label
        self.selected_line = selected_line

    def columns(self, spec):
        return [_Column() for _ in spec]

    def selectbox(self, label, options, index=0, key=None):
        return self.market_label

    def number_input(self, *args, **kwargs):
        return self.selected_line

    def multiselect(self, *args, **kwargs):
        return ["EDM"]

    def info(self, message):
        raise AssertionError(message)
