def recommendation(edge, confidence):
    edge = edge or 0
    confidence = confidence or 0

    if edge >= 10 and confidence >= 70:
        return "🔥 CHEEK RIPPER"

    if edge >= 7 and confidence >= 65:
        return "✅ STRONG PLAY"

    if edge >= 5 and confidence >= 55:
        return "🟡 PLAYABLE"

    if edge >= 2 and confidence >= 50:
        return "LEAN"

    return "PASS"


def grade_label(edge):
    if edge is None:
        return "NO DATA"
    if edge >= 10:
        return "CHEEK RIPPER 🔥"
    if edge >= 7:
        return "STRONG PLAY"
    if edge >= 5:
        return "PLAYABLE"
    if edge >= 2:
        return "LEAN"
    return "PASS"
