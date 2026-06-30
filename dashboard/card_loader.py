import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "output" / "cards"
LEGACY_CARD = ROOT / "output" / "sharpstack_card.json"


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


def normalize_card(card):
    sport = (card.get("sport") or "unknown").lower()

    normalized_games = []

    for game in card.get("games", []):
        normalized_games.append(normalize_game(game, sport))

    card["games"] = normalized_games

    return card


def normalize_game(game, sport):

    #
    # Already using new SharpStack contract.
    #
    if (
        "matchup" in game
        and "model" in game
        and "pitching" in game
    ):
        game["sport"] = game.get("sport") or sport

        model = game.setdefault("model", {})

        model["signals"] = normalize_signals(
            model.get("signals", [])
        )

        return game

    #
    # Legacy KBO contract
    #
    away = game.get("away", {})
    home = game.get("home", {})
    result = game.get("result", {})

    away_name = away.get("name") or "Away"
    home_name = home.get("name") or "Home"

    return {
        "sport": game.get("sport") or sport,
        "game_id": game.get("game_id") or game.get("game_url"),
        "venue": game.get("venue"),
        "start_time": game.get("start_time"),
        "status": game.get("status"),

        "matchup": {
            "away": away_name,
            "home": home_name,
        },

        "pitching": {
            "away": normalize_pitcher(
                away.get("pitcher", {})
            ),
            "home": normalize_pitcher(
                home.get("pitcher", {})
            ),
        },

        "teams": {
            "away": away,
            "home": home,
        },

        "model": {
            "market": result.get("market") or "Moneyline",
            "play": result.get("play") or home_name,
            "model_probability": result.get("model_probability"),
            "edge": result.get("edge"),
            "confidence": result.get("confidence"),
            "recommendation": result.get("recommendation"),
            "reasons": result.get("reasons", []),
            "signals": normalize_signals(
                result.get("signals", [])
            ),
        },

        "odds": game.get("odds", {}),

        "market_edge": game.get("market_edge", {}),

        "raw": game,
    }


def normalize_pitcher(pitcher):
    return {
        "name": pitcher.get("name") or "Unknown Starter",
        "throws": pitcher.get("throws"),
        "bats": pitcher.get("bats"),
        "record": pitcher.get("record"),
        "era": pitcher.get("era"),
        "whip": pitcher.get("whip"),
        "ip": pitcher.get("ip"),
        "so": pitcher.get("so"),
        "bb": pitcher.get("bb"),
        "hr_allowed": pitcher.get("hr_allowed"),
        "k_rate": pitcher.get("k_rate"),
        "bb_rate": pitcher.get("bb_rate"),
        "hr9": pitcher.get("hr9"),
    }


def normalize_signals(signals):
    """
    Make every signal look like:

    {
        "name": "...",
        "value": 0
    }

    regardless of what older exporters produced.
    """

    normalized = []

    if not signals:
        return normalized

    for index, signal in enumerate(signals):

        if isinstance(signal, dict):
            normalized.append({
                "name": signal.get("name") or f"Signal {index+1}",
                "value": signal.get("value") or 0,
            })

        elif isinstance(signal, (list, tuple)):
            if len(signal) >= 2:
                normalized.append({
                    "name": str(signal[0]),
                    "value": signal[1] or 0,
                })
            elif len(signal) == 1:
                normalized.append({
                    "name": str(signal[0]),
                    "value": 0,
                })

        else:
            normalized.append({
                "name": str(signal),
                "value": 0,
            })

    return normalized


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
