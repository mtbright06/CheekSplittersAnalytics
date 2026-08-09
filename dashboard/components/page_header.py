from __future__ import annotations

from typing import Any
import html

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


def render_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    eyebrow: str | None = None,
    status_html: str | None = None,
    metrics: list[tuple[str, Any]] | None = None,
) -> None:
    """Render the standard SharpStack page header pattern."""

    metrics = metrics or []
    columns = st.columns([2.4] + [1] * len(metrics))

    with columns[0]:
        st.markdown(
            page_header_html(
                title,
                subtitle,
                eyebrow=eyebrow,
                status_html=status_html,
            ),
            unsafe_allow_html=True,
        )

    for column, (label, value) in zip(columns[1:], metrics):
        with column:
            st.metric(label, value)


def page_header_html(
    title: str,
    subtitle: str | None = None,
    *,
    eyebrow: str | None = None,
    status_html: str | None = None,
) -> str:
    """Return safe HTML for the standard SharpStack page header."""

    eyebrow_html = (
        "<div class='ss-page-header__eyebrow'>"
        f"{html.escape(str(eyebrow).strip().upper())}</div>"
        if eyebrow
        else ""
    )
    status_markup = (
        f"<div class='ss-page-header__status'>{status_html}</div>"
        if status_html
        else ""
    )
    subtitle_html = (
        "<div class='ss-page-header__subtitle'>"
        f"{html.escape(str(subtitle))}</div>"
        if subtitle
        else ""
    )

    return (
        "<div class='ss-page-header'>"
        f"{eyebrow_html}"
        "<div class='ss-page-header__title-row'>"
        f"<div class='ss-page-header__title'>{html.escape(str(title))}</div>"
        f"{status_markup}"
        "</div>"
        f"{subtitle_html}"
        "</div>"
    )
