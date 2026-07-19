from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from recommendation_engine.schema import (
    NormalizedRecord,
)


class RecommendationAdapter(ABC):
    """
    Base contract for SharpStack card adapters.

    Each adapter must answer:

        1. Can I recognize this card?
        2. What normalized records does it contain?
    """

    adapter_name = "base"
    source_family = "unknown"

    supported_extensions = {
        ".json",
    }

    def supports_extension(
        self,
        path: Path,
    ) -> bool:
        return (
            path.suffix.lower()
            in self.supported_extensions
        )

    @abstractmethod
    def can_load(
        self,
        path: Path,
        frame: pd.DataFrame | None = None,
    ) -> bool:
        """
        Return True when the adapter recognizes this card.
        """

        raise NotImplementedError

    @abstractmethod
    def load(
        self,
        path: Path,
        frame: pd.DataFrame,
    ) -> list[NormalizedRecord]:
        """
        Convert a card dataframe into normalized records.
        """

        raise NotImplementedError

    def normalized_filename(
        self,
        path: Path,
    ) -> str:
        return (
            path.name
            .lower()
            .replace("-", "_")
        )

    def normalized_path(
        self,
        path: Path,
    ) -> str:
        return (
            str(path)
            .lower()
            .replace("\\", "/")
        )

    def normalized_columns(
        self,
        frame: pd.DataFrame | None,
    ) -> set[str]:
        if frame is None:
            return set()

        return {
            str(column).strip().lower()
            for column in frame.columns
        }

    def has_filename_token(
        self,
        path: Path,
        *tokens: str,
    ) -> bool:
        filename = self.normalized_filename(path)

        return any(
            token.lower().replace("-", "_")
            in filename
            for token in tokens
        )

    def has_any_column(
        self,
        frame: pd.DataFrame | None,
        *columns: str,
    ) -> bool:
        available = self.normalized_columns(frame)

        return any(
            column.lower() in available
            for column in columns
        )

    def has_all_columns(
        self,
        frame: pd.DataFrame | None,
        *columns: str,
    ) -> bool:
        available = self.normalized_columns(frame)

        return all(
            column.lower() in available
            for column in columns
        )

    def card_type(
        self,
        frame: pd.DataFrame | None,
    ) -> str | None:
        if frame is None or frame.empty:
            return None

        if "type" not in frame.columns:
            return None

        value = frame.iloc[0].get("type")

        if value is None:
            return None

        return str(value).strip().lower()
