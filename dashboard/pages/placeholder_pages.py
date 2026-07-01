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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pitchers", summary.get("pitchers_loaded", 0))
    c2.metric("Elite", summary.get("elite", 0))
    c3.metric("Strong", summary.get("strong", 0))
    c4.metric("Watch", summary.get("watch", 0))

    st.markdown("### Quick Attack Board")

    if table:
        df = pd.DataFrame(table)

        df = df.rename(
            columns={
                "tier": "Tier",
                "bomb_score": "Bomb",
                "confidence": "Conf",
                "pitcher": "Pitcher",
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
                df[col] = (pd.to_numeric(df[col], errors="coerce") * 100).round(1).astype(str) + "%"

        st.dataframe(
            df,
            
            width="stretch",
            hide_index=True,
        )

    st.markdown("### Pitcher Detail Cards")

    if not pitchers:
        st.info(card.get("message", "No Bomb Lab pitchers available."))
        return

    for item in pitchers[:30]:
        render_bomb_pitcher_card(item)


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
    render_module_dashboard(
        icon="🏆",
        title="Hall of Fame",
        subtitle="Historical SharpStack greatness and model performance.",
        badge="PERFORMANCE TRACKING",
        sections=[
            {
                "title": "Leaderboards",
                "items": [
                    ("Biggest Edge", "planned"),
                    ("Highest Confidence", "planned"),
                    ("Largest Upset", "planned"),
                    ("Longest Win Streak", "planned"),
                ],
            },
            {
                "title": "Analytics",
                "items": [
                    ("Lifetime ROI", "planned"),
                    ("Win Rate by Confidence", "planned"),
                    ("Closing Line Value", "planned"),
                    ("Profit by Market", "planned"),
                ],
            },
        ],
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