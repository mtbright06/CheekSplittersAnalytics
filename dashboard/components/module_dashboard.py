import streamlit as st

from components.page_header import render_compact_header


STATUS = {
    "complete": ("🟢", "Complete", "module-complete"),
    "next": ("🟡", "Next", "module-next"),
    "planned": ("⚫", "Planned", "module-planned"),
}


def render_module_dashboard(icon, title, subtitle, badge, sections):
    render_compact_header(
        icon,
        title,
        subtitle,
        [("Status", badge)],
    )

    cols = st.columns(len(sections))

    for col, section in zip(cols, sections):
        with col:
            render_module_section(section)


def render_module_section(section):
    st.markdown(
        f"""
<div class="module-card">
    <div class="module-card-title">{section["title"]}</div>
""",
        unsafe_allow_html=True,
    )

    for label, status in section["items"]:
        icon, text, css = STATUS.get(status, STATUS["planned"])

        st.markdown(
            f"""
<div class="module-row">
    <span>{icon} {label}</span>
    <strong class="{css}">{text}</strong>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
