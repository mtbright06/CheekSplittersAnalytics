from engine.odds.provider_factory import get_odds_provider


def main():
    provider = get_odds_provider("the_odds_api")
    quotes = provider.get_moneylines("KBO")

    print("=" * 70)
    print("KBO Moneyline Quotes")
    print("=" * 70)
    print(f"Quotes found: {len(quotes)}")
    print()

    for quote in quotes[:40]:
        print(
            f"{quote.away_team} @ {quote.home_team} | "
            f"{quote.selection} | "
            f"{quote.sportsbook}: {quote.american_odds} "
            f"({quote.implied_probability}%)"
        )


if __name__ == "__main__":
    main()
