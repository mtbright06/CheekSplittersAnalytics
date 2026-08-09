from __future__ import annotations

import streamlit as st

from components.page_header import render_compact_header


def render_decisions():
    render_compact_header(
        "🔨",
        "Decisions",
        "Under redesign. Current betting cards remain in Best Bets, MLB, and KBO.",
    )

    st.info(
        "This page is intentionally paused while its unique role is redesigned."
    )
