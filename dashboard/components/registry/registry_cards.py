from __future__ import annotations
import html
from typing import Any
from components.logos import team_logo_html
import pandas as pd
import streamlit as st
from components.confirmation import (
    hammer_confirmation_label,
)
from components.badges import (
    market_value_badge_html,
    recommendation_badge_html,
)


def compact_html(value):
    return "\n".join(
        line.strip()
        for line in value.splitlines()
        if line.strip()
    )

def safe(
    value: Any,
    default: str = "N/A",
) -> str:
    if value in [
        None,
        "",
        "None",
    ]:
        return default

    return str(value)


def esc(
    value: Any,
    default: str = "N/A",
) -> str:
    return html.escape(
        safe(
            value,
            default,
        )
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
    decimals: int = 1,
) -> str:
    try:
        number_value = float(value)

        if abs(number_value) <= 1:
            number_value *= 100

        return (
            f"{number_value:.{decimals}f}%"
        )
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def signed_percent(
    value: Any,
    decimals: int = 1,
) -> str:
    try:
        return (
            f"{float(value):+.{decimals}f}%"
        )
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def american(value: Any) -> str:
    try:
        odds = int(
            round(float(value))
        )

        return (
            f"+{odds}"
            if odds > 0
            else str(odds)
        )
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def render_registry_summary(
    summary: dict,
):
    columns = st.columns(6)

    columns[0].metric(
        "Recommendations",
        summary.get(
            "recommendations",
            0,
        ),
    )

    columns[1].metric(
        "Actionable",
        summary.get(
            "actionable",
            0,
        ),
    )

    columns[2].metric(
        "Hammers",
        summary.get(
            "hammers",
            0,
        ),
    )

    columns[3].metric(
        "Real Markets",
        summary.get(
            "real_market",
            0,
        ),
    )

    columns[4].metric(
        "Sports",
        len(
            summary.get(
                "sports",
                [],
            )
        ),
    )

    columns[5].metric(
        "Leagues",
        len(
            summary.get(
                "leagues",
                [],
            )
        ),
    )


def render_registry_card(
    item: dict,
    rank: int,
):
    recommendation = safe(
        item.get("recommendation"),
        "PASS",
    )

    recommendation_class = (
        recommendation
        .lower()
        .replace(" ", "-")
    )

    quote = item.get(
        "market_quote",
        {},
    )

    market_status = (
        "REAL MARKET"
        if item.get(
            "real_market_loaded"
        )
        else "MODEL ONLY"
    )

    hammer_assessment = item.get(
        "hammer_assessment"
    )
    hammer_tier = item.get("hammer_tier")

    team_name = item.get("selection")

    sport = str(
        item.get("league")
        or item.get("sport")
        or "mlb"
    ).strip().lower()
    is_mlb_moneyline = sport == "mlb" and item.get("market") == "moneyline"

    if sport == "kbo" and not item.get("real_market_loaded"):
        st.markdown(
            compact_html(
                kbo_model_only_card_html(item, rank)
            ),
            unsafe_allow_html=True,
        )
        return

    logo_html = team_logo_html(
        team_name,
        sport,
    )

    reasons = item.get(
        "reasons",
        [],
    )

    visible_reasons = [
        esc(reason)
        for reason in reasons[:3]
        if reason
    ]

    if visible_reasons:
        reasons_html = "".join(
            f"<li>{reason}</li>"
            for reason in visible_reasons
        )
    else:
        reasons_html = (
            "<li>No supporting reasons available.</li>"
        )

    html_block = f"""
    <div class="decision-card decision-{recommendation_class}">
        <div class="decision-top-row">
           <div class="decision-rank decision-team-logo">
                {logo_html}
            </div>
            <div class="decision-main">
                <div class="decision-team">
                    {esc(item.get("selection"))}
                </div>

                <div class="decision-matchup">
                    {esc(item.get("matchup"))}
                </div>

                <div class="registry-recommendation-row">
                    {recommendation_badge_html(
                        recommendation,
                        fallback_stars=safe(item.get("stars"), ""),
                    )}
                    <span class="registry-market-badge">
                        {esc(item.get("league"))} · {esc(item.get("market"))}
                    </span>
                    <span class="registry-market-badge">{market_status}</span>
                    {(
                        market_value_badge_html(
                            item.get("market_value_label"),
                            item.get("market_value_tone"),
                        )
                        if is_mlb_moneyline
                        else ""
                    )}
                </div>
                {(
                    '<div class="decision-matchup">'
                    f'{esc(hammer_confirmation_label(hammer_tier))} · '
                    f'{esc(hammer_assessment)}'
                    '</div>'
                    if hammer_assessment or hammer_tier
                    else ''
                )}
            </div>

            <div class="decision-score">
                <span>Hammer Score</span>
                <strong>
                    {number(item.get("hammer_score"))}
                </strong>
                <small>
                    Rank {number(item.get("ranking_score"))}
                </small>
            </div>
        </div>

        <div class="decision-metrics">
            <div>
                <span>Model Win</span>
                <strong>
                    {percent(item.get("model_probability"))}
                </strong>
            </div>

            <div>
                <span>Market Win</span>
                <strong>
                    {percent(item.get("market_probability"))}
                </strong>
            </div>

            <div>
                <span>Edge</span>
                <strong>
                    {signed_percent(item.get("edge_pct"))}
                </strong>
            </div>

            <div>
                <span>EV</span>
                <strong>
                    {signed_percent(item.get("expected_value_pct"))}
                </strong>
            </div>

            <div>
                <span>Odds</span>
                <strong>
                    {american(quote.get("odds"))}
                </strong>
            </div>

            <div>
                <span>Units</span>
                <strong>
                    {number(item.get("units"))}
                </strong>
            </div>
        </div>

        <div style="
            margin-top:0.85rem;
            padding-top:0.75rem;
            border-top:1px solid rgba(255,255,255,0.08);
        ">
            <div style="
                margin-bottom:0.35rem;
                font-size:0.72rem;
                font-weight:800;
                letter-spacing:0.10em;
                text-transform:uppercase;
                opacity:0.68;
            ">
                Why SharpStack Likes It
            </div>

            <ul style="
                margin:0;
                padding-left:1.1rem;
                line-height:1.42;
                font-size:0.88rem;
                opacity:0.86;
            ">
                {reasons_html}
            </ul>
        </div>
    </div>
    """

    st.markdown(
        compact_html(html_block),
        unsafe_allow_html=True,
    )


    with st.expander(
        f"Why {item.get('selection')}?",
        expanded=False,
    ):
        reasons = item.get(
            "reasons",
            [],
        )

        if not reasons:
            st.info(
                "No supporting reasons available."
            )
        else:
            for reason in reasons:
                st.markdown(
                    f"- {reason}"
                )

        components = item.get(
            "components",
            {},
        )

        if components:
            rows = []

            for name, details in (
                components.items()
            ):
                if isinstance(
                    details,
                    dict,
                ):
                    rows.append(
                        {
                            "Component": (
                                name.replace(
                                    "_",
                                    " ",
                                ).title()
                            ),
                            "Available": (
                                details.get(
                                    "available"
                                )
                            ),
                            "Score": (
                                details.get(
                                    "score"
                                )
                            ),
                            "Weight": (
                                details.get(
                                    "weight"
                                )
                            ),
                            "Contribution": (
                                details.get(
                                    "contribution"
                                )
                            ),
                        }
                    )
                else:
                    rows.append(
                        {
                            "Component": (
                                name.replace(
                                    "_",
                                    " ",
                                ).title()
                            ),
                            "Value": details,
                        }
                    )

            st.dataframe(
                pd.DataFrame(rows),
                width="stretch",
                hide_index=True,
            )


def kbo_model_only_card_html(item: dict, rank: int) -> str:
    """Render KBO model-only entries with the shared recommendation display."""
    recommendation = safe(item.get("recommendation"), "❌ NO PLAY")
    team_name = item.get("selection")
    logo_html = team_logo_html(team_name, "kbo")
    market = safe(item.get("market"), "moneyline").title()

    return f"""
    <div class="decision-card decision-kbo-model-only">
        <div class="decision-top-row">
            <div class="decision-rank decision-team-logo">{logo_html}</div>
            <div class="decision-main">
                <div class="decision-team">{esc(team_name)}</div>
                <div class="decision-matchup">{esc(item.get("matchup"))}</div>
                <div class="registry-recommendation-row">
                    {recommendation_badge_html(recommendation, model_only=True)}
                    <span class="registry-market-badge">KBO · {esc(market)}</span>
                    <span class="registry-market-badge">MODEL ONLY</span>
                </div>
            </div>
            <div class="decision-score">
                <span>Model Strength</span>
                <strong>{number(item.get("hammer_score"))}</strong>
                <small>Rank {number(item.get("ranking_score"))}</small>
            </div>
        </div>
    </div>
    """


def render_registry_table(
    recommendations: list[dict],
):
    rows = []

    for index, item in enumerate(
        recommendations,
        start=1,
    ):
        quote = item.get(
            "market_quote",
            {},
        )

        rows.append(
            {
                "Rank": index,
                "Sport": item.get(
                    "sport"
                ),
                "League": item.get(
                    "league"
                ),
                "Market": item.get(
                    "market"
                ),
                "Selection": item.get(
                    "selection"
                ),
                "Matchup": item.get(
                    "matchup"
                ),
                "Recommendation": (
                    item.get(
                        "recommendation"
                    )
                ),
                "Hammer": item.get(
                    "hammer_score"
                ),
                "Ranking": item.get(
                    "ranking_score"
                ),
                "Model %": (
                    round(
                        item[
                            "model_probability"
                        ] * 100,
                        1,
                    )
                    if item.get(
                        "model_probability"
                    )
                    is not None
                    else None
                ),
                "Market %": (
                    round(
                        item[
                            "market_probability"
                        ] * 100,
                        1,
                    )
                    if item.get(
                        "market_probability"
                    )
                    is not None
                    else None
                ),
                "Edge %": item.get(
                    "edge_pct"
                ),
                "EV %": item.get(
                    "expected_value_pct"
                ),
                "Odds": quote.get(
                    "odds"
                ),
                "Units": item.get(
                    "units"
                ),
                "Price": (
                    "REAL"
                    if item.get(
                        "real_market_loaded"
                    )
                    else "MODEL ONLY"
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
    )
