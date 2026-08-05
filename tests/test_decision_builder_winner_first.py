import json
from pathlib import Path
import tempfile

from engine.decision import decision_builder


def test_decision_builder_never_uses_edge_as_hammer_fallback():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        mlb_path = root / "mlb.json"
        first5_path = root / "first5.json"
        first5_market_path = root / "first5_market.json"
        bomb_path = root / "bomb.json"
        output_path = root / "decision.json"

        mlb_path.write_text(
            json.dumps(
                {
                    "games": [
                        {
                            "game_pk": "edge-only-game",
                            "matchup": {
                                "away": "Away Club",
                                "home": "Home Club",
                            },
                            "teams": {
                                "away": {"name": "Away Club"},
                                "home": {"name": "Home Club"},
                            },
                            "model": {
                                "play": "Away Club",
                                "recommendation": "PASS",
                                "edge": 15.0,
                            },
                            "pregame_eligible": True,
                            "pregame_eligibility_reason": "GAME_NOT_STARTED",
                        }
                    ]
                }
            )
        )
        first5_path.write_text(json.dumps({"games": []}))
        first5_market_path.write_text(json.dumps({"games": []}))
        bomb_path.write_text(json.dumps({"pitchers": []}))

        original_paths = (
            decision_builder.MLB_CARD_PATH,
            decision_builder.FIRST5_CARD_PATH,
            decision_builder.FIRST5_MARKET_PATH,
            decision_builder.BOMB_CARD_PATH,
            decision_builder.OUTPUT_PATH,
        )
        decision_builder.MLB_CARD_PATH = mlb_path
        decision_builder.FIRST5_CARD_PATH = first5_path
        decision_builder.FIRST5_MARKET_PATH = first5_market_path
        decision_builder.BOMB_CARD_PATH = bomb_path
        decision_builder.OUTPUT_PATH = output_path

        try:
            card = decision_builder.build_decision_card()
        finally:
            (
                decision_builder.MLB_CARD_PATH,
                decision_builder.FIRST5_CARD_PATH,
                decision_builder.FIRST5_MARKET_PATH,
                decision_builder.BOMB_CARD_PATH,
                decision_builder.OUTPUT_PATH,
            ) = original_paths

    decision = card["decisions"][0]

    assert decision["market_edge_pct"] is None
    assert decision["model_probability"] is None
    assert decision["score_breakdown"]["mlb_model"]["available"] is False
