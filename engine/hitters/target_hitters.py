POWER_HINTS = {
    "Hunter Goodman": 92,
    "Brenton Doyle": 82,
    "Ryan McMahon": 78,
    "James Wood": 91,
    "Ben Rice": 88,
    "Garrett Mitchell": 82,
    "Shohei Ohtani": 98,
    "Aaron Judge": 99,
    "Kyle Schwarber": 96,
    "Matt Olson": 92,
    "Yordan Alvarez": 95,
}


PLACEHOLDER_HITTERS = [
    {"name": "Hunter Goodman", "team": "Colorado Rockies", "bat_side": "R"},
    {"name": "Brenton Doyle", "team": "Colorado Rockies", "bat_side": "R"},
    {"name": "Ryan McMahon", "team": "Colorado Rockies", "bat_side": "L"},
    {"name": "James Wood", "team": "Washington Nationals", "bat_side": "L"},
    {"name": "Ben Rice", "team": "New York Yankees", "bat_side": "L"},
    {"name": "Garrett Mitchell", "team": "Milwaukee Brewers", "bat_side": "L"},
    {"name": "Shohei Ohtani", "team": "Los Angeles Dodgers", "bat_side": "L"},
    {"name": "Aaron Judge", "team": "New York Yankees", "bat_side": "R"},
    {"name": "Kyle Schwarber", "team": "Philadelphia Phillies", "bat_side": "L"},
    {"name": "Matt Olson", "team": "Atlanta Braves", "bat_side": "L"},
    {"name": "Yordan Alvarez", "team": "Houston Astros", "bat_side": "L"},
]


def safe_num(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def side_matches(bat_side, attack_side):
    bat_side = str(bat_side or "").upper()
    attack_side = str(attack_side or "ANY").upper()

    if attack_side in ["ANY", "BOTH"]:
        return True

    return bat_side == attack_side


def star_rating(score):
    if score >= 90:
        return "★★★★★"
    if score >= 82:
        return "★★★★☆"
    if score >= 74:
        return "★★★★"
    if score >= 66:
        return "★★★☆"
    if score >= 58:
        return "★★★"
    return "★★"


def build_target_score(hitter, attack_side, bomb_score):
    power = POWER_HINTS.get(hitter["name"], 70)
    side_fit = 100 if side_matches(hitter["bat_side"], attack_side) else 55
    bomb_boost = safe_num(bomb_score)

    score = (
        power * 0.50
        + side_fit * 0.25
        + bomb_boost * 0.25
    )

    return round(max(0, min(100, score)), 1)


def get_team_targets(team_name, attack_side, bomb_score):
    rows = []

    for hitter in PLACEHOLDER_HITTERS:
        if hitter["team"] != team_name:
            continue

        score = build_target_score(hitter, attack_side, bomb_score)

        rows.append(
            {
                **hitter,
                "target_score": score,
                "stars": star_rating(score),
                "side_fit": side_matches(hitter["bat_side"], attack_side),
            }
        )

    return sorted(rows, key=lambda x: x["target_score"], reverse=True)


def attach_target_hitters_to_pitchers(pitchers):
    enriched = []

    for item in pitchers:
        item["top_hitters"] = get_team_targets(
            team_name=item.get("opponent"),
            attack_side=item.get("target_side"),
            bomb_score=item.get("bomb_score"),
        )[:5]

        enriched.append(item)

    return enriched
