import json
from pathlib import Path

from engine.adapters import (
    adapt_mlb_decision_card,
)
from engine.core import (
    RecommendationRegistry,
)


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"

DECISION_CARD_PATH = (
    CARDS_DIR
    / "decision_card.json"
)

OUTPUT_PATH = (
    CARDS_DIR
    / "recommendation_registry.json"
)


def load_json(
    path: Path,
) -> dict:
    if not path.exists():
        return {}

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}


def main():
    print("")
    print("=" * 64)
    print("SharpStack Recommendation Registry")
    print("=" * 64)

    registry = RecommendationRegistry()

    decision_card = load_json(
        DECISION_CARD_PATH
    )

    mlb_recommendations = (
        adapt_mlb_decision_card(
            decision_card
        )
    )

    registry.extend(
        mlb_recommendations
    )

    registry.save(
        OUTPUT_PATH
    )

    summary = registry.summary()

    print(f"Output: {OUTPUT_PATH}")
    print(
        f"Recommendations: "
        f"{summary.get('recommendations', 0)}"
    )
    print(
        f"Actionable: "
        f"{summary.get('actionable', 0)}"
    )
    print(
        f"Real market: "
        f"{summary.get('real_market', 0)}"
    )
    print(
        f"Model only: "
        f"{summary.get('model_only', 0)}"
    )
    print(
        f"Sports: "
        f"{summary.get('sports', [])}"
    )
    print(
        f"Leagues: "
        f"{summary.get('leagues', [])}"
    )
    print(
        f"Markets: "
        f"{summary.get('markets', [])}"
    )

    ranked = registry.ranked(
        limit=10
    )

    if ranked:
        print("")
        print("Top Recommendations")
        print("-" * 64)

        for index, item in enumerate(
            ranked,
            start=1,
        ):
            print(
                f"{index:>2}. "
                f"{item.league} | "
                f"{item.market} | "
                f"{item.selection} | "
                f"{item.recommendation} | "
                f"Hammer {item.hammer_score:.1f} | "
                f"Rank {item.ranking_score:.1f}"
            )
    else:
        print("")
        print(
            "No recommendations available."
        )


if __name__ == "__main__":
    main()
