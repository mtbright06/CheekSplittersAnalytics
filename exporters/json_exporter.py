import json
from datetime import datetime
from pathlib import Path

from engine.contracts.sharpstack_card import normalize_card


class JsonExporter:

    @staticmethod
    def export(games, sport=None, version=None):
        root = Path(__file__).resolve().parents[1]

        output_dir = root / "output"
        cards_dir = output_dir / "cards"

        output_dir.mkdir(exist_ok=True)
        cards_dir.mkdir(parents=True, exist_ok=True)

        sport_name = (sport or "unknown").lower()

        raw_payload = {
            "sport": sport,
            "version": version,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "games": [
                JsonExporter.game_to_dict(game)
                for game in games
            ],
        }

        payload = normalize_card(raw_payload)

        sport_path = cards_dir / f"{sport_name}_card.json"
        legacy_path = output_dir / "sharpstack_card.json"

        with open(sport_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=JsonExporter.default_serializer)

        with open(legacy_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=JsonExporter.default_serializer)

        return sport_path

    @staticmethod
    def game_to_dict(game):
        if isinstance(game, dict):
            return game

        if hasattr(game, "__dict__"):
            return game.__dict__

        return {}

    @staticmethod
    def default_serializer(obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__

        return str(obj)
