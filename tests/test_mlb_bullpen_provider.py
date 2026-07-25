from datetime import date
from unittest.mock import patch

from engine.mlb.bullpen.provider import (
    build_bullpen_snapshot,
    classify_reliever_appearances,
    fetch_bullpen_profile,
    observed_relief_workload,
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
    assert profile["evidence_ledger"] == []


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


def test_bullpen_evidence_ledger_preserves_evaluated_pitcher_facts():
    included = [
        appearance("2026-07-23", outs=3, earned_runs=0, hits=1, walks=0),
        appearance("2026-07-21", outs=6, earned_runs=1, hits=2, walks=1),
    ]
    mixed_role = [
        appearance("2026-07-22", outs=3, earned_runs=0, hits=1, walks=0),
        appearance("2026-07-20", outs=6, earned_runs=1, hits=2, walks=1, started=1),
    ]
    roster = [
        {"player_id": 1, "player_name": "Included Reliever", "position": "RP"},
        {"player_id": 2, "player_name": "Mixed Role", "position": "P"},
        {"player_id": 3, "player_name": "Missing Log", "position": "RP"},
    ]

    with (
        patch(
            "engine.mlb.bullpen.provider.fetch_active_pitcher_roster",
            return_value=roster,
        ),
        patch(
            "engine.mlb.bullpen.provider.fetch_pitcher_game_log",
            side_effect=[included, mixed_role, None],
        ),
    ):
        profile = fetch_bullpen_profile(
            1,
            "Test Club",
            as_of=date(2026, 7, 23),
        )

    assert profile["season_era"] == 3.0
    assert profile["season_whip"] == 1.33
    assert profile["reliever_count"] == 1

    included_entry, mixed_entry, failed_entry = profile["evidence_ledger"]
    assert included_entry == {
        "pitcher_id": 1,
        "pitcher_name": "Included Reliever",
        "roster_position": "RP",
        "season_starts": 0,
        "relief_appearances": 2,
        "observed_relief_appearances": 2,
        "included_relief_appearances": 2,
        "last_appearance_date": "2026-07-23",
        "appearances_last3": 2,
        "innings_last3": 3.0,
        "observed_last_appearance_date": "2026-07-23",
        "observed_appearances_last3": 2,
        "observed_innings_last3": 3.0,
        "appearances_last5": 2,
        "innings_last5": 3.0,
        "multi_inning_appearances_last5": 1,
        "days_since_last_appearance": 0,
        "appeared_on_consecutive_days": False,
        "consecutive_days_used": 1,
        "limited_history": True,
        "inclusion_status": "INCLUDED",
        "exclusion_reason": None,
        "source_quality": "COMPLETE",
        "game_log_status": "AVAILABLE",
    }
    assert mixed_entry["inclusion_status"] == "EXCLUDED"
    assert mixed_entry["exclusion_reason"] == "non_reliever_with_season_starts"
    assert mixed_entry["season_starts"] == 1
    assert mixed_entry["relief_appearances"] == 1
    assert mixed_entry["observed_relief_appearances"] == 1
    assert mixed_entry["included_relief_appearances"] == 0
    assert mixed_entry["observed_appearances_last3"] == 1
    assert mixed_entry["observed_innings_last3"] == 1.0
    assert mixed_entry["appearances_last5"] == 1
    assert mixed_entry["innings_last5"] == 1.0
    assert failed_entry["inclusion_status"] == "EXCLUDED"
    assert failed_entry["exclusion_reason"] == "game_log_unavailable"
    assert failed_entry["game_log_status"] == "FAILED"
    assert failed_entry["relief_appearances"] is None
    assert failed_entry["observed_relief_appearances"] is None
    assert failed_entry["included_relief_appearances"] is None


def test_observed_relief_workload_uses_calendar_windows_and_outs():
    workload = observed_relief_workload(
        [
            appearance("2026-07-25", outs=1, earned_runs=0, hits=0, walks=0),
            appearance("2026-07-24", outs=5, earned_runs=0, hits=0, walks=0),
            appearance("2026-07-23", outs=6, earned_runs=0, hits=0, walks=0),
            appearance("2026-07-21", outs=8, earned_runs=0, hits=0, walks=0),
            appearance("2026-07-26", outs=9, earned_runs=0, hits=0, walks=0),
        ],
        as_of=date(2026, 7, 25),
        game_log_empty=False,
    )

    assert workload["appearances_last3"] == 3
    assert workload["innings_last3"] == 4.0
    assert workload["appearances_last5"] == 4
    assert workload["innings_last5"] == 6.7
    assert workload["multi_inning_appearances_last5"] == 2
    assert workload["days_since_last_appearance"] == 0
    assert workload["appeared_on_consecutive_days"] is True
    assert workload["consecutive_days_used"] == 3
    assert workload["limited_history"] is False


def test_observed_relief_workload_does_not_bridge_date_gaps():
    workload = observed_relief_workload(
        [
            appearance("2026-07-25", outs=3, earned_runs=0, hits=0, walks=0),
            appearance("2026-07-23", outs=3, earned_runs=0, hits=0, walks=0),
        ],
        as_of=date(2026, 7, 25),
        game_log_empty=False,
    )

    assert workload["appeared_on_consecutive_days"] is False
    assert workload["consecutive_days_used"] == 1
    assert workload["limited_history"] is True


def test_empty_game_log_workload_remains_unknown():
    workload = observed_relief_workload(
        [],
        as_of=date(2026, 7, 25),
        game_log_empty=True,
    )

    assert workload["appearances_last3"] is None
    assert workload["innings_last5"] is None
    assert workload["consecutive_days_used"] is None
    assert workload["limited_history"] is True


def test_empty_and_failed_game_logs_remain_distinguishable_in_ledger():
    roster = [
        {"player_id": 1, "player_name": "Empty Log", "position": "RP"},
        {"player_id": 2, "player_name": "Failed Log", "position": "RP"},
    ]

    with (
        patch(
            "engine.mlb.bullpen.provider.fetch_active_pitcher_roster",
            return_value=roster,
        ),
        patch(
            "engine.mlb.bullpen.provider.fetch_pitcher_game_log",
            side_effect=[[], None],
        ),
    ):
        profile = fetch_bullpen_profile(
            1,
            "Test Club",
            as_of=date(2026, 7, 25),
        )

    empty_entry, failed_entry = profile["evidence_ledger"]
    assert empty_entry["game_log_status"] == "EMPTY"
    assert empty_entry["source_quality"] == "COMPLETE"
    assert empty_entry["appearances_last3"] is None
    assert empty_entry["limited_history"] is True
    assert failed_entry["game_log_status"] == "FAILED"
    assert failed_entry["source_quality"] == "UNAVAILABLE"
    assert failed_entry["appearances_last3"] is None
    assert failed_entry["limited_history"] is None
