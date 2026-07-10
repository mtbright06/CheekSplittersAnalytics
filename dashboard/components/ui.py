from pathlib import Path
import base64

import streamlit as st

from components.sidebar import render_sidebar
from version import VERSION, BUILD, SPORT

ROOT = Path(__file__).resolve().parents[2]


def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def load_logo():
    path = ROOT / "assets" / "logo.png"
    return image64(path) if path.exists() else None


def load_splitter():
    path = ROOT / "assets" / "mascot.png"
    return image64(path) if path.exists() else None


def render_header():
    logo = load_logo()
    mascot = load_splitter()

    html = f"""
<div class="app-header">

{"<img src='data:image/png;base64,"+mascot+"' class='mascot-img'>" if mascot else ""}

<div class="version-chip">
v{VERSION}<br>
Build {BUILD}
</div>

<div class="brand-row">

{"<img src='data:image/png;base64,"+logo+"' class='logo-img'>" if logo else ""}

<div>

<div class="brand-title">
SharpStack
</div>

<div class="brand-subtitle">
Sports Analytics Platform
</div>

<div class="header-status-row">

<span class="status-pill good">
🟢 {SPORT}
</span>

<span class="status-pill good">
🟢 Engine Ready
</span>

<span class="status-pill warn">
🟡 Odds Soon
</span>

<span class="status-pill off">
⚫ Weather Phase 3
</span>

</div>

</div>

</div>

</div>
"""

    st.markdown(html, unsafe_allow_html=True)

    cols = st.columns(7)

    labels = [
        ("🏠 Dashboard", "Dashboard"),
        ("⚾ MLB", "MLB"),
        ("🇰🇷 KBO", "KBO"),
        ("💣 Bomb Lab", "Bomb Lab"),
        ("🎯 Props", "Props"),
        ("🎯 First 5", "First 5"),
        ("🏆 Hall", "Hall"),
        ("⚙ Settings", "Settings"),
    ]

    for c, item in zip(cols, labels):
        with c:
            if st.button(item[0],
                         width="stretch"):
                st.session_state.page = item[1]


def render_placeholder(title, subtitle, body):

    st.markdown(
        f"""
<div class="lab-hero">

<div class="lab-title">
{title}
</div>

<div class="lab-subtitle">
{subtitle}
</div>

<div class="lab-badge">

ROADMAP MODULE

</div>

</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(body)
