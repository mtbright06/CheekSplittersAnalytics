import streamlit as st


def _confirmed_pitchers(card):
    games = card.get("games", []) if card else []
    confirmed = 0
    total = 0

    for game in games:
        pitching = game.get("pitching", {})
        for side in ["away", "home"]:
            total += 1
            pitcher = pitching.get(side, {})
            name = pitcher.get("name")
            if name and name != "Unknown Starter":
                confirmed += 1

    return confirmed, total


def row(label, value, status="good"):
    dot = {
        "good": "🟢",
        "warn": "🟡",
        "bad": "🔴",
        "off": "⚫",
    }.get(status, "⚫")

    st.markdown(
        (
            "<div class='pipeline-row'>"
            f"<span>{dot} {label}</span>"
            f"<strong>{value}</strong>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_pipeline_status(card):
    games = card.get("games", []) if card else []
    confirmed, total = _confirmed_pitchers(card)

    st.markdown(
        (
            "<div class='pipeline-card'>"
            "<div class='pipeline-title'>Data Pipeline</div>"
        ),
        unsafe_allow_html=True,
    )

    row("Schedule", "Loaded" if games else "No Games", "good" if games else "warn")
    row("Pitchers", f"{confirmed}/{total}", "good" if total and confirmed == total else "warn")
    row("Team Logos", "Ready", "good")
    row("Team Colors", "Ready", "good")
    row("Odds Feed", "Coming Soon", "warn")
    row("Weather", "Phase 3", "off")
    row("JSON", "Healthy", "good")
    row("Model", "Ready", "good")

    st.markdown("</div>", unsafe_allow_html=True)
