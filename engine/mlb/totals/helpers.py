from __future__ import annotations

from typing import Any


MISSING_VALUES = {
    None,
    "",
    "None",
    "N/A",
    "NA",
    "-",
    "--",
}


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in MISSING_VALUES:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    low: float,
    high: float,
) -> float:
    return max(
        low,
        min(high, value),
    )


def nested_get(
    data: Any,
    *path: str,
    default: Any = None,
) -> Any:
    current = data

    for key in path:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def first_number(
    *values: Any,
    default: float | None = None,
) -> float | None:
    for value in values:
        number = safe_float(value)

        if number is not None:
            return number

    return default


def normalize_rate(
    value: Any,
) -> float | None:
    """
    Converts percentage-like values to decimal form.

    Examples:
        0.245 -> 0.245
        24.5  -> 0.245
    """

    number = safe_float(value)

    if number is None:
        return None

    if number > 1:
        number /= 100

    return number