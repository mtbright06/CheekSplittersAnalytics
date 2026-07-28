"""Transactional Azure persistence for immutable prediction snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import (
    ActiveRecommendationSlot,
    ModelRun,
    ModelVersion,
    Recommendation,
    RecommendationActivationEvent,
)
from app.services.prediction_snapshot_service import (
    PredictionRunContext,
    PredictionSnapshot,
)


EVENT_ACTIVATED = "ACTIVATED"
EVENT_SUPERSEDED = "SUPERSEDED"
EVENT_WITHDRAWN = "WITHDRAWN"
EVENT_REINSTATED = "REINSTATED"

REASON_SELECTION_CHANGED = "SELECTION_CHANGED"
REASON_UPDATED_MODEL = "UPDATED_MODEL"
REASON_MARKET_REFRESH = "MARKET_REFRESH"
REASON_NEW_LOGICAL_BUILD = "NEW_LOGICAL_BUILD"
REASON_PASS_REPLACEMENT = "PASS_REPLACEMENT"
REASON_MARKET_UNAVAILABLE = "MARKET_UNAVAILABLE"
REASON_GAME_POSTPONED = "GAME_POSTPONED"
REASON_GAME_CANCELED = "GAME_CANCELED"
REASON_MANUAL_WITHDRAWAL = "MANUAL_WITHDRAWAL"
REASON_REINSTATED = "REINSTATED"


class PredictionSnapshotPersistenceError(RuntimeError):
    """Raised when immutable prediction persistence cannot complete."""


@dataclass(frozen=True, slots=True)
class WithdrawalRequest:
    provider_game_id: str
    league_code: str
    market_type: str
    reason: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PersistedPredictionRun:
    model_run_id: UUID
    logical_run_key: str
    recommendation_ids: tuple[UUID, ...]
    created_snapshot_count: int
    lifecycle_event_count: int
    status: str


def supersession_reason(
    prior: Recommendation,
    snapshot: PredictionSnapshot,
    model_version_id: UUID,
) -> str:
    """Classify a replacement only from persisted/snapshot evidence."""

    if _is_pass(snapshot.prediction.recommendation):
        return REASON_PASS_REPLACEMENT
    if prior.selection != snapshot.identity.selection:
        return REASON_SELECTION_CHANGED
    if prior.model_version_id != model_version_id:
        return REASON_UPDATED_MODEL

    prior_market = (prior.components or {}).get("market", {})
    current_market = snapshot.to_dict()["market"]
    if prior_market != current_market:
        return REASON_MARKET_REFRESH
    return REASON_NEW_LOGICAL_BUILD


class PredictionSnapshotPersistenceService:
    """Writes a complete slate atomically without changing Registry behavior."""

    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def persist_run(
        self,
        *,
        run: PredictionRunContext,
        snapshots: Sequence[PredictionSnapshot],
        withdrawals: Sequence[WithdrawalRequest] = (),
    ) -> PersistedPredictionRun:
        self._validate_snapshots(run, snapshots)
        session = self._session_factory()
        try:
            with session.begin():
                existing_run = session.execute(
                    select(ModelRun).where(ModelRun.logical_run_key == run.logical_run_key)
                ).scalar_one_or_none()
                if existing_run is not None:
                    return self._completed_existing_run_or_raise(session, existing_run)

                model_version = self._get_or_create_model_version(session, run)
                model_run = ModelRun(
                    model_version_id=model_version.id,
                    started_at=run.started_at,
                    status="running",
                    source=run.source,
                    run_metadata={
                        "logical_build_id": run.logical_build_id,
                        "artifact_fingerprint": run.artifact_fingerprint,
                        "artifact_schema_version": run.artifact_schema_version,
                        "artifact_pointer": run.artifact_pointer,
                    },
                    logical_run_key=run.logical_run_key,
                )
                session.add(model_run)
                session.flush()

                recommendations: list[Recommendation] = []
                event_count = 0
                for snapshot in snapshots:
                    recommendation, created = self._insert_snapshot(
                        session, model_run, model_version, snapshot
                    )
                    recommendations.append(recommendation)
                    if created:
                        event_count += self._activate_snapshot(
                            session, model_run, recommendation, snapshot
                        )

                for withdrawal in withdrawals:
                    event_count += self._withdraw_slot(session, model_run, withdrawal)

                model_run.completed_at = datetime.now(UTC)
                model_run.status = "completed"

            return PersistedPredictionRun(
                model_run_id=model_run.id,
                logical_run_key=run.logical_run_key,
                recommendation_ids=tuple(item.id for item in recommendations),
                created_snapshot_count=len(recommendations),
                lifecycle_event_count=event_count,
                status="completed",
            )
        except IntegrityError as exc:
            session.rollback()
            concurrent_run = session.execute(
                select(ModelRun).where(ModelRun.logical_run_key == run.logical_run_key)
            ).scalar_one_or_none()
            if concurrent_run is not None:
                return self._completed_existing_run_or_raise(session, concurrent_run)
            raise PredictionSnapshotPersistenceError(
                "Concurrent prediction persistence did not produce a completed run."
            ) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            raise PredictionSnapshotPersistenceError(
                "Prediction snapshot transaction failed."
            ) from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_active_recommendations(self) -> tuple[Recommendation, ...]:
        """Return the current operational view; history remains separate."""

        session = self._session_factory()
        try:
            return tuple(
                session.execute(
                    select(Recommendation)
                    .join(
                        ActiveRecommendationSlot,
                        ActiveRecommendationSlot.active_recommendation_id
                        == Recommendation.id,
                    )
                    .where(ActiveRecommendationSlot.active_recommendation_id.is_not(None))
                    .order_by(ActiveRecommendationSlot.activated_at.desc())
                ).scalars().all()
            )
        except SQLAlchemyError as exc:
            raise PredictionSnapshotPersistenceError(
                "Active recommendation query failed."
            ) from exc
        finally:
            session.close()

    def _existing_run_result(
        self, session: Session, model_run: ModelRun
    ) -> PersistedPredictionRun:
        recommendations = session.execute(
            select(Recommendation.id).where(Recommendation.model_run_id == model_run.id)
        ).scalars().all()
        event_count = session.execute(
            select(RecommendationActivationEvent.id).where(
                RecommendationActivationEvent.model_run_id == model_run.id
            )
        ).scalars().all()
        return PersistedPredictionRun(
            model_run_id=model_run.id,
            logical_run_key=model_run.logical_run_key or "",
            recommendation_ids=tuple(recommendations),
            created_snapshot_count=0,
            lifecycle_event_count=len(event_count),
            status=model_run.status,
        )

    def _completed_existing_run_or_raise(
        self, session: Session, model_run: ModelRun
    ) -> PersistedPredictionRun:
        if model_run.status != "completed" or model_run.completed_at is None:
            raise PredictionSnapshotPersistenceError(
                "Logical run already exists but is not completed; refusing to "
                "treat incomplete persisted state as an idempotent retry."
            )
        return self._existing_run_result(session, model_run)

    def _get_or_create_model_version(
        self, session: Session, run: PredictionRunContext
    ) -> ModelVersion:
        model = run.model
        git_commit = model.git_commit or "unknown"
        existing = session.execute(
            select(ModelVersion).where(
                ModelVersion.model_name == model.model_name,
                ModelVersion.version == model.version,
                ModelVersion.git_commit == git_commit,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        version = ModelVersion(
            model_name=model.model_name,
            version=model.version,
            git_commit=git_commit,
        )
        session.add(version)
        session.flush()
        return version

    def _insert_snapshot(
        self, session: Session, model_run: ModelRun, model_version: ModelVersion,
        snapshot: PredictionSnapshot,
    ) -> tuple[Recommendation, bool]:
        existing = session.execute(
            select(Recommendation).where(
                Recommendation.idempotency_key == snapshot.idempotency_key
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing, False

        payload = snapshot.to_dict()
        recommendation = Recommendation(
            game_id=None,
            model_version_id=model_version.id,
            model_run_id=model_run.id,
            market_type=snapshot.identity.market.upper(),
            selection=snapshot.identity.selection,
            market_line=_decimal_or_none(snapshot.market.market_line),
            projection=_decimal_or_none(snapshot.prediction.model_probability),
            edge=None,
            confidence=_normalized_confidence(snapshot.prediction.confidence_score),
            components=payload,
            explanation=_explanation_text(payload["explanation"]),
            source=run_source(snapshot),
            recommendation_time=snapshot.run.build_timestamp,
            idempotency_key=snapshot.idempotency_key,
            provider_game_id=snapshot.identity.provider_game_id,
            league_code=snapshot.identity.league,
            sport=snapshot.identity.sport,
            scheduled_start_at_prediction=snapshot.identity.scheduled_start_at_prediction,
        )
        session.add(recommendation)
        session.flush()
        return recommendation, True

    def _activate_snapshot(
        self, session: Session, model_run: ModelRun,
        recommendation: Recommendation, snapshot: PredictionSnapshot,
    ) -> int:
        slot = self._locked_slot(session, snapshot)
        prior_id = slot.active_recommendation_id if slot is not None else None
        prior = session.get(Recommendation, prior_id) if prior_id is not None else None
        now = datetime.now(UTC)

        if slot is None:
            slot = ActiveRecommendationSlot(
                provider_game_id=snapshot.identity.provider_game_id,
                league_code=snapshot.identity.league,
                market_type=snapshot.identity.market,
                active_recommendation_id=recommendation.id,
                activated_at=now,
            )
            session.add(slot)
            self._append_event(session, model_run, snapshot, None, recommendation.id, EVENT_ACTIVATED, EVENT_ACTIVATED)
            return 1

        if prior_id == recommendation.id:
            return 0

        event_type = EVENT_REINSTATED if prior_id is None else EVENT_SUPERSEDED
        reason = (
            REASON_REINSTATED
            if event_type == EVENT_REINSTATED
            else supersession_reason(prior, snapshot, model_run.model_version_id)
        )
        slot.active_recommendation_id = recommendation.id
        slot.activated_at = now
        self._append_event(session, model_run, snapshot, prior_id, recommendation.id, event_type, reason)
        if event_type == EVENT_SUPERSEDED:
            self._append_event(
                session,
                model_run,
                snapshot,
                prior_id,
                recommendation.id,
                EVENT_ACTIVATED,
                reason,
            )
            return 2
        return 1

    def _withdraw_slot(self, session: Session, model_run: ModelRun, request: WithdrawalRequest) -> int:
        slot = session.execute(
            select(ActiveRecommendationSlot).where(
                ActiveRecommendationSlot.provider_game_id == request.provider_game_id,
                ActiveRecommendationSlot.league_code == request.league_code.upper(),
                ActiveRecommendationSlot.market_type == request.market_type.lower(),
            ).with_for_update()
        ).scalar_one_or_none()
        if slot is None or slot.active_recommendation_id is None:
            return 0
        prior_id = slot.active_recommendation_id
        slot.active_recommendation_id = None
        slot.activated_at = None
        self._append_event_for_slot(session, model_run, request, prior_id)
        return 1

    def _locked_slot(self, session: Session, snapshot: PredictionSnapshot) -> ActiveRecommendationSlot | None:
        return session.execute(
            select(ActiveRecommendationSlot).where(
                ActiveRecommendationSlot.provider_game_id == snapshot.identity.provider_game_id,
                ActiveRecommendationSlot.league_code == snapshot.identity.league,
                ActiveRecommendationSlot.market_type == snapshot.identity.market,
            ).with_for_update()
        ).scalar_one_or_none()

    def _append_event(self, session: Session, model_run: ModelRun, snapshot: PredictionSnapshot,
        prior_id: UUID | None, new_id: UUID | None, event_type: str, reason: str,
    ) -> None:
        session.add(RecommendationActivationEvent(
            provider_game_id=snapshot.identity.provider_game_id,
            league_code=snapshot.identity.league,
            market_type=snapshot.identity.market,
            model_run_id=model_run.id,
            prior_recommendation_id=prior_id,
            new_recommendation_id=new_id,
            logical_run_key=snapshot.run.logical_run_key,
            event_type=event_type,
            reason=reason,
            occurred_at=datetime.now(UTC),
            event_metadata={},
        ))

    def _append_event_for_slot(self, session: Session, model_run: ModelRun,
        request: WithdrawalRequest, prior_id: UUID,
    ) -> None:
        if request.reason not in {REASON_MARKET_UNAVAILABLE, REASON_GAME_POSTPONED,
                                  REASON_GAME_CANCELED, REASON_MANUAL_WITHDRAWAL}:
            raise PredictionSnapshotPersistenceError("Unsupported withdrawal reason.")
        session.add(RecommendationActivationEvent(
            provider_game_id=request.provider_game_id,
            league_code=request.league_code.upper(),
            market_type=request.market_type.lower(),
            model_run_id=model_run.id,
            prior_recommendation_id=prior_id,
            new_recommendation_id=None,
            logical_run_key=model_run.logical_run_key or "",
            event_type=EVENT_WITHDRAWN,
            reason=request.reason,
            occurred_at=datetime.now(UTC),
            event_metadata=dict(request.metadata or {}),
        ))

    @staticmethod
    def _validate_snapshots(run: PredictionRunContext, snapshots: Sequence[PredictionSnapshot]) -> None:
        seen: set[tuple[str, str, str]] = set()
        for snapshot in snapshots:
            if snapshot.run.logical_run_key != run.logical_run_key:
                raise PredictionSnapshotPersistenceError("Snapshot belongs to another logical run.")
            key = (snapshot.identity.provider_game_id, snapshot.identity.league, snapshot.identity.market)
            if key in seen:
                raise PredictionSnapshotPersistenceError("A logical run may activate only one selection per slot.")
            seen.add(key)


def _decimal_or_none(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _normalized_confidence(value: float | None) -> Decimal | None:
    if value is None:
        return None
    normalized = value / 100 if value > 1 else value
    return Decimal(str(max(0.0, min(1.0, normalized))))


def _is_pass(value: str | None) -> bool:
    return str(value or "").upper() in {"PASS", "NO PLAY"}


def _explanation_text(value: dict[str, Any]) -> str | None:
    return value.get("summary") or None


def run_source(snapshot: PredictionSnapshot) -> str:
    return snapshot.run.source
