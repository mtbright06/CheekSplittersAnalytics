import json
from pathlib import Path

from engine.first5.first5_model import build_first5_card


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "cards"
OUTPUT_FILE = OUTPUT_DIR / "first5_card.json"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("")
    print("=" * 60)
    print("SharpStack First 5 Lab")
    print("=" * 60)
    print("Building First 5 model card...")

    card = build_first5_card()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(card, file, indent=2)

    summary = card.get("summary", {})

    print("")
    print(f"First 5 card written to: {OUTPUT_FILE}")
    print(f"Games loaded: {summary.get('games_loaded', 0)}")
    print(f"F5 ML leans: {summary.get('f5_ml_leans', 0)}")
    print(f"F5 total leans: {summary.get('f5_total_leans', 0)}")
    print(f"Top ML play: {summary.get('top_ml_play', 'PASS')}")
    print(f"Top total play: {summary.get('top_total_play', 'PASS')}")


if __name__ == "__main__":
    main()
