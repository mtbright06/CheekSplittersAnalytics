"""Shell-only styling for navigation and global context chrome."""

from __future__ import annotations

import streamlit as st


SHELL_CSS = """
<style>
[data-testid="stSidebar"][aria-expanded="true"] {
    min-width: 240px;
    max-width: 240px;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 0.75rem 0.65rem;
}

[data-testid="stSidebar"] div.stButton {
    margin: 0 0 0.2rem;
}

[data-testid="stSidebar"] div.stButton > button {
    min-height: 36px;
    border-radius: 7px;
    justify-content: flex-start;
    padding: 0.35rem 0.65rem;
    text-align: left;
}

.sharpstack-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 42px;
    margin: 0 0 0.85rem;
    padding: 0.25rem 0 0.5rem;
    border-bottom: 1px solid rgba(160, 190, 230, 0.16);
    color: #b9c7dc;
    font-size: 0.8rem;
}
</style>
"""


def render_shell_styles() -> None:
    """Apply styles limited to the application shell."""

    st.markdown(SHELL_CSS, unsafe_allow_html=True)
