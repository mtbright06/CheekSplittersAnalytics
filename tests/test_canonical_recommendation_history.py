from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.canonical_recommendation_read_model import (
    CanonicalRecommendationRecord,
    RecommendationTimelineSnapshot,
)
from app.services.recommendation_history_service import (
    RecommendationHistoryFilters,
    RecommendationHistoryService,
)


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class _ReadModel:
    def __init__(self, records, timeline=()):
        self.records = tuple(records)
        self.timeline = tuple(timeline)
        self.timeline_calls = []

    def list_graded_records(self):
        return self.records

    def list_episode_timeline(self, episode_id):
        self.timeline_calls.append(episode_id)
        return self.timeline


def _record(
    *,
    league="MLB",
    market="MONEYLINE",
    selection="HOME",
    tier="STRONG PLAY",
    status="WIN",
    model_version="1.0.0",
    minutes=0,
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
        selection_side="HOME",
        canonical_snapshot_id=uuid4(),
        canonical_snapshot_time=NOW + timedelta(minutes=minutes),
        canonical_market_line=Decimal("8.5") if market == "TOTALS" else None,
        recommendation_tier=tier,
        confidence=Decimal("0.74"),
        hammer_score=Decimal("68.2"),
        model_probability=Decimal("0.612"),
        opened_at=NOW - timedelta(minutes=15),
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
        components={"signal_combination": "MLB + FIRST5", "real_market_loaded": True},
        explanation="Signals agree.",
        source="sharpstack",
    )


def test_history_returns_one_canonical_item_with_episode_fields():
    record = _record()
    service = RecommendationHistoryService(canonical_read_model=_ReadModel([record]))

    items = service.list_recommendations()

    assert len(items) == 1
    item = items[0]
    assert item.recommendation_episode_id == record.episode_id
    assert item.recommendation_id == record.canonical_snapshot_id
    assert item.selection == "HOME"
    assert item.latest_grade is not None
    assert item.latest_grade.outcome == "WIN"
    assert item.locked_at == record.locked_at
    assert item.graded_at == record.graded_at


def test_history_filters_date_league_market_and_model_version():
    kept = _record(model_version="1.0.0")
    dropped = _record(league="KBO", market="MONEYLINE", model_version="2.0.0")
    service = RecommendationHistoryService(
        canonical_read_model=_ReadModel([kept, dropped])
    )

    items = service.list_recommendations(
        filters=RecommendationHistoryFilters(
            start_time=NOW - timedelta(minutes=1),
            end_time=NOW + timedelta(minutes=1),
            league_code="MLB",
            market_type="MONEYLINE",
            model_version="1.0.0",
        )
    )

    assert [item.recommendation_episode_id for item in items] == [kept.episode_id]


def test_history_timeline_access_is_explicit_and_not_official_rows():
    record = _record()
    timeline = (
        RecommendationTimelineSnapshot(
            snapshot_id=uuid4(),
            recommendation_time=NOW,
            selection="HOME",
            market_line=None,
            recommendation_tier="LEAN",
            confidence=Decimal("0.66"),
            hammer_score=Decimal("61.0"),
        ),
        RecommendationTimelineSnapshot(
            snapshot_id=uuid4(),
            recommendation_time=NOW + timedelta(minutes=4),
            selection="HOME",
            market_line=None,
            recommendation_tier="STRONG PLAY",
            confidence=Decimal("0.74"),
            hammer_score=Decimal("68.2"),
        ),
    )
    read_model = _ReadModel([record], timeline)
    service = RecommendationHistoryService(canonical_read_model=read_model)

    items = service.list_recommendations()
    snapshots = service.list_episode_timeline(record.episode_id)

    assert len(items) == 1
    assert len(snapshots) == 2
    assert read_model.timeline_calls == [record.episode_id]


def test_history_empty_state_does_not_fall_back_to_legacy_rows():
    service = RecommendationHistoryService(canonical_read_model=_ReadModel([]))

    assert service.list_recommendations() == ()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
