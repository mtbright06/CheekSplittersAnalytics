from __future__ import annotations

from typing import Any


PITCHER_BASELINES = {
    "era": 4.50,
    "whip": 1.35,
    "k9": 8.50,
    "bb9": 3.20,
    "hr9": 1.20,
    "h9": 8.50,
    "k_bb_pct": 14.0,
    "strike_pct": 64.0,
    "pitches_per_inning": 16.5,
    "ground_air_ratio": 1.00,
}

# A pitcher has half of the observed-stat influence at 50 innings. This keeps
# brief starter samples close to league average while retaining 75% of an
# established 150-inning sample.
PITCHER_STABILIZATION_IP = 50.0


def stabilize_pitcher_stat(
    observed_value: Any,
    innings_pitched: Any,
    league_average: float,
    stabilization_ip: float = PITCHER_STABILIZATION_IP,
) -> float | None:
    """Blend one observed pitcher stat toward its league-average baseline."""
    observed = to_float(observed_value)

    if observed is None:
        return None

    innings = to_float(innings_pitched)

    if innings is None or innings <= 0:
        # Missing innings is a source-quality limitation, not proof that the
        # pitcher is unknown. Preserve established raw-stat fallbacks; callers
        # that require a known starter retain their own neutral handling.
        return observed

    reliability = innings / (innings + stabilization_ip)

    return league_average + reliability * (observed - league_average)


def stabilize_pitcher_metrics(
    pitcher: dict[str, Any],
    *,
    innings_key: str = "ip",
    metric_keys: dict[str, str] | None = None,
) -> dict[str, float | None]:
    """Return a shared stabilized view without mutating raw provider values."""
    metric_keys = metric_keys or {
        "era": "era",
        "whip": "whip",
        "k9": "k_rate",
        "bb9": "bb_rate",
        "hr9": "hr9",
    }
    innings = pitcher.get(innings_key)

    return {
        metric: stabilize_pitcher_stat(
            observed_value=pitcher.get(source_key),
            innings_pitched=innings,
            league_average=PITCHER_BASELINES[metric],
        )
        for metric, source_key in metric_keys.items()
    }


def to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None

        return float(value)
    except (TypeError, ValueError):
        return None
