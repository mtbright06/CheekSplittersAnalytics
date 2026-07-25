from random import choice


STRONG_PLAY_MESSAGES = [
    "🍑 Splitter says: The model found a strong signal. Keep the market context in view.",
    "🍑 Splitter says: Strong model support here. This is the clearest signal on the card.",
]

PLAYABLE_MESSAGES = [
    "🍑 Splitter says: A playable model signal with room for normal variance.",
    "🍑 Splitter says: The model likes this side. Treat it as a measured position.",
]

LEAN_MESSAGES = [
    "🍑 Splitter says: Lean only. The signal is present, but it is not a force-it spot.",
    "🍑 Splitter says: A modest model preference. Discipline still matters here.",
]

NO_PLAY_MESSAGES = [
    "🍑 Splitter says: Save the bankroll. The model does not see a playable signal.",
    "🍑 Splitter says: Pass this one. Waiting for a clearer edge is part of the process.",
]


def message_pool_for_recommendation(recommendation):
    """Classify the final recommendation before choosing dashboard commentary."""
    label = str(recommendation or "").upper()

    if "CHEEK RIPPER" in label or "STRONG PLAY" in label:
        return STRONG_PLAY_MESSAGES

    if "PLAYABLE" in label:
        return PLAYABLE_MESSAGES

    if "LEAN" in label:
        return LEAN_MESSAGES

    return NO_PLAY_MESSAGES


def splitter_commentary(game):
    recommendation = game.get("model", {}).get("recommendation")
    return choice(message_pool_for_recommendation(recommendation))
