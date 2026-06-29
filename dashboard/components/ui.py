from pathlib import Path
import base64

import streamlit as st

from version import VERSION, BUILD, SPORT


ROOT = Path(__file__).resolve().parents[2]


def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def load_logo():
    logo = ROOT / "assets" / "logo.png"

    if logo.exists():
        return image64(logo)

    return None


def load_splitter():
    mascot = ROOT / "assets" / "mascot.png"

    if mascot.exists():
        return image64(mascot)

    return None


def render_header():
    logo = load_logo()
    splitter = load_splitter()

    logo_html = ""
    if logo:
        logo_html = (
            f"<img src='data:image/png;base64,{logo}' "
            "class='logo-img'>"
        )

    mascot_html = ""
    if splitter:
        mascot_html = (
            f"<img src='data:image/png;base64,{splitter}' "
            "class='mascot-img'>"
        )

    header_html = (
        "<div class='app-header'>"
        f"{mascot_html}"
        "<div class='version-chip'>"
        f"v{VERSION}<br>Build {BUILD}"
        "</div>"
        "<div class='brand-row'>"
        f"{logo_html}"
        "<div>"
        "<div class='brand-title'>SharpStack</div>"
        "<div class='brand-subtitle'>Sports Analytics Platform</div>"
        "<div class='header-status-row'>"
        f"<span class='status-pill good'>🟢 {SPORT}</span>"
        "<span class='status-pill good'>🟢 Model Ready</span>"
        "<span class='status-pill warn'>🟡 Odds Soon</span>"
        "<span class='status-pill off'>⚫ Weather Phase 3</span>"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )

    st.markdown(header_html, unsafe_allow_html=True)

    nav = st.columns(7)

    pages = [
        ("🏠 Dashboard", "Dashboard"),
        ("⚾ MLB", "MLB"),
        ("🇰🇷 KBO", "KBO"),
        ("💣 Bomb Lab", "Bomb Lab"),
        ("🎯 Props", "Props"),
        ("🏆 Hall", "Hall"),
        ("⚙ Settings", "Settings"),
    ]

    for column, (label, page) in zip(nav, pages):
        with column:
            if st.button(label, use_container_width=True, key=f"nav_{page}"):
                st.session_state.page = page


def render_sidebar(card):
    st.sidebar.markdown("## SHARPSTACK")
    st.sidebar.caption("Cheeks operational.")

    if card:
        st.sidebar.metric("Sport", card.get("sport") or "N/A")
        st.sidebar.metric("Version", card.get("version") or "N/A")
        st.sidebar.write(f"Generated: {card.get('generated_at')}")
    else:
        st.sidebar.warning("No card loaded.")

    st.sidebar.markdown("---")
    st.sidebar.write("🍑 Mode: Professional Nonsense")
    st.sidebar.write("🔥 Status: Online")
    st.sidebar.write("🍺 Beer: Recommended")


def render_placeholder(title, subtitle, body):
    html = (
        "<div class='placeholder-card'>"
        f"<div class='section-title'>{title}</div>"
        f"<div class='muted'>{subtitle}</div>"
        "<br>"
        f"<div>{body}</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)
