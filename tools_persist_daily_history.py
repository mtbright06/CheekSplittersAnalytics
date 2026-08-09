#!/usr/bin/env python3
"""Persist the completed Registry, ingest recent MLB results, and grade matches."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.providers.mlb_game_results import MLBGameResultProvider
from app.services.daily_persistence_service import DailyPersistenceService


ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "output" / "cards" / "recommendation_registry.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--days-back", type=int, default=7)
    args = parser.parse_args()

    summary = DailyPersistenceService().run(
        registry_path=args.registry,
        provider=MLBGameResultProvider(),
        days_back=args.days_back,
    )
    print("Daily persistence complete")
    print(f"Logical run: {summary.logical_run_key}")
    print(f"Persisted snapshots: {summary.persisted_snapshots}")
    print(f"Ingested MLB results: {summary.ingested_results}")
    print(f"Changed results: {summary.changed_results}")
    print(f"Created grades: {summary.created_grades}")
    print(f"Reused grades: {summary.reused_grades}")
    print(f"Unmatched results: {summary.unmatched_results}")


if __name__ == "__main__":
    main()
