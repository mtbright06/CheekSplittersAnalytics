from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.odds.best_line import (
    rank_quotes,
    select_best_quote,
)


def main() -> None:
    now = datetime.now(
        timezone.utc
    )

    quotes = [
        {
            "sportsbook": "FanDuel",
            "american_odds": -125,
            "updated_at": (
                now - timedelta(minutes=4)
            ).isoformat(),
        },
        {
            "sportsbook": "Fanatics Sportsbook",
            "american_odds": -115,
            "updated_at": (
                now - timedelta(minutes=6)
            ).isoformat(),
        },
        {
            "sportsbook": "Draft Kings",
            "american_odds": -120,
            "updated_at": (
                now - timedelta(minutes=5)
            ).isoformat(),
        },
        {
            "sportsbook": "Mock Odds",
            "american_odds": +150,
            "updated_at": now.isoformat(),
        },
        {
            "sportsbook": "Caesars",
            "american_odds": -105,
            "updated_at": (
                now - timedelta(minutes=35)
            ).isoformat(),
        },
    ]

    model_probability = 0.58

    print("")
    print("=" * 72)
    print("SharpStack Best-Line Test")
    print("=" * 72)

    ranked = rank_quotes(
        quotes,
        model_probability=(
            model_probability
        ),
    )

    for index, quote in enumerate(
        ranked,
        start=1,
    ):
        odds = quote.get(
            "american_odds"
        )

        odds_text = (
            f"+{int(odds)}"
            if odds is not None
            and odds > 0
            else str(int(odds))
            if odds is not None
            else "N/A"
        )

        print(
            f"{index}. "
            f"{quote.get('sportsbook'):12} "
            f"{odds_text:>6} | "
            f"Edge "
            f"{quote.get('edge_pct', 0):+.2f}% | "
            f"EV "
            f"{quote.get('expected_value_pct', 0):+.2f}% | "
            f"Stale: {quote.get('stale')}"
        )

    best = select_best_quote(
        quotes,
        model_probability=(
            model_probability
        ),
    )

    print("")
    print("BEST ACTIVE PRICE")
    print("-" * 72)

    if best is None:
        print("No valid active quote.")
        return

    print(
        best.get("sportsbook"),
        best.get("american_odds"),
    )
    print(
        "Implied:",
        round(
            best.get(
                "implied_probability",
                0,
            )
            * 100,
            2,
        ),
    )
    print(
        "Edge:",
        round(
            best.get(
                "edge_pct",
                0,
            ),
            2,
        ),
    )
    print(
        "EV:",
        round(
            best.get(
                "expected_value_pct",
                0,
            ),
            2,
        ),
    )
    print(
        "Quotes compared:",
        best.get(
            "quotes_compared"
        ),
    )


if __name__ == "__main__":
    main()
