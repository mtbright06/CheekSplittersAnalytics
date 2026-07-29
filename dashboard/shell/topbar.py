"""Slim global context bar for the SharpStack application shell."""

from __future__ import annotations

import streamlit as st

from version import BUILD, VERSION


def render_topbar() -> None:
    """Render shell context without duplicating page-level headers."""

    st.markdown(
        (
            '<div class="sharpstack-topbar">'
            '<span>SharpStack | Sports Analytics Platform</span>'
            f'<span>v{VERSION} | Build {BUILD}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
