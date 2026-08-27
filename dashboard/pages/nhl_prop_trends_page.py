from __future__ import annotations

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

    control_columns = st.columns([1.2, 0.8, 1.6])
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
            team_options,
            default=default_teams,
            key="nhl_prop_trends_teams",
        )

    season_id = current_nhl_season_id()
    player_universe = tuple(
        players
        if players is not None
        else _load_players_for_teams(
            tuple(selected_teams),
            saves_market=(market == SAVES),
        )
    )

    if not selected_teams and players is None:
        st.info("Select at least one NHL team to load prop trends.")
        return
    if not player_universe:
        st.info("No eligible players found for the selected market.")
        return

    service = read_service or NHLPropTrendReadService()
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

    render_data_table(
        _rows_to_dataframe(rows),
        column_config={
            "L5": st.column_config.TextColumn("L5"),
            "L10": st.column_config.TextColumn("L10"),
            "L20": st.column_config.TextColumn("L20"),
            "Season": st.column_config.TextColumn("Season"),
            "Concerns": st.column_config.TextColumn("Concerns"),
        },
        height=640,
        key="nhl_prop_trends_table",
    )


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
            "Concerns": ", ".join(row.concerns) if row.concerns else "",
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
    return frame.drop(columns=["_sort_l10", "_sort_l5", "_sort_season"])


def _format_hit_rate(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _sort_hit_rate(value: float | None) -> float:
    return value if value is not None else -1.0


@st.cache_data(ttl=1800, show_spinner=False)
def _load_available_teams():
    try:
        return load_nhl_teams()
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def _load_players_for_teams(
    team_abbreviations: tuple[str, ...],
    *,
    saves_market: bool,
) -> tuple[NHLPlayer, ...]:
    teams = {
        team.abbreviation: team
        for team in _load_available_teams()
    }
    service = NHLRosterService()
    players: list[NHLPlayer] = []
    for abbreviation in team_abbreviations:
        team = teams.get(abbreviation)
        if team is None:
            continue
        for player in service.load_team_roster(team):
            if saves_market and player.position == "G":
                players.append(player)
            elif not saves_market and player.position != "G":
                players.append(player)
    return tuple(players)
