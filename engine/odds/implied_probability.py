def american_to_implied_probability(odds):
    if odds is None:
        return None

    try:
        odds = int(odds)
    except Exception:
        return None

    if odds < 0:
        return round(abs(odds) / (abs(odds) + 100) * 100, 2)

    if odds > 0:
        return round(100 / (odds + 100) * 100, 2)

    return None


def implied_probability_to_american(probability):
    if probability is None:
        return None

    try:
        p = float(probability) / 100
    except Exception:
        return None

    if p <= 0 or p >= 1:
        return None

    if p >= 0.5:
        return int(round(-(p / (1 - p)) * 100))

    return int(round(((1 - p) / p) * 100))
