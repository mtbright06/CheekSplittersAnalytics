import json
import os
from datetime import datetime


class JsonExporter:

    OUTPUT_FOLDER = "output"
    OUTPUT_FILE = "sharpstack_card.json"

    @classmethod
    def export(cls, games, sport=None, version=None):

        os.makedirs(cls.OUTPUT_FOLDER, exist_ok=True)

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "sport": sport,
            "version": version,
            "games": [],
        }

        for game in games:

            payload["games"].append(
                {
                    "matchup": {
                        "away": game.away.name,
                        "home": game.home.name,
                        "venue": game.venue,
                        "start_time": game.start_time,
                        "game_url": game.game_url,
                    },
                    "pitching": {
                        "away": cls._pitcher(game.away.pitcher),
                        "home": cls._pitcher(game.home.pitcher),
                    },
                    "odds": {
                        "moneyline": game.odds.moneyline,
                        "book_probability": game.odds.book_probability,
                    },
                    "model": {
                        "market": game.result.market,
                        "play": game.result.play,
                        "model_probability": game.result.model_probability,
                        "edge": game.result.edge,
                        "confidence": game.result.confidence,
                        "recommendation": game.result.recommendation,
                        "signals": cls._signals(game.result.signals),
                        "reasons": game.result.reasons,
                    },
                }
            )

        output_path = os.path.join(cls.OUTPUT_FOLDER, cls.OUTPUT_FILE)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return output_path

    @classmethod
    def _pitcher(cls, pitcher):

        return {
            "name": pitcher.name,
            "throws": pitcher.throws,
            "bats": pitcher.bats,
            "record": pitcher.record,
            "era": pitcher.era,
            "whip": pitcher.whip,
            "ip": pitcher.ip,
            "so": pitcher.so,
            "bb": pitcher.bb,
            "hr_allowed": pitcher.hr_allowed,
            "k_rate": pitcher.k_rate,
            "bb_rate": pitcher.bb_rate,
            "hr9": pitcher.hr9,
        }

    @classmethod
    def _signals(cls, signals):

        formatted = []

        for signal in signals:

            if isinstance(signal, (list, tuple)) and len(signal) == 2:
                formatted.append(
                    {
                        "name": signal[0],
                        "value": signal[1],
                    }
                )
            else:
                formatted.append(
                    {
                        "name": str(signal),
                        "value": None,
                    }
                )

        return formatted
