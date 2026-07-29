"""Shell-only styling for navigation and global context chrome."""

from __future__ import annotations

import streamlit as st


SHELL_CSS = """
<style>
[data-testid="stSidebar"][aria-expanded="true"] {
    min-width: var(--ss-size-sidebar);
    max-width: var(--ss-size-sidebar);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: var(--ss-space-3) var(--ss-space-3);
}

[data-testid="stSidebar"] div.stButton {
    margin: 0 0 var(--ss-space-1);
}

[data-testid="stSidebar"] div.stButton > button {
    min-height: var(--ss-size-control-compact);
    border-radius: var(--ss-radius-lg);
    justify-content: flex-start;
    padding: var(--ss-space-1) var(--ss-space-3);
    text-align: left;
}

.sharpstack-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: var(--ss-size-topbar-min-height);
    margin: 0 0 var(--ss-space-3);
    padding: var(--ss-space-1) 0 var(--ss-space-2);
    border-bottom: 1px solid var(--ss-color-border);
    color: var(--ss-color-text-secondary);
    font-size: var(--ss-font-caption);
}
</style>
"""


def render_shell_styles() -> None:
    """Apply styles limited to the application shell."""

    st.markdown(SHELL_CSS, unsafe_allow_html=True)
