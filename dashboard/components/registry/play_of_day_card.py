from __future__ import annotations

import html
from typing import Any

import streamlit as st

def compact_html(value):
    return "\n".join(
        line.strip()
        for line in value.splitlines()
        if line.strip()
    )

def esc(
    value: Any,
    default: str = "N/A",
) -> str:
    if value in [
        None,
        "",
        "None",
    ]:
        value = default

    return html.escape(
        str(value)
    )


def number(
    value: Any,
    decimals: int = 1,
    default: str = "N/A",
) -> str:
    try:
        return (
            f"{float(value):.{decimals}f}"
        )
    except (
        TypeError,
        ValueError,
    ):
        return default


def percent(
    value: Any,
    *,
    signed: bool = False,
) -> str:
    try:
        number_value = float(
            value
        )

        if abs(number_value) <= 1:
            number_value *= 100

        prefix = (
            "+"
            if signed
            and number_value > 0
            else ""
        )

        return (
            f"{prefix}{number_value:.1f}%"
        )
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def american(
    value: Any,
) -> str:
    try:
        odds = int(
            round(float(value))
        )

        if odds > 0:
            return f"+{odds}"

        return str(odds)
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def render_play_of_day(
    play_data: dict,
) -> None:
    recommendation = (
        play_data.get(
            "recommendation"
        )
    )

    st.markdown(
        "## 🔥 Play of the Day"
    )

    if not recommendation:
        st.info(
            play_data.get(
                "reason",
                "No Play of the Day "
                "is available.",
            )
        )
        return

    quote = recommendation.get(
        "market_quote",
        {},
    )

    consensus = (
        recommendation.get(
            "source_signals",
            {},
        ).get(
            "consensus",
            {},
        )
    )

    support_count = (
        consensus.get(
            "support_count",
            0,
        )
    )

    available_count = (
        consensus.get(
            "available_count",
            0,
        )
    )

    market_label = (
        "REAL MARKET"
        if recommendation.get(
            "real_market_loaded"
        )
        else "MODEL ONLY"
    )

    card = f"""
    <div class="decision-card decision-hammer">
        <div class="decision-top-row play-day-top-row">
            <div class="decision-main">
                <div class="decision-kicker">
                    PLAY OF THE DAY
                    <span>
                        {esc(recommendation.get("league"))}
                        &middot;
                        {esc(recommendation.get("market"))}
                        &middot;
                        {market_label}
                    </span>
                </div>

                <div class="decision-team">
                    {esc(recommendation.get("selection"))}
                </div>

                <div class="decision-matchup">
                    {esc(recommendation.get("matchup"))}
                </div>

                <div class="decision-stars">
                    {esc(recommendation.get("stars"), "")}
                </div>
            </div>

            <div class="decision-score">
                <span>Hammer Score</span>
                <strong>
                    {number(recommendation.get("hammer_score"))}
                </strong>
                <small>
                    {esc(recommendation.get("recommendation"))}
                </small>
            </div>
        </div>

        <div class="decision-metrics">
            <div>
                <span>Consensus</span>
                <strong>
                    {support_count}/{available_count}
                </strong>
            </div>

            <div>
                <span>Agreement</span>
                <strong>
                    {percent(consensus.get("agreement_pct"))}
                </strong>
            </div>

            <div>
                <span>Model Win</span>
                <strong>
                    {percent(recommendation.get("model_probability"))}
                </strong>
            </div>

            <div>
                <span>Edge</span>
                <strong>
                    {percent(recommendation.get("edge_pct"), signed=True)}
                </strong>
            </div>

            <div>
                <span>EV</span>
                <strong>
                    {percent(recommendation.get("expected_value_pct"), signed=True)}
                </strong>
            </div>

            <div>
                <span>Best Price</span>
                <strong>
                    {american(quote.get("odds"))}
                </strong>
            </div>
        </div>
    </div>
    """

    st.markdown(
        compact_html(card),
        unsafe_allow_html=True,
    )

    st.caption(
        play_data.get(
            "reason",
            "",
        )
    )

    if not recommendation.get(
        "real_market_loaded"
    ):
        st.warning(
            "This is currently a model-only "
            "selection. Confirm a real sportsbook "
            "price before treating it as actionable."
        )
