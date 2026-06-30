import json
from pathlib import Path

from providers.mlb.schedule_provider import MLBScheduleProvider
from engine.mlb.game_builder import build_mlb_card


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "sharpstack_card.json"


def main():
    provider = MLBScheduleProvider()
    raw_games = provider.load()

    card = build_mlb_card(raw_games)

    OUTPUT.parent.mkdir(exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)

    print(f"MLB SharpStack card written to {OUTPUT}")
    print(f"Games loaded: {len(card.get('games', []))}")


if __name__ == "__main__":
    main()
