import json
from pathlib import Path

import pandas as pd
import streamlit as st

from components.module_dashboard import render_module_dashboard


def render_mlb():
    render_module_dashboard(
        icon="⚾",
        title="MLB Command Center",
        subtitle="The flagship league is now inside the SharpStack engine.",
        badge="LIVE ENGINE",
        sections=[
            {
                "title": "Foundation",
                "items": [
                    ("Schedule Ingestion", "complete"),
                    ("Team Logo System", "complete"),
                    ("Team Colors", "complete"),
                    ("Dashboard Ready", "complete"),
                ],
            },
            {
                "title": "Data Pipeline",
                "items": [
                    ("Probable Pitchers", "complete"),
                    ("Pitcher Stats", "complete"),
                    ("Team Offense", "complete"),
                    ("Bullpens", "planned"),
                ],
            },
            {
                "title": "Market Intelligence",
                "items": [
                    ("Live Odds", "complete"),
                    ("Implied Probability", "complete"),
                    ("SharpScore", "complete"),
                    ("Line Movement", "planned"),
                ],
            },
        ],
    )


def render_kbo():
    render_module_dashboard(
        icon="🇰🇷",
        title="KBO Analytics",
        subtitle="Current production league and SharpStack validation environment.",
        badge="LIVE ENGINE",
        sections=[
            {
                "title": "Current Capabilities",
                "items": [
                    ("Schedule Loading", "complete"),
                    ("Pitcher Profiles", "complete"),
                    ("Model Scoring", "complete"),
                    ("JSON Output", "complete"),
                ],
            },
            {
                "title": "Enhancements",
                "items": [
                    ("Odds Feed", "next"),
                    ("Weather", "planned"),
                    ("Bullpen Intelligence", "planned"),
                    ("Line Movement", "planned"),
                ],
            },
        ],
    )


def render_bomb_lab():
    from components.bomb_lab.bomb_lab_cards import render_bomb_pitcher_card
    from components.bomb_lab.decision_board import (
        render_bomb_lab_header,
        render_decision_board,
        render_game_explorer,
    )

    root = Path(__file__).resolve().parents[2]
    path = root / "output" / "cards" / "bomb_lab_card.json"

    st.markdown(
        '<div class="section-title">💣 Bomb Lab</div>',
        unsafe_allow_html=True,
    )

    if not path.exists():
        st.warning("No Bomb Lab card found. Run `python tools_build_bomb_lab.py` first.")
        return

    with open(path, "r", encoding="utf-8") as f:
        card = json.load(f)

    summary = card.get("summary", {})
    pitchers = card.get("pitchers", [])
    table = card.get("table", [])

    render_bomb_lab_header(summary)

    if not pitchers:
        st.info(card.get("message", "No Bomb Lab pitchers available."))
        return

    tabs = st.tabs(
        [
            "Decision Board",
            "Game Explorer",
            "Pitcher Explorer",
            "Metrics Lab",
        ]
    )

    with tabs[0]:
        render_decision_board(pitchers)

    with tabs[1]:
        options = {
            f"{p.get('opponent')} attacking {p.get('pitcher')} ({p.get('pitching_team')})": i
            for i, p in enumerate(pitchers[:20])
        }

        selected_label = st.selectbox(
            "Choose an offense to inspect",
            list(options.keys()),
            index=0,
        )

        selected_index = options[selected_label]
        render_game_explorer(pitchers[selected_index])

    with tabs[2]:
        st.markdown("### Pitcher Explorer")

        for item in pitchers[:20]:
            render_bomb_pitcher_card(item)

    with tabs[3]:
        st.markdown("### Metrics Lab")

        if not table:
            st.info("No metrics table available.")
            return

        df = pd.DataFrame(table)

        df = df.rename(
            columns={
                "tier": "Tier",
                "bomb_score": "Bomb",
                "confidence": "Conf",
                "pitcher": "Pitcher",
                "pitching_team": "Pitcher Team",
                "target_offense": "Target Offense",
                "game": "Game",
                "attack_side": "Side",
                "pitcher_risk": "Risk",
                "barrel_pct": "Barrel%",
                "hard_hit_pct": "HH%",
                "hr_per_bbe": "HR/BBE",
                "park": "Park",
                "bbe": "BBE",
            }
        )

        for col in ["Barrel%", "HH%", "HR/BBE"]:
            if col in df.columns:
                df[col] = (
                    pd.to_numeric(df[col], errors="coerce")
                    * 100
                ).round(1).astype(str) + "%"

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
        )


def render_props():
    render_module_dashboard(
        icon="🎯",
        title="Props Lab",
        subtitle="Player prop research and edge detection.",
        badge="FUTURE MODULE",
        sections=[
            {
                "title": "Markets",
                "items": [
                    ("Strikeouts", "planned"),
                    ("Hits", "planned"),
                    ("Total Bases", "planned"),
                    ("Home Runs", "planned"),
                    ("Pitching Outs", "planned"),
                ],
            },
            {
                "title": "Model Inputs",
                "items": [
                    ("Player Form", "planned"),
                    ("Opponent Matchup", "planned"),
                    ("Odds Feed", "planned"),
                    ("Historical Hit Rate", "planned"),
                ],
            },
        ],
    )


def render_hall():
    from engine.results.recommendation_tracker import load_results
    from components.results.results_summary import render_results_summary

    st.markdown(
        '<div class="section-title">🏆 Model Results</div>',
        unsafe_allow_html=True,
    )

    rows = load_results()

    render_results_summary(rows)

    st.markdown("### Recommendation Log")

    if not rows:
        st.info("No recommendations tracked yet. Run `python tools_track_recommendations.py` after building cards.")
        return

    df = pd.DataFrame(rows)

    preferred = [
        "date",
        "sport",
        "pick",
        "game",
        "market",
        "recommendation",
        "edge",
        "confidence",
        "odds",
        "result",
        "notes",
    ]

    available = [col for col in preferred if col in df.columns]

    st.dataframe(
        df[available].sort_values("date", ascending=False),
        width="stretch",
        hide_index=True,
    )


def render_settings():
    render_module_dashboard(
        icon="⚙",
        title="Control Center",
        subtitle="Configure SharpStack behavior, integrations, and defaults.",
        badge="ADMIN AREA",
        sections=[
            {
                "title": "Configuration",
                "items": [
                    ("Theme", "planned"),
                    ("League Defaults", "planned"),
                    ("Odds Provider", "planned"),
                    ("Model Weights", "planned"),
                ],
            },
            {
                "title": "Integrations",
                "items": [
                    ("Discord Alerts", "planned"),
                    ("Export Settings", "planned"),
                    ("Experimental Features", "planned"),
                    ("Notification Rules", "planned"),
                ],
            },
        ],
    )
