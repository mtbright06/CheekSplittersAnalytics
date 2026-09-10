from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from components.data_table import render_data_table
from components.page_header import render_compact_header
from engine.nfl.models import NFLGame, NFLRosterEntry
from engine.nfl.prop_markets import NFLPropMarketProvider
from engine.nfl.prop_trend_service import NFLPropTrendReadService, NFLPropTrendRow
from engine.nfl.prop_trends import (
    ANYTIME_TOUCHDOWN,
    PASSING_TOUCHDOWNS,
    PASSING_YARDS,
    RECEIVING_YARDS,
    RECEPTIONS,
    RUSHING_YARDS,
)
from engine.nfl.rosters import NFLRostersProvider
from engine.nfl.schedule import NFLScheduleProvider


MARKET_OPTIONS = {
    "Passing Yards": PASSING_YARDS,
    "Passing Touchdowns": PASSING_TOUCHDOWNS,
    "Rushing Yards": RUSHING_YARDS,
    "Receiving Yards": RECEIVING_YARDS,
    "Receptions": RECEPTIONS,
    "Anytime Touchdown": ANYTIME_TOUCHDOWN,
}
DEFAULT_THRESHOLDS = {
    PASSING_YARDS: 249.5,
    PASSING_TOUCHDOWNS: 1.5,
    RUSHING_YARDS: 49.5,
    RECEIVING_YARDS: 49.5,
    RECEPTIONS: 3.5,
    ANYTIME_TOUCHDOWN: 0.5,
}
ELIGIBLE_POSITIONS = {
    PASSING_YARDS: frozenset({"QB"}),
    PASSING_TOUCHDOWNS: frozenset({"QB"}),
    RUSHING_YARDS: frozenset({"QB", "RB", "FB", "WR", "TE"}),
    RECEIVING_YARDS: frozenset({"RB", "FB", "WR", "TE"}),
    RECEPTIONS: frozenset({"RB", "FB", "WR", "TE"}),
    ANYTIME_TOUCHDOWN: frozenset({"QB", "RB", "FB", "WR", "TE"}),
}
ALL_GAMES = "All Games"
PROP_MODES = ("Market Lines", "Research Threshold")


@dataclass(frozen=True)
class SlateMatchup:
    label: str
    team_abbreviations: tuple[str, ...]
    game_id: str | None = None


@dataclass(frozen=True)
class RosterUniverse:
    entries: tuple[NFLRosterEntry, ...]
    concerns: tuple[str, ...] = ()


def render_nfl_prop_trends(
    *,
    read_service: NFLPropTrendReadService | None = None,
    games: Iterable[NFLGame] | None = None,
    roster_entries: Iterable[NFLRosterEntry] | None = None,
) -> None:
    render_compact_header(
        "🏈",
        "NFL Prop Trends",
        None,
    )

    mode = st.radio("Mode", PROP_MODES, horizontal=True, key="nfl_props_mode")

    controls = st.columns([1, 1.1, 1.4, 1.5, 0.9], vertical_alignment="bottom")
    with controls[0]:
        selected_date = st.date_input(
            "Slate Date",
            value=date.today(),
            key="nfl_prop_trends_slate_date",
        )
    slate_games = tuple(games) if games is not None else _load_slate_games(
        selected_date.isoformat()
    )
    if not slate_games:
        st.info("No NFL regular-season games found for the selected slate.")
        return

    with controls[1]:
        selected_games = _select_games(slate_games, selected_date)
    with controls[2]:
        market_label = st.selectbox(
            "Market",
            list(MARKET_OPTIONS),
            key="nfl_prop_trends_market",
        )
    market = MARKET_OPTIONS[market_label]
    with controls[4]:
        selected_threshold = DEFAULT_THRESHOLDS[market]
        refresh = False
        if mode == "Research Threshold":
            selected_threshold = st.number_input(
                "Threshold", min_value=0.0, value=selected_threshold, step=0.5,
                format="%g", key=f"nfl_prop_trends_threshold_{market}",
            )
        else:
            refresh = st.button("Refresh", icon=":material/refresh:", key="nfl_market_refresh")
    with controls[3]:
        player_search = st.text_input(
            "Player Search",
            key="nfl_prop_trends_player_search",
            placeholder="Name contains...",
        )

    if not selected_games:
        st.info("Select one or more games to view available props.")
        return
    season = selected_games[0].season
    week = selected_games[0].week
    selected_teams = tuple(dict.fromkeys(
        team.abbreviation for game in selected_games
        for team in (game.away_team, game.home_team)
    ))

    if roster_entries is None:
        universe = _load_roster_universe(season, week, selected_teams)
        entries = universe.entries
        if universe.concerns:
            st.caption("Roster concerns: " + "; ".join(universe.concerns))
    else:
        entries = tuple(
            entry
            for entry in roster_entries
            if entry.team_abbreviation in selected_teams
        )
    if mode == "Market Lines":
        _render_market_board(selected_games, entries, market, player_search,
                             read_service or _get_prop_trend_read_service(), refresh=refresh)
        return
    entries = _eligible_roster_entries(entries, market)
    if not entries:
        st.info("No eligible NFL players found for this matchup and market.")
        return

    service = read_service or _get_prop_trend_read_service()
    result = service.build_rows(
        roster_entries=entries,
        markets=[market],
        selected_lines={market: float(selected_threshold)},
        selected_season=season,
        game_type="REG",
        require_meaningful_usage=True,
    )
    if result.rows and all(row.season.hit_rate is None for row in result.rows):
        st.caption(
            f"{season} season sample unavailable for these players. "
            f"Recent windows may include {season - 1} regular-season games."
        )
    rows = _filter_rows_by_player_search(result.rows, player_search)
    if not rows:
        st.info("No NFL prop trend rows match the current filters.")
        return

    opponent_by_team = _opponents_by_team(selected_games)
    frame = _rows_to_dataframe(rows, opponent_by_team)
    render_data_table(
        _style_trend_frame(frame),
        column_config={
            "Threshold": st.column_config.NumberColumn("Threshold", format="%g"),
            **{
            column: st.column_config.TextColumn(column)
            for column in ("L5", "L10", "L20", "Season")
            },
        },
        height=620,
        key="nfl_prop_trends_table",
    )
    if result.concerns or any(row.concerns for row in rows):
        with st.expander("Data concerns", expanded=False):
            for concern in _concern_details(rows, result.concerns):
                st.caption(concern)

    entries_by_id = {entry.player_id: entry for entry in entries if entry.player_id}
    _render_player_detail(
        rows=rows,
        entries_by_id=entries_by_id,
        service=service,
        market=market,
        board_threshold=float(selected_threshold),
        season=season,
    )


def _set_game_selection(ids: tuple[str, ...]) -> None:
    st.session_state["nfl_props_selected_games"] = list(ids)


def _select_games(games: tuple[NFLGame, ...], selected_date: date) -> tuple[NFLGame, ...]:
    games = tuple(sorted(games, key=lambda game: (
        game.game_date, game.start_time.isoformat() if game.start_time else "~", game.source_game_id,
    )))
    ids = tuple(game.source_game_id for game in games)
    key = "nfl_props_selected_games"
    if st.session_state.get("nfl_props_selection_date") != selected_date.isoformat():
        st.session_state["nfl_props_selection_date"] = selected_date.isoformat()
        st.session_state[key] = list(ids)
    else:
        st.session_state[key] = [value for value in st.session_state.get(key, ids) if value in ids]
    labels = {
        game.source_game_id: (
            f"{game.away_team.abbreviation} @ {game.home_team.abbreviation}"
            + (game.start_time.astimezone(ZoneInfo("America/New_York")).strftime(" | %a %I:%M %p %Z")
               if game.start_time else "")
        )
        for game in games
    }
    with st.popover(f"Games {len(st.session_state[key])}/{len(ids)}", use_container_width=True):
        actions = st.columns(2)
        actions[0].button("All", key="nfl_props_games_all", on_click=_set_game_selection, args=(ids,))
        actions[1].button("Clear", key="nfl_props_games_clear", on_click=_set_game_selection, args=((),))
        selected = st.multiselect("Games", ids, format_func=labels.__getitem__, key=key)
    return tuple(game for game in games if game.source_game_id in selected)


def _matchup_options(games: Iterable[NFLGame]) -> tuple[SlateMatchup, ...]:
    games = tuple(games)
    teams = tuple(dict.fromkeys(
        abbreviation
        for game in games
        for abbreviation in (
            game.away_team.abbreviation,
            game.home_team.abbreviation,
        )
    ))
    return (SlateMatchup(ALL_GAMES, teams),) + tuple(
        SlateMatchup(
            f"{game.away_team.abbreviation} @ {game.home_team.abbreviation}",
            (game.away_team.abbreviation, game.home_team.abbreviation),
            game.source_game_id,
        )
        for game in games
    )


def _games_for_matchup(
    games: Iterable[NFLGame], matchup: SlateMatchup
) -> tuple[NFLGame, ...]:
    if matchup.game_id is None:
        return tuple(games)
    return tuple(game for game in games if game.source_game_id == matchup.game_id)


def _eligible_roster_entries(
    entries: Iterable[NFLRosterEntry], market: str
) -> tuple[NFLRosterEntry, ...]:
    positions = ELIGIBLE_POSITIONS.get(market, frozenset())
    return tuple(
        entry
        for entry in entries
        if (entry.position or (entry.player.position if entry.player else None)) in positions
        and entry.player_id
        and entry.player is not None
    )


def _filter_rows_by_player_search(
    rows: Iterable[NFLPropTrendRow], search: str
) -> tuple[NFLPropTrendRow, ...]:
    needle = " ".join(str(search or "").casefold().split())
    if not needle:
        return tuple(rows)
    return tuple(row for row in rows if needle in row.player_name.casefold())


def _opponents_by_team(games: Iterable[NFLGame]) -> dict[str, str]:
    opponents = {}
    for game in games:
        away = game.away_team.abbreviation
        home = game.home_team.abbreviation
        opponents[away] = home
        opponents[home] = away
    return opponents


def _rows_to_dataframe(
    rows: Iterable[NFLPropTrendRow], opponents: dict[str, str]
) -> pd.DataFrame:
    records = [{
        "Player": row.player_name or row.player_id,
        "Team": row.team_abbreviation,
        "Pos": row.position or "N/A",
        "Opponent": opponents.get(row.team_abbreviation, "N/A"),
        "Threshold": row.selected_line,
        "L5": _format_hit_rate(row.last_5.hit_rate),
        "L10": _format_hit_rate(row.last_10.hit_rate),
        "L20": _format_hit_rate(row.last_20.hit_rate),
        "Season": _format_hit_rate(row.season.hit_rate),
        "L10 GP": row.last_10.games_considered,
        "_l10": _sort_rate(row.last_10.hit_rate),
        "_l5": _sort_rate(row.last_5.hit_rate),
        "_season": _sort_rate(row.season.hit_rate),
    } for row in rows]
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return frame.sort_values(
        ["_l10", "_l5", "_season", "Player"],
        ascending=[False, False, False, True],
    ).drop(columns=["_l10", "_l5", "_season"])


def _format_hit_rate(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.0f}%"


def _sort_rate(value: float | None) -> float:
    return -1.0 if value is None else value


def _style_trend_frame(frame: pd.DataFrame):
    if frame.empty:
        return frame
    return frame.style.map(
        _trend_cell_style,
        subset=["L5", "L10", "L20", "Season"],
    )


def _trend_cell_style(value: str) -> str:
    if value == "N/A":
        return "color: #7b8794;"
    try:
        rate = int(str(value).rstrip("%"))
    except ValueError:
        return ""
    if rate >= 80:
        return "color: #7ee787; font-weight: 700;"
    if rate >= 60:
        return "color: #f2d477; font-weight: 600;"
    return "color: #9aa4b2;" if rate <= 30 else ""


def _render_player_detail(
    *,
    rows: Iterable[NFLPropTrendRow],
    entries_by_id: dict[str, NFLRosterEntry],
    service: NFLPropTrendReadService,
    market: str,
    board_threshold: float,
    season: int,
) -> None:
    rows = tuple(rows)
    options = {_player_label(row): row for row in rows}
    selected_label = st.selectbox(
        "Player Detail",
        list(options),
        key="nfl_prop_trends_player_detail",
    )
    selected_row = options[selected_label]
    detail_threshold = st.number_input(
        "Detail Threshold",
        min_value=0.0,
        value=board_threshold,
        step=0.5,
        format="%g",
        key=f"nfl_prop_trends_detail_threshold_{market}_{selected_row.player_id}",
    )
    entry = entries_by_id.get(selected_row.player_id)
    detail = service.build_player_detail(
        roster_entry=entry,
        market=market,
        selected_line=float(detail_threshold),
        selected_season=season,
        game_type="REG",
    ) if entry is not None else selected_row

    st.markdown("### Player Detail")
    st.caption(
        f"{detail.player_name} | {detail.team_abbreviation} | "
        f"{detail.position or 'N/A'} | {_market_label(market)} research threshold "
        f"{detail.selected_line:g}"
    )
    summaries = (
        ("L5", detail.last_5),
        ("L10", detail.last_10),
        ("L20", detail.last_20),
        ("Season", detail.season),
        ("Previous Season", detail.previous_season),
    )
    st.dataframe(pd.DataFrame([{
        "Window": label,
        "Hit Rate": _format_hit_rate(summary.hit_rate),
        "Games": summary.games_considered,
    } for label, summary in summaries]), width="stretch", hide_index=True)

    game_frame = _game_results_to_dataframe(detail.last_20.game_results)
    if game_frame.empty:
        st.info("No game-by-game results available for this player and market.")
    else:
        st.dataframe(game_frame, width="stretch", hide_index=True)
    if detail.concerns:
        with st.expander("Player detail concerns", expanded=False):
            st.caption(", ".join(detail.concerns))


def _player_label(row: NFLPropTrendRow) -> str:
    return f"{row.player_name or row.player_id} ({row.team_abbreviation})"


def _game_results_to_dataframe(results) -> pd.DataFrame:
    return pd.DataFrame([{
        "Date": result.game_date,
        "Opponent": result.opponent_abbreviation or "N/A",
        "Home/Away": result.home_away or "N/A",
        "Actual": result.actual_value,
        "Result": result.result,
    } for result in results])


def _concern_details(
    rows: Iterable[NFLPropTrendRow], board_concerns: Iterable[str]
) -> tuple[str, ...]:
    concerns = list(board_concerns)
    for row in rows:
        concerns.extend(f"{row.player_name}: {concern}" for concern in row.concerns)
    return tuple(dict.fromkeys(concerns))


def _market_label(market: str) -> str:
    return next((label for label, value in MARKET_OPTIONS.items() if value == market), market)


@st.cache_resource(ttl=1800, show_spinner=False)
def _get_schedule_provider() -> NFLScheduleProvider:
    return NFLScheduleProvider()


@st.cache_data(ttl=300, show_spinner=False)
def _load_slate_games(target_date: str) -> tuple[NFLGame, ...]:
    try:
        return tuple(_get_schedule_provider().load_schedule(
            target_date=target_date,
            game_type="REG",
        ))
    except Exception:
        return ()


@st.cache_resource(ttl=1800, show_spinner=False)
def _get_roster_provider() -> NFLRostersProvider:
    return NFLRostersProvider()


@st.cache_data(ttl=1800, show_spinner=False)
def _load_roster_universe(
    season: int, week: int, teams: tuple[str, ...]
) -> RosterUniverse:
    try:
        entries = _get_roster_provider().load_weekly_roster(
            season=season,
            week=week,
        )
    except Exception:
        return RosterUniverse((), ("weekly_roster_unavailable",))
    team_set = set(teams)
    return RosterUniverse(tuple(
        entry for entry in entries if entry.team_abbreviation in team_set
    ))


@st.cache_resource(show_spinner=False)
def _get_prop_trend_read_service() -> NFLPropTrendReadService:
    return NFLPropTrendReadService()


@st.cache_resource(show_spinner=False)
def _get_market_provider() -> NFLPropMarketProvider:
    return NFLPropMarketProvider()


def _price(value):
    return "N/A" if value is None else f"{value:+d}"


def _line(quote):
    return "Anytime (Yes)" if quote.line is None else f"{quote.line:g}"


def _render_market_board(games, entries, market, search, service, *, refresh=False):
    provider = _get_market_provider()
    quotes, concerns = [], []
    for game in games:
        batch = provider.load_game(game, market, entries, refresh=refresh)
        quotes.extend(batch.quotes)
        concerns.extend(f"{game.away_team.abbreviation} @ {game.home_team.abbreviation}: {c}"
                        for c in batch.concerns)
    unresolved = [q for q in quotes if not q.roster_entry]
    concerns.extend(f"{q.player_name} ({q.sportsbook}): {', '.join(q.concerns)}" for q in unresolved)
    if concerns:
        with st.expander("Market availability / identity concerns", expanded=not quotes):
            for concern in dict.fromkeys(concerns):
                st.caption(concern)
    if unresolved:
        render_data_table(pd.DataFrame([{'Unmatched player': q.player_name, 'Book': q.sportsbook,
                         'Line': _line(q), 'Over / Yes': _price(q.over_price),
                         'Under / No': _price(q.under_price)} for q in unresolved]))
    if not quotes:
        st.info("No available player markets from FanDuel or Fanatics for this slate and market.")
        return
    market_rows = service.build_market_rows(quotes, selected_season=games[0].season,
                                            before_date=games[0].game_date)
    needle = search.strip().casefold()
    market_rows = sorted((r for r in market_rows if needle in r.trend.player_name.casefold()),
                        key=lambda r: (-_sort_rate(r.trend.last_10.hit_rate),
                                       -_sort_rate(r.trend.last_5.hit_rate),
                                       -_sort_rate(r.trend.season.hit_rate), r.trend.player_name,
                                       r.quote.game_id, r.trend.player_id))
    if not market_rows:
        st.info("No matched player markets match the current filters.")
        return
    opponents = _opponents_by_team(games)
    frame = _market_dataframe(market_rows, opponents)
    render_data_table(_style_trend_frame(frame), height=540, key="nfl_market_board")
    if all(r.trend.season.games_considered == 0 for r in market_rows):
        st.caption(f"{games[0].season} season sample unavailable. Recent windows may include "
                   f"{games[0].season - 1}; Previous Season is shown in player detail.")
    st.caption("Hit rates measure historical Over / Yes results. Prices are separate market context.")
    updates = [q.retrieved_at for q in quotes]
    st.caption(f"Retrieved {max(updates).strftime('%Y-%m-%d %H:%M UTC')} | Five-minute market cache")
    all_concerns = _concern_details([r.trend for r in market_rows], ())
    if all_concerns:
        with st.expander("Data concerns"):
            for concern in all_concerns:
                st.caption(concern)
    options = {(r.quote.game_id, r.trend.player_id): r for r in market_rows}
    selected = st.selectbox("Player Detail", list(options),
                           format_func=lambda key: _player_label(options[key].trend),
                           key="nfl_market_player_detail")
    _render_market_detail(options[selected], service, opponents, games[0].game_date)


def _market_dataframe(rows, opponents):
    return pd.DataFrame([{
        'Player': r.trend.player_name, 'Team': r.trend.team_abbreviation,
        'Opp': opponents.get(r.trend.team_abbreviation, 'N/A'), 'Pos': r.trend.position,
        'Book': r.quote.sportsbook, 'Actual Line': _line(r.quote),
        'Over / Yes': _price(r.quote.over_price), 'Under / No': _price(r.quote.under_price),
        'L5': _format_hit_rate(r.trend.last_5.hit_rate),
        'L10': _format_hit_rate(r.trend.last_10.hit_rate),
        'L20': _format_hit_rate(r.trend.last_20.hit_rate),
        'Season': _format_hit_rate(r.trend.season.hit_rate),
        'L10 GP': r.trend.last_10.games_considered,
        'Status': 'STALE' if 'market_stale' in r.quote.concerns else ('!' if r.trend.concerns else ''),
    } for r in rows])


def _render_market_detail(row, service, opponents, before_date):
    trend, quote = row.trend, row.quote
    st.subheader(trend.player_name)
    st.caption(f"{trend.team_abbreviation} vs {opponents.get(trend.team_abbreviation, 'N/A')} | "
               f"{trend.position or 'N/A'} | {_market_label(trend.market)} | {quote.sportsbook}")
    st.caption('Source updated: ' + (quote.updated_at.strftime('%Y-%m-%d %H:%M UTC')
                                    if quote.updated_at else 'Unknown'))
    if 'market_stale' in quote.concerns:
        st.warning('STALE market quote. Refresh before relying on this line or price.')
    cols = st.columns(3)
    cols[0].metric('Actual market', _line(quote))
    cols[1].metric('Over / Yes', _price(quote.over_price))
    cols[2].metric('Under / No', _price(quote.under_price))
    if quote.line is None:
        st.caption("Anytime scorer Yes/No market; equivalent research threshold: 0.5 TD.")
    summaries = [('L5', trend.last_5), ('L10', trend.last_10), ('L20', trend.last_20),
                 (f'Season {trend.selected_season}', trend.season),
                 (f'Previous Season {trend.selected_season - 1}', trend.previous_season)]
    render_data_table(pd.DataFrame([{'Window': label, 'Hit rate': _format_hit_rate(s.hit_rate),
                                    'GP': s.games_considered, 'Pushes': s.pushes} for label, s in summaries]))
    results = _game_results_to_dataframe(trend.last_20.game_results)
    if not results.empty:
        results.insert(4, 'Line / Threshold', f'{quote.research_line:g}')
        render_data_table(results)
        st.bar_chart(pd.DataFrame({'Date': [r.game_date for r in trend.last_20.game_results],
                                  'Actual': [r.actual_value for r in trend.last_20.game_results]}).set_index('Date'),
                     height=180)
    else:
        st.info('No qualifying historical game results for this player.')
    st.subheader('Research alternate thresholds')
    center = st.number_input('Explore threshold', min_value=0.0, value=quote.research_line,
                             step=0.5, format='%g',
                             key=f'nfl_explore_{quote.game_id}_{trend.player_id}_{trend.market}')
    step = 5.0 if trend.market in {PASSING_YARDS, RUSHING_YARDS, RECEIVING_YARDS} else 1.0
    thresholds = sorted({max(0.0, center + offset * step) for offset in (-2, -1, 0, 1, 2)})
    nearby = service.nearby_thresholds(trend, thresholds, before_date=before_date)
    render_data_table(pd.DataFrame([{
        'Research Threshold': f'{threshold:g}',
        **{label: _format_hit_rate(windows[window].hit_rate) for label, window in
           [('L5', 'LAST_5'), ('L10', 'LAST_10'), ('L20', 'LAST_20'), ('Season', 'SEASON')]},
    } for threshold, windows in nearby.items()]))
