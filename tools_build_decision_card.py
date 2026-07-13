from pathlib import Path

from engine.decision import build_decision_card


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "output" / "cards" / "decision_card.json"


def main():
    print("")
    print("=" * 64)
    print("SharpStack Decision Engine")
    print("=" * 64)

    card = build_decision_card()
    summary = card.get("summary", {})

    print(f"Output: {OUTPUT_PATH}")
    print(f"Games loaded: {summary.get('games_loaded', 0)}")
    print(f"Actionable: {summary.get('actionable', 0)}")
    print(f"Hammer plays: {summary.get('hammer_plays', 0)}")
    print(f"Bets: {summary.get('bets', 0)}")
    print(f"Leans: {summary.get('leans', 0)}")
    print(
        f"Real market games: "
        f"{summary.get('real_market_games', 0)}"
    )
    print(
        f"Model-only games: "
        f"{summary.get('model_only_games', 0)}"
    )
    print(
        f"Top play: {summary.get('top_play', 'PASS')} "
        f"({summary.get('top_score', 0)})"
    )

    decisions = card.get("decisions", [])

    if decisions:
        print("")
        print("Top Decisions")
        print("-" * 64)

        for index, decision in enumerate(
            decisions[:10],
            start=1,
        ):
            print(
                f"{index:>2}. "
                f"{decision.get('selected_team')} | "
                f"{decision.get('recommendation')} | "
                f"{decision.get('hammer_score')} | "
                f"{decision.get('market')}"
            )


if __name__ == "__main__":
    main()
