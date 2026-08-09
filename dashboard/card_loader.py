import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "output" / "cards"
LEGACY_CARD = ROOT / "output" / "sharpstack_card.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.contracts.sharpstack_card import normalize_card


def load_card_file(path):
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            card = json.load(f)
    except Exception as ex:
        print(f"Skipping invalid card file {path}: {ex}")
        return None

    return normalize_card(card)


def load_sport_card(sport):
    return load_card_file(CARDS_DIR / f"{sport.lower()}_card.json")


def load_all_cards():
    cards = []

    for sport in ["kbo", "mlb"]:
        card = load_sport_card(sport)
        if card:
            cards.append(card)

    if not cards:
        legacy = load_card_file(LEGACY_CARD)
        if legacy:
            cards.append(legacy)

    return cards


def combined_dashboard_card():
    cards = load_all_cards()
    games = []

    for card in cards:
        sport = (card.get("sport") or "unknown").lower()

        for game in card.get("games", []):
            game["sport"] = game.get("sport") or sport
            games.append(game)

    return {
        "sport": "MULTI",
        "version": cards[0].get("version") if cards else "N/A",
        "generated_at": cards[0].get("generated_at") if cards else None,
        "cards": cards,
        "games": games,
    }
