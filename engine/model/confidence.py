def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def data_completeness_score(*values):
    total = len(values)

    if total == 0:
        return 0

    present = len([v for v in values if v is not None])

    return present / total


def calculate_confidence(
    score_diff,
    away_pitcher,
    home_pitcher,
    odds,
    away_offense,
    home_offense,
):
    confidence = 45

    confidence += min(score_diff * 1.1, 30)

    completeness = data_completeness_score(
        away_pitcher.get("era"),
        away_pitcher.get("whip"),
        home_pitcher.get("era"),
        home_pitcher.get("whip"),
        odds.get("book_probability"),
        away_offense.get("ops"),
        home_offense.get("ops"),
    )

    confidence += completeness * 20

    return round(clamp(confidence, 35, 95), 1)
