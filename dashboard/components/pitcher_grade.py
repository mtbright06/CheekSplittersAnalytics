from math import isnan


def _clean(value, default=None):
    try:
        if value is None:
            return default

        value = float(value)

        if isnan(value):
            return default

        return value

    except Exception:
        return default


def grade_pitcher(stats):
    """
    Returns:
        ACE
        STRONG
        SOLID
        AVERAGE
        TARGET
    """

    era = _clean(stats.get("era"), 4.50)
    whip = _clean(stats.get("whip"), 1.35)
    k9 = _clean(stats.get("k_rate"), 7.0)
    bb9 = _clean(stats.get("bb_rate"), 3.2)
    hr9 = _clean(stats.get("hr9"), 1.2)

    score = 0

    # ERA
    if era <= 3.00:
        score += 3
    elif era <= 3.75:
        score += 2
    elif era <= 4.50:
        score += 1
    else:
        score -= 2

    # WHIP
    if whip <= 1.10:
        score += 3
    elif whip <= 1.25:
        score += 2
    elif whip <= 1.35:
        score += 1
    else:
        score -= 2

    # Strikeouts
    if k9 >= 9:
        score += 3
    elif k9 >= 8:
        score += 2
    elif k9 >= 7:
        score += 1

    # Walks
    if bb9 <= 2:
        score += 2
    elif bb9 <= 3:
        score += 1
    else:
        score -= 1

    # Home Runs
    if hr9 <= 0.8:
        score += 2
    elif hr9 <= 1.1:
        score += 1
    elif hr9 >= 1.5:
        score -= 2

    if score >= 11:
        return "ACE"

    if score >= 8:
        return "STRONG"

    if score >= 5:
        return "SOLID"

    if score >= 2:
        return "AVERAGE"

    return "TARGET"


def grade_color(grade):

    return {
        "ACE": "#2ecc71",
        "STRONG": "#4CAF50",
        "SOLID": "#f1c40f",
        "AVERAGE": "#f39c12",
        "TARGET": "#e74c3c",
    }.get(grade, "#95a5a6")


def grade_icon(grade):

    return {
        "ACE": "👑",
        "STRONG": "🛡️",
        "SOLID": "👍",
        "AVERAGE": "⚠️",
        "TARGET": "🎯",
    }.get(grade, "❔")


def pitcher_tags(stats):

    tags = []

    era = _clean(stats.get("era"))
    whip = _clean(stats.get("whip"))
    k9 = _clean(stats.get("k_rate"))
    bb9 = _clean(stats.get("bb_rate"))
    hr9 = _clean(stats.get("hr9"))

    if k9 and k9 >= 9:
        tags.append(("🔥 Strikeout Arm", "good"))

    if bb9 and bb9 <= 2:
        tags.append(("🎯 Elite Control", "good"))

    if whip and whip <= 1.15:
        tags.append(("🧊 Limits Traffic", "good"))

    if hr9 and hr9 >= 1.4:
        tags.append(("💣 HR Risk", "bad"))

    if era and era <= 3:
        tags.append(("👑 Ace Stuff", "good"))

    if era and era >= 5:
        tags.append(("🍑 Attack Spot", "bad"))

    return tags
