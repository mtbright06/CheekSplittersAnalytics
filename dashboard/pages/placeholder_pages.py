import json
from pathlib import Path

import pandas as pd
import streamlit as st

from components.module_dashboard import render_module_dashboard
from components.page_header import render_compact_header


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
        render_decision_board,
        render_game_explorer,
    )
    from components.bomb_lab.workstation import (
        render_bomb_lab_workstation_cards,
        render_bomb_lab_workstation_header,
    )

    root = Path(__file__).resolve().parents[2]
    path = root / "output" / "cards" / "bomb_lab_card.json"

    if not path.exists():
        render_compact_header(
            "💣",
            "Bomb Lab",
            "Pitcher vulnerabilities and home-run target diagnostics.",
        )
        st.warning("No Bomb Lab card found. Run `python tools_build_bomb_lab.py` first.")
        return

    with open(path, "r", encoding="utf-8") as f:
        card = json.load(f)

    summary = card.get("summary", {})
    pitchers = card.get("pitchers", [])
    table = card.get("table", [])

    if not pitchers:
        st.info(card.get("message", "No Bomb Lab pitchers available."))
        return

    render_bomb_lab_workstation_header(summary)
    selected_view = _render_bomb_lab_view_selector()

    if selected_view == "Bomb Lab":
        render_bomb_lab_workstation_cards(pitchers)
    elif selected_view == "Decision Board":
        render_decision_board(pitchers)
    elif selected_view == "Game Explorer":
        _render_bomb_game_explorer(pitchers, render_game_explorer)
    elif selected_view == "Pitcher Explorer":
        _render_bomb_pitcher_explorer(pitchers, render_bomb_pitcher_card)
    elif selected_view == "Metrics Lab":
        _render_bomb_metrics_lab(table)


def _render_bomb_lab_view_selector() -> str:
    key = "bomb_lab_selected_view"
    views = [
        "Bomb Lab",
        "Decision Board",
        "Game Explorer",
        "Pitcher Explorer",
        "Metrics Lab",
    ]

    if st.session_state.get(key) not in views:
        st.session_state[key] = "Bomb Lab"

    st.markdown("<div class='mlb-analytics-controls bomb-lab-view-selector'>", unsafe_allow_html=True)
    columns = st.columns(len(views), gap="small")
    for column, view in zip(columns, views):
        with column:
            if st.button(
                view,
                key=f"bomb_lab_view_{view.lower().replace(' ', '_')}",
                width="stretch",
                type="primary" if st.session_state[key] == view else "secondary",
            ):
                st.session_state[key] = view
    st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state[key]


def _render_bomb_game_explorer(pitchers, render_game_explorer):
    options = {
        f"{p.get('opponent')} attacking {p.get('pitcher')} ({p.get('pitching_team')})": i
        for i, p in enumerate(pitchers[:20])
    }

    selected_label = st.selectbox(
        "Choose an offense to inspect",
        list(options.keys()),
        index=0,
        key="bomb_lab_game_explorer_selection",
    )

    render_game_explorer(pitchers[options[selected_label]])


def _render_bomb_pitcher_explorer(pitchers, render_bomb_pitcher_card):
    st.markdown("### Pitcher Explorer")

    for item in pitchers[:20]:
        render_bomb_pitcher_card(item)


def _render_bomb_metrics_lab(table):
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

def render_first5():
    from components.first5.first5_cards import (
        render_first5_game_card,
        render_first5_table,
    )

    from components.first5.market_cards import (
        render_market_edge_card,
        render_market_summary,
        render_market_table,
    )

    root = Path(__file__).resolve().parents[2]
    path = root / "output" / "cards" / "first5_card.json"

    market_path = root / "output" / "cards" / "first5_market_card.json"

    market_card = {}

    if market_path.exists():
        with open(market_path, "r", encoding="utf-8") as file:
            market_card = json.load(file)


    if not path.exists():
        render_compact_header(
            "⚾",
            "First 5 Lab",
            "Starter-driven First Five moneyline and totals analysis.",
        )
        st.warning(
            "No First 5 card found. Run "
            "`python tools_build_first5_card.py` first."
        )
        return

    with open(path, "r", encoding="utf-8") as file:
        card = json.load(file)

    summary = card.get("summary", {})
    games = card.get("games", [])

    render_compact_header(
        "⚾",
        "First 5 Lab",
        "Starter-driven First Five moneyline and totals analysis.",
        [
            ("Games", summary.get("games_loaded", 0)),
            ("ML Leans", summary.get("f5_ml_leans", 0)),
            ("Total Leans", summary.get("f5_total_leans", 0)),
            ("Top ML", summary.get("top_ml_play", "PASS")),
        ],
    )

    if not games:
        st.info(card.get("message", "No First 5 games available."))
        return

    tabs = st.tabs(
        [
            "Market Edge",
            "Top Leans",
            "Full Slate",
            "Game Explorer",
        ]
    )

    with tabs[0]:
        market_games = market_card.get("games", [])
        market_summary = market_card.get("summary", {})

        if not market_games:
            st.info(
                "No market card found. Run "
                "`python tools_build_first5_market_card.py`."
            )
        else:
            render_market_summary(market_summary)

            actionable = [
                game
                for game in market_games
                if (
                    game.get("best_market_side", {}).get("recommendation")
                    not in {"PASS", "NO MARKET"}
                    or game.get("f5_total_market", {}).get("lean")
                    in {"OVER", "UNDER"}
                )
            ]

            if actionable:
                for rank, game in enumerate(actionable[:8], start=1):
                    render_market_edge_card(game, rank)
            else:
                st.info(
                    "Market data is loaded, but no actionable edges "
                    "currently qualify."
                )

            st.markdown("### Full Market Board")
            render_market_table(market_games)

    with tabs[1]:
        actionable = [
            game
            for game in games
            if (
                game.get("f5_ml", {}).get("lean") != "PASS"
                or game.get("f5_total", {}).get("lean") != "PASS"
            )
        ]

        for rank, game in enumerate(actionable[:8], start=1):
            render_first5_game_card(game, rank)

    with tabs[2]:
        render_first5_table(games)

    with tabs[3]:
        labels = [
            game.get("matchup", f"Game {index + 1}")
            for index, game in enumerate(games)
        ]

        selected_label = st.selectbox(
            "Choose a First 5 matchup",
            labels,
        )

        selected_index = labels.index(selected_label)
        render_first5_game_card(games[selected_index])

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
