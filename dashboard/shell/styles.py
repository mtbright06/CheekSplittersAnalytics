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

.sharpstack-sidebar-brand {
    color: var(--ss-color-text-primary);
    font-size: var(--ss-font-body);
    font-weight: 800;
    margin: 0 0 var(--ss-space-1);
}

.sharpstack-sidebar-subtitle {
    color: var(--ss-color-text-secondary);
    font-size: var(--ss-font-caption);
    margin: 0 0 var(--ss-space-5);
}

.sharpstack-nav-group-label {
    color: var(--ss-color-text-secondary);
    font-size: var(--ss-font-caption);
    font-weight: 700;
    letter-spacing: 0.08em;
    margin: var(--ss-space-4) 0 var(--ss-space-1);
    text-transform: uppercase;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: var(--ss-space-1);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    align-items: center;
    border-left: 3px solid transparent;
    border-radius: var(--ss-radius-md);
    color: var(--ss-color-text-secondary);
    min-height: var(--ss-size-control-compact);
    margin: 0;
    padding: 0 var(--ss-space-2);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: color-mix(in srgb, var(--ss-color-accent) 10%, transparent);
    color: var(--ss-color-text-primary);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: color-mix(in srgb, var(--ss-color-accent) 16%, transparent);
    border-left-color: var(--ss-color-accent);
    color: var(--ss-color-text-primary);
    font-weight: 700;
}

[data-testid="stSidebar"] [data-testid="stRadio"] input {
    opacity: 0;
    position: absolute;
}

.sharpstack-sidebar-status {
    border-top: 1px solid var(--ss-color-border);
    color: var(--ss-color-success);
    font-size: var(--ss-font-caption);
    margin-top: var(--ss-space-5);
    padding-top: var(--ss-space-2);
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
