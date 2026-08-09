from engine.odds.the_odds_api_provider import TheOddsApiProvider


def get_odds_provider(name="the_odds_api"):
    if name == "the_odds_api":
        return TheOddsApiProvider()

    raise ValueError(f"Unknown odds provider: {name}")
