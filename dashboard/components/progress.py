import streamlit as st


def clamp(value, low=0, high=100):
    if value is None:
        return 0

    try:
        value = float(value)
    except Exception:
        return 0

    return max(low, min(high, value))


def bar_color(value):
    value = clamp(value)

    if value >= 80:
        return "#8ee6a3"

    if value >= 60:
        return "#ffd976"

    if value >= 40:
        return "#ffb86b"

    return "#ff7b7b"


def render_progress_bar(label, value, suffix="/100"):
    value = clamp(value)
    color = bar_color(value)

    html = (
        "<div class='progress-wrap'>"
        "<div class='progress-top'>"
        f"<span>{label}</span>"
        f"<strong>{value:.0f}{suffix}</strong>"
        "</div>"
        "<div class='progress-track'>"
        f"<div class='progress-fill' style='width:{value}%; background:{color};'></div>"
        "</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)


def render_score_bar(label, value, max_value=1.0):
    try:
        value = float(value or 0)
    except Exception:
        value = 0

    pct = 0 if max_value == 0 else clamp((value / max_value) * 100)
    color = bar_color(pct)

    html = (
        "<div class='progress-wrap compact-progress'>"
        "<div class='progress-top'>"
        f"<span>{label}</span>"
        f"<strong>{value:.2f}</strong>"
        "</div>"
        "<div class='progress-track'>"
        f"<div class='progress-fill' style='width:{pct}%; background:{color};'></div>"
        "</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)
