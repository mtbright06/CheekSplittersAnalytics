from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace

os.environ["DEBUG"] = "false"

from app.services.reference_price_service import ReferencePriceService
from engine.odds.reference_price_policy import (
    KBO_REFERENCE_MINUTES_BEFORE_START,
    MLB_REFERENCE_MINUTES_BEFORE_START,
    ReferencePriceRequest,
    ReferencePriceResult,
    policy_for_league,
    reference_eligibility,
)
from engine.odds.reference_price import resolve_reference_quote
from engine.odds.best_line import quote_to_dict


def request_for(
    league: str,
    *,
    now: datetime,
    start: datetime,
    live: bool = False,
) -> ReferencePriceRequest:
    return ReferencePriceRequest(
        provider="the_odds_api",
        provider_event_id="event-1",
        league=league,
        market="Moneyline",
        selection="Example Club",
        price=-110,
        implied_probability=0.52381,
        sportsbook="FanDuel",
        scheduled_start_utc=start,
        now_utc=now,
        quote_is_live=live,
    )


def test_mlb_capture_requires_more_than_sixty_minutes():
    start = datetime(2026, 7, 25, 18, 0, tzinfo=UTC)
    eligible = request_for(
        "MLB",
        now=datetime(2026, 7, 25, 16, 59, tzinfo=UTC),
        start=start,
    )
    missed = request_for(
        "MLB",
        now=datetime(2026, 7, 25, 17, 0, tzinfo=UTC),
        start=start,
    )

    assert MLB_REFERENCE_MINUTES_BEFORE_START == 60
    assert reference_eligibility(eligible) is None
    assert reference_eligibility(missed) == "REFERENCE_UNAVAILABLE_CUTOFF_MISSED"


def test_kbo_capture_uses_its_own_cutoff_and_rejects_live_games():
    start = datetime(2026, 7, 25, 9, 0, tzinfo=UTC)
    eligible = request_for(
        "KBO",
        now=datetime(2026, 7, 25, 8, 14, tzinfo=UTC),
        start=start,
    )
    live = request_for(
        "KBO",
        now=datetime(2026, 7, 25, 8, 0, tzinfo=UTC),
        start=start,
        live=True,
    )

    assert KBO_REFERENCE_MINUTES_BEFORE_START == 45
    assert reference_eligibility(eligible) is None
    assert reference_eligibility(live) == "REFERENCE_UNAVAILABLE_LIVE"


def test_slate_timezones_assign_dates_without_host_timezone():
    _, mlb_timezone = policy_for_league("MLB")
    _, kbo_timezone = policy_for_league("KBO")
    utc_start = datetime(2026, 7, 25, 3, 30, tzinfo=UTC)

    assert utc_start.astimezone(mlb_timezone).date().isoformat() == "2026-07-24"
    assert utc_start.astimezone(kbo_timezone).date().isoformat() == "2026-07-25"


class LockedReferenceResolver:
    def __init__(self):
        self.calls = 0

    def resolve_quote(self, quote, league):
        self.calls += 1
        return ReferencePriceResult(
            "LOCKED",
            {
                "reference_price": -105,
                "reference_implied_probability": 0.512195,
                "reference_book": "DraftKings",
                "reference_captured_at": "2026-07-25T15:00:00+00:00",
                "reference_minutes_before_start": 180.0,
                "reference_status": "LOCKED",
                "reference_policy_version": "SSRP_v1",
            },
        )


def test_reference_quote_keeps_current_quote_separate():
    resolver = LockedReferenceResolver()
    current = {
        "provider": "the_odds_api",
        "event_id": "event-1",
        "market": "Moneyline",
        "selection": "Example Club",
        "sportsbook": "FanDuel",
        "american_odds": -120,
        "implied_probability": 0.545455,
        "last_updated": "2026-07-25T16:00:00+00:00",
        "commence_time": "2026-07-25T18:00:00+00:00",
        "real_market_loaded": True,
    }

    result = resolve_reference_quote(
        current,
        league="MLB",
        resolver=resolver,
    )

    assert result.current_quote["american_odds"] == -120
    assert result.reference_quote["american_odds"] == -105
    assert result.reference_quote["implied_probability"] == 0.512195
    assert result.reference_fields["current_price"] == -120
    assert result.reference_fields["reference_price"] == -105


def test_missing_reference_never_uses_current_quote_for_edge():
    class MissedCutoffResolver:
        def resolve_quote(self, quote, league):
            return ReferencePriceResult("REFERENCE_UNAVAILABLE_CUTOFF_MISSED")

    result = resolve_reference_quote(
        {
            "american_odds": -110,
            "implied_probability": 0.52381,
            "sportsbook": "FanDuel",
        },
        league="MLB",
        resolver=MissedCutoffResolver(),
    )

    assert result.reference_quote is None
    assert result.reference_status == "REFERENCE_UNAVAILABLE_CUTOFF_MISSED"


def test_repeated_resolution_reuses_the_locked_reference():
    resolver = LockedReferenceResolver()
    current = {
        "american_odds": -120,
        "implied_probability": 0.545455,
        "sportsbook": "FanDuel",
    }

    first = resolve_reference_quote(current, league="MLB", resolver=resolver)
    later = resolve_reference_quote(
        {**current, "american_odds": -130, "implied_probability": 0.565217},
        league="MLB",
        resolver=resolver,
    )

    assert first.reference_quote["american_odds"] == -105
    assert later.reference_quote["american_odds"] == -105
    assert later.current_quote["american_odds"] == -130


def test_mlb_object_quote_reaches_reference_service_with_event_metadata():
    quote = SimpleNamespace(
        provider="the_odds_api",
        event_id="mlb-event-1",
        commence_time="2026-07-25T18:00:00Z",
        market="Moneyline",
        selection="Example Club",
        sportsbook="FanDuel",
        american_odds=-110,
        implied_probability=0.52381,
        real_market_loaded=True,
        last_updated="2026-07-25T15:00:00Z",
        is_live=False,
    )
    service = ReferencePriceService.__new__(ReferencePriceService)
    captured = {}

    def resolve(request):
        captured["request"] = request
        return ReferencePriceResult(
            "LOCKED",
            {"reference_price": -110},
        )

    service.resolve = resolve

    result = service.resolve_quote(
        quote_to_dict(quote),
        "MLB",
    )

    assert result.status == "LOCKED"
    assert captured["request"].provider_event_id == "mlb-event-1"
    assert captured["request"].scheduled_start_utc == datetime(
        2026,
        7,
        25,
        18,
        0,
        tzinfo=UTC,
    )
    assert captured["request"].implied_probability == 0.52381
