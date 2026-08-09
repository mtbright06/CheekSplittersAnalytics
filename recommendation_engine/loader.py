from __future__ import annotations

from recommendation_engine.schema import (
    LoadResult,
    SourceInventory,
)

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from recommendation_engine.adapters.base import (
    RecommendationAdapter,
)
from recommendation_engine.schema import (
    LoadResult,
    SourceInventory,
)


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".json",
}


def discover_source_files(
    output_root: Path,
    excluded_directories: Iterable[str] | None = None,
) -> list[Path]:
    """
    Recursively discover candidate model-output files.

    Recommendation Explorer's own output directory is excluded to prevent
    the engine from reading files that it created during a previous run.
    """

    excluded = {
        "__pycache__",
        "recommendation_explorer",
    }

    if excluded_directories:
        excluded.update(
            directory.lower()
            for directory in excluded_directories
        )

    if not output_root.exists():
        return []

    discovered: list[Path] = []

    for path in output_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        relative_parts = {
            part.lower()
            for part in path.relative_to(output_root).parts[:-1]
        }

        if relative_parts.intersection(excluded):
            continue

        discovered.append(path)

    return sorted(
        discovered,
        key=lambda item: str(item).lower(),
    )


def read_source_frame(path: Path) -> pd.DataFrame:
    """
    Read CSV or JSON model output into a dataframe.
    """

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(
            path,
            low_memory=False,
        )

    if suffix == ".json":
        with path.open(
            "r",
            encoding="utf-8",
        ) as source:
            payload = json.load(source)

        if isinstance(payload, list):
            return pd.DataFrame(payload)

        if isinstance(payload, dict):
            for key in (
                "records",
                "recommendations",
                "signals",
                "games",
                "plays",
                "rows",
                "data",
            ):
                value = payload.get(key)

                if isinstance(value, list):
                    return pd.DataFrame(value)

            return pd.DataFrame([payload])

        raise ValueError(
            f"Unsupported JSON structure: {type(payload).__name__}"
        )

    raise ValueError(
        f"Unsupported source extension: {suffix}"
    )


def find_adapter(
    path: Path,
    frame: pd.DataFrame,
    adapters: Iterable[RecommendationAdapter],
) -> RecommendationAdapter | None:
    """
    Return the first adapter that recognizes the source.
    """

    for adapter in adapters:
        try:
            if adapter.can_load(path, frame):
                return adapter
        except Exception:
            # One adapter should not prevent another adapter from evaluating
            # the same source file.
            continue

    return None


def load_recommendations(
    output_root: Path,
    adapters: Iterable[RecommendationAdapter],
) -> LoadResult:
    """
    Discover model outputs, identify their adapters, and normalize records.
    """

    result = LoadResult()

    for path in discover_source_files(output_root):
        relative_path = str(
            path.relative_to(output_root.parent)
        )

        try:
            frame = read_source_frame(path)
        except Exception as exc:
            result.inventory.append(
                SourceInventory(
                    source_file=relative_path,
                    source_family="unknown",
                    status="error",
                    error=f"Read error: {exc}",
                )
            )
            continue

        adapter = find_adapter(
            path=path,
            frame=frame,
            adapters=adapters,
        )

        if adapter is None:
            result.inventory.append(
                SourceInventory(
                    source_file=relative_path,
                    source_family="unmatched",
                    status="unmatched",
                    input_rows=len(frame),
                )
            )
            continue

        try:
            records = adapter.load(
                path=path,
                frame=frame,
            )

            recommendation_count = sum(
                record.is_recommendation
                for record in records
            )

            signal_count = sum(
                record.is_signal
                for record in records
            )

            result.records.extend(records)

            result.inventory.append(
                SourceInventory(
                    source_file=relative_path,
                    source_family=adapter.source_family,
                    adapter_name=adapter.adapter_name,
                    status="loaded",
                    input_rows=len(frame),
                    output_records=len(records),
                    recommendations=recommendation_count,
                    signals=signal_count,
                    skipped_rows=max(
                        len(frame) - len(records),
                        0,
                    ),
                )
            )

        except Exception as exc:
            result.inventory.append(
                SourceInventory(
                    source_file=relative_path,
                    source_family=adapter.source_family,
                    adapter_name=adapter.adapter_name,
                    status="error",
                    input_rows=len(frame),
                    error=f"Adapter error: {exc}",
                )
            )

    result.completed_at = datetime.now().isoformat(
        timespec="seconds"
    )

    return result
