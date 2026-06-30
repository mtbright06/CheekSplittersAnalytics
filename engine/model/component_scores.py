def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def offense_score(offense):
    score = 50

    if not offense:
        return score

    rpg = offense.get("runs_per_game")
    ops = offense.get("ops")
    hrpg = offense.get("hr_per_game")
    iso = offense.get("iso")
    k_rate = offense.get("k_rate")
    bb_rate = offense.get("bb_rate")

    if rpg is not None:
        score += (rpg - 4.4) * 7

    if ops is not None:
        score += (ops - 0.710) * 120

    if hrpg is not None:
        score += (hrpg - 1.1) * 8

    if iso is not None:
        score += (iso - 0.160) * 90

    if k_rate is not None:
        score -= (k_rate - 22.0) * 0.6

    if bb_rate is not None:
        score += (bb_rate - 8.0) * 0.8

    return round(clamp(score), 1)


def starting_pitcher_score(pitcher):
    if not pitcher or pitcher.get("name") == "Unknown Starter":
        return 50

    score = 50

    era = pitcher.get("era")
    whip = pitcher.get("whip")
    k9 = pitcher.get("k_rate")
    bb9 = pitcher.get("bb_rate")
    hr9 = pitcher.get("hr9")

    if era is not None:
        score += (4.50 - era) * 6

    if whip is not None:
        score += (1.35 - whip) * 18

    if k9 is not None:
        score += (k9 - 8.0) * 2

    if bb9 is not None:
        score += (3.2 - bb9) * 2

    if hr9 is not None:
        score += (1.2 - hr9) * 6

    return round(clamp(score), 1)


def bullpen_score(bullpen):
    if not bullpen:
        return 50

    era = bullpen.get("era")
    whip = bullpen.get("whip")

    score = 50

    if era is not None:
        score += (4.25 - era) * 5

    if whip is not None:
        score += (1.35 - whip) * 15

    return round(clamp(score), 1)


def market_score(book_probability, model_probability):
    if book_probability is None or model_probability is None:
        return 50

    edge = model_probability - book_probability

    return round(clamp(50 + edge * 4), 1)


def home_field_score(is_home):
    return 56 if is_home else 50
