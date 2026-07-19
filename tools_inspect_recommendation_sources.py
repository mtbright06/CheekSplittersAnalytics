from __future__ import annotations

import argparse
from pathlib import Path

from recommendation_engine.loader import (
    discover_source_files,
    read_source_frame,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "output"


def compact_value(value: object, limit: int = 50) -> str:
    text = str(value).replace(
        "\n",
        " ",
    ).replace(
        "\r",
        " ",
    )

    if len(text) <= limit:
        return text

    return text[: limit - 3] + "..."


def inspect_sources(output_root: Path) -> int:
    files = discover_source_files(output_root)

    print()
    print("=" * 88)
    print("SHARPSTACK RECOMMENDATION SOURCE INSPECTOR")
    print("=" * 88)
    print(f"Output root: {output_root}")
    print(f"Candidate files: {len(files)}")
    print()

    if not files:
        print("No CSV or JSON files were found.")
        return 0

    for number, path in enumerate(
        files,
        start=1,
    ):
        try:
            relative_path = path.relative_to(ROOT)
        except ValueError:
            relative_path = path

        print("-" * 88)
        print(f"[{number}] {relative_path}")

        try:
            frame = read_source_frame(path)

        except Exception as exc:
            print(f"STATUS: READ ERROR — {exc}")
            print()
            continue

        print(f"ROWS: {len(frame)}")
        print(f"COLUMNS: {len(frame.columns)}")

        if len(frame.columns):
            print("COLUMN LIST:")

            for column in frame.columns:
                print(f"  - {column}")

        if not frame.empty:
            print("FIRST ROW:")

            first_row = frame.iloc[0]

            for column in frame.columns:
                print(
                    f"  {column}: "
                    f"{compact_value(first_row[column])}"
                )

        print()

    print("=" * 88)
    print("INSPECTION COMPLETE")
    print("=" * 88)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect SharpStack model-output files and display "
            "their current schemas."
        )
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Model output directory to inspect.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    return inspect_sources(
        args.output_root.resolve()
    )


if __name__ == "__main__":
    raise SystemExit(main())
