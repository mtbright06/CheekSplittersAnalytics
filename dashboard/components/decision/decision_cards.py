from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st


def safe(value: Any, default: str = "N/A") -> str:
    if value in [None, "", "None"]:
        return default

    return str(value)


def esc(value: Any, default: str = "N/A") -> str:
    return html.escape(safe(value, default))


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


def render_decision_summary(summary: dict):
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

    columns[5].metric(
        "Top Play",
        summary.get("top_play", "PASS"),
    )


def render_target_list(targets: list[dict]) -> str:
    if not targets:
        return (
            '<div class="decision-empty">'
            "No hitter targets attached."
            "</div>"
        )

    rendered = []

    for target in targets[:3]:
        if isinstance(target, dict):
            name = (
                target.get("name")
                or target.get("player")
                or target.get("hitter")
            )

            score = (
                target.get("target_score")
                or target.get("score")
            )

            rendered.append(
                '<div class="decision-target">'
                f"<span>{esc(name)}</span>"
                f"<strong>{number(score, 1, '')}</strong>"
                "</div>"
            )
        else:
            rendered.append(
                '<div class="decision-target">'
                f"<span>{esc(target)}</span>"
                "</div>"
            )

    return "".join(rendered)


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
        "market",
        "MODEL ONLY",
    )

    recommendation_class = (
        str(recommendation)
        .lower()
        .replace(" ", "-")
    )

    targets_html = render_target_list(
        decision.get("top_hr_targets", [])
    )

    html_block = f"""
    <div class="decision-card decision-{recommendation_class}">
        <div class="decision-top-row">
            <div class="decision-rank">{rank}</div>

            <div class="decision-main">
                <div class="decision-kicker">
                    {esc(recommendation)}
                    <span>{esc(market_status)}</span>
                </div>

                <div class="decision-team">
                    {esc(decision.get("selected_team"))}
                </div>

                <div class="decision-matchup">
                    {esc(decision.get("matchup"))}
                </div>

                <div class="decision-stars">
                    {esc(decision.get("stars"), "")}
                </div>
            </div>

            <div class="decision-score">
                <span>Hammer Score</span>
                <strong>{number(score, 1)}</strong>
                <small>{esc(decision.get("confidence"))}</small>
            </div>
        </div>

        <div class="decision-metrics">
            <div>
                <span>Model Win</span>
                <strong>
                    {percent(decision.get("model_probability"))}
                </strong>
            </div>

            <div>
                <span>F5 Score</span>
                <strong>
                    {number(decision.get("first5_score"))}
                </strong>
            </div>

            <div>
                <span>Bomb</span>
                <strong>
                    {number(decision.get("bomb_score"))}
                </strong>
            </div>

            <div>
                <span>Agreement</span>
                <strong>
                    {safe(decision.get("agreement_count"), "0")}
                </strong>
            </div>

            <div>
                <span>Market Edge</span>
                <strong>
                    {signed_percent(decision.get("market_edge_pct"))}
                </strong>
            </div>

            <div>
                <span>Book</span>
                <strong>
                    {american(decision.get("book_odds"))}
                </strong>
            </div>
        </div>

        <div class="decision-lower">
            <div>
                <div class="decision-subtitle">
                    Why SharpStack Likes It
                </div>
            </div>

            <div>
                <div class="decision-subtitle">
                    HR Support
                </div>
                {targets_html}
            </div>
        </div>
    </div>
    """

    st.markdown(
        html_block,
        unsafe_allow_html=True,
    )

    with st.expander(
        f"Why {decision.get('selected_team')}?",
        expanded=False,
    ):
        reasons = decision.get("reasons", [])

        if not reasons:
            st.info("No supporting reasons were generated.")
        else:
            for reason in reasons:
                st.markdown(f"- {reason}")

        st.markdown("#### Component Breakdown")

        breakdown = decision.get(
            "score_breakdown",
            {},
        )

        rows = []

        for name, details in breakdown.items():
            rows.append(
                {
                    "Component": name.replace(
                        "_",
                        " ",
                    ).title(),
                    "Available": details.get(
                        "available",
                        False,
                    ),
                    "Score": details.get("score"),
                    "Weight": details.get("weight"),
                    "Contribution": details.get(
                        "contribution"
                    ),
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
                "Confidence": decision.get("confidence"),
                "Market": decision.get("market"),
                "Model Win %": (
                    round(
                        decision["model_probability"] * 100,
                        1,
                    )
                    if decision.get("model_probability")
                    is not None
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
