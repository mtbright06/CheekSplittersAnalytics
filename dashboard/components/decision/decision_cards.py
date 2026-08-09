from __future__ import annotations
from typing import Any
import pandas as pd
import streamlit as st

from components.confirmation import (
    hammer_confirmation_label,
)

def safe(value: Any, default: str = "N/A") -> str:
    if value in [None, "", "None"]:
        return default

    return str(value)


def number(
    value: Any,
    decimals: int = 1,
    default: str = "N/A",
) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return default


def percent(
    value: Any,
    decimals: int = 1,
    default: str = "N/A",
) -> str:
    try:
        number_value = float(value)

        if number_value <= 1:
            number_value *= 100

        return f"{number_value:.{decimals}f}%"
    except (TypeError, ValueError):
        return default


def signed_percent(
    value: Any,
    decimals: int = 1,
) -> str:
    try:
        return f"{float(value):+.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def american(value: Any) -> str:
    try:
        odds = int(round(float(value)))

        if odds > 0:
            return f"+{odds}"

        return str(odds)
    except (TypeError, ValueError):
        return "N/A"


def render_decision_summary(
    summary: dict,
    *,
    top_decision: dict | None = None,
):
    columns = st.columns(6)

    columns[0].metric(
        "Games",
        summary.get("games_loaded", 0),
    )

    columns[1].metric(
        "Actionable",
        summary.get("actionable", 0),
    )

    columns[2].metric(
        "Hammers",
        summary.get("hammer_plays", 0),
    )

    columns[3].metric(
        "Bets",
        summary.get("bets", 0),
    )

    columns[4].metric(
        "Real Markets",
        summary.get("real_market_games", 0),
    )

    top_label = "Unavailable"
    top_status = "No decision rows"

    if isinstance(top_decision, dict):
        top_label = top_decision.get("selected_team") or "Unavailable"
        top_status = (
            f"{top_decision.get('recommendation') or 'PASS'} · "
            f"{top_decision.get('market') or 'MODEL ONLY'}"
        )

    columns[5].metric(
        "Top Model Signal",
        top_label,
        top_status,
    )


def render_decision_card(
    decision: dict,
    rank: int,
):
    recommendation = decision.get(
        "recommendation",
        "PASS",
    )

    score = decision.get("hammer_score", 0)
    market_status = decision.get(
        "market_status",
        decision.get("market", "MODEL ONLY"),
    )

    recommendation_class = (
        str(recommendation)
        .lower()
        .replace(" ", "-")
    )

    with st.expander(
        (
            f"#{rank} {safe(decision.get('matchup'))} · "
            f"{safe(recommendation, 'PASS')} · {safe(market_status)}"
        ),
        expanded=False,
    ):
        render_decision_details(decision)


def render_decision_details(decision: dict):
    """Render the canonical Decision Builder explanation without an expander."""
    recommendation_columns = st.columns(4)
    recommendation_columns[0].metric(
        "Model Recommendation",
        safe(
            decision.get("model_recommendation")
            or decision.get("recommendation"),
            "PASS",
        ),
    )
    recommendation_columns[1].metric(
        "Selection",
        safe(decision.get("selected_team")),
    )
    recommendation_columns[2].metric(
        "Hammer Score",
        number(decision.get("hammer_score"), 1),
    )
    recommendation_columns[3].metric(
        "Hammer Assessment",
        safe(
            decision.get("hammer_assessment")
            or decision.get("hammer_confidence")
            or decision.get("confidence"),
        ),
    )

    st.caption(
        "Confirmation: "
        f"{hammer_confirmation_label(decision.get('hammer_tier'))}"
    )

    st.markdown("#### Why We Like It")
    reasons = decision.get("reasons", [])

    if not reasons:
        st.info("No supporting reasons were generated.")
    else:
        for reason in reasons:
            st.markdown(f"- {reason}")

    targets = decision.get("top_hr_targets", [])
    if targets:
        st.markdown("**HR Support**")
        for target in targets[:3]:
            if isinstance(target, dict):
                st.markdown(
                    f"- {safe(target.get('name') or target.get('player') or target.get('hitter'))}"
                )
            else:
                st.markdown(f"- {safe(target)}")

    st.markdown("#### Pitching")
    pitching_columns = st.columns(2)
    pitching_columns[0].metric(
        "Starter Score",
        number(decision.get("starter_score")),
    )
    pitching_columns[1].metric(
        "First Five Score",
        number(decision.get("first5_score")),
    )

    st.markdown("#### Bullpen")
    st.metric(
        "Bullpen Score",
        number(decision.get("bullpen_score")),
    )

    st.markdown("#### Model Signals")
    source_signals = decision.get("source_signals", [])
    if source_signals:
        signal_rows = []
        for signal in source_signals:
            signal_rows.append(
                {
                    "Signal": signal.get("name"),
                    "Available": signal.get("available"),
                    "Supports": signal.get("supports"),
                    "Score": signal.get("score"),
                    "Reason": signal.get("reason"),
                }
            )
        st.dataframe(
            pd.DataFrame(signal_rows),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No model signals were generated.")

    st.markdown("#### Market Information")
    market_columns = st.columns(4)
    market_columns[0].metric(
        "Market Status",
        safe(
            decision.get("market_status")
            or decision.get("market"),
            "MODEL ONLY",
        ),
    )
    market_columns[1].metric(
        "Book Odds",
        american(decision.get("book_odds")),
    )
    market_columns[2].metric(
        "Market Edge",
        signed_percent(decision.get("market_edge_pct")),
    )
    market_columns[3].metric(
        "Expected Value",
        signed_percent(decision.get("expected_value_pct")),
    )

    st.markdown("#### Component Breakdown")
    breakdown = decision.get("score_breakdown", {})
    rows = []

    for name, details in breakdown.items():
        rows.append(
            {
                "Component": name.replace("_", " ").title(),
                "Available": details.get("available", False),
                "Score": details.get("score"),
                "Weight": details.get("weight"),
                "Contribution": details.get("contribution"),
            }
        )

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            width="stretch",
            hide_index=True,
        )


def render_decision_table(decisions: list[dict]):
    rows = []

    for decision in decisions:
        rows.append(
            {
                "Rank": len(rows) + 1,
                "Team": decision.get("selected_team"),
                "Matchup": decision.get("matchup"),
                "Recommendation": decision.get(
                    "recommendation"
                ),
                "Hammer": decision.get("hammer_score"),
                "Hammer Confidence": (
                    decision.get("hammer_confidence")
                    or decision.get("confidence")
                ),
                "Market": decision.get("market"),
                "Model Win Strength": (
                    round(
                        (
                            decision.get("model_win_strength")
                            if decision.get("model_win_strength")
                            is not None
                            else decision["model_probability"]
                        ) * 100,
                        1,
                    )
                    if (
                        decision.get("model_win_strength")
                        is not None
                        or decision.get("model_probability")
                        is not None
                    )
                    else None
                ),
                "F5": decision.get("first5_score"),
                "Bomb": decision.get("bomb_score"),
                "Agreement": decision.get(
                    "agreement_count"
                ),
                "Book Odds": decision.get("book_odds"),
                "Edge %": decision.get(
                    "market_edge_pct"
                ),
                "EV %": decision.get(
                    "expected_value_pct"
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
    )
