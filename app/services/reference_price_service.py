from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models.reference_price import ReferencePrice
from engine.odds.reference_price_policy import (
    SSRP_POLICY_VERSION,
    ReferencePriceRequest,
    ReferencePriceResult,
    ensure_utc,
    normalize_selection,
    policy_for_league,
    reference_eligibility,
)


class ReferencePriceStoreError(RuntimeError):
    """Raised when SSRP persistence cannot establish the canonical quote."""


class ReferencePriceService:
    """Persistence boundary for immutable SharpStack Reference Prices."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def resolve(self, request: ReferencePriceRequest) -> ReferencePriceResult:
        normalized = self._normalize_request(request)
        session = self._session_factory()

        try:
            existing = self._find(session, normalized)
            if existing is not None:
                return ReferencePriceResult("LOCKED", self._to_dict(existing))

            unavailable = reference_eligibility(normalized)
            if unavailable is not None:
                return ReferencePriceResult(unavailable)

            minutes, timezone = policy_for_league(normalized.league)
            start = ensure_utc(normalized.scheduled_start_utc)
            now = ensure_utc(normalized.now_utc or datetime.now(UTC))
            statement = insert(ReferencePrice).values(
                provider=normalized.provider,
                provider_event_id=normalized.provider_event_id,
                league=normalized.league,
                market=normalized.market,
                selection=normalized.selection,
                reference_price=Decimal(str(normalized.price)),
                reference_implied_probability=Decimal(
                    str(normalized.implied_probability)
                ),
                reference_book=normalized.sportsbook,
                reference_captured_at=now,
                reference_minutes_before_start=Decimal(
                    str((start - now).total_seconds() / 60)
                ),
                reference_policy_version=SSRP_POLICY_VERSION,
                scheduled_start_utc=start,
                slate_date=start.astimezone(timezone).date(),
                reference_status="LOCKED",
            ).on_conflict_do_nothing(
                constraint="uq_reference_prices_identity"
            )
            session.execute(statement)
            session.commit()

            locked = self._find(session, normalized)
            if locked is None:
                raise ReferencePriceStoreError("SSRP insert completed without a row.")
            return ReferencePriceResult("LOCKED", self._to_dict(locked))
        except SQLAlchemyError as exc:
            session.rollback()
            raise ReferencePriceStoreError(
                "SSRP persistence is unavailable; current odds cannot become edge input."
            ) from exc
        finally:
            session.close()

    def resolve_quote(
        self,
        quote: Mapping[str, Any],
        league: str,
    ) -> ReferencePriceResult:
        """Adapt an ingestion quote at the persistence boundary."""
        commence_time = self._parse_timestamp(quote.get("commence_time"))
        if commence_time is None:
            return ReferencePriceResult("REFERENCE_UNAVAILABLE_MISSING_EVENT")

        provider_event_id = str(quote.get("event_id") or "").strip()
        provider = str(quote.get("provider") or "").strip()
        selection = str(quote.get("selection") or "").strip()
        sportsbook = str(quote.get("sportsbook") or "").strip()
        price = quote.get("american_odds")
        implied_probability = quote.get("implied_probability")

        if not all((provider_event_id, provider, selection, sportsbook)):
            return ReferencePriceResult("REFERENCE_UNAVAILABLE_MISSING_EVENT")
        if price is None or implied_probability is None:
            return ReferencePriceResult("REFERENCE_UNAVAILABLE_MISSING_PRICE")

        return self.resolve(
            ReferencePriceRequest(
                provider=provider,
                provider_event_id=provider_event_id,
                league=league,
                market=str(quote.get("market") or "Moneyline"),
                selection=selection,
                price=price,
                implied_probability=implied_probability,
                sportsbook=sportsbook,
                scheduled_start_utc=commence_time,
                quote_is_real=bool(quote.get("real_market_loaded")),
                quote_is_live=bool(quote.get("is_live")),
            )
        )

    @staticmethod
    def _normalize_request(request: ReferencePriceRequest) -> ReferencePriceRequest:
        return ReferencePriceRequest(
            provider=str(request.provider or "").strip(),
            provider_event_id=str(request.provider_event_id or "").strip(),
            league=str(request.league or "").upper().strip(),
            market=str(request.market or "").upper().strip(),
            selection=normalize_selection(request.selection),
            price=request.price,
            implied_probability=request.implied_probability,
            sportsbook=str(request.sportsbook or "").strip(),
            scheduled_start_utc=ensure_utc(request.scheduled_start_utc),
            now_utc=(ensure_utc(request.now_utc) if request.now_utc else None),
            quote_is_real=bool(request.quote_is_real),
            quote_is_live=bool(request.quote_is_live),
        )

    @staticmethod
    def _find(session: Session, request: ReferencePriceRequest) -> ReferencePrice | None:
        return session.execute(
            select(ReferencePrice).where(
                ReferencePrice.provider == request.provider,
                ReferencePrice.provider_event_id == request.provider_event_id,
                ReferencePrice.league == request.league,
                ReferencePrice.market == request.market,
                ReferencePrice.selection == request.selection,
                ReferencePrice.scheduled_start_utc
                == ensure_utc(request.scheduled_start_utc),
            )
        ).scalar_one_or_none()

    @staticmethod
    def _to_dict(reference: ReferencePrice) -> dict[str, Any]:
        return {
            "reference_price": float(reference.reference_price),
            "reference_implied_probability": float(
                reference.reference_implied_probability
            ),
            "reference_book": reference.reference_book,
            "reference_captured_at": reference.reference_captured_at.isoformat(),
            "reference_minutes_before_start": float(
                reference.reference_minutes_before_start
            ),
            "reference_status": reference.reference_status,
            "reference_policy_version": reference.reference_policy_version,
            "provider_event_id": reference.provider_event_id,
            "scheduled_start_utc": reference.scheduled_start_utc.isoformat(),
            "slate_date": reference.slate_date.isoformat(),
        }

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return ensure_utc(value)
        text = str(value or "").strip().replace("Z", "+00:00")
        if not text:
            return None
        try:
            return ensure_utc(datetime.fromisoformat(text))
        except ValueError:
            return None
