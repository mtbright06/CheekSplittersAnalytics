import json
from pathlib import Path

import streamlit as st

from components.ui import render_header, render_sidebar
from pages.dashboard_page import render_dashboard
from pages.placeholder_pages import (
    render_bomb_lab,
    render_hall,
    render_kbo,
    render_mlb,
    render_props,
    render_settings,
)
from styles import CSS


ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "output" / "sharpstack_card.json"


st.set_page_config(
    page_title="SharpStack",
    page_icon="🍑",
    layout="wide",
)


if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


st.markdown(CSS, unsafe_allow_html=True)


def load_card():
    if not CARD_PATH.exists():
        return None

    with open(CARD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def render_page(card):
    page = st.session_state.page

    if page == "Dashboard":
        render_dashboard(card)
    elif page == "MLB":
        render_mlb()
    elif page == "KBO":
        render_kbo()
    elif page == "Bomb Lab":
        render_bomb_lab()
    elif page == "Props":
        render_props()
    elif page == "Hall":
        render_hall()
    elif page == "Settings":
        render_settings()


card = load_card()

render_header()
render_sidebar(card)

if card is None:
    st.warning("No JSON card found. Run `python cheek_splitters_engine.py` first.")
    st.stop()

render_page(card)

from components.footer import render_footer
render_footer()
