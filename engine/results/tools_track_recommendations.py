from pathlib import Path

from engine.results.recommendation_tracker import append_from_card_file


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"


def main():
    total = 0

    for filename in ["kbo_card.json", "mlb_card.json"]:
        path = CARDS_DIR / filename
        count = append_from_card_file(path)
        total += count
        print(f"{filename}: {count} new recommendation(s) tracked")

    print(f"\nTotal new recommendations tracked: {total}")


if __name__ == "__main__":
    main()