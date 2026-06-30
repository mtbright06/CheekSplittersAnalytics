import streamlit as st

from components.best_pick import render_best_pick
from components.cards import render_game
from components.compact_pick import render_compact_pick
from components.dashboard_metrics import render_dashboard_metrics
from components.pipeline_status import render_pipeline_status


def best_games_by_sport(games):
    grouped = {}

    for game in games:
        sport = (game.get("sport") or "unknown").upper()
        grouped.setdefault(sport, []).append(game)

    best = {}

    for sport, sport_games in grouped.items():
        best[sport] = sorted(
            sport_games,
            key=lambda g: g.get("model", {}).get("edge") or 0,
            reverse=True,
        )

    return best


def render_multi_sport_dashboard(card):
    games = card.get("games", [])

    render_dashboard_metrics(card)

    st.markdown(
        '<div class="section-title">🍑 SharpStack Command Board</div>',
        unsafe_allow_html=True,
    )

    grouped = best_games_by_sport(games)

    for sport, sport_games in grouped.items():
        st.markdown(
            f'<div class="sport-section-title">{sport} Best Picks</div>',
            unsafe_allow_html=True,
        )

        for game in sport_games[:3]:
            render_compact_pick(game)

    st.markdown("---")

    left, right = st.columns([2.5, 1])

    if games:
        best_game = max(
            games,
            key=lambda g: g.get("model", {}).get("edge") or 0,
        )

        with left:
            render_best_pick(best_game)

        with right:
            render_pipeline_status(card)


def render_single_sport_dashboard(card):
    games = card.get("games", [])

    render_dashboard_metrics(card)

    if not games:
        st.info("No confirmed plays today. The cheeks remain unclapped.")
        render_pipeline_status(card)
        return

    best_game = max(
        games,
        key=lambda g: g.get("model", {}).get("edge") or 0,
    )

    left, right = st.columns([2.5, 1])

    with left:
        render_best_pick(best_game)

    with right:
        render_pipeline_status(card)

    st.markdown(
        '<div class="section-title">Today’s Slate</div>',
        unsafe_allow_html=True,
    )

    for game in sorted(
        games,
        key=lambda g: g.get("model", {}).get("edge") or 0,
        reverse=True,
    ):
        render_game(game)


def render_dashboard(card):
    if card.get("sport") == "MULTI":
        render_multi_sport_dashboard(card)
    else:
        render_single_sport_dashboard(card)
