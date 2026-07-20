import streamlit as st

from engine.mlb.totals.explanation import TotalsExplanation
from engine.mlb.totals.explanation_renderer import (
    render_totals_explanation_compact,
)


def _format_number(value, *, signed=False):
    if value is None:
        return "N/A"

    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:.2f}"


def _compact_explanation(totals_model):
    payload = totals_model.get("explanation")

    if not isinstance(payload, dict):
        return None

    try:
        explanation = TotalsExplanation.from_dict(payload)
    except (KeyError, TypeError, ValueError):
        return None

    return render_totals_explanation_compact(explanation)


def render_mlb_totals_card(game):
    totals_model = game.get("totals_model")

    if not isinstance(totals_model, dict):
        return

    recommendation = totals_model.get("recommendation") or "PASS"
    selection = totals_model.get("selection") or "NONE"
    explanation = _compact_explanation(totals_model)
    confidence = totals_model.get("confidence")

    st.markdown("#### Totals Model")

    top = st.columns(3)
    top[0].metric("Recommendation", recommendation)
    top[1].metric("Selection", selection)
    top[2].metric(
        "Confidence",
        "N/A" if confidence is None else f"{confidence:.1f}/100",
    )

    metrics = st.columns(3)
    metrics[0].metric(
        "Projected Total",
        _format_number(totals_model.get("projected_total")),
    )
    metrics[1].metric(
        "Market Total",
        _format_number(totals_model.get("market_total")),
    )
    metrics[2].metric(
        "Edge",
        _format_number(totals_model.get("edge"), signed=True),
    )

    if explanation:
        st.markdown(
            f"<div class='reason'>{explanation}</div>",
            unsafe_allow_html=True,
        )
