import streamlit as st

from components.cards import grade_label, render_game
from components.dashboard_metrics import render_dashboard_metrics
from components.model_health import render_model_health


def render_dashboard(card):
    games = card.get("games", [])

    render_dashboard_metrics(card)

    st.markdown("---")

    if not games:
        st.info("No confirmed plays today. The cheeks remain unclapped.")

        with st.container(border=True):
            render_model_health()

        return

    best_game = max(
        games,
        key=lambda g: g["model"].get("edge") or 0,
    )

    left, right = st.columns([3, 1])

    with left:
        st.markdown(
            '<div class="section-title">🔥 Cheek Splitter of the Day</div>',
            unsafe_allow_html=True,
        )

        matchup = best_game["matchup"]
        model = best_game["model"]

        st.markdown('<div class="best-card">', unsafe_allow_html=True)

        cols = st.columns([3, 1, 1])

        cols[0].markdown(f"## {model.get('play')} ({model.get('market')})")
        cols[0].caption(
            f"{matchup['away']} @ {matchup['home']} · "
            f"{grade_label(model.get('edge'))}"
        )

        cols[1].markdown(
            '<div class="small-label">Edge</div>',
            unsafe_allow_html=True,
        )
        cols[1].markdown(
            f'<div class="big-number">{model.get("edge")}%</div>',
            unsafe_allow_html=True,
        )

        cols[2].markdown(
            '<div class="small-label">Confidence</div>',
            unsafe_allow_html=True,
        )
        cols[2].markdown(
            f'<div class="big-number">{model.get("confidence")}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        with st.container(border=True):
            render_model_health()

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
