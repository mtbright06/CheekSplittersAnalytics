from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.services.canonical_recommendation_grading_service import (
    CanonicalRecommendationGradingService,
)
from app.services.game_result_ingestion_service import GameResultIngestionService, GameResultInput
from app.services.prediction_snapshot_grading_service import PredictionSnapshotGradingService
from app.services.prediction_snapshot_persistence_service import (
    PersistedPredictionRun,
    PredictionSnapshotPersistenceService,
)
from app.services.prediction_snapshot_service import (
    PredictionSnapshot,
    PredictionSnapshotLifecycle,
    PredictionSnapshotValidationError,
    SnapshotModelIdentity,
)
from engine.core.pregame_eligibility import (
    PregameEligibilityReason,
    evaluate_pregame_eligibility,
)

LOGGER = logging.getLogger(__name__)


class GameResultProvider(Protocol):
    def fetch_recent(self, *, days_back: int) -> tuple[GameResultInput, ...]: ...


class DailyPersistenceError(RuntimeError):
    """Raised when the daily persistence workflow cannot complete safely."""


@dataclass(frozen=True)
class DailyPersistenceSummary:
    logical_run_key: str
    persisted_snapshots: int
    ingested_results: int
    changed_results: int
    created_grades: int
    reused_grades: int
    unmatched_results: int


class DailyPersistenceService:
    """Operational adapter from the canonical Registry into persistence services."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        snapshot_persistence: PredictionSnapshotPersistenceService | None = None,
        result_ingestion: GameResultIngestionService | None = None,
        grading: PredictionSnapshotGradingService | None = None,
        canonical_grading: CanonicalRecommendationGradingService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._snapshot_persistence = snapshot_persistence or PredictionSnapshotPersistenceService(session_factory)
        self._result_ingestion = result_ingestion or GameResultIngestionService(session_factory)
        self._grading = grading or PredictionSnapshotGradingService(session_factory)
        self._canonical_grading = canonical_grading or CanonicalRecommendationGradingService(
            session_factory
        )

    def persist_registry(self, registry_path: Path) -> PersistedPredictionRun:
        registry = _load_registry(registry_path)
        artifact_fingerprint = _fingerprint(registry)
        build_timestamp = _registry_build_timestamp(registry, registry_path)
        logical_build_id = str(registry.get("generated_at") or artifact_fingerprint)
        lifecycle = PredictionSnapshotLifecycle()
        run = lifecycle.begin_run(
            model=SnapshotModelIdentity(
                "sharpstack_registry",
                str(registry.get("version") or "unknown"),
                _git_commit(),
            ),
            logical_build_id=logical_build_id,
            artifact_fingerprint=artifact_fingerprint,
            started_at=build_timestamp,
            build_timestamp=build_timestamp,
            artifact_pointer=str(registry_path),
        )
        rows = registry.get("recommendations")
        if not isinstance(rows, list):
            raise DailyPersistenceError("Registry recommendations must be a list.")
        snapshots = tuple(
            _valid_registry_snapshots(
                rows,
                run,
            )
        )
        return self._snapshot_persistence.persist_run(run=run, snapshots=snapshots)

    def ingest_and_grade(
        self,
        provider: GameResultProvider,
        *,
        days_back: int,
    ) -> tuple[int, int, int, int, int]:
        inputs = provider.fetch_recent(days_back=days_back)
        ingested = changed = created_grades = reused_grades = unmatched_results = 0
        for result_input in inputs:
            saved_result = self._result_ingestion.ingest(result_input)
            ingested += 1
            changed += int(saved_result.changed)
            graded, reused, unmatched_count = self._grade_matching_snapshots(
                saved_result.game_result_id,
                result_input.league_code,
                result_input.provider_game_id,
            )
            created_grades += graded
            reused_grades += reused
            unmatched_results += unmatched_count
        return ingested, changed, created_grades, reused_grades, unmatched_results

    def run(
        self,
        *,
        registry_path: Path,
        provider: GameResultProvider,
        days_back: int = 7,
    ) -> DailyPersistenceSummary:
        persisted = self.persist_registry(registry_path)
        ingested, changed, created, reused, unmatched = self.ingest_and_grade(
            provider,
            days_back=days_back,
        )
        return DailyPersistenceSummary(
            logical_run_key=persisted.logical_run_key,
            persisted_snapshots=persisted.created_snapshot_count,
            ingested_results=ingested,
            changed_results=changed,
            created_grades=created,
            reused_grades=reused,
            unmatched_results=unmatched,
        )

    def _grade_matching_snapshots(
        self,
        game_result_id: object,
        league_code: str,
        provider_game_id: str,
    ) -> tuple[int, int, int]:
        try:
            return self._canonical_grading.grade_for_result(
                league_code=league_code,
                provider_game_id=provider_game_id,
                game_result_id=game_result_id,
            )
        except SQLAlchemyError as exc:
            raise DailyPersistenceError("Unable to grade canonical episode.") from exc


def _load_registry(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DailyPersistenceError(f"Unable to load Registry artifact: {path}") from exc
    if not isinstance(payload, Mapping):
        raise DailyPersistenceError("Registry artifact must be a JSON object.")
    return payload


def _fingerprint(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _registry_build_timestamp(registry: Mapping[str, Any], path: Path) -> datetime:
    generated_at = registry.get("generated_at")
    if isinstance(generated_at, str) and generated_at.strip():
        try:
            parsed = datetime.fromisoformat(
                generated_at.strip().replace("Z", "+00:00")
            )
            if parsed.tzinfo is not None and parsed.utcoffset() is not None:
                return parsed.astimezone(UTC)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _valid_registry_snapshots(
    rows: list[Any],
    run: Any,
) -> tuple[PredictionSnapshot, ...]:
    snapshots: list[PredictionSnapshot] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if not _row_has_verified_pregame_eligibility(row):
            _log_refused_registry_row(
                row,
                str(
                    row.get("pregame_eligibility_reason")
                    or PregameEligibilityReason.UNVERIFIED.value
                ),
            )
            continue
        try:
            snapshot = PredictionSnapshot.from_registry_row(row, run=run)
        except (PredictionSnapshotValidationError, ValueError) as exc:
            _log_refused_registry_row(row, PregameEligibilityReason.UNVERIFIED.value, exc)
            continue

        if not _eligible_for_pregame_persistence(snapshot):
            _log_refused_registry_row(
                row,
                str(
                    row.get("pregame_eligibility_reason")
                    or PregameEligibilityReason.UNVERIFIED.value
                ),
            )
            continue

        snapshots.append(snapshot)
    return tuple(snapshots)


def _row_has_verified_pregame_eligibility(row: Mapping[str, Any]) -> bool:
    return (
        row.get("pregame_eligible") is True
        and row.get("pregame_eligibility_reason")
        == PregameEligibilityReason.GAME_NOT_STARTED.value
    )


def _log_refused_registry_row(
    row: Mapping[str, Any],
    reason: str,
    exc: Exception | None = None,
) -> None:
    LOGGER.warning(
        "Refusing unsafe pregame snapshot: reason=%s league=%s event_id=%s "
        "market=%s selection=%s scheduled_start_at=%r%s",
        reason,
        row.get("league"),
        row.get("event_id"),
        row.get("market"),
        row.get("selection"),
        row.get("scheduled_start_at"),
        f" error={exc}" if exc else "",
    )


def _eligible_for_pregame_persistence(snapshot: PredictionSnapshot) -> bool:
    if snapshot.identity.sport != "BASEBALL":
        return True

    if snapshot.identity.market not in {
        "moneyline",
        "totals",
        "total",
        "first5_moneyline",
        "first5_total",
        "nrfi",
        "home_run",
    }:
        return True

    start = snapshot.identity.scheduled_start_at_prediction
    if start is None:
        return False

    eligibility = evaluate_pregame_eligibility(
        game_status="SCHEDULED",
        scheduled_start=start,
        now=snapshot.run.build_timestamp,
        market={
            "is_live": (
                snapshot.market.market_status
                == PregameEligibilityReason.LIVE_MARKET.value
            )
        },
    )

    return eligibility.eligible


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"
