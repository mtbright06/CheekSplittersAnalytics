import json
from pathlib import Path

from engine.market.first5_market import build_first5_market_card


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "cards" / "first5_market_card.json"


def main():
    print("")
    print("=" * 64)
    print("SharpStack First 5 Market Edge")
    print("=" * 64)

    card = build_first5_market_card()
    summary = card.get("summary", {})

    print(f"Output: {OUTPUT}")
    print(f"Games loaded: {summary.get('games_loaded', 0)}")
    print(f"Market bets: {summary.get('market_bets', 0)}")
    print(f"Market leans: {summary.get('market_leans', 0)}")
    print(f"Total edges: {summary.get('total_edges', 0)}")
    print(f"Top side: {summary.get('top_side', 'PASS')}")

    if card.get("games"):
        print("")
        print("Top market opportunities:")

        for game in card["games"][:5]:
            side = game.get("best_market_side", {})
            total = game.get("f5_total_market", {})

            print(
                f"- {game.get('matchup')}: "
                f"{side.get('recommendation')} "
                f"edge={side.get('edge_pct')}% | "
                f"F5 total={total.get('lean')} "
                f"edge={total.get('run_edge')}"
            )


if __name__ == "__main__":
    main()
