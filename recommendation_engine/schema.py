from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


RecordType = Literal[
    "recommendation",
    "signal",
]


@dataclass(slots=True, kw_only=True)
class BaseRecord:
    """
    Shared fields for all normalized SharpStack records.

    kw_only=True prevents inherited dataclass field-order problems.
    """

    record_id: str
    run_date: str
    created_at: str

    sport: str
    league: str

    model_name: str
    model_version: str | None = None

    event_id: str | None = None
    event_time: str | None = None

    game: str | None = None
    away_team: str | None = None
    home_team: str | None = None

    selection: str | None = None

    confidence_score: float | None = None
    rank: int | None = None

    recommendation_label: str | None = None

    tags: list[str] = field(
        default_factory=list
    )

    notes: str | None = None

    supporting_record_ids: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    source_family: str | None = None
    source_file: str | None = None
    source_row: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def record_type(self) -> RecordType:
        raise NotImplementedError

    @property
    def is_recommendation(self) -> bool:
        return self.record_type == "recommendation"

    @property
    def is_signal(self) -> bool:
        return self.record_type == "signal"

    @property
    def display_confidence(self) -> str:
        if self.confidence_score is None:
            return "—"

        return f"{self.confidence_score:.1f}"

    def has_tag(self, tag: str) -> bool:
        target = tag.strip().lower()

        return any(
            existing.strip().lower() == target
            for existing in self.tags
        )


@dataclass(slots=True, kw_only=True)
class Recommendation(BaseRecord):
    """
    A directly actionable betting recommendation.
    """

    market: str | None = None
    market_scope: str | None = None

    selection_side: str | None = None

    sportsbook: str | None = None

    american_odds: int | None = None
    decimal_odds: float | None = None

    model_probability: float | None = None
    market_probability: float | None = None

    edge: float | None = None

    outcome: str | None = None
    profit_units: float | None = None

    @property
    def record_type(
        self,
    ) -> Literal["recommendation"]:
        return "recommendation"

    @property
    def is_plus_money(self) -> bool:
        return (
            self.american_odds is not None
            and self.american_odds > 0
        )

    @property
    def display_odds(self) -> str:
        if self.american_odds is None:
            return "—"

        if self.american_odds > 0:
            return f"+{self.american_odds}"

        return str(self.american_odds)

    @property
    def display_edge(self) -> str:
        if self.edge is None:
            return "—"

        prefix = "+" if self.edge > 0 else ""

        return f"{prefix}{self.edge:.1f}%"


@dataclass(slots=True, kw_only=True)
class Signal(BaseRecord):
    """
    Supporting analytical evidence.

    Examples:
        Bomb Lab target
        team stack ranking
        vulnerable pitcher
        model lean without available odds
    """

    signal_type: str | None = None

    score: float | None = None
    tier: str | None = None
    grade: str | None = None

    target: str | None = None
    opponent: str | None = None
    pitcher: str | None = None

    metric_name: str | None = None
    metric_value: float | None = None

    @property
    def record_type(
        self,
    ) -> Literal["signal"]:
        return "signal"

    @property
    def display_score(self) -> str:
        if self.score is None:
            return "—"

        return f"{self.score:.1f}"


NormalizedRecord = Recommendation | Signal


@dataclass(slots=True, kw_only=True)
class SourceInventory:
    """
    Diagnostic information for one scanned source card.
    """

    source_file: str
    source_family: str
    status: str

    input_rows: int = 0
    output_records: int = 0

    recommendations: int = 0
    signals: int = 0

    skipped_rows: int = 0

    adapter_name: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, kw_only=True)
class LoadResult:
    """
    Full result returned by the Recommendation Engine loader.
    """

    records: list[NormalizedRecord] = field(
        default_factory=list
    )

    inventory: list[SourceInventory] = field(
        default_factory=list
    )

    started_at: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"
        )
    )

    completed_at: str | None = None

    @property
    def recommendations(
        self,
    ) -> list[Recommendation]:
        return [
            record
            for record in self.records
            if isinstance(record, Recommendation)
        ]

    @property
    def signals(
        self,
    ) -> list[Signal]:
        return [
            record
            for record in self.records
            if isinstance(record, Signal)
        ]

    @property
    def loaded_sources(
        self,
    ) -> list[SourceInventory]:
        return [
            source
            for source in self.inventory
            if source.status == "loaded"
        ]

    @property
    def errors(
        self,
    ) -> list[SourceInventory]:
        return [
            source
            for source in self.inventory
            if source.status == "error"
        ]

    @property
    def unmatched_sources(
        self,
    ) -> list[SourceInventory]:
        return [
            source
            for source in self.inventory
            if source.status == "unmatched"
        ]
