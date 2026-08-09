import json
from pathlib import Path

from engine.odds.the_odds_api_provider import (
    fetch_mlb_moneyline_raw,
    normalize_mlb_moneyline_events,
    save_sample,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
NORMALIZED_PATH = OUTPUT / "odds_api_normalized_mlb.json"


def main():
    print("=" * 70)
    print("SharpStack Odds API Test Harness")
    print("=" * 70)

    raw = fetch_mlb_moneyline_raw()
    save_sample(raw)

    normalized = normalize_mlb_moneyline_events(raw)

    OUTPUT.mkdir(exist_ok=True)

    with open(NORMALIZED_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)

    print(f"Saved normalized odds to {NORMALIZED_PATH}")
    print()
    print(f"Events found: {len(normalized)}")

    print()
    print("Preview:")
    print("-" * 70)

    for event in normalized[:5]:
        print(f"{event['away_team']} @ {event['home_team']}")
        print(f"Start: {event['commence_time']}")
        print(f"Books: {len(event['bookmakers'])}")

        if event["bookmakers"]:
            book = event["bookmakers"][0]
            print(f"Sample book: {book['sportsbook']}")

            for outcome in book["outcomes"]:
                print(
                    f"  {outcome['team']}: "
                    f"{outcome['american_odds']} "
                    f"({outcome['implied_probability']}%)"
                )

        print("-" * 70)


if __name__ == "__main__":
    main()
