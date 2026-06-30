from datetime import datetime

from engine.mlb.pitchers import fetch_pitcher_stats
from engine.odds.provider_factory import get_odds_provider
from engine.odds.market_edge import calculate_market_edge, market_edge_to_dict


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


def quote_to_dict(quote):
    if not quote:
        return {
            "moneyline": None,
            "book_probability": None,
            "sportsbook": "Unavailable",
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


def clean(value):
    return (value or "").strip().lower()


def choose_placeholder_play(home, away, quote_lookup):
    """
    Temporary MLB model:
    prefer the side with better available market value if odds exist;
    otherwise default home.
    """

    home_quote = quote_lookup.get((clean(away), clean(home), clean(home)))
    away_quote = quote_lookup.get((clean(away), clean(home), clean(away)))

    if home_quote and away_quote:
        if home_quote.american_odds > away_quote.american_odds:
            return home
        return away

    return home


def build_mlb_card(raw_games):
    quote_lookup = build_quote_lookup()
    games = []

    for raw in raw_games:
        teams = raw.get("teams", {})
        away_blob = teams.get("away", {})
        home_blob = teams.get("home", {})

        away = away_blob.get("team", {}).get("name")
        home = home_blob.get("team", {}).get("name")

        if not away or not home:
            continue

        away_pitcher = pitcher_from_team(away_blob)
        home_pitcher = pitcher_from_team(home_blob)

        play = choose_placeholder_play(home, away, quote_lookup)

        model_probability = 50.0

        quote = quote_lookup.get(
            (
                clean(away),
                clean(home),
                clean(play),
            )
        )

        odds = quote_to_dict(quote)
        market_edge = {}
        edge = 0.0

        if quote:
            calculated = calculate_market_edge(model_probability, quote)
            market_edge = market_edge_to_dict(calculated)
            edge = market_edge.get("edge") or 0.0

        game = {
            "sport": "mlb",
            "game_id": raw.get("gamePk"),
            "status": raw.get("status", {}).get("detailedState"),
            "commence_time": raw.get("gameDate"),
            "matchup": {
                "away": away,
                "home": home,
            },
            "pitching": {
                "away": away_pitcher,
                "home": home_pitcher,
            },
            "model": {
                "play": play,
                "market": "Moneyline",
                "model_probability": model_probability,
                "edge": edge,
                "confidence": 50,
                "signals": [
                    {"name": "MLB Schedule", "value": 1.0},
                    {"name": "Probable Pitchers", "value": pitcher_signal(away_pitcher, home_pitcher)},
                    {"name": "Market Connected", "value": 1.0 if quote else 0.0},
                ],
                "reasons": [
                    "MLB schedule loaded from MLB Stats API.",
                    "Probable pitchers attached when available.",
                    "Pitcher season stats attached when available.",
                    "Real odds attached when available.",
                    "SharpScore model still pending.",
                ],
            },
            "odds": odds,
            "market_edge": market_edge,
        }

        games.append(game)

    return {
        "sport": "MLB",
        "version": "0.8 Alpha",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "games": games,
    }


def pitcher_signal(away_pitcher, home_pitcher):
    away_ready = 1 if away_pitcher.get("era") is not None else 0
    home_ready = 1 if home_pitcher.get("era") is not None else 0

    return (away_ready + home_ready) / 2
