from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import GameResult, Recommendation
from app.services.game_result_ingestion_service import GameResultIngestionService, GameResultInput
from app.services.prediction_snapshot_grading_service import PredictionSnapshotGradingService
from app.services.prediction_snapshot_persistence_service import (
    PersistedPredictionRun,
    PredictionSnapshotPersistenceService,
)
from app.services.prediction_snapshot_service import (
    PredictionSnapshot,
    PredictionSnapshotLifecycle,
    SnapshotModelIdentity,
)


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
    ) -> None:
        self._session_factory = session_factory
        self._snapshot_persistence = snapshot_persistence or PredictionSnapshotPersistenceService(session_factory)
        self._result_ingestion = result_ingestion or GameResultIngestionService(session_factory)
        self._grading = grading or PredictionSnapshotGradingService(session_factory)

    def persist_registry(self, registry_path: Path) -> PersistedPredictionRun:
        registry = _load_registry(registry_path)
        artifact_fingerprint = _fingerprint(registry)
        build_timestamp = datetime.fromtimestamp(registry_path.stat().st_mtime, UTC)
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
            PredictionSnapshot.from_registry_row(row, run=run)
            for row in rows
            if isinstance(row, Mapping)
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
        session = self._session_factory()
        try:
            snapshots = session.execute(
                select(Recommendation.id).where(
                    Recommendation.league_code == league_code.upper(),
                    Recommendation.provider_game_id == str(provider_game_id),
                )
            ).scalars().all()
        except SQLAlchemyError as exc:
            raise DailyPersistenceError("Unable to match snapshots to GameResult.") from exc
        finally:
            session.close()

        if not snapshots:
            return 0, 0, 1
        created = reused = 0
        for snapshot_id in snapshots:
            grade = self._grading.grade(
                prediction_snapshot_id=snapshot_id,
                game_result_id=game_result_id,
            )
            if grade.created:
                created += 1
            else:
                reused += 1
        return created, reused, 0


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


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"
