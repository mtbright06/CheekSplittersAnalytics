import streamlit as st

from components.best_pick import render_best_pick
from components.cards import render_game
from components.dashboard_metrics import render_dashboard_metrics
from components.engine_status import render_engine_status
from components.pipeline_status import render_pipeline_status


def render_dashboard(card):
    games = card.get("games", [])

    render_dashboard_metrics(card)

    st.markdown("---")

    if not games:
        st.info("No confirmed plays today. The cheeks remain unclapped.")

        left, right = st.columns(2)

        with left:
            render_engine_status(card)

        with right:
            render_pipeline_status(card)

        return

    best_game = max(
        games,
        key=lambda g: g["model"].get("edge") or 0,
    )

    left, right = st.columns([2.5, 1])

    with left:
        render_best_pick(best_game)

    with right:
        render_pipeline_status(card)

    st.markdown(
        '<div class="section-title">Today’s Card</div>',
        unsafe_allow_html=True,
    )

    for game in sorted(
        games,
        key=lambda g: g["model"].get("edge") or 0,
        reverse=True,
    ):
        render_game(game)
