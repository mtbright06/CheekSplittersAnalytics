import streamlit as st


def count_confirmed_pitchers(card):
    games = card.get("games", [])
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


def status_dot(status):
    return {
        "good": "🟢",
        "warn": "🟡",
        "bad": "🔴",
        "off": "⚫",
    }.get(status, "⚫")


def render_status_row(label, value, status="good"):
    st.markdown(
        f"""
        <div class="engine-row">
            <span>{status_dot(status)} {label}</span>
            <strong>{value}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_engine_status(card):
    games = card.get("games", [])
    confirmed, total = count_confirmed_pitchers(card)

    pitcher_status = "good" if total and confirmed == total else "warn"

    st.markdown(
        """
        <div class="engine-status-card">
            <div class="engine-title">Engine Status</div>
        """,
        unsafe_allow_html=True,
    )

    render_status_row("Model", "SharpStack Core", "good")
    render_status_row("Version", card.get("version") or "v0.8 Alpha", "good")
    render_status_row("Sport", card.get("sport") or "N/A", "good")
    render_status_row("Games Loaded", len(games), "good" if games else "warn")
    render_status_row("Confirmed SP", f"{confirmed}/{total}", pitcher_status)
    render_status_row("Odds Feed", "Coming Soon", "warn")
    render_status_row("Weather", "Phase 3", "off")
    render_status_row("JSON", "Healthy", "good")

    st.markdown("</div>", unsafe_allow_html=True)
