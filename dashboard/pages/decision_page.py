from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from components.decision.decision_cards import (
    render_decision_card,
    render_decision_summary,
    render_decision_table,
)


ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = (
    ROOT
    / "output"
    / "cards"
    / "decision_card.json"
)


def load_decision_card() -> dict:
    if not DECISION_PATH.exists():
        return {}

    try:
        with open(
            DECISION_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def render_decisions():
    card = load_decision_card()

    st.markdown(
        '<div class="section-title">'
        "🔨 Today's Decisions"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="decision-hero">
            <div>
                <span>SHARPSTACK DECISION ENGINE</span>
                <h1>One Slate. One Ranking. No Guessing.</h1>
                <p>
                    Hammer Score combines the full-game model,
                    First 5, Bomb Lab, matchup components and
                    real market information when available.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not card:
        st.warning(
            "No Decision Engine card found. Run "
            "`python tools_build_decision_card.py`."
        )
        return

    summary = card.get("summary", {})
    decisions = card.get("decisions", [])

    render_decision_summary(summary)

    if not decisions:
        st.info("No decisions were generated.")
        return

    real_markets = summary.get(
        "real_market_games",
        0,
    )

    if real_markets == 0:
        st.warning(
            "No real sportsbook markets are loaded. "
            "All recommendations are MODEL ONLY and "
            "should not be treated as verified market edges."
        )

    tabs = st.tabs(
        [
            "Official Card",
            "Full Slate",
            "Model Agreement",
            "Market Ready",
        ]
    )

    with tabs[0]:
        actionable = [
            decision
            for decision in decisions
            if decision.get("recommendation")
            in {"HAMMER", "BET", "LEAN"}
        ]

        if not actionable:
            st.info(
                "SharpStack found no qualifying plays. "
                "The official recommendation is PASS."
            )
        else:
            for rank, decision in enumerate(
                actionable[:8],
                start=1,
            ):
                render_decision_card(
                    decision,
                    rank,
                )

    with tabs[1]:
        render_decision_table(decisions)

    with tabs[2]:
        agreement_rows = [
            decision
            for decision in decisions
            if decision.get("agreement_count", 0) >= 2
        ]

        if not agreement_rows:
            st.info(
                "No games currently have two or more "
                "supporting module signals."
            )
        else:
            for rank, decision in enumerate(
                agreement_rows,
                start=1,
            ):
                render_decision_card(
                    decision,
                    rank,
                )

    with tabs[3]:
        market_rows = [
            decision
            for decision in decisions
            if decision.get("market")
            == "REAL MARKET"
        ]

        if not market_rows:
            st.info(
                "No real market comparisons are available. "
                "Automatic odds ingestion remains the next "
                "major dependency."
            )
        else:
            render_decision_table(market_rows)
