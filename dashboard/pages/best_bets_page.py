from __future__ import annotations

from components.registry.play_of_day_card import (
    render_play_of_day,
)

import json
from pathlib import Path

import streamlit as st

from components.registry.registry_cards import (
    render_registry_card,
    render_registry_summary,
    render_registry_table,
)

def load_play_of_day() -> dict:
    if not PLAY_OF_DAY_PATH.exists():
        return {}

    try:
        with open(
            PLAY_OF_DAY_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}

ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = (
    ROOT
    / "output"
    / "cards"
    / "recommendation_registry.json"
)

PLAY_OF_DAY_PATH = (
    ROOT
    / "output"
    / "cards"
    / "play_of_day.json"
)

def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}

    try:
        with open(
            REGISTRY_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}


def render_best_bets():
    registry = load_registry()

    st.markdown(
        '<div class="section-title">'
        "🏆 Best Bets"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="decision-hero">
            <div>
                <span>SHARPSTACK REGISTRY</span>
                <h1>
                    Every Sport. One Ranked Board.
                </h1>
                <p>
                    MLB and KBO recommendations now flow
                    through the shared SharpStack recommendation
                    registry. NHL and football will join the same
                    board as their engines are added.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    play_of_day = (
        load_play_of_day()
    )

    if play_of_day:
        render_play_of_day(
            play_of_day
        )

        st.markdown("---")

    if not registry:
        st.warning(
            "No recommendation registry found. "
            "Run `py tools_build_recommendation_registry.py`."
        )
        return

    summary = registry.get(
        "summary",
        {},
    )

    recommendations = registry.get(
        "recommendations",
        [],
    )

    render_registry_summary(summary)

    if not recommendations:
        st.info(
            "No recommendations are available. "
            "This is expected during an empty slate."
        )
        return

    sports = sorted(
        {
            row.get("sport")
            for row in recommendations
            if row.get("sport")
        }
    )

    leagues = sorted(
        {
            row.get("league")
            for row in recommendations
            if row.get("league")
        }
    )

    markets = sorted(
        {
            row.get("market")
            for row in recommendations
            if row.get("market")
        }
    )

    filter_columns = st.columns(4)

    sport_filter = (
        filter_columns[0].selectbox(
            "Sport",
            ["All"] + sports,
        )
    )

    league_filter = (
        filter_columns[1].selectbox(
            "League",
            ["All"] + leagues,
        )
    )

    market_filter = (
        filter_columns[2].selectbox(
            "Market",
            ["All"] + markets,
        )
    )

    price_filter = (
        filter_columns[3].selectbox(
            "Price Status",
            [
                "All",
                "Real Market",
                "Model Only",
            ],
        )
    )

    filtered = recommendations

    if sport_filter != "All":
        filtered = [
            row
            for row in filtered
            if row.get("sport")
            == sport_filter
        ]

    if league_filter != "All":
        filtered = [
            row
            for row in filtered
            if row.get("league")
            == league_filter
        ]

    if market_filter != "All":
        filtered = [
            row
            for row in filtered
            if row.get("market")
            == market_filter
        ]

    if price_filter == "Real Market":
        filtered = [
            row
            for row in filtered
            if row.get(
                "real_market_loaded"
            )
        ]

    if price_filter == "Model Only":
        filtered = [
            row
            for row in filtered
            if not row.get(
                "real_market_loaded"
            )
        ]

    tabs = st.tabs(
        [
            "Official Card",
            "Full Board",
            "Real Markets",
            "By League",
        ]
    )

    with tabs[0]:
        actionable = [
            row
            for row in filtered
            if row.get(
                "recommendation"
            )
            in {
                "HAMMER",
                "BET",
                "LEAN",
            }
        ]

        if not actionable:
            st.info(
                "No actionable recommendations "
                "match the current filters."
            )
        else:
            for rank, item in enumerate(
                actionable[:10],
                start=1,
            ):
                render_registry_card(
                    item,
                    rank,
                )

    with tabs[1]:
        render_registry_table(
            filtered
        )

    with tabs[2]:
        real_market_rows = [
            row
            for row in filtered
            if row.get(
                "real_market_loaded"
            )
        ]

        if not real_market_rows:
            st.info(
                "No real sportsbook prices "
                "are currently loaded."
            )
        else:
            render_registry_table(
                real_market_rows
            )

    with tabs[3]:
        if not filtered:
            st.info(
                "No recommendations match "
                "the current filters."
            )
        else:
            league_values = sorted(
                {
                    row.get("league")
                    for row in filtered
                    if row.get("league")
                }
            )

            for league in league_values:
                st.markdown(
                    f"### {league}"
                )

                league_rows = [
                    row
                    for row in filtered
                    if row.get("league")
                    == league
                ]

                render_registry_table(
                    league_rows
                )
