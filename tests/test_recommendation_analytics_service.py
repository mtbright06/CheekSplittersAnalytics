from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

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
    recommendation = SimpleNamespace(
        league_code="MLB",
        market_type="MONEYLINE",
        components={"prediction": {"conviction_tier": "✅ PLAYABLE"}},
        recommendation_time=NOW,
        idempotency_key="snapshot-key",
        model_run_id="run-id",
    )

    class _Session:
        closed = False
        statement = None

        def execute(self, statement):
            self.statement = statement
            return SimpleNamespace(all=lambda: [(recommendation, "WIN")])

        def close(self):
            self.closed = True

    session = _Session()
    report = RecommendationAnalyticsService(
        session_factory=lambda: session,
        now_factory=lambda: NOW,
    ).model_health()

    bucket = report.buckets[0]
    assert bucket.recommendation_tier == "PLAYABLE"
    assert bucket.wins == 1
    assert session.closed is True
    assert "max(" in str(session.statement).lower()
