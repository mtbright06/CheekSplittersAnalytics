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
    artifact_timestamp = latest_artifact_timestamp(card)

    st.markdown(
        (
            "<div class='pipeline-card'>"
            "<div class='pipeline-title'>Data Pipeline</div>"
        ),
        unsafe_allow_html=True,
    )

    row("Schedule", "Loaded" if games else "No Games", "good" if games else "warn")
    row(
        "Latest Artifact",
        artifact_timestamp or "Unavailable",
        "good" if artifact_timestamp else "warn",
    )
    row("Pitchers", f"{confirmed}/{total}", "good" if total and confirmed == total else "warn")
    row("Team Logos", "Ready", "good")
    row("Team Colors", "Ready", "good")
    priced_games = sum(
        1
        for game in games
        if game.get("odds", {}).get("book_probability") is not None
    )
    row(
        "Odds Feed",
        f"{priced_games}/{len(games)} priced",
        "good" if games and priced_games == len(games) else "warn",
    )
    row("Weather", "Phase 3", "off")
    row("JSON", "Healthy", "good")
    row("Model", "Ready", "good")

    st.markdown("</div>", unsafe_allow_html=True)


def latest_artifact_timestamp(card):
    if not isinstance(card, dict):
        return None

    timestamps = [card.get("generated_at")]

    for sport_card in card.get("cards", []):
        if isinstance(sport_card, dict):
            timestamps.append(sport_card.get("generated_at"))

    available = [timestamp for timestamp in timestamps if timestamp]
    return max(available) if available else None
