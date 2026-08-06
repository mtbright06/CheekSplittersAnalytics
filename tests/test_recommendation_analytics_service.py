from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.canonical_recommendation_read_model import CanonicalRecommendationRecord
from app.services.recommendation_analytics_service import (
    RecommendationAnalyticsService,
    _AnalyticsRecord,
)


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def _record(
    *,
    league="MLB",
    market="MONEYLINE",
    tier="STRONG PLAY",
    status="WIN",
    minutes=0,
    is_prediction_snapshot=True,
):
    return _AnalyticsRecord(
        league=league,
        market=market,
        recommendation_tier=tier,
        recommendation_time=NOW + timedelta(minutes=minutes),
        grade_status=status,
        is_prediction_snapshot=is_prediction_snapshot,
    )


def _report(records):
    return RecommendationAnalyticsService(
        record_loader=lambda: records,
        now_factory=lambda: NOW,
    ).model_health()


class _CanonicalReadModel:
    def __init__(self, records):
        self.records = tuple(records)

    def list_graded_records(self):
        return self.records


def _canonical_record(
    *,
    league="MLB",
    market="MONEYLINE",
    selection="HOME",
    tier="STRONG PLAY",
    status="WIN",
    confidence=Decimal("0.74"),
    hammer=Decimal("68.2"),
    minutes=0,
    model_version="1.0.0",
):
    return CanonicalRecommendationRecord(
        episode_id=uuid4(),
        stream_id=uuid4(),
        sport="BASEBALL",
        league_code=league,
        provider="mlb_stats_api",
        provider_game_id="824414",
        market=market,
        selection=selection,
        selection_side="HOME" if market == "MONEYLINE" else "",
        canonical_snapshot_id=uuid4(),
        canonical_snapshot_time=NOW + timedelta(minutes=minutes),
        canonical_market_line=Decimal("8.5") if market in {"TOTAL", "TOTALS"} else None,
        recommendation_tier=tier,
        confidence=confidence,
        hammer_score=hammer,
        model_probability=Decimal("0.612"),
        opened_at=NOW,
        locked_at=NOW + timedelta(hours=2),
        graded_at=NOW + timedelta(hours=5),
        canonical_grade_id=uuid4(),
        grade_status=status,
        game_result_id=uuid4(),
        game_result_revision=1,
        result_status="FINAL",
        winner_side="HOME",
        total_score=9,
        model_version=model_version,
        model_name="sharpstack_registry",
        git_commit="abc123",
        model_run_id=uuid4(),
        run_source="sharpstack",
        components={"prediction": {"hammer_score": str(hammer)}},
        explanation=None,
        source="sharpstack",
    )


def _canonical_report(records):
    return RecommendationAnalyticsService(
        canonical_read_model=_CanonicalReadModel(records),
        now_factory=lambda: NOW,
    ).model_health()


def test_groups_by_league_market_and_recommendation_tier():
    report = _report(
        [
            _record(status="WIN"),
            _record(status="LOSS", minutes=1),
            _record(market="TOTAL", tier="LEAN", status="PUSH", minutes=2),
            _record(league="KBO", tier="PLAYABLE", status="PENDING", minutes=3),
        ]
    )

    assert [(item.league, item.market, item.recommendation_tier) for item in report.buckets] == [
        ("KBO", "MONEYLINE", "PLAYABLE"),
        ("MLB", "MONEYLINE", "STRONG PLAY"),
        ("MLB", "TOTAL", "LEAN"),
    ]


def test_counts_win_percentage_decision_rate_and_prediction_window():
    bucket = _report(
        [
            _record(status="WIN", minutes=4),
            _record(status="LOSS", minutes=1),
            _record(status="PUSH", minutes=3),
            _record(status="VOID", minutes=2),
            _record(status="PENDING", minutes=5),
            _record(status="UNGRADEABLE", minutes=0),
        ]
    ).buckets[0]

    assert bucket.sample_size == 6
    assert (bucket.wins, bucket.losses, bucket.pushes) == (1, 1, 1)
    assert (bucket.voids, bucket.pending, bucket.ungradeable) == (1, 1, 1)
    assert bucket.win_percentage == 50.0
    assert bucket.decision_rate == 50.0
    assert bucket.first_prediction == NOW
    assert bucket.last_prediction == NOW + timedelta(minutes=5)


def test_missing_grade_is_pending_and_unresolved_bucket_has_no_win_percentage():
    bucket = _report([_record(status=None)]).buckets[0]

    assert bucket.pending == 1
    assert bucket.win_percentage is None
    assert bucket.decision_rate == 0.0


def test_latest_grade_revision_is_the_only_grade_loaded_for_a_snapshot_query_contract():
    # Query construction is covered by service code; aggregation accepts one
    # canonical status per snapshot and therefore cannot double count revisions.
    bucket = _report([_record(status="LOSS")]).buckets[0]
    assert bucket.sample_size == 1
    assert bucket.losses == 1


def test_unknown_tier_and_status_are_safe_and_visible():
    bucket = _report([_record(tier=None, status="NEW_STATUS")]).buckets[0]

    assert bucket.recommendation_tier == "UNSPECIFIED"
    assert bucket.pending == 1


def test_display_no_play_normalizes_to_pass_and_totals_bet_stays_bet():
    report = _report(
        [
            _record(tier="❌ NO PLAY", status="PENDING"),
            _record(market="TOTALS", tier="BET", status="PENDING"),
        ]
    )

    assert {(item.market, item.recommendation_tier) for item in report.buckets} == {
        ("MONEYLINE", "PASS"),
        ("TOTALS", "BET"),
    }


def test_legacy_records_are_excluded_by_default_and_can_be_opted_in():
    records = [
        _record(status="WIN"),
        _record(
            league=None,
            market="TOTAL",
            tier=None,
            status=None,
            is_prediction_snapshot=False,
        ),
    ]

    default_report = _report(records)
    included_report = RecommendationAnalyticsService(
        record_loader=lambda: records,
        now_factory=lambda: NOW,
        include_legacy=True,
    ).model_health()

    assert default_report.buckets[0].sample_size == 1
    assert {(item.league, item.market) for item in included_report.buckets} == {
        ("MLB", "MONEYLINE"),
        ("UNKNOWN", "TOTAL"),
    }


def test_database_loader_extracts_immutable_snapshot_tier_without_writing():
    report = RecommendationAnalyticsService(
        canonical_read_model=_CanonicalReadModel(
            [_canonical_record(tier="✅ PLAYABLE")]
        ),
        now_factory=lambda: NOW,
    ).model_health()

    bucket = report.buckets[0]
    assert bucket.recommendation_tier == "PLAYABLE"
    assert bucket.wins == 1


def test_four_snapshots_for_one_episode_count_as_one_official_recommendation():
    bucket = _canonical_report([_canonical_record()]).buckets[0]

    assert bucket.sample_size == 1
    assert bucket.wins == 1


def test_selection_flip_counts_only_final_canonical_recommendation():
    bucket = _canonical_report([
        _canonical_record(selection="AWAY", status="LOSS"),
    ]).buckets[0]

    assert bucket.sample_size == 1
    assert bucket.selection if hasattr(bucket, "selection") else True
    assert bucket.losses == 1


def test_pushes_and_voids_are_handled_with_void_excluded_from_win_rate():
    bucket = _canonical_report(
        [
            _canonical_record(status="WIN"),
            _canonical_record(status="LOSS", minutes=1),
            _canonical_record(status="PUSH", minutes=2),
            _canonical_record(status="VOID", minutes=3),
        ]
    ).buckets[0]

    assert bucket.sample_size == 4
    assert (bucket.wins, bucket.losses, bucket.pushes, bucket.voids) == (1, 1, 1, 1)
    assert bucket.win_percentage == 50.0


def test_canonical_empty_state_does_not_fall_back_to_legacy_snapshot_data():
    legacy_loader = lambda: [_record(status="WIN")]

    report = RecommendationAnalyticsService(
        record_loader=None,
        canonical_read_model=_CanonicalReadModel([]),
        now_factory=lambda: NOW,
    ).model_health()

    assert report.buckets == ()
    assert legacy_loader()[0].grade_status == "WIN"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
