from datetime import date
from unittest.mock import patch

from engine.mlb.bullpen.provider import (
    build_bullpen_snapshot,
    classify_reliever_appearances,
    serialize_bullpen_snapshot,
)
from engine.mlb.game_builder import team_profile


def appearance(day, *, outs, earned_runs, hits, walks, started=0):
    return {
        "date": day,
        "stat": {
            "outs": outs,
            "earnedRuns": earned_runs,
            "hits": hits,
            "baseOnBalls": walks,
            "gamesStarted": started,
        },
    }


def test_reliever_classification_excludes_starts():
    appearances = [
        appearance("2026-07-20", outs=3, earned_runs=0, hits=1, walks=0),
        appearance("2026-07-18", outs=9, earned_runs=2, hits=4, walks=1, started=1),
    ]

    result = classify_reliever_appearances(
        {"position": "RP"},
        appearances,
    )

    assert result == appearances[:1]


def test_unlabeled_pitcher_with_starts_is_not_a_reliever():
    appearances = [
        appearance("2026-07-20", outs=3, earned_runs=0, hits=1, walks=0),
        appearance("2026-07-18", outs=9, earned_runs=2, hits=4, walks=1, started=1),
    ]

    assert classify_reliever_appearances({"position": "P"}, appearances) == []


def test_snapshot_aggregates_raw_counts_and_recent_windows():
    snapshot = build_bullpen_snapshot(
        team_name="Test Club",
        appearances=[
            appearance("2026-07-23", outs=3, earned_runs=0, hits=1, walks=0),
            appearance("2026-07-21", outs=6, earned_runs=1, hits=2, walks=1),
            appearance("2026-07-16", outs=3, earned_runs=2, hits=3, walks=0),
        ],
        as_of=date(2026, 7, 23),
    )

    assert snapshot.season_era == 6.75
    assert snapshot.season_whip == 1.75
    assert snapshot.last7_era == 3.0
    assert snapshot.innings_last3 == 3.0
    assert snapshot.appearances_last3 == 2


def test_serialized_profile_preserves_canonical_and_legacy_contracts():
    snapshot = build_bullpen_snapshot(
        team_name="Test Club",
        appearances=[
            appearance("2026-07-23", outs=3, earned_runs=0, hits=1, walks=0),
        ],
        as_of=date(2026, 7, 23),
    )

    profile = serialize_bullpen_snapshot(
        snapshot,
        reliever_count=1,
        source_quality="COMPLETE",
        source_detail="fixture",
    )

    assert profile["season_era"] == profile["era"]
    assert profile["season_whip"] == profile["whip"]
    assert profile["availability_status"] == "UNCONFIRMED_NEUTRAL"
    assert profile["source_quality"] == "COMPLETE"


def test_game_builder_uses_the_normalized_bullpen_profile():
    bullpen = {"season_era": 3.5, "era": 3.5}

    with (
        patch(
            "engine.mlb.game_builder.fetch_team_batting_stats",
            return_value={},
        ),
        patch(
            "engine.mlb.game_builder.fetch_bullpen_profile",
            return_value=bullpen,
        ),
    ):
        profile = team_profile(
            {"team": {"id": 147, "name": "New York Yankees"}}
        )

    assert profile["bullpen"] == bullpen
