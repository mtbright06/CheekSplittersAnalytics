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


def dashboard_metric_values(card) -> list[tuple[str, str | int]]:
    games = card.get("games", [])
    sport = str(card.get("sport") or "").upper()

    game_count = len(games)

    playable = sum(
        1
        for game in games
        if (
            str(game.get("model", {}).get("recommendation") or "")
            in {"🔥 STRONG PLAY", "✅ PLAYABLE", "👀 LEAN"}
            if sport == "KBO"
            else edge(game) >= 5
        )
    )

    if sport == "KBO" and all(
        game.get("model", {}).get("edge") is None
        for game in games
    ):
        best_market_metric = (
            "Best Model Score",
            f"{max((game.get('model', {}).get('model_probability') or 0 for game in games), default=0):.1f}",
        )
    else:
        best_edge = max(
            (edge(game) for game in games),
            default=0,
        )
        best_market_metric = ("Best Edge", f"{best_edge:.1f}%")

    avg_confidence = (
        sum(confidence(game) for game in games) / game_count
        if game_count
        else 0
    )

    return [
        ("Games", game_count),
        ("Playable", playable),
        best_market_metric,
        ("Avg Confidence", f"{avg_confidence:.1f}"),
    ]


def render_dashboard_metrics(card):
    columns = st.columns(4)

    for column, (label, value) in zip(
        columns,
        dashboard_metric_values(card),
    ):
        with column:
            st.metric(label, value)
