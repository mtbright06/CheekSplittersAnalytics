from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models.game_result import GameResult


RESULT_STATUSES = frozenset(
    {
        "SCHEDULED",
        "LIVE",
        "FINAL",
        "POSTPONED",
        "SUSPENDED",
        "CANCELED",
        "INCOMPLETE",
    }
)
WINNER_SIDES = frozenset({"HOME", "AWAY", "TIE"})


class GameResultIngestionError(RuntimeError):
    """Raised when authoritative game truth cannot be persisted safely."""


@dataclass(frozen=True)
class GameResultInput:
    provider: str
    league_code: str
    provider_game_id: str
    status: str
    source_status: str | None = None
    away_score: int | None = None
    home_score: int | None = None
    total_score: int | None = None
    winner_side: str | None = None
    game_completed_at: datetime | None = None
    went_extra_innings: bool | None = None
    source_updated_at: datetime | None = None
    source_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GameResultIngestionResult:
    game_result_id: UUID
    created: bool
    changed: bool
    revision: int
    status: str


class GameResultIngestionService:
    """Transactional persistence boundary for mutable provider game truth."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        *,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._now_factory = now_factory

    def ingest(self, payload: GameResultInput) -> GameResultIngestionResult:
        normalized = self._normalize(payload)
        session = self._session_factory()
        ingested_at = _ensure_utc(self._now_factory())

        try:
            with session.begin():
                existing = self._find_for_update(session, normalized)
                if existing is None:
                    result = GameResult(
                        **normalized,
                        last_ingested_at=ingested_at,
                        revision=1,
                    )
                    session.add(result)
                    session.flush()
                    return GameResultIngestionResult(
                        game_result_id=result.id,
                        created=True,
                        changed=True,
                        revision=result.revision,
                        status=result.status,
                    )

                changed = self._apply_if_changed(existing, normalized)
                existing.last_ingested_at = ingested_at
                if changed:
                    existing.revision += 1
                session.flush()
                return GameResultIngestionResult(
                    game_result_id=existing.id,
                    created=False,
                    changed=changed,
                    revision=existing.revision,
                    status=existing.status,
                )
        except SQLAlchemyError as exc:
            session.rollback()
            raise GameResultIngestionError(
                "Game-result ingestion failed; no partial authoritative result was saved."
            ) from exc
        finally:
            session.close()

    @staticmethod
    def _find_for_update(
        session: Session,
        payload: dict[str, Any],
    ) -> GameResult | None:
        return session.execute(
            select(GameResult)
            .where(
                GameResult.provider == payload["provider"],
                GameResult.league_code == payload["league_code"],
                GameResult.provider_game_id == payload["provider_game_id"],
            )
            .with_for_update()
        ).scalar_one_or_none()

    @staticmethod
    def _apply_if_changed(result: GameResult, payload: dict[str, Any]) -> bool:
        changed = False
        for field_name, value in payload.items():
            if getattr(result, field_name) != value:
                setattr(result, field_name, value)
                changed = True
        return changed

    @staticmethod
    def _normalize(payload: GameResultInput) -> dict[str, Any]:
        status = _required_text(payload.status, "status").upper()
        if status not in RESULT_STATUSES:
            raise ValueError(f"Unsupported game-result status: {status!r}")

        winner_side = _optional_text(payload.winner_side)
        if winner_side is not None:
            winner_side = winner_side.upper()
            if winner_side not in WINNER_SIDES:
                raise ValueError(f"Unsupported winner side: {winner_side!r}")

        away_score = _nonnegative_score(payload.away_score, "away_score")
        home_score = _nonnegative_score(payload.home_score, "home_score")
        supplied_total = _nonnegative_score(payload.total_score, "total_score")
        if (away_score is None) != (home_score is None):
            raise ValueError("away_score and home_score must be supplied together.")
        if away_score is None and supplied_total is not None:
            raise ValueError("total_score requires both away_score and home_score.")
        if status == "FINAL" and (away_score is None or home_score is None):
            raise ValueError("FINAL results require both final scores.")

        derived_total = (
            away_score + home_score
            if away_score is not None and home_score is not None
            else None
        )
        if supplied_total is not None and supplied_total != derived_total:
            raise ValueError("total_score must equal away_score + home_score.")

        return {
            "provider": _required_text(payload.provider, "provider"),
            "league_code": _required_text(payload.league_code, "league_code").upper(),
            "provider_game_id": _required_text(
                payload.provider_game_id,
                "provider_game_id",
            ),
            "status": status,
            "source_status": _optional_text(payload.source_status),
            "away_score": away_score,
            "home_score": home_score,
            "total_score": derived_total,
            "winner_side": winner_side,
            "game_completed_at": _optional_utc(payload.game_completed_at),
            "went_extra_innings": payload.went_extra_innings,
            "source_updated_at": _optional_utc(payload.source_updated_at),
            "source_metadata": dict(payload.source_metadata or {}),
        }


def _required_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _nonnegative_score(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer or None.")
    return value


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_utc(value: datetime | None) -> datetime | None:
    return _ensure_utc(value) if value is not None else None
