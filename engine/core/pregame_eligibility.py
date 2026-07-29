from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping


class PregameEligibilityReason(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    GAME_STARTED = "GAME_STARTED"
    LIVE_MARKET = "LIVE_MARKET"
    COMPLETED_GAME = "COMPLETED_GAME"
    POSTPONED_GAME = "POSTPONED_GAME"
    CANCELED_GAME = "CANCELED_GAME"
    INVALID_START_TIME = "INVALID_START_TIME"
    GAME_STATE_UNVERIFIED = "GAME_STATE_UNVERIFIED"


@dataclass(frozen=True, slots=True)
class PregameEligibility:
    eligible: bool
    reason: PregameEligibilityReason

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reason": self.reason.value,
        }


ELIGIBLE_PREGAME = PregameEligibility(True, PregameEligibilityReason.ELIGIBLE)

_PREGAME_STATUSES = {
    "SCHEDULED",
    "PREVIEW",
    "PRE-GAME",
    "PREGAME",
    "PRE GAME",
    "WARMUP",
    "DELAYED START",
    "DELAYED",
}

_POSTPONED_STATUSES = {
    "POSTPONED",
}

_CANCELED_STATUSES = {
    "CANCELED",
    "CANCELLED",
}

_COMPLETED_STATUSES = {
    "FINAL",
    "GAME OVER",
    "COMPLETED EARLY",
}

_LIVE_STATUSES = {
    "LIVE",
    "IN PROGRESS",
    "MANAGER CHALLENGE",
    "REVIEW",
}


def evaluate_pregame_eligibility(
    *,
    game_status: Any,
    scheduled_start: Any,
    now: datetime | None = None,
    market: Mapping[str, Any] | None = None,
) -> PregameEligibility:
    status = _canonical_status(game_status)
    start = _parse_aware_utc(scheduled_start)
    current = _ensure_aware_utc(now or datetime.now(UTC))

    if bool((market or {}).get("is_live")):
        return PregameEligibility(False, PregameEligibilityReason.LIVE_MARKET)

    if status is None:
        return PregameEligibility(False, PregameEligibilityReason.GAME_STATE_UNVERIFIED)

    if status in _COMPLETED_STATUSES:
        return PregameEligibility(False, PregameEligibilityReason.COMPLETED_GAME)

    if status in _LIVE_STATUSES:
        return PregameEligibility(False, PregameEligibilityReason.GAME_STARTED)

    if status in _CANCELED_STATUSES:
        return PregameEligibility(False, PregameEligibilityReason.CANCELED_GAME)

    if start is None:
        return PregameEligibility(False, PregameEligibilityReason.INVALID_START_TIME)

    if current >= start:
        return PregameEligibility(False, PregameEligibilityReason.GAME_STARTED)

    if status in _POSTPONED_STATUSES:
        return PregameEligibility(False, PregameEligibilityReason.POSTPONED_GAME)

    if status not in _PREGAME_STATUSES:
        return PregameEligibility(False, PregameEligibilityReason.GAME_STATE_UNVERIFIED)

    if _quote_is_live_or_after_start(market, start):
        return PregameEligibility(False, PregameEligibilityReason.LIVE_MARKET)

    return ELIGIBLE_PREGAME


def _canonical_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("abstractGameState", "detailedState", "status", "state"):
            text = str(value.get(key) or "").strip()
            if text:
                return " ".join(text.upper().split())
        return None
    text = str(value or "").strip()
    if not text:
        return None
    return " ".join(text.upper().replace("_", " ").split())


def _parse_aware_utc(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(UTC)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Current time must be timezone-aware.")
    return value.astimezone(UTC)


def _quote_is_live_or_after_start(
    market: Mapping[str, Any] | None,
    scheduled_start: datetime,
) -> bool:
    if not market:
        return False
    quote_start = _parse_aware_utc(market.get("commence_time"))
    if quote_start is None:
        return False
    return quote_start > scheduled_start
