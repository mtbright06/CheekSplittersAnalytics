from components.runtime import ensure_project_root


ensure_project_root()


import streamlit as st
from pages.best_bets_page import render_best_bets

from card_loader import (
    combined_dashboard_card,
    load_sport_card,
)
from components.footer import render_footer
from pages.dashboard_page import render_dashboard
from pages.decision_page import render_decisions
from pages.model_health_page import render_model_health_dashboard
from pages.nhl_prop_trends_page import render_nhl_prop_trends
from pages.nfl_prop_trends_page import render_nfl_prop_trends
from pages.placeholder_pages import (
    render_bomb_lab,
    render_first5,
    render_hall,
    render_kbo,
    render_mlb,
    render_settings,
)
from shell import initialize_shell, render_application_shell
from styles import CSS


st.set_page_config(
    page_title="SharpStack",
    page_icon="🍑",
    layout="wide",
)


initialize_shell()


st.markdown(
    CSS,
    unsafe_allow_html=True,
)


def render_page():
    page = st.session_state.page

    if page == "Dashboard":
        dashboard_card = combined_dashboard_card()
        render_dashboard(
            dashboard_card
        )
        if not dashboard_card.get("games"):
            st.warning(
                "No cards found. Run an "
                "engine/build script first."
            )

    elif page == "Best Bets":
        render_best_bets()

    elif page == "Decisions":
        render_decisions()

    elif page == "Model Health":
        render_model_health_dashboard()

    elif page == "MLB":
        mlb_card = load_sport_card("mlb")

        if mlb_card:
            render_dashboard(mlb_card)
        else:
            render_mlb()

    elif page == "KBO":
        kbo_card = load_sport_card("kbo")

        if kbo_card:
            render_dashboard(kbo_card)
        else:
            render_kbo()

    elif page == "Bomb Lab":
        render_bomb_lab()

    elif page == "First 5":
        render_first5()

    elif page == "Props":
        render_nhl_prop_trends()

    elif page == "NFL Props":
        render_nfl_prop_trends()

    elif page == "Hall":
        render_hall()

    elif page == "Settings":
        render_settings()


render_application_shell()

render_page()
render_footer()
