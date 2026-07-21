from __future__ import annotations

import streamlit as st

from components.mlb.mlb_card import render_mlb_totals_card


def _safe(value, default="N/A"):
    if value in [None, "", "None"]:
        return default

    return value


def _format_number(value, decimals=2, default="N/A"):
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return default


def _format_percent(value, decimals=1, default="N/A"):
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return default


def _format_odds(value):
    try:
        odds = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if odds > 0:
        return f"+{odds:.0f}"

    return f"{odds:.0f}"


def _render_placeholder(title, description):
    st.markdown(f"#### {title}")
    st.info(description)


def _render_overview(game):
    model = game.get("model", {})
    odds = game.get("odds", {})
    market_edge = game.get("market_edge", {})
    totals_model = game.get("totals_model", {})

    st.markdown("#### Game Overview")

    top = st.columns(4)

    top[0].metric(
        "Recommended Play",
        _safe(model.get("play"), "No Play"),
    )
    top[1].metric(
        "Market",
        _safe(model.get("market"), "N/A"),
    )
    top[2].metric(
        "Recommendation",
        _safe(model.get("recommendation"), "PASS"),
    )
    top[3].metric(
        "Confidence",
        (
            "N/A"
            if model.get("confidence") is None
            else f"{float(model.get('confidence')):.1f}/100"
        ),
    )

    details = st.columns(4)

    details[0].metric(
        "Sportsbook",
        _safe(odds.get("sportsbook")),
    )
    details[1].metric(
        "Odds",
        _format_odds(
            odds.get("american_odds")
            or odds.get("moneyline")
        ),
    )
    details[2].metric(
        "Moneyline Edge",
        _format_percent(
            market_edge.get("edge")
            if market_edge.get("edge") is not None
            else model.get("edge"),
            decimals=2,
        ),
    )
    details[3].metric(
        "Expected ROI",
        _format_percent(
            market_edge.get("expected_roi"),
            decimals=2,
        ),
    )

    if isinstance(totals_model, dict) and totals_model:
        st.markdown("##### Totals Snapshot")

        totals = st.columns(4)

        totals[0].metric(
            "Totals Recommendation",
            _safe(totals_model.get("recommendation"), "PASS"),
        )
        totals[1].metric(
            "Projected Total",
            _format_number(totals_model.get("projected_total")),
        )
        totals[2].metric(
            "Market Total",
            _format_number(totals_model.get("market_total")),
        )
        totals[3].metric(
            "Totals Edge",
            _format_number(totals_model.get("edge")),
        )


def _render_moneyline(game):
    model = game.get("model", {})
    odds = game.get("odds", {})
    market_edge = game.get("market_edge", {})

    st.markdown("#### Moneyline Model")

    top = st.columns(4)

    top[0].metric(
        "Selection",
        _safe(
            market_edge.get("selection")
            or model.get("play"),
            "No Play",
        ),
    )
    top[1].metric(
        "Recommendation",
        _safe(model.get("recommendation"), "PASS"),
    )
    top[2].metric(
        "Sportsbook",
        _safe(
            market_edge.get("sportsbook")
            or odds.get("sportsbook")
        ),
    )
    top[3].metric(
        "Odds",
        _format_odds(
            market_edge.get("american_odds")
            or market_edge.get("moneyline")
            or odds.get("american_odds")
            or odds.get("moneyline")
        ),
    )

    metrics = st.columns(4)

    metrics[0].metric(
        "Model Probability",
        _format_percent(
            market_edge.get("model_probability")
            if market_edge.get("model_probability") is not None
            else model.get("model_probability"),
        ),
    )
    metrics[1].metric(
        "Book Probability",
        _format_percent(
            market_edge.get("book_probability")
            if market_edge.get("book_probability") is not None
            else (
                float(odds.get("book_probability")) * 100
                if odds.get("book_probability") is not None
                else None
            ),
        ),
    )
    metrics[2].metric(
        "Edge",
        _format_percent(
            market_edge.get("edge")
            if market_edge.get("edge") is not None
            else model.get("edge"),
            decimals=2,
        ),
    )
    metrics[3].metric(
        "Expected ROI",
        _format_percent(
            market_edge.get("expected_roi"),
            decimals=2,
        ),
    )

    fair_odds = market_edge.get("fair_odds")

    if fair_odds is not None:
        st.markdown(
            f"**Model fair odds:** {_format_odds(fair_odds)}"
        )

    reasons = model.get("reasons", [])

    if reasons:
        st.markdown("##### Supporting Evidence")

        for reason in reasons:
            st.markdown(
                f"<div class='reason'>✅ {reason}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No moneyline supporting evidence is available.")


def render_recommendation_explorer(game):
    if (game.get("sport") or "").lower() != "mlb":
        return

    with st.expander(
        "🧠 SharpStack Intelligence",
        expanded=False,
    ):
        (
            overview_tab,
            moneyline_tab,
            totals_tab,
            hammer_tab,
            bomb_tab,
            market_tab,
            history_tab,
        ) = st.tabs(
            [
                "Overview",
                "Moneyline",
                "Totals",
                "Hammer",
                "Bomb Lab",
                "Market",
                "History",
            ]
        )

        with overview_tab:
            _render_overview(game)

        with moneyline_tab:
            _render_moneyline(game)

        with totals_tab:
            render_mlb_totals_card(game)

        with hammer_tab:
            _render_placeholder(
                "Hammer",
                (
                    "Hammer diagnostics will be surfaced here from "
                    "existing recommendation output. No score will be "
                    "recalculated in the dashboard."
                ),
            )

        with bomb_tab:
            _render_placeholder(
                "Bomb Lab",
                (
                    "Bomb Lab matchup context will be added when its "
                    "existing game-level output is connected to the "
                    "dashboard card."
                ),
            )

        with market_tab:
            _render_placeholder(
                "Market Intelligence",
                (
                    "Sportsbook comparisons, line movement and closing-line "
                    "value will appear here after the market query contracts "
                    "are available."
                ),
            )

        with history_tab:
            _render_placeholder(
                "Recommendation History",
                (
                    "Historical recommendations, grading, ROI and model-run "
                    "context will appear here through the Azure-backed query "
                    "and analytics services."
                ),
            )
