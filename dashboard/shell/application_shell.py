"""Application-shell coordinator for existing SharpStack pages."""

from __future__ import annotations

import streamlit as st

from .sidebar import render_shell_sidebar
from .styles import render_shell_styles
from .topbar import render_topbar


def initialize_shell() -> None:
    """Initialize shell-owned state before route dispatch."""

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"


def render_application_shell() -> None:
    """Render only global chrome; pages retain their current internals."""

    render_shell_styles()
    render_shell_sidebar()
    render_topbar()
