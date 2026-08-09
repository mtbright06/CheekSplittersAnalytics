from pathlib import Path
import base64

import streamlit as st

from components.page_header import render_compact_header

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

    labels = [
        ("🏠 Dashboard", "Dashboard"),
        ("🏆Best Bets", "Best Bets"),
        ("⚾ MLB", "MLB"),
        ("🇰🇷 KBO", "KBO"),
        ("💣 Bomb Lab", "Bomb Lab"),
        ("🔨 Decisions", "Decisions"),
        ("📊 Model Health", "Model Health"),
        ("🎯 Props", "Props"),
        ("🎯 First 5", "First 5"),
        ("🏆 Hall", "Hall"),
        ("⚙ Settings", "Settings"),
    ]

    for start in range(0, len(labels), 7):
        columns = st.columns(7)
        for column, item in zip(columns, labels[start : start + 7]):
            with column:
                if st.button(item[0], width="stretch"):
                    st.session_state.page = item[1]


def render_placeholder(title, subtitle, body):
    render_compact_header(title.split()[0], title, subtitle)
    st.markdown(body)
