import base64
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[2]
LOGO_PATH = ROOT / "assets" / "logo.png"


def logo_base64():
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def logo_html():
    if LOGO_PATH.exists():
        return f'<img src="data:image/png;base64,{logo_base64()}" class="logo-img" />'

    return '<div class="logo-badge">🍑⚾</div>'


def nav_button(label, page):
    if st.button(label, use_container_width=True, key=f"nav_{page}"):
        st.session_state.page = page


def render_header():
    st.markdown(
        f"""
        <div class="app-header">
            <div class="brand-row">
                {logo_html()}
                <div>
                    <div class="brand-title">SHARPSTACK</div>
                    <div class="brand-subtitle">Cheek Splitters Decision Support System</div>
                    <div class="brand-tagline">We split cheeks, not bankrolls.</div>
                </div>
            </div>
            <div class="logo-strip">
                <span class="sport-chip">ESPN-ish Command Center</span>
                <span class="sport-chip">PrizePicks Energy</span>
                <span class="sport-chip">FanDuel Edge</span>
                <span class="sport-chip">Cheeks Included</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    st.markdown(
        f"""
        <div class="placeholder-card">
            <div class="section-title">{title}</div>
            <div class="muted">{subtitle}</div>
            <br>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
