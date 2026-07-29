from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.runtime import ensure_project_root

ensure_project_root()

from app.services.recommendation_analytics_service import (
    ModelHealthBucket,
    RecommendationAnalyticsError,
    RecommendationAnalyticsService,
    filter_model_health_buckets,
    summarize_model_health,
)
from components.page_header import render_compact_header


def render_model_health_dashboard(
    service: RecommendationAnalyticsService | None = None,
) -> None:
    """Render persisted model health without changing any analytics state."""

    render_compact_header(
        "",
        "Model Health",
        "Read-only performance from immutable prediction snapshots and grades.",
    )
    try:
        report = (service or RecommendationAnalyticsService()).model_health()
    except RecommendationAnalyticsError as exc:
        st.error(f"Model health is unavailable: {exc}")
        return

    leagues = sorted({bucket.league for bucket in report.buckets})
    markets = sorted({bucket.market for bucket in report.buckets})
    league_column, market_column = st.columns(2)
    with league_column:
        selected_leagues = st.multiselect("League", leagues, default=leagues)
    with market_column:
        selected_markets = st.multiselect("Market", markets, default=markets)

    buckets = filter_model_health_buckets(
        report,
        leagues=selected_leagues,
        markets=selected_markets,
    )
    summary = summarize_model_health(buckets)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Recommendations", summary.recommendations)
    metric_columns[1].metric("Resolved", summary.resolved)
    metric_columns[2].metric("Pending", summary.pending)
    metric_columns[3].metric(
        "Overall Win %",
        _percentage(summary.overall_win_percentage),
    )

    if not buckets:
        st.info("No model-health buckets match the selected filters.")
        return

    st.dataframe(
        [_table_row(bucket) for bucket in buckets],
        width="stretch",
        hide_index=True,
    )
    st.caption(f"As of {_timestamp(report.generated_at)}")


def _table_row(bucket: ModelHealthBucket) -> dict[str, object]:
    return {
        "League": bucket.league,
        "Market": bucket.market,
        "Tier": bucket.recommendation_tier,
        "Sample Size": bucket.sample_size,
        "Wins": bucket.wins,
        "Losses": bucket.losses,
        "Pushes": bucket.pushes,
        "Pending": bucket.pending,
        "Win %": _percentage(bucket.win_percentage),
        "Decision %": _percentage(bucket.decision_rate),
        "First Prediction": _timestamp(bucket.first_prediction),
        "Last Prediction": _timestamp(bucket.last_prediction),
    }


def _percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _timestamp(value: datetime | None) -> str:
    return "N/A" if value is None else value.isoformat()
