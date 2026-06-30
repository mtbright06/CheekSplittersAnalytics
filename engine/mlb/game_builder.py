from datetime import datetime

from engine.odds.provider_factory import get_odds_provider
from engine.odds.market_edge import calculate_market_edge, market_edge_to_dict


def pitcher_from_team(team_blob):
    pitcher = team_blob.get("probablePitcher") or {}

    return {
        "name": pitcher.get("fullName") or "Unknown Starter",
        "throws": None,
        "record": None,
        "era": None,
        "whip": None,
        "ip": None,
        "so": None,
        "bb": None,
        "hr_allowed": None,
        "k_rate": None,
        "bb_rate": None,
        "hr9": None,
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
            quote.away_team.lower(),
            quote.home_team.lower(),
            quote.selection.lower(),
        )

        current = lookup.get(key)

        if current is None or (
            quote.american_odds is not None
            and current.american_odds is not None
            and quote.american_odds > current.american_odds
        ):
            lookup[key] = quote

    return lookup


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

        play = home
        model_probability = 50.0

        quote = quote_lookup.get(
            (
                away.lower(),
                home.lower(),
                play.lower(),
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
                "away": pitcher_from_team(away_blob),
                "home": pitcher_from_team(home_blob),
            },
            "model": {
                "play": play,
                "market": "Moneyline",
                "model_probability": model_probability,
                "edge": edge,
                "confidence": 50,
                "signals": [
                    {"name": "MLB Foundation", "value": 1.0},
                    {"name": "Market Connected", "value": 1.0 if quote else 0.0},
                ],
                "reasons": [
                    "MLB schedule loaded from MLB Stats API.",
                    "Probable pitchers attached when available.",
                    "Real odds attached when available.",
                    "Model scoring is placeholder until SharpScore ships.",
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
