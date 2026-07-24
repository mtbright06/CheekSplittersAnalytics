from __future__ import annotations

from components.registry.play_of_day_card import (
    render_play_of_day,
)
from components.page_header import render_compact_header

import json
from pathlib import Path

import streamlit as st

from components.registry.registry_cards import (
    render_registry_card,
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


ACTIONABLE_TIERS = {"HAMMER", "BET", "LEAN"}


def top_market_plays(
    recommendations: list[dict],
    league: str,
    market: str,
) -> list[dict]:
    """Filter the canonical registry order; ranking remains registry-owned."""
    return [
        row
        for row in recommendations
        if row.get("league") == league
        and row.get("market") == market
        and row.get("recommendation") in ACTIONABLE_TIERS
    ][:3]


def render_market_card(
    recommendations: list[dict],
    league: str,
    market: str,
):
    plays = top_market_plays(recommendations, league, market)

    if not plays:
        st.info("No qualifying plays today.")
        return

    for rank, item in enumerate(plays, start=1):
        render_registry_card(item, rank)


def render_best_bets():
    registry = load_registry()

    if not registry:
        render_compact_header(
            "🏆",
            "Best Bets",
            "Official betting card from the SharpStack registry.",
        )
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

    render_compact_header(
        "🏆",
        "Best Bets",
        "Official betting card from the SharpStack registry.",
        [
            ("Actionable", summary.get("actionable", 0)),
            ("Hammers", summary.get("hammers", 0)),
            ("Real Markets", summary.get("real_market", 0)),
            ("Recommendations", summary.get("recommendations", 0)),
        ],
    )

    play_of_day = load_play_of_day()
    if play_of_day:
        render_play_of_day(play_of_day)
        st.markdown("---")

    if not recommendations:
        st.info(
            "No recommendations are available. "
            "This is expected during an empty slate."
        )
        return

    moneyline_tab, totals_tab, kbo_tab = st.tabs(
        [
            "MLB Moneyline",
            "MLB Totals",
            "KBO Moneyline",
        ]
    )

    with moneyline_tab:
        render_market_card(recommendations, "MLB", "moneyline")

    with totals_tab:
        render_market_card(recommendations, "MLB", "totals")

    with kbo_tab:
        render_market_card(recommendations, "KBO", "moneyline")
