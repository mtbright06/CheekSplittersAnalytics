from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"

MLB_CARD_PATH = CARDS_DIR / "mlb_card.json"
DECISION_CARD_PATH = CARDS_DIR / "decision_card.json"
REGISTRY_PATH = CARDS_DIR / "recommendation_registry.json"


NON_REAL_BOOKS = {
    "",
    "mock",
    "mock odds",
    "synthetic",
    "test",
    "test book",
    "unknown",
    "unavailable",
    "placeholder",
    "sample",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            loaded = json.load(file)

        return loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in {
            None,
            "",
            "None",
            "N/A",
            "-",
            "--",
        }:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def clean(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def display(value: Any) -> str:
    return str(value or "").strip()


def get_nested(
    data: dict[str, Any],
    *paths: tuple[str, ...],
) -> Any:
    for path in paths:
        current: Any = data

        for key in path:
            if not isinstance(current, dict):
                current = None
                break

            current = current.get(key)

        if current not in {
            None,
            "",
        }:
            return current

    return None


def matchup_parts(row: dict[str, Any]) -> tuple[str, str]:
    matchup = row.get("matchup")

    if isinstance(matchup, dict):
        away = display(
            matchup.get("away")
            or matchup.get("away_team")
        )

        home = display(
            matchup.get("home")
            or matchup.get("home_team")
        )

        return away, home

    away = display(
        row.get("away_team")
        or get_nested(
            row,
            ("teams", "away", "name"),
        )
    )

    home = display(
        row.get("home_team")
        or get_nested(
            row,
            ("teams", "home", "name"),
        )
    )

    if away or home:
        return away, home

    text = display(matchup)

    if " @ " in text:
        away, home = text.split(
            " @ ",
            1,
        )
        return away.strip(), home.strip()

    if " vs " in text.lower():
        parts = text.replace(
            " VS ",
            " vs ",
        ).split(
            " vs ",
            1,
        )

        if len(parts) == 2:
            return (
                parts[0].strip(),
                parts[1].strip(),
            )

    return "", ""


def extract_selection(row: dict[str, Any]) -> str:
    return display(
        row.get("selection")
        or row.get("play")
        or get_nested(
            row,
            ("model", "play"),
            ("recommendation", "selection"),
        )
    )


def extract_market(row: dict[str, Any]) -> str:
    return display(
        row.get("market")
        or get_nested(
            row,
            ("model", "market"),
            ("market_quote", "market"),
        )
        or "Moneyline"
    )


def extract_quote(row: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        row.get("market_quote"),
        row.get("odds"),
        get_nested(
            row,
            ("recommendation", "market_quote"),
        ),
    ]

    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate

    return {}


def extract_book(row: dict[str, Any]) -> str:
    quote = extract_quote(row)

    return display(
        quote.get("sportsbook")
        or quote.get("book")
        or quote.get("provider")
        or row.get("sportsbook")
        or row.get("book")
    )


def extract_odds(row: dict[str, Any]) -> float | None:
    quote = extract_quote(row)

    candidates = [
        quote.get("american_odds"),
        quote.get("odds"),
        quote.get("moneyline"),
        row.get("american_odds"),
        row.get("odds"),
        row.get("moneyline"),
    ]

    for candidate in candidates:
        value = safe_float(candidate)

        if value is not None:
            return value

    return None


def extract_real_market_flag(
    row: dict[str, Any],
) -> bool | None:
    quote = extract_quote(row)

    candidates = [
        row.get("real_market_loaded"),
        quote.get("real_market_loaded"),
    ]

    for candidate in candidates:
        if isinstance(candidate, bool):
            return candidate

    return None


def is_real_book(book: str) -> bool:
    return clean(book) not in NON_REAL_BOOKS


def market_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    away, home = matchup_parts(row)

    return (
        clean(away),
        clean(home),
        clean(extract_market(row)),
        clean(extract_selection(row)),
    )


def rows_from_card(
    card: dict[str, Any],
) -> list[dict[str, Any]]:
    for key in [
        "games",
        "recommendations",
        "decisions",
        "picks",
        "rows",
    ]:
        rows = card.get(key)

        if isinstance(rows, list):
            return [
                row
                for row in rows
                if isinstance(row, dict)
            ]

    return []


@dataclass
class MarketRecord:
    source: str
    key: tuple[str, str, str, str]
    away: str
    home: str
    market: str
    selection: str
    sportsbook: str
    american_odds: float | None
    real_market_loaded: bool
    raw: dict[str, Any]

    @classmethod
    def from_row(
        cls,
        source: str,
        row: dict[str, Any],
    ) -> "MarketRecord":
        away, home = matchup_parts(row)
        sportsbook = extract_book(row)
        odds = extract_odds(row)
        explicit_flag = extract_real_market_flag(row)

        inferred_real = (
            bool(sportsbook)
            and is_real_book(sportsbook)
            and odds is not None
        )

        real_market_loaded = (
            explicit_flag
            if explicit_flag is not None
            else inferred_real
        )

        return cls(
            source=source,
            key=market_key(row),
            away=away,
            home=home,
            market=extract_market(row),
            selection=extract_selection(row),
            sportsbook=sportsbook,
            american_odds=odds,
            real_market_loaded=real_market_loaded,
            raw=row,
        )


def records_from_file(
    source: str,
    path: Path,
) -> list[MarketRecord]:
    card = load_json(path)

    return [
        MarketRecord.from_row(
            source,
            row,
        )
        for row in rows_from_card(card)
    ]


def odds_text(value: float | None) -> str:
    if value is None:
        return "N/A"

    rounded = int(round(value))

    if rounded > 0:
        return f"+{rounded}"

    return str(rounded)


def record_text(record: MarketRecord) -> str:
    matchup = (
        f"{record.away} @ {record.home}"
        if record.away or record.home
        else "Unknown matchup"
    )

    return (
        f"{matchup} | "
        f"{record.selection or 'No selection'} | "
        f"{record.sportsbook or 'No book'} "
        f"{odds_text(record.american_odds)}"
    )


def compare_records(
    records_by_source: dict[str, list[MarketRecord]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    indexed: dict[
        str,
        dict[
            tuple[str, str, str, str],
            MarketRecord,
        ],
    ] = {}

    for source, records in records_by_source.items():
        indexed[source] = {
            record.key: record
            for record in records
            if any(record.key)
        }

        for record in records:
            if (
                record.real_market_loaded
                and not is_real_book(
                    record.sportsbook
                )
            ):
                errors.append(
                    f"{source}: non-real sportsbook marked real: "
                    f"{record_text(record)}"
                )

            if (
                record.real_market_loaded
                and record.american_odds is None
            ):
                errors.append(
                    f"{source}: real market has no odds: "
                    f"{record_text(record)}"
                )

            if (
                not record.real_market_loaded
                and record.american_odds is not None
                and is_real_book(
                    record.sportsbook
                )
            ):
                warnings.append(
                    f"{source}: real-looking quote marked model-only: "
                    f"{record_text(record)}"
                )

    source_names = list(
        records_by_source
    )

    if not source_names:
        return errors, warnings

    reference_source = source_names[0]
    reference_rows = indexed.get(
        reference_source,
        {},
    )

    for key, reference in reference_rows.items():
        if not reference.real_market_loaded:
            continue

        for source in source_names[1:]:
            candidate = indexed.get(
                source,
                {},
            ).get(key)

            if candidate is None:
                warnings.append(
                    f"{source}: missing downstream record for "
                    f"{record_text(reference)}"
                )
                continue

            if not candidate.real_market_loaded:
                errors.append(
                    f"{source}: lost real-market flag for "
                    f"{record_text(reference)}"
                )
                continue

            if clean(
                candidate.sportsbook
            ) != clean(
                reference.sportsbook
            ):
                errors.append(
                    f"{source}: sportsbook changed for "
                    f"{record_text(reference)}; "
                    f"found {candidate.sportsbook or 'none'}"
                )

            if (
                candidate.american_odds
                != reference.american_odds
            ):
                errors.append(
                    f"{source}: odds changed for "
                    f"{record_text(reference)}; "
                    f"found {odds_text(candidate.american_odds)}"
                )

    return errors, warnings


def print_source_summary(
    source: str,
    records: list[MarketRecord],
) -> None:
    real_count = sum(
        record.real_market_loaded
        for record in records
    )

    model_only_count = (
        len(records) - real_count
    )

    print(
        f"{source:<24}"
        f"Rows: {len(records):>3} | "
        f"Real: {real_count:>3} | "
        f"Model-only: {model_only_count:>3}"
    )

    for record in records[:3]:
        status = (
            "REAL"
            if record.real_market_loaded
            else "MODEL"
        )

        print(
            f"  {status:<5} "
            f"{record_text(record)}"
        )


def main() -> int:
    print("")
    print("=" * 78)
    print("SharpStack Market Pipeline Validation")
    print("=" * 78)

    paths = {
        "MLB Card": MLB_CARD_PATH,
        "Decision Card": DECISION_CARD_PATH,
        "Registry": REGISTRY_PATH,
    }

    missing = [
        path
        for path in paths.values()
        if not path.exists()
    ]

    if missing:
        for path in missing:
            print(
                f"WARNING: Missing {path.relative_to(ROOT)}"
            )

    records_by_source = {
        source: records_from_file(
            source,
            path,
        )
        for source, path in paths.items()
        if path.exists()
    }

    print("")

    for source, records in records_by_source.items():
        print_source_summary(
            source,
            records,
        )

    errors, warnings = compare_records(
        records_by_source
    )

    print("")
    print("-" * 78)
    print("Warnings")
    print("-" * 78)

    if warnings:
        for warning in warnings:
            print(
                f"WARNING: {warning}"
            )
    else:
        print("None")

    print("")
    print("-" * 78)
    print("Errors")
    print("-" * 78)

    if errors:
        for error in errors:
            print(
                f"ERROR: {error}"
            )

        print("")
        print(
            f"FAILED: {len(errors)} market-pipeline "
            f"error(s) detected."
        )
        return 1

    print("None")
    print("")
    print(
        "PASSED: Real prices remained consistent "
        "through all available pipeline stages."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
