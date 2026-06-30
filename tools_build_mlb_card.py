import json
from pathlib import Path

from providers.mlb.schedule_provider import MLBScheduleProvider
from engine.mlb.game_builder import build_mlb_card


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "cards"
OUTPUT = OUTPUT_DIR / "mlb_card.json"
LEGACY_OUTPUT = ROOT / "output" / "sharpstack_card.json"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    provider = MLBScheduleProvider()
    raw_games = provider.load()

    card = build_mlb_card(raw_games)

    write_json(OUTPUT, card)
    write_json(LEGACY_OUTPUT, card)

    print(f"MLB card written to {OUTPUT}")
    print(f"Legacy dashboard card written to {LEGACY_OUTPUT}")
    print(f"Games loaded: {len(card.get('games', []))}")


if __name__ == "__main__":
    main()
