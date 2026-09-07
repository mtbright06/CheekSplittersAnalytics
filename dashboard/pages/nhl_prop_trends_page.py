from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import streamlit as st

from components.data_table import render_data_table
from components.page_header import render_compact_header
from engine.nhl.models import NHLPlayer
from engine.nhl.player_game_logs import REGULAR_SEASON
from engine.nhl.players import NHLRosterService
from engine.nhl.prop_trend_service import NHLPropTrendReadService
from engine.nhl.prop_trends import (
    ASSISTS,
    GOALS,
    POINTS,
    SAVES,
    SHOTS_ON_GOAL,
)
from engine.nhl.schedule import build_nhl_schedule
from engine.nhl.stats import current_nhl_season_id
from engine.nhl.teams import load_nhl_teams


MARKET_OPTIONS = {
    "Shots on Goal": SHOTS_ON_GOAL,
    "Goals": GOALS,
    "Assists": ASSISTS,
    "Points": POINTS,
    "Saves": SAVES,
}
DEFAULT_LINES = {
    SHOTS_ON_GOAL: 2.5,
    GOALS: 0.5,
    ASSISTS: 0.5,
    POINTS: 0.5,
    SAVES: 24.5,
}
ALL_TEAMS = "All Teams"


@dataclass(frozen=True)
class PlayerUniverse:
    players: tuple[NHLPlayer, ...]
    concerns: tuple[str, ...] = ()


def render_nhl_prop_trends(
    *,
    read_service: NHLPropTrendReadService | None = None,
    players: Iterable[NHLPlayer] | None = None,
) -> None:
    render_compact_header(
        "🏒",
        "NHL Prop Trends",
        "Historical player prop performance across recent and season windows.",
    )

    teams = _load_available_teams()
    team_options = [team.abbreviation for team in teams]
    default_teams = team_options[:1]

    control_columns = st.columns([1.1, 0.7, 1.4, 1.0])
    with control_columns[0]:
        market_label = st.selectbox(
            "Market",
            list(MARKET_OPTIONS),
            index=0,
            key="nhl_prop_trends_market",
        )
    market = MARKET_OPTIONS[market_label]

    with control_columns[1]:
        selected_line = st.number_input(
            "Prop Line",
            min_value=0.0,
            value=DEFAULT_LINES[market],
            step=0.5,
            key=f"nhl_prop_trends_line_{market}",
        )

    with control_columns[2]:
        selected_teams = st.multiselect(
            "Teams",
            [ALL_TEAMS] + team_options,
            default=default_teams,
            key="nhl_prop_trends_teams",
        )
    with control_columns[3]:
        player_search = st.text_input(
            "Player Search",
            value="",
            key="nhl_prop_trends_player_search",
            placeholder="Name contains...",
        )

    season_id = current_nhl_season_id()
    if players is not None:
        player_universe = tuple(players)
        universe_concerns: tuple[str, ...] = ()
    else:
        selected_team_abbreviations = _selected_team_abbreviations(
            selected_teams,
            team_options,
            _load_current_slate_team_abbreviations(),
        )
        universe = _load_players_for_teams(
            tuple(selected_team_abbreviations),
            saves_market=(market == SAVES),
        )
        player_universe = universe.players
        universe_concerns = universe.concerns

    if not selected_teams and players is None:
        st.info("Select at least one NHL team to load prop trends.")
        return
    if not player_universe:
        st.info("No eligible players found for the selected market.")
        return
    if universe_concerns:
        st.caption(
            "Roster concerns: "
            + "; ".join(universe_concerns)
        )

    service = read_service or _get_prop_trend_read_service()
    rows = service.build_rows(
        players=player_universe,
        markets=[market],
        selected_lines={market: float(selected_line)},
        season_id=season_id,
        game_type=REGULAR_SEASON,
    )
    if not rows:
        st.info("No NHL prop trend rows available.")
        return
    rows = _filter_rows_by_player_search(rows, player_search)
    if not rows:
        st.info("No NHL prop trend rows match the current filters.")
        return

    frame = _rows_to_dataframe(rows)
    concerns = _concern_details(rows)

    render_data_table(
        _style_trend_frame(frame),
        column_config={
            "L5": st.column_config.TextColumn("L5"),
            "L10": st.column_config.TextColumn("L10"),
            "L20": st.column_config.TextColumn("L20"),
            "Season": st.column_config.TextColumn("Season"),
            "Concern": st.column_config.TextColumn("Concern"),
        },
        height=640,
        key="nhl_prop_trends_table",
    )
    if concerns:
        with st.expander("Rows with data concerns", expanded=False):
            for detail in concerns:
                st.caption(detail)


def _rows_to_dataframe(rows) -> pd.DataFrame:
    records = [
        {
            "Player": row.player_name or f"Player {row.player_id}",
            "Team": row.team_abbreviation or "N/A",
            "Pos": row.position or "N/A",
            "Line": row.selected_line,
            "L5": _format_hit_rate(row.last_5.hit_rate),
            "L10": _format_hit_rate(row.last_10.hit_rate),
            "L20": _format_hit_rate(row.last_20.hit_rate),
            "Season": _format_hit_rate(row.season.hit_rate),
            "Games": row.season.games_considered,
            "Concern": "!" if row.concerns else "",
            "_concerns": ", ".join(row.concerns) if row.concerns else "",
            "_sort_l10": _sort_hit_rate(row.last_10.hit_rate),
            "_sort_l5": _sort_hit_rate(row.last_5.hit_rate),
            "_sort_season": _sort_hit_rate(row.season.hit_rate),
        }
        for row in rows
    ]
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame = frame.sort_values(
        by=["_sort_l10", "_sort_l5", "_sort_season", "Player"],
        ascending=[False, False, False, True],
    )
    return frame.drop(
        columns=[
            "_sort_l10",
            "_sort_l5",
            "_sort_season",
            "_concerns",
        ]
    )


def _style_trend_frame(frame: pd.DataFrame):
    if frame.empty:
        return frame
    return frame.style.map(
        _trend_cell_style,
        subset=["L5", "L10", "L20", "Season"],
    )


def _format_hit_rate(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _sort_hit_rate(value: float | None) -> float:
    return value if value is not None else -1.0


def _trend_cell_style(value: str) -> str:
    text = str(value or "")
    if text == "N/A":
        return "color: #7b8794;"
    try:
        rate = int(text.rstrip("%"))
    except ValueError:
        return ""
    if rate >= 80:
        return "color: #7ee787; font-weight: 700;"
    if rate >= 60:
        return "color: #f2d477; font-weight: 600;"
    if rate <= 30:
        return "color: #9aa4b2;"
    return ""


def _selected_team_abbreviations(
    selected_teams: Iterable[str],
    team_options: list[str],
    slate_team_options: Iterable[str] = (),
) -> tuple[str, ...]:
    selected = tuple(selected_teams or ())
    if ALL_TEAMS in selected:
        return tuple(slate_team_options)
    return selected


def _filter_rows_by_player_search(rows, search: str):
    needle = " ".join(str(search or "").lower().split())
    if not needle:
        return list(rows)
    return [
        row
        for row in rows
        if needle in str(row.player_name or "").lower()
    ]


def _concern_details(rows) -> list[str]:
    details = []
    for row in rows:
        if row.concerns:
            player = row.player_name or f"Player {row.player_id}"
            details.append(
                f"{player}: {', '.join(row.concerns)}"
            )
    return details


@st.cache_data(ttl=1800, show_spinner=False)
def _load_available_teams():
    try:
        return load_nhl_teams()
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _load_current_slate_team_abbreviations() -> tuple[str, ...]:
    try:
        games = build_nhl_schedule()
    except Exception:
        return ()

    abbreviations = []
    for game in games:
        abbreviations.extend([
            game.away_team.abbreviation,
            game.home_team.abbreviation,
        ])
    return tuple(
        dict.fromkeys(
            abbreviation
            for abbreviation in abbreviations
            if abbreviation
        )
    )


@st.cache_resource(show_spinner=False)
def _get_prop_trend_read_service() -> NHLPropTrendReadService:
    return NHLPropTrendReadService()


@st.cache_data(ttl=1800, show_spinner=False)
def _load_players_for_teams(
    team_abbreviations: tuple[str, ...],
    *,
    saves_market: bool,
) -> PlayerUniverse:
    teams = {
        team.abbreviation: team
        for team in _load_available_teams()
    }
    service = NHLRosterService()
    players: list[NHLPlayer] = []
    concerns: list[str] = []
    for abbreviation in team_abbreviations:
        team = teams.get(abbreviation)
        if team is None:
            concerns.append(f"{abbreviation}: team unavailable")
            continue
        try:
            roster = service.load_team_roster(team)
        except Exception:
            concerns.append(f"{abbreviation}: roster unavailable")
            continue
        for player in roster:
            if saves_market and player.position == "G":
                players.append(player)
            elif not saves_market and player.position != "G":
                players.append(player)
    return PlayerUniverse(
        players=tuple(players),
        concerns=tuple(concerns),
    )
