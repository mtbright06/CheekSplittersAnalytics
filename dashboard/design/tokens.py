"""Canonical frontend tokens exposed as CSS custom properties."""

from __future__ import annotations

import streamlit as st


DESIGN_TOKENS_CSS = """
<style>
:root {
    --ss-color-app-background: #080d14;
    --ss-color-panel: #101827;
    --ss-color-panel-muted: #0d1420;
    --ss-color-border: rgba(160, 190, 230, 0.16);
    --ss-color-text-primary: #f5f7fb;
    --ss-color-text-secondary: #b9c7dc;
    --ss-color-accent: #7cb5ff;
    --ss-color-success: #9cffb0;
    --ss-color-warning: #ffd976;
    --ss-color-danger: #ffb0b0;
    --ss-color-neutral: #aebbd0;
    --ss-shadow-panel: 0 14px 36px rgba(0, 0, 0, 0.28);

    --ss-space-1: 4px;
    --ss-space-2: 8px;
    --ss-space-3: 12px;
    --ss-space-4: 16px;
    --ss-space-5: 24px;
    --ss-space-6: 32px;
    --ss-space-7: 48px;

    --ss-radius-sm: 4px;
    --ss-radius-md: 6px;
    --ss-radius-lg: 8px;

    --ss-font-page-title: 28px;
    --ss-font-section-title: 20px;
    --ss-font-body: 14px;
    --ss-font-label: 12px;
    --ss-font-caption: 12px;
    --ss-font-metric: 30px;

    --ss-size-sidebar: 240px;
    --ss-size-topbar-min-height: 42px;
    --ss-size-control-compact: 32px;
    --ss-size-control-default: 42px;
    --ss-size-table-row: 40px;
    --ss-size-metric-card-min-height: 108px;
}
</style>
"""


def render_design_tokens() -> None:
    """Make the shared token set available to the current page."""

    st.markdown(DESIGN_TOKENS_CSS, unsafe_allow_html=True)
