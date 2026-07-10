import streamlit as st

from card_loader import combined_dashboard_card, load_sport_card
from components.footer import render_footer
from components.ui import render_header, render_sidebar
from pages.dashboard_page import render_dashboard
from pages.placeholder_pages import (
    render_bomb_lab,
    render_first5,
    render_hall,
    render_kbo,
    render_mlb,
    render_props,
    render_settings,
)
from styles import CSS


st.set_page_config(
    page_title="SharpStack",
    page_icon="🍑",
    layout="wide",
)


if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


st.markdown(CSS, unsafe_allow_html=True)


def render_page():
    page = st.session_state.page

    if page == "Dashboard":
        render_dashboard(combined_dashboard_card())

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
        render_props()

    elif page == "Hall":
        render_hall()

    elif page == "Settings":
        render_settings()

    else:
        st.warning(f"Unknown page: {page}")
        st.session_state.page = "Dashboard"
        st.rerun()


dashboard_card = combined_dashboard_card()

render_header()
render_sidebar(dashboard_card)

if not dashboard_card.get("games"):
    st.warning("No cards found. Run an engine/build script first.")

render_page()
render_footer()
