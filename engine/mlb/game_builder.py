from datetime import datetime

from engine.mlb.offense import fetch_team_batting_stats
from engine.mlb.pitchers import fetch_pitcher_stats
from engine.mlb.team_mapping import MLB_TEAM_ABBR
from engine.odds.market_edge import calculate_market_edge, market_edge_to_dict
from engine.odds.provider_factory import get_odds_provider


def clean(value):
    return (value or "").strip().lower()


def pitcher_from_team(team_blob):
    pitcher = team_blob.get("probablePitcher") or {}
    pitcher_id = pitcher.get("id")

    stats = fetch_pitcher_stats(pitcher_id)

    return {
        "id": pitcher_id,
        "name": pitcher.get("fullName") or "Unknown Starter",
        "throws": pitcher.get("pitchHand", {}).get("code"),
        "record": stats.get("record"),
        "era": stats.get("era"),
        "whip": stats.get("whip"),
        "ip": stats.get("ip"),
        "so": stats.get("so"),
        "bb": stats.get("bb"),
        "hr_allowed": stats.get("hr_allowed"),
        "k_rate": stats.get("k_rate"),
        "bb_rate": stats.get("bb_rate"),
        "hr9": stats.get("hr9"),
    }


def team_profile(team_blob):
    team = team_blob.get("team", {})
    name = team.get("name")
    team_id = team.get("id")

    return {
        "id": team_id,
        "name": name,
        "abbr": MLB_TEAM_ABBR.get(name),
        "record": None,
        "form": None,
        "offense": fetch_team_batting_stats(team_id),
        "bullpen": {
            "era": None,
            "whip": None,
            "fip": None,
            "recent_usage": None,
        },
    }


def quote_to_dict(quote):
    if not quote:
        return {
            "provider": None,
            "sportsbook": "Unavailable",
            "market": "Moneyline",
            "selection": None,
            "moneyline": None,
            "american_odds": None,
            "book_probability": None,
            "implied_probability": None,
            "last_updated": None,
        }

    return {
        "provider": quote.provider,
        "sportsbook": quote.sportsbook,
        "league": quote.league,
        "market": quote.market,
        "selection": quote.selection,
        "moneyline": quote.american_odds,
        "american_odds": quote.american_odds,
        "book_probability": quote.implied_probability,
        "implied_probability": quote.implied_probability,
        "event_id": quote.event_id,
        "commence_time": quote.commence_time,
        "last_updated": quote.last_updated,
    }


def build_quote_lookup():
    try:
        provider = get_odds_provider("the_odds_api")
        quotes = provider.get_moneylines("MLB")
    except Exception as ex:
        print(f"MLB odds unavailable: {ex}")
        return {}

    lookup = {}

    for quote in quotes:
        key = (
            clean(quote.away_team),
            clean(quote.home_team),
            clean(quote.selection),
        )

        current = lookup.get(key)

        if current is None:
            lookup[key] = quote
            continue

        if quote.american_odds is not None and current.american_odds is not None:
            if quote.american_odds > current.american_odds:
                lookup[key] = quote

    return lookup


def offense_score(offense):
    score = 50

    rpg = offense.get("runs_per_game")
    ops = offense.get("ops")
    hrpg = offense.get("hr_per_game")
    iso = offense.get("iso")
    k_rate = offense.get("k_rate")

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

    return clamp(score, 0, 100)


def pitching_score(pitcher):
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

    return clamp(score, 0, 100)


def choose_play(away, home, away_score, home_score):
    if away_score > home_score:
        return away

    return home


def build_model(away_name, home_name, away_profile, home_profile, away_pitcher, home_pitcher, quote_lookup):
    away_off = offense_score(away_profile.get("offense", {}))
    home_off = offense_score(home_profile.get("offense", {}))

    away_pitch = pitching_score(away_pitcher)
    home_pitch = pitching_score(home_pitcher)

    away_total = (away_off * 0.45) + (away_pitch * 0.45) + 5
    home_total = (home_off * 0.45) + (home_pitch * 0.45) + 10

    play = choose_play(away_name, home_name, away_total, home_total)

    diff = abs(home_total - away_total)

    model_probability = clamp(50 + diff * 0.55, 50, 68)
    confidence = clamp(50 + diff * 1.2, 50, 95)

    quote = quote_lookup.get((clean(away_name), clean(home_name), clean(play)))

    edge = 0
    market_edge = {}

    if quote:
        calculated = calculate_market_edge(model_probability, quote)
        market_edge = market_edge_to_dict(calculated)
        edge = market_edge.get("edge") or 0

    signals = [
        {"name": "Away Offense", "value": round(away_off / 100, 2)},
        {"name": "Home Offense", "value": round(home_off / 100, 2)},
        {"name": "Away Pitching", "value": round(away_pitch / 100, 2)},
        {"name": "Home Pitching", "value": round(home_pitch / 100, 2)},
        {"name": "Market Connected", "value": 1.0 if quote else 0.0},
    ]

    reasons = [
        f"{away_name} offense score: {away_off:.1f}",
        f"{home_name} offense score: {home_off:.1f}",
        f"{away_name} starter score: {away_pitch:.1f}",
        f"{home_name} starter score: {home_pitch:.1f}",
        "SharpScore v0.1 uses offense, starting pitching, home field, and market odds.",
    ]

    return {
        "model": {
            "play": play,
            "market": "Moneyline",
            "model_probability": round(model_probability, 1),
            "edge": edge,
            "confidence": round(confidence, 1),
            "recommendation": recommendation(edge),
            "signals": signals,
            "reasons": reasons,
            "component_scores": {
                "away_offense": round(away_off, 1),
                "home_offense": round(home_off, 1),
                "away_pitching": round(away_pitch, 1),
                "home_pitching": round(home_pitch, 1),
            },
        },
        "quote": quote,
        "market_edge": market_edge,
    }


def recommendation(edge):
    if edge >= 10:
        return "🔥 CHEEK RIPPER"
    if edge >= 7:
        return "✅ STRONG PLAY"
    if edge >= 5:
        return "🟡 PLAYABLE"
    if edge >= 2:
        return "LEAN"
    return "PASS"


def build_mlb_card(raw_games):
    quote_lookup = build_quote_lookup()
    games = []

    for raw in raw_games:
        teams = raw.get("teams", {})
        away_blob = teams.get("away", {})
        home_blob = teams.get("home", {})

        away_profile = team_profile(away_blob)
        home_profile = team_profile(home_blob)

        away = away_profile.get("name")
        home = home_profile.get("name")

        if not away or not home:
            continue

        away_pitcher = pitcher_from_team(away_blob)
        home_pitcher = pitcher_from_team(home_blob)

        decision = build_model(
            away,
            home,
            away_profile,
            home_profile,
            away_pitcher,
            home_pitcher,
            quote_lookup,
        )

        quote = decision["quote"]

        game = {
            "sport": "mlb",
            "game_id": raw.get("gamePk"),
            "status": raw.get("status", {}).get("detailedState"),
            "commence_time": raw.get("gameDate"),
            "venue": raw.get("venue", {}).get("name"),
            "matchup": {
                "away": away,
                "home": home,
            },
            "teams": {
                "away": away_profile,
                "home": home_profile,
            },
            "pitching": {
                "away": away_pitcher,
                "home": home_pitcher,
            },
            "model": decision["model"],
            "odds": quote_to_dict(quote),
            "market_edge": decision["market_edge"],
        }

        games.append(game)

    return {
        "sport": "MLB",
        "version": "0.8 Alpha",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "games": games,
    }


def clamp(value, low, high):
    return max(low, min(high, value))
