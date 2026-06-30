import json
from datetime import datetime
from pathlib import Path


class JsonExporter:

    @staticmethod
    def export(games, sport=None, version=None):
        root = Path(__file__).resolve().parents[1]

        output_dir = root / "output"
        cards_dir = output_dir / "cards"

        output_dir.mkdir(exist_ok=True)
        cards_dir.mkdir(parents=True, exist_ok=True)

        sport_name = (sport or "unknown").lower()

        payload = {
            "sport": sport,
            "version": version,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "games": [JsonExporter.game_to_dict(game, sport_name) for game in games],
        }

        sport_path = cards_dir / f"{sport_name}_card.json"
        legacy_path = output_dir / "sharpstack_card.json"

        with open(sport_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=JsonExporter.default_serializer)

        with open(legacy_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=JsonExporter.default_serializer)

        return sport_path

    @staticmethod
    def game_to_dict(game, sport_name):
        if isinstance(game, dict):
            game["sport"] = game.get("sport") or sport_name
            return game

        data = game.__dict__.copy()
        data["sport"] = data.get("sport") or sport_name
        return data

    @staticmethod
    def default_serializer(obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__

        return str(obj)
