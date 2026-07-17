from __future__ import annotations

from engine.mlb.totals import (
    build_totals_projection,
)


def main() -> None:
    game = {
        "teams": {
            "away": {
                "name": "Away Test Club",
                "offense": {
                    "runs_per_game": 4.92,
                    "ops": 0.748,
                    "wrc_plus": 108,
                },
            },
            "home": {
                "name": "Home Test Club",
                "offense": {
                    "runs_per_game": 4.18,
                    "ops": 0.701,
                    "wrc_plus": 94,
                },
            },
        },
        "pitching": {
            "away": {
                "era": 3.62,
                "whip": 1.18,
                "hr9": 0.94,
            },
            "home": {
                "era": 4.76,
                "whip": 1.42,
                "hr9": 1.38,
            },
        },
    }

    projection = build_totals_projection(
        game
    )

    print("")
    print("=" * 72)
    print("SharpStack MLB Totals Projection Test")
    print("=" * 72)

    print(
        "Away expected runs:",
        projection[
            "away_expected_runs"
        ],
    )

    print(
        "Home expected runs:",
        projection[
            "home_expected_runs"
        ],
    )

    print(
        "Projected total:",
        projection[
            "projected_total"
        ],
    )

    print(
        "Confidence:",
        projection[
            "confidence"
        ],
    )

    print(
        "Data quality:",
        projection[
            "data_quality"
        ],
    )

    print(
        "Status:",
        projection[
            "market_status"
        ],
    )

    assert (
        projection[
            "away_expected_runs"
        ]
        >
        projection[
            "home_expected_runs"
        ]
    )

    assert (
        6.0
        <= projection[
            "projected_total"
        ]
        <= 12.5
    )

    assert (
        projection[
            "market_status"
        ]
        == "MODEL_ONLY"
    )

    print("")
    print(
        "PASSED: Totals projection "
        "core behaved as expected."
    )


if __name__ == "__main__":
    main()