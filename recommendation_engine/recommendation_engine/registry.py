from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Type

from recommendation_engine.adapters.base import (
    RecommendationAdapter,
)


@dataclass(slots=True)
class AdapterRegistration:
    """
    Registry entry describing one Recommendation Engine adapter.
    """

    model_name: str
    adapter_name: str
    source_family: str

    record_kind: str

    card_filename: str

    enabled: bool = True
    model_version: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AdapterRegistry:
    """
    Runtime registry for card adapters.

    The registry controls which source cards are recognized without
    requiring the loader to know individual model names.
    """

    def __init__(self) -> None:
        self._adapter_classes: list[
            Type[RecommendationAdapter]
        ] = []

        self._registrations: list[
            AdapterRegistration
        ] = []

    def register(
        self,
        adapter_class: Type[
            RecommendationAdapter
        ],
        registration: AdapterRegistration,
    ) -> None:
        if not registration.enabled:
            return

        if adapter_class not in self._adapter_classes:
            self._adapter_classes.append(
                adapter_class
            )

        existing = {
            item.adapter_name
            for item in self._registrations
        }

        if (
            registration.adapter_name
            not in existing
        ):
            self._registrations.append(
                registration
            )

    def create_adapters(
        self,
    ) -> list[RecommendationAdapter]:
        return [
            adapter_class()
            for adapter_class
            in self._adapter_classes
        ]

    @property
    def registrations(
        self,
    ) -> list[AdapterRegistration]:
        return list(self._registrations)

    def write_registry(
        self,
        destination: Path,
    ) -> None:
        import json

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = [
            registration.to_dict()
            for registration
            in self._registrations
        ]

        with destination.open(
            "w",
            encoding="utf-8",
        ) as target:
            json.dump(
                payload,
                target,
                indent=2,
            )


registry = AdapterRegistry()
