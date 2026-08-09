"""Compact left navigation for the SharpStack application shell."""

from __future__ import annotations

import streamlit as st

from .navigation import NAVIGATION_GROUPS, navigation_item_label


def _group_widget_key(group_key: str) -> str:
    return f"shell-navigation-{group_key}"


def _select_page(group_key: str) -> None:
    """Keep the existing page state as the sole routing signal."""

    selected_page = st.session_state.get(_group_widget_key(group_key))
    if selected_page:
        st.session_state.page = selected_page


def _sync_group_selections(active_page: str) -> None:
    """Reflect the active route in exactly one expanded navigation group."""

    for group in NAVIGATION_GROUPS:
        key = _group_widget_key(group.key)
        selected_page = next(
            (item.page for item in group.items if item.page == active_page),
            None,
        )
        if st.session_state.get(key) != selected_page:
            st.session_state[key] = selected_page


def render_shell_sidebar() -> None:
    """Render navigation only; page-specific data stays in the main content."""

    active_page = st.session_state.get("page", "Dashboard")
    _sync_group_selections(active_page)

    with st.sidebar:
        st.markdown('<div class="sharpstack-sidebar-brand">SharpStack</div>', unsafe_allow_html=True)
        st.markdown('<div class="sharpstack-sidebar-subtitle">Command Center</div>', unsafe_allow_html=True)

        for group in NAVIGATION_GROUPS:
            st.markdown(
                f'<div class="sharpstack-nav-group-label">{group.label}</div>',
                unsafe_allow_html=True,
            )
            st.radio(
                group.label,
                options=tuple(item.page for item in group.items),
                index=None,
                key=_group_widget_key(group.key),
                format_func=lambda page, items=group.items: navigation_item_label(
                    page,
                    items,
                ),
                on_change=_select_page,
                args=(group.key,),
                label_visibility="collapsed",
                width="stretch",
            )

        st.markdown('<div class="sharpstack-sidebar-status">Engine Online</div>', unsafe_allow_html=True)
