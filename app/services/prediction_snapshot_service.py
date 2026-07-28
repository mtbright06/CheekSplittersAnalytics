"""Immutable prediction-time snapshots and slate-level run lifecycle.

This module is deliberately persistence-neutral.  It defines the canonical
boundary that a future Azure adapter will consume after the Recommendation
Registry has been built.  Prediction engines and current artifact builders do
not import or call it yet.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4


SNAPSHOT_SCHEMA_VERSION = "prediction_snapshot_v1"

_MUTABLE_RESOLUTION_FIELDS = frozenset(
    {
        "closing_line",
        "final_score",
        "result",
        "outcome",
        "profit",
        "profit_units",
        "roi",
        "clv",
    }
)

_TRANSIENT_ARTIFACT_FIELDS = frozenset(
    {
        "recommendation_id",
        "generated_at",
    }
)


class PredictionSnapshotValidationError(ValueError):
    """Raised when data is not valid prediction-time snapshot evidence."""


class PredictionRunLifecycleError(RuntimeError):
    """Raised when a slate-level lifecycle transition is invalid."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PredictionSnapshotValidationError(
            "Prediction timestamps must be timezone-aware."
        )
    return value.astimezone(UTC)


def _parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str):
        raise PredictionSnapshotValidationError("Timestamp must be ISO-8601.")

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _as_utc(parsed)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    return value


def _require_text(value: Any, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise PredictionSnapshotValidationError(f"{name} is required.")
    return normalized


def normalize_selection(value: Any) -> str:
    """Normalize selection identity without changing the display selection."""

    return " ".join(_require_text(value, "selection").upper().split())


def canonical_artifact_fingerprint(value: Any) -> str:
    """Fingerprint canonical Registry content without rebuild-generated fields."""

    def normalize(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {
                str(key): normalize(child)
                for key, child in sorted(item.items(), key=lambda pair: str(pair[0]))
                if str(key) not in _TRANSIENT_ARTIFACT_FIELDS
            }
        if isinstance(item, list | tuple):
            return [normalize(child) for child in item]
        if isinstance(item, datetime):
            return _thaw(_as_utc(item))
        return item

    encoded = json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_logical_run_key(
    *,
    model: "SnapshotModelIdentity",
    logical_build_id: str,
    artifact_fingerprint: str,
    artifact_schema_version: str = SNAPSHOT_SCHEMA_VERSION,
) -> str:
    """Build retry-stable identity for one logical canonical Registry build."""

    payload = {
        "schema_version": _require_text(
            artifact_schema_version,
            "artifact_schema_version",
        ),
        "model_name": model.model_name,
        "model_version": model.version,
        "git_commit": model.git_commit,
        "logical_build_id": _require_text(logical_build_id, "logical_build_id"),
        "artifact_fingerprint": _require_text(
            artifact_fingerprint,
            "artifact_fingerprint",
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _assert_prediction_time_only(value: Any, path: str = "snapshot") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in _MUTABLE_RESOLUTION_FIELDS:
                raise PredictionSnapshotValidationError(
                    f"{path}.{key} is mutable resolution data and cannot be "
                    "stored in a PredictionSnapshot."
                )
            _assert_prediction_time_only(item, f"{path}.{key}")
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _assert_prediction_time_only(item, f"{path}[{index}]")


def _without_full_ledger(value: Any) -> Any:
    """Keep diagnostic components compact by excluding pitcher-level ledgers."""

    if isinstance(value, Mapping):
        return {
            str(key): _without_full_ledger(item)
            for key, item in value.items()
            if str(key) != "evidence_ledger"
        }
    if isinstance(value, list | tuple):
        return [_without_full_ledger(item) for item in value]
    return value


def _numeric(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class SnapshotModelIdentity:
    model_name: str
    version: str
    git_commit: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_name", _require_text(self.model_name, "model_name"))
        object.__setattr__(self, "version", _require_text(self.version, "model version"))


@dataclass(frozen=True, slots=True)
class PredictionRunContext:
    model_run_id: UUID
    logical_run_key: str
    logical_build_id: str
    artifact_fingerprint: str
    model: SnapshotModelIdentity
    started_at: datetime
    build_timestamp: datetime
    artifact_schema_version: str = SNAPSHOT_SCHEMA_VERSION
    source: str = "sharpstack"
    artifact_pointer: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", _as_utc(self.started_at))
        object.__setattr__(self, "build_timestamp", _as_utc(self.build_timestamp))
        object.__setattr__(
            self,
            "artifact_schema_version",
            _require_text(self.artifact_schema_version, "artifact_schema_version"),
        )
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(
            self,
            "logical_build_id",
            _require_text(self.logical_build_id, "logical_build_id"),
        )
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_text(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        expected_logical_run_key = build_logical_run_key(
            model=self.model,
            logical_build_id=self.logical_build_id,
            artifact_fingerprint=self.artifact_fingerprint,
            artifact_schema_version=self.artifact_schema_version,
        )
        if self.logical_run_key != expected_logical_run_key:
            raise PredictionSnapshotValidationError(
                "logical_run_key does not match the supplied logical build identity."
            )


@dataclass(frozen=True, slots=True)
class PredictionIdentity:
    provider_game_id: str
    sport: str
    league: str
    market: str
    selection: str
    scheduled_start_at_prediction: datetime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_game_id", _require_text(self.provider_game_id, "provider_game_id"))
        object.__setattr__(self, "sport", _require_text(self.sport, "sport").upper())
        object.__setattr__(self, "league", _require_text(self.league, "league").upper())
        object.__setattr__(self, "market", _require_text(self.market, "market").lower())
        object.__setattr__(self, "selection", normalize_selection(self.selection))
        if self.scheduled_start_at_prediction is not None:
            object.__setattr__(
                self,
                "scheduled_start_at_prediction",
                _as_utc(self.scheduled_start_at_prediction),
            )

    @property
    def scheduled_start(self) -> datetime | None:
        """Compatibility alias for the frozen prediction-time schedule value."""

        return self.scheduled_start_at_prediction


@dataclass(frozen=True, slots=True)
class PredictionData:
    model_probability: float | None = None
    confidence_score: float | None = None
    confidence_label: str | None = None
    recommendation: str | None = None
    model_recommendation: str | None = None
    conviction_tier: str | None = None
    hammer_score: float | None = None
    hammer_tier: str | None = None
    hammer_assessment: str | None = None
    market_value_label: str | None = None
    market_value_tone: str | None = None


@dataclass(frozen=True, slots=True)
class MarketData:
    sportsbook: str | None = None
    offered_odds: float | None = None
    market_line: float | None = None
    reference_price: float | None = None
    reference_implied_probability: float | None = None
    reference_book: str | None = None
    reference_captured_at: datetime | None = None
    implied_probability: float | None = None
    consensus_probability: float | None = None
    no_vig_probability: float | None = None
    market_status: str | None = None
    real_market_loaded: bool | None = None

    def __post_init__(self) -> None:
        if self.reference_captured_at is not None:
            object.__setattr__(
                self,
                "reference_captured_at",
                _as_utc(self.reference_captured_at),
            )


@dataclass(frozen=True, slots=True)
class SupportingEvidence:
    bullpen: Mapping[str, Any] = field(default_factory=dict)
    artifact_pointer: str | None = None
    artifact_checksum: str | None = None

    def __post_init__(self) -> None:
        _assert_prediction_time_only(self.bullpen, "supporting_evidence.bullpen")
        object.__setattr__(self, "bullpen", _freeze(self.bullpen))


@dataclass(frozen=True, slots=True)
class PredictionSnapshot:
    identity: PredictionIdentity
    run: PredictionRunContext
    prediction: PredictionData
    market: MarketData
    supporting_evidence: SupportingEvidence
    components: Mapping[str, Any] = field(default_factory=dict)
    explanation: Mapping[str, Any] = field(default_factory=dict)
    idempotency_key: str = field(init=False)

    def __post_init__(self) -> None:
        _assert_prediction_time_only(self.components, "components")
        _assert_prediction_time_only(self.explanation, "explanation")
        object.__setattr__(self, "components", _freeze(_without_full_ledger(self.components)))
        object.__setattr__(self, "explanation", _freeze(self.explanation))
        object.__setattr__(self, "idempotency_key", self._build_idempotency_key())

    def _build_idempotency_key(self) -> str:
        payload = {
            "logical_run_key": self.run.logical_run_key,
            "provider_game_id": self.identity.provider_game_id,
            "league": self.identity.league,
            "market": self.identity.market,
            "selection": self.identity.selection,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "idempotency_key": self.idempotency_key,
            "identity": _thaw(self.identity.__dict__) if hasattr(self.identity, "__dict__") else {
                "provider_game_id": self.identity.provider_game_id,
                "sport": self.identity.sport,
                "league": self.identity.league,
                "market": self.identity.market,
                "selection": self.identity.selection,
                "scheduled_start_at_prediction": _thaw(
                    self.identity.scheduled_start_at_prediction
                ),
            },
            "run": {
                "model_run_id": str(self.run.model_run_id),
                "logical_run_key": self.run.logical_run_key,
                "logical_build_id": self.run.logical_build_id,
                "artifact_fingerprint": self.run.artifact_fingerprint,
                "model": {
                    "model_name": self.run.model.model_name,
                    "version": self.run.model.version,
                    "git_commit": self.run.model.git_commit,
                },
                "started_at": _thaw(self.run.started_at),
                "build_timestamp": _thaw(self.run.build_timestamp),
                "artifact_schema_version": self.run.artifact_schema_version,
                "source": self.run.source,
                "artifact_pointer": self.run.artifact_pointer,
            },
            "prediction": _thaw({
                "model_probability": self.prediction.model_probability,
                "confidence_score": self.prediction.confidence_score,
                "confidence_label": self.prediction.confidence_label,
                "recommendation": self.prediction.recommendation,
                "model_recommendation": self.prediction.model_recommendation,
                "conviction_tier": self.prediction.conviction_tier,
                "hammer_score": self.prediction.hammer_score,
                "hammer_tier": self.prediction.hammer_tier,
                "hammer_assessment": self.prediction.hammer_assessment,
                "market_value_label": self.prediction.market_value_label,
                "market_value_tone": self.prediction.market_value_tone,
            }),
            "market": _thaw({
                "sportsbook": self.market.sportsbook,
                "offered_odds": self.market.offered_odds,
                "market_line": self.market.market_line,
                "reference_price": self.market.reference_price,
                "reference_implied_probability": self.market.reference_implied_probability,
                "reference_book": self.market.reference_book,
                "reference_captured_at": self.market.reference_captured_at,
                "implied_probability": self.market.implied_probability,
                "consensus_probability": self.market.consensus_probability,
                "no_vig_probability": self.market.no_vig_probability,
                "market_status": self.market.market_status,
                "real_market_loaded": self.market.real_market_loaded,
            }),
            "supporting_evidence": {
                "bullpen": _thaw(self.supporting_evidence.bullpen),
                "artifact_pointer": self.supporting_evidence.artifact_pointer,
                "artifact_checksum": self.supporting_evidence.artifact_checksum,
            },
            "components": _thaw(self.components),
            "explanation": _thaw(self.explanation),
        }

    @classmethod
    def from_registry_row(
        cls,
        row: Mapping[str, Any],
        *,
        run: PredictionRunContext,
    ) -> "PredictionSnapshot":
        quote = _mapping(row.get("market_quote"))
        components = _mapping(row.get("components"))
        source_signals = _mapping(row.get("source_signals"))
        market_source = _mapping(source_signals.get("market"))
        reference = _mapping(row.get("reference_price"))
        if not reference:
            reference = _mapping(source_signals.get("reference_price"))

        confidence_value = _numeric(row.get("confidence_score"))
        if confidence_value is None:
            confidence_value = _numeric(components.get("model_confidence"))

        return cls(
            identity=PredictionIdentity(
                provider_game_id=row.get("event_id"),
                sport=row.get("sport"),
                league=row.get("league"),
                market=row.get("market"),
                selection=row.get("selection"),
                scheduled_start_at_prediction=_parse_timestamp(
                    row.get("event_time")
                ),
            ),
            run=run,
            prediction=PredictionData(
                model_probability=_numeric(row.get("model_probability")),
                confidence_score=confidence_value,
                confidence_label=_text_or_none(row.get("confidence")),
                recommendation=_text_or_none(row.get("recommendation")),
                model_recommendation=_text_or_none(row.get("model_recommendation")),
                conviction_tier=_text_or_none(
                    row.get("model_recommendation") or row.get("recommendation")
                ),
                hammer_score=_numeric(row.get("hammer_score")),
                hammer_tier=_text_or_none(row.get("hammer_tier")),
                hammer_assessment=_text_or_none(row.get("hammer_assessment")),
                market_value_label=_text_or_none(row.get("market_value_label")),
                market_value_tone=_text_or_none(row.get("market_value_tone")),
            ),
            market=MarketData(
                sportsbook=_text_or_none(quote.get("sportsbook")),
                offered_odds=_numeric(quote.get("odds")),
                market_line=_numeric(quote.get("line")),
                reference_price=_numeric(
                    row.get("reference_price") if not isinstance(row.get("reference_price"), Mapping)
                    else reference.get("reference_price")
                ),
                reference_implied_probability=_numeric(
                    row.get("reference_implied_probability") or reference.get("reference_implied_probability")
                ),
                reference_book=_text_or_none(row.get("reference_book") or reference.get("reference_book")),
                reference_captured_at=_parse_timestamp(
                    row.get("reference_captured_at") or reference.get("reference_captured_at")
                ),
                implied_probability=_numeric(quote.get("implied_probability")),
                consensus_probability=_numeric(
                    row.get("consensus_probability") or market_source.get("consensus_probability")
                ),
                no_vig_probability=_numeric(quote.get("no_vig_probability")),
                market_status=_text_or_none(row.get("market_status") or source_signals.get("market_status")),
                real_market_loaded=_bool_or_none(row.get("real_market_loaded")),
            ),
            supporting_evidence=SupportingEvidence(
                bullpen=summarize_bullpen_evidence(components, source_signals),
                artifact_pointer=run.artifact_pointer,
                artifact_checksum=_text_or_none(row.get("artifact_checksum")),
            ),
            components=_without_full_ledger(components),
            explanation={
                "recommendation_explanation": row.get("recommendation_explanation") or {},
                "reasons": row.get("reasons") or [],
            },
        )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text_or_none(value: Any) -> str | None:
    text = str(value).strip() if value not in (None, "") else ""
    return text or None


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    return None


def summarize_bullpen_evidence(
    components: Mapping[str, Any],
    source_signals: Mapping[str, Any],
) -> dict[str, Any]:
    """Return concise provenance counts without serializing the full ledger."""

    bullpen = _mapping(components.get("bullpen")) or _mapping(source_signals.get("bullpen"))
    ledger = bullpen.get("evidence_ledger")
    summary: dict[str, Any] = {
        key: bullpen[key]
        for key in (
            "source_quality",
            "source_detail",
            "reliever_count",
            "availability_confidence",
        )
        if key in bullpen
    }
    if not isinstance(ledger, list):
        return summary

    source_quality_counts: Counter[str] = Counter()
    workload_counts: Counter[str] = Counter()
    availability_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    limited_history_count = 0

    for entry in ledger:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("source_quality"):
            source_quality_counts[str(entry["source_quality"])] += 1
        if entry.get("limited_history") is True:
            limited_history_count += 1
        workload = _mapping(entry.get("workload_assessment"))
        if workload.get("overall_workload"):
            workload_counts[str(workload["overall_workload"])] += 1
        availability = _mapping(entry.get("availability_evidence"))
        if availability.get("status"):
            availability_counts[str(availability["status"])] += 1
        role_evidence = _mapping(entry.get("role_evidence"))
        for candidate in role_evidence.get("candidate_roles", []):
            if isinstance(candidate, Mapping) and candidate.get("role"):
                role_counts[str(candidate["role"])] += 1

    summary["evidence_summary"] = {
        "evaluated_pitcher_count": len(ledger),
        "limited_history_count": limited_history_count,
        "source_quality_counts": dict(sorted(source_quality_counts.items())),
        "overall_workload_counts": dict(sorted(workload_counts.items())),
        "availability_status_counts": dict(sorted(availability_counts.items())),
        "role_candidate_counts": dict(sorted(role_counts.items())),
    }
    return summary


@dataclass(frozen=True, slots=True)
class PredictionRunRecord:
    context: PredictionRunContext
    status: str
    snapshots: tuple[PredictionSnapshot, ...]
    completed_at: datetime | None = None
    failure_reason: str | None = None


class PredictionSnapshotLifecycle:
    """In-memory orchestration contract for one slate-level model run.

    This is intentionally not an Azure writer.  A later persistence adapter
    will use these transitions in one database transaction.
    """

    def __init__(self) -> None:
        self._runs: dict[UUID, PredictionRunRecord] = {}

    def begin_run(
        self,
        *,
        model: SnapshotModelIdentity,
        logical_build_id: str,
        artifact_fingerprint: str,
        started_at: datetime | None = None,
        build_timestamp: datetime | None = None,
        source: str = "sharpstack",
        artifact_pointer: str | None = None,
        model_run_id: UUID | None = None,
    ) -> PredictionRunContext:
        now = datetime.now(UTC)
        logical_run_key = build_logical_run_key(
            model=model,
            logical_build_id=logical_build_id,
            artifact_fingerprint=artifact_fingerprint,
        )
        context = PredictionRunContext(
            model_run_id=model_run_id or uuid4(),
            logical_run_key=logical_run_key,
            logical_build_id=logical_build_id,
            artifact_fingerprint=artifact_fingerprint,
            model=model,
            started_at=started_at or now,
            build_timestamp=build_timestamp or now,
            source=source,
            artifact_pointer=artifact_pointer,
        )
        if context.model_run_id in self._runs:
            raise PredictionRunLifecycleError("Model run already exists.")
        self._runs[context.model_run_id] = PredictionRunRecord(
            context=context,
            status="running",
            snapshots=(),
        )
        return context

    def persist_snapshots(
        self,
        run: PredictionRunContext,
        snapshots: Sequence[PredictionSnapshot],
    ) -> PredictionRunRecord:
        record = self._get_running_record(run)
        existing = {item.idempotency_key: item for item in record.snapshots}
        additions: list[PredictionSnapshot] = []

        for snapshot in snapshots:
            if snapshot.run.model_run_id != run.model_run_id:
                raise PredictionRunLifecycleError(
                    "Snapshot belongs to a different model run."
                )
            previous = existing.get(snapshot.idempotency_key)
            if previous is None:
                existing[snapshot.idempotency_key] = snapshot
                additions.append(snapshot)
            elif previous != snapshot:
                raise PredictionRunLifecycleError(
                    "Idempotency key collision with different snapshot data."
                )

        updated = PredictionRunRecord(
            context=record.context,
            status="running",
            snapshots=record.snapshots + tuple(additions),
        )
        self._runs[run.model_run_id] = updated
        return updated

    def complete_run(
        self,
        run: PredictionRunContext,
        *,
        completed_at: datetime | None = None,
    ) -> PredictionRunRecord:
        record = self._get_running_record(run)
        finished_at = _as_utc(completed_at or datetime.now(UTC))
        if finished_at < record.context.started_at:
            raise PredictionRunLifecycleError("Run cannot complete before it starts.")
        updated = PredictionRunRecord(
            context=record.context,
            status="completed",
            snapshots=record.snapshots,
            completed_at=finished_at,
        )
        self._runs[run.model_run_id] = updated
        return updated

    def fail_run(
        self,
        run: PredictionRunContext,
        *,
        reason: str,
    ) -> PredictionRunRecord:
        record = self._get_running_record(run)
        updated = PredictionRunRecord(
            context=record.context,
            status="failed",
            snapshots=record.snapshots,
            failure_reason=_require_text(reason, "failure reason"),
        )
        self._runs[run.model_run_id] = updated
        return updated

    def get_run(self, run: PredictionRunContext) -> PredictionRunRecord:
        try:
            return self._runs[run.model_run_id]
        except KeyError as exc:
            raise PredictionRunLifecycleError("Unknown model run.") from exc

    def _get_running_record(self, run: PredictionRunContext) -> PredictionRunRecord:
        record = self.get_run(run)
        if record.status != "running":
            raise PredictionRunLifecycleError(
                f"Model run is {record.status}, not running."
            )
        return record
