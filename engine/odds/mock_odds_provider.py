from datetime import datetime

from engine.odds.implied_probability import american_to_implied_probability
from engine.odds.odds_models import OddsQuote


MOCK_LINES = {
    "LG Twins": -110,
    "Kiwoom Heroes": -110,
    "Lotte Giants": -105,
    "Doosan Bears": -115,
    "Samsung Lions": +105,
    "NC Dinos": -125,
    "KIA Tigers": -120,
    "Hanwha Eagles": +110,
    "KT Wiz": -108,
    "SSG Landers": -112,
}


def get_mock_moneyline(game):
    matchup = game.get("matchup", {})
    model = game.get("model", {})

    selection = model.get("play") or matchup.get("home")
    away = matchup.get("away")
    home = matchup.get("home")

    odds = MOCK_LINES.get(selection, -110)

    opening = odds + 8 if odds < 0 else odds - 8
    movement = odds - opening

    return OddsQuote(
        sport="baseball",
        league="KBO",
        away_team=away,
        home_team=home,
        market="Moneyline",
        selection=selection,
        american_odds=odds,
        opening_odds=opening,
        current_odds=odds,
        line_movement=movement,
        implied_probability=american_to_implied_probability(odds),
        sportsbook="MockBook",
        last_updated=datetime.now().isoformat(timespec="seconds"),
    )


def odds_quote_to_dict(quote):
    return {
        "sport": quote.sport,
        "league": quote.league,
        "away_team": quote.away_team,
        "home_team": quote.home_team,
        "market": quote.market,
        "selection": quote.selection,
        "moneyline": quote.american_odds,
        "american_odds": quote.american_odds,
        "opening_odds": quote.opening_odds,
        "current_odds": quote.current_odds,
        "line_movement": quote.line_movement,
        "book_probability": quote.implied_probability,
        "implied_probability": quote.implied_probability,
        "sportsbook": quote.sportsbook,
        "last_updated": quote.last_updated,
    }
