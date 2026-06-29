import streamlit as st


def safe_float(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def value_color(edge):
    edge = safe_float(edge)

    if edge >= 8:
        return "#8ee6a3"

    if edge >= 4:
        return "#ffd976"

    if edge >= 1:
        return "#ffb86b"

    return "#ff7b7b"


def render_value_meter(game):
    model = game.get("model", {})
    odds = game.get("odds", {})

    book_prob = clamp(safe_float(odds.get("book_probability")))
    model_prob = clamp(safe_float(model.get("model_probability")))
    edge = safe_float(model.get("edge"))
    color = value_color(edge)

    html = (
        "<div class='value-meter'>"
        "<div class='value-title'>Market vs Model</div>"

        "<div class='value-row'>"
        "<div class='value-label'>Book Win %</div>"
        "<div class='value-track'>"
        f"<div class='value-fill book-fill' style='width:{book_prob}%;'></div>"
        "</div>"
        f"<div class='value-number'>{book_prob:.1f}%</div>"
        "</div>"

        "<div class='value-row'>"
        "<div class='value-label'>Model Win %</div>"
        "<div class='value-track'>"
        f"<div class='value-fill' style='width:{model_prob}%; background:{color};'></div>"
        "</div>"
        f"<div class='value-number'>{model_prob:.1f}%</div>"
        "</div>"

        "<div class='value-edge'>"
        f"<span>Value Edge</span><strong style='color:{color};'>{edge:+.1f}%</strong>"
        "</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)
