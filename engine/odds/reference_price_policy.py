from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


MLB_REFERENCE_MINUTES_BEFORE_START = 60
KBO_REFERENCE_MINUTES_BEFORE_START = 45
MLB_SLATE_TIMEZONE = "America/New_York"
KBO_SLATE_TIMEZONE = "Asia/Seoul"
SSRP_POLICY_VERSION = "SSRP_v1"

LEAGUE_POLICY = {
    "MLB": (MLB_REFERENCE_MINUTES_BEFORE_START, MLB_SLATE_TIMEZONE),
    "KBO": (KBO_REFERENCE_MINUTES_BEFORE_START, KBO_SLATE_TIMEZONE),
}


@dataclass(frozen=True, slots=True)
class ReferencePriceRequest:
    provider: str
    provider_event_id: str
    league: str
    market: str
    selection: str
    price: float | int
    implied_probability: float
    sportsbook: str
    scheduled_start_utc: datetime
    now_utc: datetime | None = None
    quote_is_real: bool = True
    quote_is_live: bool = False


@dataclass(frozen=True, slots=True)
class ReferencePriceResult:
    status: str
    reference: dict[str, Any] | None = None

    @property
    def locked(self) -> bool:
        return self.status == "LOCKED" and self.reference is not None


def normalize_selection(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("SSRP timestamps must include timezone information.")
    return value.astimezone(UTC)


def policy_for_league(league: str) -> tuple[int, ZoneInfo]:
    normalized = str(league or "").upper()
    try:
        minutes, timezone_name = LEAGUE_POLICY[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported SSRP league: {league!r}") from exc
    return minutes, ZoneInfo(timezone_name)


def reference_eligibility(request: ReferencePriceRequest) -> str | None:
    if not request.quote_is_real:
        return "REFERENCE_UNAVAILABLE_NOT_REAL"
    if request.quote_is_live:
        return "REFERENCE_UNAVAILABLE_LIVE"

    start = ensure_utc(request.scheduled_start_utc)
    now = ensure_utc(request.now_utc or datetime.now(UTC))
    minutes, _ = policy_for_league(request.league)

    if now >= start:
        return "REFERENCE_UNAVAILABLE_STARTED"
    if now >= start - timedelta(minutes=minutes):
        return "REFERENCE_UNAVAILABLE_CUTOFF_MISSED"
    return None
