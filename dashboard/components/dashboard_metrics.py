import streamlit as st


def _model(game):
    """
    Safely return the model dictionary regardless of whether the
    game is an older or newer JSON contract.
    """
    if not isinstance(game, dict):
        return {}

    return game.get("model", {})


def edge(game):
    model = _model(game)

    if model:
        return model.get("edge") or 0

    return game.get("edge") or 0


def confidence(game):
    model = _model(game)

    if model:
        return model.get("confidence") or 0

    return game.get("confidence") or 0


def render_dashboard_metrics(card):
    games = card.get("games", [])

    game_count = len(games)

    playable = sum(
        1
        for game in games
        if edge(game) >= 5
    )

    best_edge = max(
        (edge(game) for game in games),
        default=0,
    )

    avg_confidence = (
        sum(confidence(game) for game in games) / game_count
        if game_count
        else 0
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Games",
        game_count,
    )

    col2.metric(
        "Playable",
        playable,
    )

    col3.metric(
        "Best Edge",
        f"{best_edge:.1f}%",
    )

    col4.metric(
        "Avg Confidence",
        f"{avg_confidence:.1f}",
    )
