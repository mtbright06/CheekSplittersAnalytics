from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class KBOFreshness:
    status: str
    message: str | None = None
    last_successful_build: str | None = None
    expected_game_date: str | None = None
    card_game_dates: tuple[str, ...] = ()
    source_game_count: int | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "message": self.message,
            "last_successful_build": self.last_successful_build,
            "expected_game_date": self.expected_game_date,
            "card_game_dates": list(self.card_game_dates),
            "source_game_count": self.source_game_count,
        }


def evaluate_kbo_card_freshness(
    card: dict | None,
    *,
    now: datetime | None = None,
    schedule_games: list[dict] | None = None,
) -> KBOFreshness:
    now_kst = _as_kst(now or datetime.now(tz=UTC))
    expected_date = _expected_kst_slate_date(
        now_kst,
        schedule_games,
    )

    if not card:
        return KBOFreshness(
            status="UNAVAILABLE",
            message="KBO DATA UNAVAILABLE",
            expected_game_date=expected_date,
            source_game_count=_source_count(schedule_games),
        )

    generated_at = card.get("generated_at")
    generated_date = _generated_kst_date(generated_at)
    if generated_date is None:
        return KBOFreshness(
            status="STALE",
            message="KBO DATA STALE",
            last_successful_build=generated_at,
            expected_game_date=expected_date,
            card_game_dates=_card_game_dates(card),
            source_game_count=_source_count(schedule_games),
        )

    card_dates = _card_game_dates(card)
    source_count = _source_count(schedule_games)

    if source_count and not card.get("games"):
        return KBOFreshness(
            status="UNAVAILABLE",
            message="KBO DATA UNAVAILABLE",
            last_successful_build=generated_at,
            expected_game_date=expected_date,
            card_game_dates=card_dates,
            source_game_count=source_count,
        )

    if expected_date and card_dates:
        if expected_date not in card_dates:
            return KBOFreshness(
                status="STALE",
                message="KBO DATA STALE",
                last_successful_build=generated_at,
                expected_game_date=expected_date,
                card_game_dates=card_dates,
                source_game_count=source_count,
            )

        return KBOFreshness(
            status="CURRENT",
            expected_game_date=expected_date,
            card_game_dates=card_dates,
            source_game_count=source_count,
        )

    if not card.get("games") and source_count == 0:
        return KBOFreshness(
            status="CURRENT",
            expected_game_date=expected_date,
            card_game_dates=card_dates,
            source_game_count=source_count,
        )

    if expected_date and generated_date < expected_date:
        return KBOFreshness(
            status="STALE",
            message="KBO DATA STALE",
            last_successful_build=generated_at,
            expected_game_date=expected_date,
            card_game_dates=card_dates,
            source_game_count=source_count,
        )

    return KBOFreshness(
        status="CURRENT",
        expected_game_date=expected_date,
        card_game_dates=card_dates,
        source_game_count=source_count,
    )


def _expected_kst_slate_date(
    now_kst: datetime,
    schedule_games: list[dict] | None,
) -> str:
    schedule_dates = sorted(
        {
            str(game.get("game_date"))
            for game in schedule_games or []
            if game.get("game_date")
        }
    )
    if schedule_dates:
        return schedule_dates[0]

    return now_kst.date().isoformat()


def _card_game_dates(card: dict) -> tuple[str, ...]:
    dates = sorted(
        {
            str(game.get("game_date"))
            for game in card.get("games", [])
            if game.get("game_date")
        }
    )
    return tuple(dates)


def _generated_kst_date(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=KST)

    return parsed.astimezone(KST).date().isoformat()


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=KST)

    return value.astimezone(KST)


def _source_count(
    schedule_games: list[dict] | None,
) -> int | None:
    if schedule_games is None:
        return None

    return len(schedule_games)
