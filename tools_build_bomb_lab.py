import json
from pathlib import Path

from engine.bomb_lab.pitcher_attack import build_bomb_lab_card


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "cards" / "bomb_lab_card.json"


def main():
    card = build_bomb_lab_card()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)

    print(f"Bomb Lab card written to {OUTPUT}")
    print(f"Pitchers loaded: {card.get('summary', {}).get('pitchers_loaded')}")
    print(f"Elite: {card.get('summary', {}).get('elite')}")
    print(f"Strong: {card.get('summary', {}).get('strong')}")
    print(f"Watch: {card.get('summary', {}).get('watch')}")


if __name__ == "__main__":
    main()