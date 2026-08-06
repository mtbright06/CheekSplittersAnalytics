def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def data_completeness_score(*values):
    total = len(values)

    if total == 0:
        return 0

    present = len([v for v in values if v is not None])

    return present / total


def is_unknown_starter(pitcher):
    return (
        not pitcher
        or pitcher.get("name") == "Unknown Starter"
    )


def calculate_confidence(
    score_diff,
    away_pitcher,
    home_pitcher,
    odds,
    away_offense,
    home_offense,
):
    # Compatibility argument only. MLB moneyline confidence is model-derived
    # from score separation, core data completeness, and starter certainty; it
    # intentionally does not consume odds, edge, price, or market quality.
    _ = odds

    breakdown = {
        "base": 45,
        "matchup_strength": 0,
        "data_quality": 0,
        "starter_certainty": 0,
    }

    # Bigger model separation = more confidence
    breakdown["matchup_strength"] = min(score_diff * 1.1, 30)

    completeness = data_completeness_score(
        away_pitcher.get("era"),
        away_pitcher.get("whip"),
        home_pitcher.get("era"),
        home_pitcher.get("whip"),
        away_offense.get("ops"),
        home_offense.get("ops"),
    )

    breakdown["data_quality"] = completeness * 20

    unknown_count = sum([
        is_unknown_starter(away_pitcher),
        is_unknown_starter(home_pitcher),
    ])

    if unknown_count == 0:
        breakdown["starter_certainty"] = 0
    elif unknown_count == 1:
        breakdown["starter_certainty"] = -10
    else:
        breakdown["starter_certainty"] = -20

    confidence = sum(breakdown.values())

    for key in breakdown:
        breakdown[key] = round(breakdown[key], 1)

    return (
        round(clamp(confidence, 35, 95), 1),
        breakdown,
    )
