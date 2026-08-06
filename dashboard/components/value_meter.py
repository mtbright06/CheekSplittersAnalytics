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
    st.markdown(
        value_meter_html(game),
        unsafe_allow_html=True,
    )


def value_meter_html(game):
    model = game.get("model", {})
    odds = game.get("odds", {})

    raw_book_probability = odds.get("book_probability")
    raw_model_probability = model.get("model_probability")
    raw_edge = model.get("edge")

    book_prob = clamp(as_percentage(raw_book_probability))
    model_prob = clamp(as_percentage(raw_model_probability))
    edge = safe_float(raw_edge)
    color = value_color(edge)
    market_available = raw_book_probability is not None

    if str(game.get("sport") or "").lower() == "kbo":
        return (
            "<div class='value-meter model-analysis'>"
            "<div class='value-title'>Model Assessment</div>"
            "<div class='value-row'>"
            "<div class='value-label'>Model Score</div>"
            "<div class='value-track'>"
            f"<div class='value-fill' style='width:{model_prob}%; background:#7cb5ff;'></div>"
            "</div>"
            f"<div class='value-number'>{model_prob:.1f}%</div>"
            "</div>"
            "</div>"
        )

    if not market_available:
        st.info(
            "Model-only view: sportsbook price and market edge are unavailable."
        )

    book_value = f"{book_prob:.1f}%" if market_available else "Unavailable"
    edge_value = f"{edge:+.1f}%" if market_available and raw_edge is not None else "Unavailable"

    html = (
        "<div class='value-meter'>"
        "<div class='value-title'>Market vs Model</div>"

        "<div class='value-row'>"
        "<div class='value-label'>Book Win %</div>"
        "<div class='value-track'>"
        f"<div class='value-fill book-fill' style='width:{book_prob}%;'></div>"
        "</div>"
        f"<div class='value-number'>{book_value}</div>"
        "</div>"

        "<div class='value-row'>"
        "<div class='value-label'>Model Win Strength</div>"
        "<div class='value-track'>"
        f"<div class='value-fill' style='width:{model_prob}%; background:#7cb5ff;'></div>"
        "</div>"
        f"<div class='value-number'>{model_prob:.1f}%</div>"
        "</div>"

        "<div class='value-edge'>"
        f"<span>Value Edge</span><strong style='color:{color};'>{edge_value}</strong>"
        "</div>"
        "</div>"
    )

    return html


def as_percentage(value):
    number = safe_float(value)
    return number * 100 if abs(number) <= 1 else number
