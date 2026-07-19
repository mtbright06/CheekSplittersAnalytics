from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


NULL_VALUES = {
    "",
    "-",
    "--",
    "nan",
    "none",
    "null",
    "n/a",
    "na",
    "unknown",
    "<na>",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in NULL_VALUES:
        return None

    return text


def normalize_column_name(value: Any) -> str:
    text = str(value).strip().lower()

    text = text.replace("%", "_pct")
    text = text.replace("+/-", "_difference")

    text = re.sub(r"[^a-z0-9]+", "_", text)

    return text.strip("_")


def normalize_dataframe_columns(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    output = frame.copy()

    output.columns = [
        normalize_column_name(column)
        for column in output.columns
    ]

    return output


def normalize_row(row: pd.Series) -> dict[str, Any]:
    return {
        normalize_column_name(column): value
        for column, value in row.items()
    }


def first_value(
    row: dict[str, Any],
    aliases: Iterable[str],
) -> Any:
    for alias in aliases:
        key = normalize_column_name(alias)

        if key not in row:
            continue

        value = row[key]

        if clean_text(value) is not None:
            return value

    return None


def parse_float(value: Any) -> float | None:
    text = clean_text(value)

    if text is None:
        return None

    cleaned = (
        text.replace(",", "")
        .replace("$", "")
        .replace("%", "")
        .replace("−", "-")
        .replace("–", "-")
    )

    cleaned = re.sub(
        r"[^0-9eE.+-]",
        "",
        cleaned,
    )

    if cleaned in {
        "",
        "+",
        "-",
        ".",
        "+.",
        "-.",
    }:
        return None

    try:
        number = float(cleaned)
    except ValueError:
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    return number


def parse_int(value: Any) -> int | None:
    number = parse_float(value)

    if number is None:
        return None

    return int(round(number))


def parse_probability(value: Any) -> float | None:
    """
    Returns probability as 0.0 through 1.0.

    Supports:
        0.58
        58
        58%
    """

    number = parse_float(value)

    if number is None:
        return None

    if 1 < number <= 100:
        number /= 100

    if not 0 <= number <= 1:
        return None

    return round(number, 6)


def parse_percentage_points(value: Any) -> float | None:
    """
    Returns a percentage-point value.

    Supports:
        0.074 -> 7.4
        7.4   -> 7.4
        7.4%  -> 7.4
    """

    number = parse_float(value)

    if number is None:
        return None

    if -1 <= number <= 1:
        number *= 100

    return round(number, 4)


def parse_confidence(value: Any) -> float | None:
    """
    Returns confidence on a 0 through 100 scale.
    """

    number = parse_float(value)

    if number is None:
        return None

    if 0 <= number <= 1:
        number *= 100

    if not 0 <= number <= 100:
        return None

    return round(number, 2)


def parse_american_odds(value: Any) -> int | None:
    text = clean_text(value)

    if text is None:
        return None

    if text.lower() in {
        "even",
        "evens",
        "even money",
    }:
        return 100

    number = parse_float(text)

    if number is None:
        return None

    # Convert decimal odds when they were placed in an odds field.
    if 1.01 <= number < 20:
        if number >= 2:
            return int(
                round((number - 1) * 100)
            )

        return int(
            round(-100 / (number - 1))
        )

    odds = int(round(number))

    if -100 < odds < 100:
        return None

    return odds


def american_to_decimal(
    odds: int | None,
) -> float | None:
    if odds is None:
        return None

    if odds > 0:
        return round(
            1 + odds / 100,
            4,
        )

    if odds < 0:
        return round(
            1 + 100 / abs(odds),
            4,
        )

    return None


def american_to_probability(
    odds: int | None,
) -> float | None:
    if odds is None:
        return None

    if odds > 0:
        probability = 100 / (odds + 100)

    elif odds < 0:
        probability = abs(odds) / (
            abs(odds) + 100
        )

    else:
        return None

    return round(probability, 6)


def normalize_date(
    value: Any,
    fallback: date | None = None,
) -> str:
    fallback = fallback or date.today()

    text = clean_text(value)

    if text is None:
        return fallback.isoformat()

    parsed = pd.to_datetime(
        text,
        errors="coerce",
    )

    if pd.isna(parsed):
        return fallback.isoformat()

    return parsed.date().isoformat()


def normalize_datetime(
    value: Any,
) -> str | None:
    text = clean_text(value)

    if text is None:
        return None

    parsed = pd.to_datetime(
        text,
        errors="coerce",
    )

    if pd.isna(parsed):
        return None

    return parsed.isoformat()


def normalize_team(value: Any) -> str | None:
    text = clean_text(value)

    if text is None:
        return None

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    compact = text.replace(".", "")

    if (
        compact.isalpha()
        and 2 <= len(compact) <= 4
    ):
        return compact.upper()

    return text


def slugify(value: Any) -> str:
    text = clean_text(value) or ""

    text = text.upper()

    text = re.sub(
        r"[^A-Z0-9]+",
        "-",
        text,
    )

    return text.strip("-")


def build_record_id(
    run_date: str,
    league: str,
    model_name: str,
    market: str | None,
    selection: str | None,
    game: str | None,
) -> str:
    pieces = [
        run_date,
        league,
        model_name,
        market or "UNKNOWN-MARKET",
        selection or "UNKNOWN-SELECTION",
        game or "UNKNOWN-GAME",
    ]

    raw = "|".join(pieces)

    digest = hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()[:10].upper()

    readable = "-".join(
        part
        for part in [
            slugify(run_date),
            slugify(league),
            slugify(model_name),
            slugify(selection),
        ]
        if part
    )

    return f"{readable}-{digest}"


def dedupe_tags(
    tags: Iterable[str],
) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        normalized = (
            slugify(tag)
            .lower()
            .replace("-", "_")
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        output.append(normalized)

    return output


def relative_source_path(
    path: Path,
    root: Path,
) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
