from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.runtime import ensure_project_root

ensure_project_root()

from app.services.recommendation_analytics_service import ModelHealthBucket
from pages.model_health_page import _percentage, _table_row, _timestamp


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def _bucket(**overrides):
    values = {
        "league": "MLB",
        "market": "MONEYLINE",
        "recommendation_tier": "STRONG PLAY",
        "sample_size": 5,
        "wins": 3,
        "losses": 1,
        "pushes": 0,
        "voids": 0,
        "pending": 1,
        "ungradeable": 0,
        "win_percentage": 75.0,
        "decision_rate": 80.0,
        "first_prediction": NOW,
        "last_prediction": NOW,
    }
    values.update(overrides)
    return ModelHealthBucket(**values)


def test_table_rows_only_format_existing_bucket_values_for_presentation():
    row = _table_row(_bucket())

    assert row == {
        "League": "MLB",
        "Market": "MONEYLINE",
        "Tier": "STRONG PLAY",
        "Sample Size": 5,
        "Wins": 3,
        "Losses": 1,
        "Pushes": 0,
        "Pending": 1,
        "Win %": "75.0%",
        "Decision %": "80.0%",
        "First Prediction": "2026-07-28T12:00:00+00:00",
        "Last Prediction": "2026-07-28T12:00:00+00:00",
    }


def test_empty_metric_values_are_rendered_as_presentation_na():
    assert _percentage(None) == "N/A"
    assert _timestamp(None) == "N/A"
