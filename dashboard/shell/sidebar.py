"""Compact left navigation for the SharpStack application shell."""

from __future__ import annotations

import streamlit as st

from .navigation import NAVIGATION_GROUPS


def render_shell_sidebar() -> None:
    """Render navigation only; page-specific data stays in the main content."""

    active_page = st.session_state.get("page", "Dashboard")

    with st.sidebar:
        st.markdown("### SharpStack")
        st.caption("Command Center")

        for group, entries in NAVIGATION_GROUPS:
            st.caption(group.upper())
            for label, page in entries:
                if st.button(
                    label,
                    key=f"shell-navigation-{page}",
                    type="primary" if page == active_page else "secondary",
                    width="stretch",
                ):
                    st.session_state.page = page
                    st.rerun()

        st.caption("Engine Online")
