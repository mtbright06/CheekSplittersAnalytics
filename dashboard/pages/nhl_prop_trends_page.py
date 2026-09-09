from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd
import streamlit as st

from components.data_table import render_data_table
from components.page_header import render_compact_header
from engine.nhl.models import NHLPlayer
from engine.nhl.player_game_logs import REGULAR_SEASON
from engine.nhl.players import NHLRosterService
from engine.nhl.prop_trend_service import NHLPropTrendRow
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
ALL_GAMES = "All Games"


@dataclass(frozen=True)
class PlayerUniverse:
    players: tuple[NHLPlayer, ...]
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class SlateMatchup:
    label: str
    team_abbreviations: tuple[str, ...]
    game_id: int | None = None


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

    with st.container():
        selected_date = st.date_input(
            "Slate Date",
            value=date.today(),
            key="nhl_prop_trends_slate_date",
        )
        st.caption(f"Selected slate: {selected_date.isoformat()}")

    slate_games = _load_current_slate_games(selected_date.isoformat())
    matchup_options = _matchup_options(slate_games)
    if not slate_games and players is None:
        st.info("No NHL games found for the selected slate.")
        return

    teams = _load_available_teams()
    team_options = [team.abbreviation for team in teams]

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
        selected_matchup_label = st.selectbox(
            "Matchup",
            [matchup.label for matchup in matchup_options],
            index=0,
            key="nhl_prop_trends_matchup",
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
            selected_matchup_label,
            team_options,
            matchup_options,
        )
        universe = _load_players_for_teams(
            tuple(selected_team_abbreviations),
            saves_market=(market == SAVES),
        )
        player_universe = universe.players
        universe_concerns = universe.concerns

    if players is None and selected_date != date.today():
        st.caption(
            "Current NHL rosters are used for this research view; "
            "this is not a historical lineup reconstruction."
        )
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

    row_players = {
        player.source_player_id: player
        for player in player_universe
    }
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

    _render_player_detail(
        rows=rows,
        row_players=row_players,
        service=service,
        market=market,
        board_line=float(selected_line),
        season_id=season_id,
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
    selected_matchup_label: str | Iterable[str],
    team_options: list[str],
    matchup_options: Iterable[SlateMatchup] = (),
) -> tuple[str, ...]:
    if isinstance(selected_matchup_label, str):
        for matchup in matchup_options:
            if matchup.label == selected_matchup_label:
                return matchup.team_abbreviations
        return ()

    selected = tuple(selected_matchup_label or ())
    if ALL_TEAMS in selected or ALL_GAMES in selected:
        if not matchup_options:
            return ()
        if matchup_options and all(
            isinstance(matchup, str)
            for matchup in matchup_options
        ):
            return tuple(matchup_options)
        for matchup in matchup_options:
            if matchup.label == ALL_GAMES:
                return matchup.team_abbreviations
        return tuple(team_options)
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


def _matchup_options(games) -> list[SlateMatchup]:
    slate_teams = []
    matchups = []
    for game in games:
        away = game.away_team.abbreviation
        home = game.home_team.abbreviation
        if away:
            slate_teams.append(away)
        if home:
            slate_teams.append(home)
        if away and home:
            matchups.append(
                SlateMatchup(
                    label=f"{away} @ {home}",
                    team_abbreviations=(away, home),
                    game_id=game.source_game_id,
                )
            )
    return [
        SlateMatchup(
            label=ALL_GAMES,
            team_abbreviations=tuple(dict.fromkeys(slate_teams)),
        )
    ] + matchups


def _render_player_detail(
    *,
    rows: list[NHLPropTrendRow],
    row_players: dict[int, NHLPlayer],
    service: NHLPropTrendReadService,
    market: str,
    board_line: float,
    season_id: int,
) -> None:
    if not rows:
        return

    options = {
        _player_detail_label(row): row
        for row in rows
    }
    selected_label = st.selectbox(
        "Player Detail",
        list(options),
        index=0,
        key="nhl_prop_trends_player_detail",
    )
    selected_row = options[selected_label]
    detail_line = st.number_input(
        "Detail Line",
        min_value=0.0,
        value=float(board_line),
        step=0.5,
        key=f"nhl_prop_trends_detail_line_{market}_{selected_row.player_id}",
    )

    player = row_players.get(selected_row.player_id)
    detail_row = (
        service.build_player_detail(
            player=player,
            market=market,
            selected_line=float(detail_line),
            season_id=season_id,
            game_type=REGULAR_SEASON,
        )
        if player is not None
        else selected_row
    )

    st.markdown("### Player Detail")
    st.caption(
        f"{detail_row.player_name or f'Player {detail_row.player_id}'} | "
        f"{detail_row.team_abbreviation or 'N/A'} | "
        f"{detail_row.position or 'N/A'} | "
        f"{_market_label(market)} {detail_row.selected_line:g}"
    )
    summary_frame = pd.DataFrame([
        {
            "Window": "L5",
            "Hit Rate": _format_hit_rate(detail_row.last_5.hit_rate),
            "Games": detail_row.last_5.games_considered,
        },
        {
            "Window": "L10",
            "Hit Rate": _format_hit_rate(detail_row.last_10.hit_rate),
            "Games": detail_row.last_10.games_considered,
        },
        {
            "Window": "L20",
            "Hit Rate": _format_hit_rate(detail_row.last_20.hit_rate),
            "Games": detail_row.last_20.games_considered,
        },
        {
            "Window": "Season",
            "Hit Rate": _format_hit_rate(detail_row.season.hit_rate),
            "Games": detail_row.season.games_considered,
        },
    ])
    st.dataframe(
        summary_frame,
        width="stretch",
        hide_index=True,
    )

    game_frame = _game_results_to_dataframe(detail_row.last_20.game_results)
    if game_frame.empty:
        st.info("No game-by-game results available for this player and market.")
    else:
        st.dataframe(
            game_frame,
            width="stretch",
            hide_index=True,
        )

    if detail_row.concerns:
        with st.expander("Player detail concerns", expanded=False):
            st.caption(", ".join(detail_row.concerns))


def _player_detail_label(row: NHLPropTrendRow) -> str:
    return (
        f"{row.player_name or f'Player {row.player_id}'} "
        f"({row.team_abbreviation or 'N/A'})"
    )


def _game_results_to_dataframe(results) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Date": getattr(result.game_date, "date", lambda: result.game_date)(),
            "Opponent": result.opponent_abbreviation or "N/A",
            "Home/Away": result.home_away or "N/A",
            "Actual": result.actual_value,
            "Result": result.result,
        }
        for result in results
    ])


def _market_label(market: str) -> str:
    for label, value in MARKET_OPTIONS.items():
        if value == market:
            return label
    return str(market)


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


@st.cache_data(ttl=300, show_spinner=False)
def _load_current_slate_games(target_date: str):
    try:
        return tuple(build_nhl_schedule(target_date))
    except Exception:
        return ()


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
