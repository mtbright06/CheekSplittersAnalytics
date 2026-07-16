import json
from pathlib import Path

from engine.adapters import (
    adapt_kbo_card,
    adapt_mlb_decision_card,
)
from engine.core import (
    RecommendationRegistry,
    calculate_ranking_score,
    select_play_of_day,
)


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"

DECISION_CARD_PATH = (
    CARDS_DIR
    / "decision_card.json"
)

KBO_CARD_PATH = (
    CARDS_DIR
    / "kbo_card.json"
)

OUTPUT_PATH = (
    CARDS_DIR
    / "recommendation_registry.json"
)

PLAY_OF_DAY_PATH = (
    CARDS_DIR
    / "play_of_day.json"
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


def save_json(
    path: Path,
    data: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
        )


def main():
    print("")
    print("=" * 64)
    print("SharpStack Recommendation Registry")
    print("=" * 64)

    registry = RecommendationRegistry()

    decision_card = load_json(
        DECISION_CARD_PATH
    )

    kbo_card = load_json(
        KBO_CARD_PATH
    )

    registry.extend(
        adapt_mlb_decision_card(
            decision_card
        )
    )

    registry.extend(
        adapt_kbo_card(
            kbo_card
        )
    )

    registry.save(
        OUTPUT_PATH
    )

    all_recommendations = (
        registry.all()
    )

    play_of_day = (
        select_play_of_day(
            all_recommendations,
            require_real_market=False,
            minimum_hammer_score=74,
        )
    )

    save_json(
        PLAY_OF_DAY_PATH,
        play_of_day.to_dict(),
    )

    summary = registry.summary()

    print(f"Registry: {OUTPUT_PATH}")
    print(
        f"Play of Day: "
        f"{PLAY_OF_DAY_PATH}"
    )
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

    ranked = sorted(
        all_recommendations,
        key=calculate_ranking_score,
        reverse=True,
    )[:10]

    if ranked:
        print("")
        print("Top Recommendations")
        print("-" * 64)

        for index, item in enumerate(
            ranked,
            start=1,
        ):
            consensus = (
                item.source_signals.get(
                    "consensus",
                    {},
                )
            )

            print(
                f"{index:>2}. "
                f"{item.league} | "
                f"{item.market} | "
                f"{item.selection} | "
                f"{item.recommendation} | "
                f"Hammer {item.hammer_score:.1f} | "
                f"Rank "
                f"{calculate_ranking_score(item):.1f} | "
                f"Consensus "
                f"{consensus.get('support_count', 0)}/"
                f"{consensus.get('available_count', 0)}"
            )
    else:
        print("")
        print(
            "No recommendations available."
        )

    print("")
    print("Play of the Day")
    print("-" * 64)

    if play_of_day.recommendation:
        item = (
            play_of_day.recommendation
        )

        print(
            f"{item.league} | "
            f"{item.market} | "
            f"{item.selection}"
        )
        print(
            f"Hammer: "
            f"{item.hammer_score:.1f}"
        )
        print(
            f"Rank: "
            f"{calculate_ranking_score(item):.1f}"
        )
        print(
            play_of_day.reason
        )
    else:
        print(
            play_of_day.reason
        )


if __name__ == "__main__":
    main()
