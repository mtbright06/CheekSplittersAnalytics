def splitter_commentary(game):
    model = game.get("model", {})
    edge = model.get("edge") or 0
    confidence = model.get("confidence") or 0
    play = model.get("play") or "this play"

    if edge >= 10:
        return f"🍑 Splitter says: Vegas left the door open on {play}. Don't let them close it."

    if edge >= 7 and confidence >= 85:
        return f"🍑 Splitter says: This one checks enough boxes to make me lean in."

    if edge >= 5:
        return f"🍑 Splitter says: Not a nuke, but the model sees something worth respecting."

    if edge >= 2:
        return f"🍑 Splitter says: Lean only. No need to force cheeks where cheeks do not belong."

    return "🍑 Splitter says: Save the bankroll. Even degenerates need discipline."
