from engine.odds.provider_factory import get_odds_provider
from engine.odds.market_edge import (
    calculate_market_edge,
    market_edge_to_dict,
)


def _clean(value):
    return (value or "").strip().lower()


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def _set(obj, key, value):
    if isinstance(obj, dict):
        obj[key] = value
        return

    setattr(obj, key, value)


def quote_to_odds_dict(quote):
    return {
        "provider": quote.provider,
        "sportsbook": quote.sportsbook,
        "league": quote.league,
        "market": quote.market,
        "selection": quote.selection,
        "away_team": quote.away_team,
        "home_team": quote.home_team,
        "moneyline": quote.american_odds,
        "american_odds": quote.american_odds,
        "book_probability": quote.implied_probability,
        "implied_probability": quote.implied_probability,
        "event_id": quote.event_id,
        "commence_time": quote.commence_time,
        "last_updated": quote.last_updated,
    }


class OddsEnricher:
    def __init__(self, league):
        self.provider = get_odds_provider("the_odds_api")
        self.league = (league or "MLB").upper()
        self.quote_lookup = {}

    def load_quotes(self):
        quotes = self.provider.get_moneylines(self.league)
        self.quote_lookup = {}

        for quote in quotes:
            key = (
                _clean(quote.away_team),
                _clean(quote.home_team),
                _clean(quote.selection),
            )

            current = self.quote_lookup.get(key)

            if current is None:
                self.quote_lookup[key] = quote
                continue

            if quote.american_odds is not None and current.american_odds is not None:
                if quote.american_odds > current.american_odds:
                    self.quote_lookup[key] = quote

    def find_quote(self, game):
        matchup = _get(game, "matchup", {})
        model = _get(game, "model", {})

        away = _get(matchup, "away")
        home = _get(matchup, "home")

        selection = (
            _get(game, "play")
            or _get(model, "play")
            or _get(game, "selection")
        )

        if not away or not home or not selection:
            return None

        key = (_clean(away), _clean(home), _clean(selection))
        return self.quote_lookup.get(key)

    def enrich(self, games):
        self.load_quotes()

        for game in games:
            quote = self.find_quote(game)

            if quote is None:
                continue

            odds_dict = quote_to_odds_dict(quote)
            _set(game, "odds", odds_dict)

            model = _get(game, "model", {})
            model_probability = (
                _get(game, "model_probability")
                or _get(model, "model_probability")
            )

            if model_probability is not None:
                edge = calculate_market_edge(model_probability, quote)
                _set(game, "market_edge", market_edge_to_dict(edge))

        return games
