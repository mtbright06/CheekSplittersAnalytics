import base64
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

LOGO_PATH = ASSETS / "logo.png"
MASCOT_PATH = ASSETS / "mascot.png"


def image64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def logo_html():
    if LOGO_PATH.exists():
        return f"<img src='data:image/png;base64,{image64(LOGO_PATH)}' class='logo-img' />"

    return "<div class='logo-badge'>🍑⚾</div>"


def mascot_html():
    if MASCOT_PATH.exists():
        return f"<img src='data:image/png;base64,{image64(MASCOT_PATH)}' class='mascot-img' />"

    return ""


def nav_button(label, page):
    if st.button(label, use_container_width=True, key=f"nav_{page}"):
        st.session_state.page = page


def render_header():
    header_html = (
        "<div class='app-header'>"
        "<div class='brand-row'>"
        f"{logo_html()}"
        "<div>"
        "<div class='brand-title'>SHARPSTACK</div>"
        "<div class='brand-subtitle'>Cheek Splitters Decision Support System</div>"
        "<div class='brand-tagline'>We split cheeks, not bankrolls.</div>"
        "</div>"
        "</div>"
        "<div class='logo-strip'>"
        "<span class='sport-chip'>ESPN-ish Command Center</span>"
        "<span class='sport-chip'>PrizePicks Energy</span>"
        "<span class='sport-chip'>FanDuel Edge</span>"
        "<span class='sport-chip'>Cheeks Included</span>"
        "</div>"
        f"{mascot_html()}"
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
            nav_button(label, page)


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
