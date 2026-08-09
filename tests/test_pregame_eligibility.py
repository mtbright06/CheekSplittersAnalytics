from __future__ import annotations

from datetime import UTC, datetime, timedelta

from engine.core.pregame_eligibility import (
    PregameEligibilityReason,
    evaluate_pregame_eligibility,
)


NOW = datetime(2026, 7, 29, 17, 0, tzinfo=UTC)
FUTURE = NOW + timedelta(hours=2)
PAST = NOW - timedelta(minutes=1)


def test_future_pregame_game_is_eligible():
    result = evaluate_pregame_eligibility(
        game_status={"abstractGameState": "Preview", "detailedState": "Scheduled"},
        scheduled_start=FUTURE.isoformat(),
        now=NOW,
    )

    assert result.eligible is True
    assert result.reason is PregameEligibilityReason.GAME_NOT_STARTED


def test_live_game_status_is_blocked():
    result = evaluate_pregame_eligibility(
        game_status={"abstractGameState": "Live", "detailedState": "In Progress"},
        scheduled_start=FUTURE.isoformat(),
        now=NOW,
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.GAME_STARTED


def test_after_scheduled_start_is_blocked_even_with_stale_pregame_status():
    result = evaluate_pregame_eligibility(
        game_status="Scheduled",
        scheduled_start=PAST.isoformat(),
        now=NOW,
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.GAME_STARTED


def test_live_market_is_blocked_for_future_game_record():
    result = evaluate_pregame_eligibility(
        game_status="Scheduled",
        scheduled_start=FUTURE.isoformat(),
        now=NOW,
        market={"is_live": True},
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.LIVE_MARKET


def test_missing_status_fails_closed():
    result = evaluate_pregame_eligibility(
        game_status=None,
        scheduled_start=FUTURE.isoformat(),
        now=NOW,
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.UNVERIFIED


def test_timezone_naive_start_fails_closed():
    result = evaluate_pregame_eligibility(
        game_status="Scheduled",
        scheduled_start="2026-07-29T19:00:00",
        now=NOW,
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.NO_START_TIME


def test_postponed_game_with_future_start_is_not_assumed_pregame():
    result = evaluate_pregame_eligibility(
        game_status="Postponed",
        scheduled_start=FUTURE.isoformat(),
        now=NOW,
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.POSTPONED_GAME


def test_completed_game_is_blocked():
    result = evaluate_pregame_eligibility(
        game_status="Final",
        scheduled_start=PAST.isoformat(),
        now=NOW,
    )

    assert result.eligible is False
    assert result.reason is PregameEligibilityReason.COMPLETED
