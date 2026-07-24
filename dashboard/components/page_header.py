from __future__ import annotations

from typing import Any

import streamlit as st


def render_compact_header(
    icon: str,
    title: str,
    description: str | None = None,
    metrics: list[tuple[str, Any]] | None = None,
):
    """Render a dense, consistent page header above operational data."""
    metrics = metrics or []
    columns = st.columns([2.4] + [1] * len(metrics))

    with columns[0]:
        st.markdown(
            f'<div class="section-title compact-page-title">{icon} {title}</div>',
            unsafe_allow_html=True,
        )
        if description:
            st.caption(description)

    for column, (label, value) in zip(columns[1:], metrics):
        with column:
            st.metric(label, value)
