from __future__ import annotations

from typing import Any

import streamlit as st


def render_data_table(
    data: Any,
    *,
    column_config: Any | None = None,
    height: int | None = None,
    key: str | None = None,
    selection_mode: str | None = None,
    on_select: str | None = None,
    css_class: str = "ss-data-table",
) -> Any:
    """Render a native Streamlit dataframe with SharpStack table styling."""

    st.markdown(
        f'<div class="{css_class}"></div>',
        unsafe_allow_html=True,
    )

    options: dict[str, Any] = {
        "width": "stretch",
        "hide_index": True,
    }

    if column_config is not None:
        options["column_config"] = column_config

    if height is not None:
        options["height"] = height

    if key is not None:
        options["key"] = key

    if selection_mode is not None:
        options["selection_mode"] = selection_mode

    if on_select is not None:
        options["on_select"] = on_select

    return st.dataframe(
        data,
        **options,
    )
