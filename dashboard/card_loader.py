import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "output" / "cards"
LEGACY_CARD = ROOT / "output" / "sharpstack_card.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.contracts.sharpstack_card import normalize_card
from kbo_freshness import evaluate_kbo_card_freshness
from providers.kbo_data_provider import KBODataProvider


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
    card = load_card_file(CARDS_DIR / f"{sport.lower()}_card.json")
    if sport.lower() == "kbo":
        return attach_kbo_freshness(card)

    return card


def attach_kbo_freshness(card):
    schedule_games = None
    try:
        schedule_games = KBODataProvider.get_schedule()
    except Exception:
        schedule_games = None

    freshness = evaluate_kbo_card_freshness(
        card,
        schedule_games=schedule_games,
    )

    if card is None:
        card = {
            "sport": "KBO",
            "version": None,
            "generated_at": None,
            "games": [],
        }

    card["_freshness"] = freshness.to_dict()
    return card


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
