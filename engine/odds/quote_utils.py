from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


MOCK_SPORTSBOOK_NAMES = {
    "",
    "mock",
    "mock odds",
    "synthetic",
    "test",
    "test book",
    "unknown",
    "unavailable",
    "placeholder",
    "sample",
}


SPORTSBOOK_ALIASES = {
    "fanduel": "FanDuel",
    "fan duel": "FanDuel",
    "fd": "FanDuel",

    "fanatics": "Fanatics",
    "fanatics sportsbook": "Fanatics",

    "draftkings": "DraftKings",
    "draft kings": "DraftKings",
    "dk": "DraftKings",

    "caesars": "Caesars",
    "caesars sportsbook": "Caesars",

    "betmgm": "BetMGM",
    "bet mgm": "BetMGM",

    "espn bet": "ESPN BET",
    "espnbet": "ESPN BET",

    "bet365": "bet365",
    "bet 365": "bet365",

    "betrivers": "BetRivers",
    "bet rivers": "BetRivers",

    "pointsbet": "PointsBet",
    "points bet": "PointsBet",
}


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in {
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        }:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_sportsbook_name(
    value: Any,
) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    alias_key = " ".join(
        text.lower().split()
    )

    return SPORTSBOOK_ALIASES.get(
        alias_key,
        text,
    )


def is_mock_sportsbook(
    value: Any,
) -> bool:
    normalized = normalize_sportsbook_name(
        value
    ).lower()

    return normalized in MOCK_SPORTSBOOK_NAMES


def american_to_decimal(
    odds: Any,
) -> float | None:
    number = safe_float(odds)

    if number is None or number == 0:
        return None

    if number > 0:
        return 1 + (number / 100)

    return 1 + (100 / abs(number))


def american_to_implied_probability(
    odds: Any,
) -> float | None:
    number = safe_float(odds)

    if number is None or number == 0:
        return None

    if number > 0:
        return 100 / (number + 100)

    return abs(number) / (
        abs(number) + 100
    )


def implied_probability_to_american(
    probability: Any,
) -> int | None:
    value = safe_float(probability)

    if value is None:
        return None

    if value > 1:
        value /= 100

    if value <= 0 or value >= 1:
        return None

    if value >= 0.5:
        return round(
            -100 * value / (1 - value)
        )

    return round(
        100 * (1 - value) / value
    )


def expected_value_pct(
    model_probability: Any,
    american_odds: Any,
) -> float | None:
    probability = safe_float(
        model_probability
    )

    decimal_odds = american_to_decimal(
        american_odds
    )

    if (
        probability is None
        or decimal_odds is None
    ):
        return None

    if probability > 1:
        probability /= 100

    if probability < 0 or probability > 1:
        return None

    ev = (
        probability * decimal_odds
    ) - 1

    return ev * 100


def parse_timestamp(
    value: Any,
) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()

        if not text:
            return None

        text = text.replace(
            "Z",
            "+00:00",
        )

        try:
            parsed = datetime.fromisoformat(
                text
            )
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def quote_age_minutes(
    updated_at: Any,
    *,
    now: datetime | None = None,
) -> float | None:
    timestamp = parse_timestamp(
        updated_at
    )

    if timestamp is None:
        return None

    current = now or datetime.now(
        timezone.utc
    )

    if current.tzinfo is None:
        current = current.replace(
            tzinfo=timezone.utc
        )

    age_seconds = (
        current.astimezone(timezone.utc)
        - timestamp
    ).total_seconds()

    return max(
        0.0,
        age_seconds / 60,
    )


def is_stale_quote(
    updated_at: Any,
    *,
    maximum_age_minutes: float = 20,
    now: datetime | None = None,
) -> bool:
    age = quote_age_minutes(
        updated_at,
        now=now,
    )

    if age is None:
        return True

    return age > maximum_age_minutes
