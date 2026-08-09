#!/usr/bin/env python3
"""
SharpStack Dashboard Refresh Tool

Rebuilds generated dashboard artifacts after UI, renderer, or card changes.

Usage:
    python tools_refresh_dashboard.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

BUILDERS: list[dict[str, Any]] = [
    {
        "name": "Decision Card",
        "script": ROOT / "tools_build_decision_card.py",
        "outputs": [
            ROOT / "output" / "cards" / "decision_card.json",
        ],
    },
    {
        "name": "Recommendation Registry",
        "script": ROOT / "tools_build_recommendation_registry.py",
        "outputs": [
            ROOT / "output" / "cards" / "recommendation_registry.json",
            ROOT / "output" / "cards" / "play_of_day.json",
        ],
    },
]


def format_file_size(size_bytes: int) -> str:
    """Return a compact human-readable file size."""

    if size_bytes < 1024:
        return f"{size_bytes} B"

    size_kb = size_bytes / 1024

    if size_kb < 1024:
        return f"{size_kb:.1f} KB"

    return f"{size_kb / 1024:.1f} MB"


def verify_output(output_path: Path, build_started_at: float) -> tuple[bool, str]:
    """
    Confirm that an expected output exists and was updated by this refresh.

    A small timestamp tolerance is used because some filesystems record
    modification times with limited precision.
    """

    if not output_path.exists():
        return False, f"Missing output: {output_path.relative_to(ROOT)}"

    modified_at = output_path.stat().st_mtime
    timestamp_tolerance_seconds = 2.0

    if modified_at < build_started_at - timestamp_tolerance_seconds:
        return False, f"Output was not refreshed: {output_path.relative_to(ROOT)}"

    file_size = format_file_size(output_path.stat().st_size)
    relative_path = output_path.relative_to(ROOT)

    return True, f"{relative_path} ({file_size})"


def run_builder(builder: dict[str, Any]) -> dict[str, Any]:
    """Run one dashboard builder and verify its expected outputs."""

    name = str(builder["name"])
    script = Path(builder["script"])
    outputs = [Path(path) for path in builder.get("outputs", [])]

    print()
    print("=" * 72)
    print(f"Refreshing: {name}")
    print("=" * 72)

    if not script.exists():
        message = f"Builder script not found: {script.relative_to(ROOT)}"
        print(f"FAILED: {message}")

        return {
            "name": name,
            "success": False,
            "elapsed": 0.0,
            "messages": [message],
        }

    build_started_at = time.time()
    timer_started_at = time.perf_counter()

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        check=False,
    )

    elapsed = time.perf_counter() - timer_started_at
    messages: list[str] = []

    if result.returncode != 0:
        message = f"Builder exited with code {result.returncode}"
        print()
        print(f"FAILED: {name}")
        print(message)

        return {
            "name": name,
            "success": False,
            "elapsed": elapsed,
            "messages": [message],
        }

    outputs_valid = True

    if outputs:
        print()
        print("Output verification:")

    for output_path in outputs:
        valid, message = verify_output(
            output_path=output_path,
            build_started_at=build_started_at,
        )

        outputs_valid = outputs_valid and valid
        messages.append(message)

        status = "OK" if valid else "FAILED"
        print(f"  [{status}] {message}")

    if outputs_valid:
        print()
        print(f"SUCCESS: {name} completed in {elapsed:.2f} seconds.")
    else:
        print()
        print(f"FAILED: {name} ran, but output verification failed.")

    return {
        "name": name,
        "success": outputs_valid,
        "elapsed": elapsed,
        "messages": messages,
    }


def print_summary(results: list[dict[str, Any]], elapsed: float) -> None:
    """Print the final dashboard refresh summary."""

    successful = sum(1 for result in results if result["success"])
    total = len(results)

    print()
    print("=" * 72)
    print("SharpStack Dashboard Refresh Summary")
    print("=" * 72)

    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        name = result["name"]
        step_elapsed = result["elapsed"]

        print(f"[{status}] {name} ({step_elapsed:.2f}s)")

    print("-" * 72)
    print(f"{successful}/{total} builders completed successfully.")
    print(f"Total elapsed time: {elapsed:.2f} seconds.")

    if successful == total:
        print()
        print("Dashboard artifacts refreshed successfully.")
        print("Refresh Streamlit to view the latest changes.")
    else:
        print()
        print("Dashboard refresh completed with errors.")
        print("Review the failed builder output above.")


def main() -> int:
    """Run all configured dashboard artifact builders."""

    overall_started_at = time.perf_counter()

    print()
    print("SharpStack Dashboard Refresh")
    print("-" * 72)

    results = [
        run_builder(builder)
        for builder in BUILDERS
    ]

    elapsed = time.perf_counter() - overall_started_at

    print_summary(
        results=results,
        elapsed=elapsed,
    )

    if all(result["success"] for result in results):
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())