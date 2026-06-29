def play_grade(edge):
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


def play_badge_class(edge):
    if edge is None:
        return "badge"

    if edge >= 7:
        return "badge badge-green"

    if edge >= 2:
        return "badge badge-gold"

    return "badge"


def status_badge(label, status="neutral"):
    css = {
        "good": "badge badge-green",
        "warning": "badge badge-gold",
        "bad": "badge badge-red",
        "neutral": "badge",
    }.get(status, "badge")

    return f"<span class='{css}'>{label}</span>"
