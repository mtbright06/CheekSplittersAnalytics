from datetime import datetime

from engine.mlb.offense import fetch_team_batting_stats
from engine.mlb.pitchers import fetch_pitcher_stats
from engine.mlb.team_mapping import MLB_TEAM_ABBR
from engine.model.sharpscore import build_sharpscore_decision
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


def quote_for_team(quote_lookup, away, home, selection):
    return quote_lookup.get(
        (
            clean(away),
            clean(home),
            clean(selection),
        )
    )


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

        away_quote = quote_for_team(quote_lookup, away, home, away)
        home_quote = quote_for_team(quote_lookup, away, home, home)

        decision = build_sharpscore_decision(
            away,
            home,
            away_profile,
            home_profile,
            away_pitcher,
            home_pitcher,
            away_quote,
            home_quote,
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
