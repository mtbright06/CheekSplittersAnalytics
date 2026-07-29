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
    display: flex;
    flex-direction: column;
    padding: var(--ss-space-2) var(--ss-space-3);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] > [data-testid="stVerticalBlock"] {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 0 !important;
    min-height: 100%;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:last-child {
    margin-top: auto;
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
    margin: 0 0 var(--ss-space-3);
}

.sharpstack-nav-group-label {
    color: var(--ss-color-text-secondary);
    font-size: var(--ss-font-caption);
    font-weight: 700;
    letter-spacing: 0.08em;
    margin: var(--ss-space-2) 0 var(--ss-space-1);
    text-transform: uppercase;
}

[data-testid="stSidebar"] [data-testid="stRadio"] {
    margin: 0;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] {
    gap: var(--ss-space-1) !important;
    min-height: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] [data-baseweb="radio"] {
    align-items: center;
    border-left: 3px solid transparent;
    border-radius: var(--ss-radius-md);
    color: var(--ss-color-text-secondary);
    display: flex;
    min-height: var(--ss-size-control-compact);
    margin: 0;
    padding: 0 var(--ss-space-2);
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] [data-baseweb="radio"]:hover {
    background: color-mix(in srgb, var(--ss-color-accent) 10%, transparent);
    color: var(--ss-color-text-primary);
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] [data-baseweb="radio"]:has(input:checked) {
    background: color-mix(in srgb, var(--ss-color-accent) 16%, transparent);
    border-left-color: var(--ss-color-accent);
    color: var(--ss-color-text-primary);
    font-weight: 700;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] [data-baseweb="radio"] > div:first-child,
[data-testid="stSidebar"] [data-testid="stRadioGroup"] input {
    opacity: 0;
    position: absolute;
}

.sharpstack-sidebar-status {
    border-top: 1px solid var(--ss-color-border);
    color: var(--ss-color-success);
    font-size: var(--ss-font-caption);
    margin-top: var(--ss-space-4);
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
