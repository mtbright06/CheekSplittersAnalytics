import streamlit as st


def render_dashboard_metrics(card):

    games = card.get("games", [])

    total_games = len(games)

    playable = len([
        g for g in games
        if (g["model"].get("edge") or 0) >= 5
    ])

    best_edge = max(
        (g["model"].get("edge") or 0 for g in games),
        default=0
    )

    avg_edge = (
        sum(g["model"].get("edge") or 0 for g in games)
        / total_games
        if total_games else 0
    )

    c1,c2,c3,c4 = st.columns(4)

    c1.metric(
        "Games",
        total_games
    )

    c2.metric(
        "Playable",
        playable
    )

    c3.metric(
        "Avg Edge",
        f"{avg_edge:.1f}%"
    )

    c4.metric(
        "Best Edge",
        f"{best_edge:.1f}%"
    )
