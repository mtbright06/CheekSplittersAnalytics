from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd


# =============================================================================
# CHEEK SPLITTERS — RECOMMENDATION EXPLORER
# =============================================================================
#
# PURPOSE
# -------
# Collect existing model outputs without forcing every model to adopt the new
# recommendation schema immediately.
#
# The script:
#   1. Recursively scans the output directory.
#   2. Identifies known source families.
#   3. Reads CSV and JSON outputs.
#   4. Normalizes different column names.
#   5. Separates recommendations from supporting signals.
#   6. Deduplicates equivalent records.
#   7. Writes consolidated CSV, JSON, inventory, and console reports.
#
# SUPPORTED SOURCE FAMILIES
# -------------------------
#   - Recommendation Tracker
#   - Bomb Lab
#   - First 5 Market Edge
#   - KBO Model
#   - First 5 Lab
#   - MLB hitters / pitcher stacks
#
# The adapters are intentionally forgiving. Missing values remain blank instead
# of causing the entire build to fail.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
EXPLORER_DIR = OUTPUT_DIR / "recommendation_explorer"

LOCAL_TIMEZONE = ZoneInfo("America/New_York")

SUPPORTED_EXTENSIONS = {".csv", ".json"}

EXCLUDED_DIRECTORIES = {
    "recommendation_explorer",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
}

EXCLUDED_FILENAMES = {
    "recommendations_today.csv",
    "recommendations_today.json",
    "signals_today.csv",
    "signals_today.json",
    "all_records_today.csv",
    "all_records_today.json",
    "source_inventory.csv",
}

NULL_STRINGS = {
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

POSITIVE_RECOMMENDATION_WORDS = {
    "bet",
    "play",
    "best bet",
    "official play",
    "recommend",
    "recommended",
    "strong bet",
    "strong play",
    "lean",
    "value",
    "edge",
}

NEGATIVE_RECOMMENDATION_WORDS = {
    "no bet",
    "no play",
    "pass",
    "avoid",
    "skip",
    "fade",
}

FINAL_RESULT_WORDS = {
    "win",
    "won",
    "loss",
    "lost",
    "push",
    "void",
    "cancelled",
    "canceled",
    "pending",
}


# =============================================================================
# NORMALIZED SCHEMA
# =============================================================================


@dataclass
class ExplorerRecord:
    recommendation_id: str

    run_date: str
    created_at: str

    record_type: str
    sport: str
    league: str

    event_id: str | None = None
    event_time: str | None = None
    game: str | None = None
    away_team: str | None = None
    home_team: str | None = None

    market: str | None = None
    market_scope: str | None = None

    selection: str | None = None
    selection_side: str | None = None
    opponent: str | None = None
    pitcher: str | None = None

    sportsbook: str | None = None
    american_odds: int | None = None
    decimal_odds: float | None = None
    market_probability: float | None = None

    model_probability: float | None = None
    edge: float | None = None
    confidence_score: float | None = None

    model_name: str | None = None
    model_version: str | None = None

    recommendation: str | None = None
    rank: int | None = None

    outcome: str | None = None
    profit_units: float | None = None

    tags: list[str] = field(default_factory=list)
    notes: str | None = None
    supporting_signals: dict[str, Any] = field(default_factory=dict)

    source_family: str | None = None
    source_file: str | None = None
    source_row: int | None = None


@dataclass
class SourceInventory:
    source_file: str
    source_family: str
    status: str
    input_rows: int
    output_records: int
    recommendations: int
    signals: int
    skipped_rows: int
    error: str | None = None


# =============================================================================
# COLUMN ALIASES
# =============================================================================


ALIASES: dict[str, list[str]] = {
    "date": [
        "date",
        "run_date",
        "game_date",
        "event_date",
        "slate_date",
        "tracked_date",
        "pick_date",
    ],
    "created_at": [
        "created_at",
        "created",
        "timestamp",
        "generated_at",
        "tracked_at",
    ],
    "sport": [
        "sport",
        "sport_name",
    ],
    "league": [
        "league",
        "competition",
    ],
    "game": [
        "game",
        "matchup",
        "event",
        "fixture",
        "game_matchup",
    ],
    "event_id": [
        "event_id",
        "game_id",
        "mlb_game_id",
        "espn_event_id",
    ],
    "event_time": [
        "event_time",
        "game_time",
        "start_time",
        "scheduled",
        "scheduled_time",
        "commence_time",
    ],
    "team": [
        "team",
        "team_abbr",
        "team_code",
        "club",
        "target_team",
        "stack_team",
        "offense",
    ],
    "team_name": [
        "team_name",
        "club_name",
    ],
    "away_team": [
        "away_team",
        "away",
        "visitor",
        "visitor_team",
    ],
    "home_team": [
        "home_team",
        "home",
        "home_club",
    ],
    "opponent": [
        "opponent",
        "opp",
        "opposing_team",
    ],
    "player": [
        "player",
        "player_name",
        "batter",
        "batter_name",
        "hitter",
        "hitter_name",
        "name",
    ],
    "pitcher": [
        "pitcher",
        "pitcher_name",
        "opposing_pitcher",
        "opp_pitcher",
        "starter",
        "starting_pitcher",
    ],
    "selection": [
        "selection",
        "pick",
        "bet",
        "wager",
        "target",
        "recommended_side",
    ],
    "market": [
        "market",
        "bet_type",
        "market_type",
        "wager_type",
        "play_type",
    ],
    "market_scope": [
        "market_scope",
        "scope",
        "period",
    ],
    "side": [
        "side",
        "selection_side",
        "bet_side",
    ],
    "sportsbook": [
        "sportsbook",
        "book",
        "bookmaker",
        "best_book",
    ],
    "odds": [
        "odds",
        "american_odds",
        "price",
        "line_odds",
        "best_odds",
        "market_odds",
    ],
    "model_probability": [
        "model_probability",
        "model_prob",
        "model_win_probability",
        "model_win_prob",
        "win_probability",
        "win_prob",
        "projected_probability",
        "projected_prob",
        "fair_probability",
        "hr_probability",
        "hr_prob",
    ],
    "market_probability": [
        "market_probability",
        "market_prob",
        "implied_probability",
        "implied_prob",
        "book_probability",
    ],
    "edge": [
        "edge",
        "model_edge",
        "market_edge",
        "edge_pct",
        "edge_percent",
        "value_edge",
        "probability_edge",
    ],
    "confidence": [
        "confidence",
        "confidence_score",
        "score",
        "bet_score",
        "recommendation_score",
    ],
    "recommendation": [
        "recommendation",
        "recommendation_label",
        "play",
        "action",
        "decision",
        "bet_status",
        "status",
    ],
    "rank": [
        "rank",
        "overall_rank",
        "stack_rank",
        "target_rank",
        "model_rank",
    ],
    "result": [
        "result",
        "outcome",
        "grade",
        "bet_result",
        "final_result",
    ],
    "profit_units": [
        "profit_units",
        "units_won",
        "net_units",
        "pnl_units",
        "profit",
    ],
    "notes": [
        "notes",
        "note",
        "reason",
        "rationale",
        "commentary",
        "explanation",
    ],
    "model": [
        "model",
        "model_name",
        "source_model",
    ],
    "model_version": [
        "model_version",
        "version",
    ],
    "record_type": [
        "record_type",
        "type",
    ],
}


# Signals copied into the flexible metadata field when found.
SIGNAL_ALIASES: dict[str, list[str]] = {
    "hr_score": ["hr_score"],
    "edge_score": ["edge_score"],
    "power_score": ["power_score"],
    "hr_match_score": ["hr_match_score"],
    "bomb_score": ["bomb_score"],
    "market_score": ["market_score"],
    "attack_score": ["attack_score"],
    "stack_score": ["stack_score"],
    "starter_score": ["starter_score"],
    "starter_edge": ["starter_edge", "starting_pitcher_edge"],
    "offense_score": ["offense_score"],
    "bullpen_score": ["bullpen_score"],
    "recent_score": ["recent_score", "recent_form"],
    "home_score": ["home_score"],
    "barrel_rate": ["barrel_rate", "barrel_pct", "barrel_percent", "barrel"],
    "hard_hit_rate": [
        "hard_hit_rate",
        "hard_hit_pct",
        "hard_hit_percent",
        "hh_pct",
    ],
    "average_exit_velocity": ["avg_ev", "average_exit_velocity"],
    "bat_speed": ["bat_speed", "avg_bat_speed"],
    "blast_rate": ["blast_rate", "blast_contact", "blast_pct"],
    "pull_rate": ["pull_rate", "pull_pct"],
    "weather_score": ["weather_score"],
    "park_factor": ["park_factor", "hr_park_factor"],
    "implied_runs": ["implied_runs", "team_total", "implied_team_total"],
    "target_side": ["target_side", "batter_side", "bat_side"],
    "pitcher_hand": ["pitcher_hand", "throws", "pitch_hand"],
    "recommended_units": ["units", "stake_units", "recommended_units"],
}


SOURCE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    (
        "recommendation_tracker",
        (
            "recommendation_tracker",
            "recommendations_tracker",
            "tracked_recommendation",
            "tracked_pick",
            "pick_tracker",
            "bet_tracker",
        ),
    ),
    (
        "first5_market_edge",
        (
            "first5_market",
            "first_5_market",
            "f5_market",
            "market_edge",
        ),
    ),
    (
        "bomb_lab",
        (
            "bomb_lab",
            "bomblab",
            "home_run",
            "homer",
            "hr_target",
        ),
    ),
    (
        "first5_lab",
        (
            "first5",
            "first_5",
            "f5_lab",
            "first-five",
        ),
    ),
    (
        "kbo",
        (
            "kbo",
            "korean_baseball",
        ),
    ),
    (
        "mlb_signal",
        (
            "hitter",
            "pitcher",
            "stack",
            "mlb_card",
            "mlb_target",
        ),
    ),
]


# =============================================================================
# GENERAL HELPERS
# =============================================================================


def normalize_column_name(value: Any) -> str:
    text = str(value).strip().lower()
    text = text.replace("%", "_pct")
    text = text.replace("+/-", "_diff")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in NULL_STRINGS:
        return None

    return text


def normalize_token(value: Any) -> str:
    text = normalize_text(value) or ""
    return re.sub(r"\s+", " ", text.strip().lower())


def sanitize_json_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): sanitize_json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [sanitize_json_value(item) for item in value]

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


def first_present(
    row: dict[str, Any],
    aliases: Iterable[str],
) -> Any:
    for alias in aliases:
        key = normalize_column_name(alias)

        if key not in row:
            continue

        value = row[key]

        if normalize_text(value) is not None:
            return value

    return None


def get_value(row: dict[str, Any], canonical_name: str) -> Any:
    return first_present(row, ALIASES.get(canonical_name, [canonical_name]))


def parse_float(value: Any) -> float | None:
    text = normalize_text(value)

    if text is None:
        return None

    cleaned = (
        text.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("−", "-")
        .replace("–", "-")
    )

    cleaned = re.sub(r"[^0-9eE.+-]", "", cleaned)

    if cleaned in {"", "+", "-", ".", "+.", "-."}:
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


def normalize_probability(value: Any) -> float | None:
    number = parse_float(value)

    if number is None:
        return None

    if 1 < abs(number) <= 100:
        number /= 100.0

    if not 0 <= number <= 1:
        return None

    return round(number, 6)


def normalize_edge(value: Any) -> float | None:
    number = parse_float(value)

    if number is None:
        return None

    # Store edge as a percentage-point value.
    # Examples:
    #   0.074 -> 7.4
    #   7.4   -> 7.4
    if -1 <= number <= 1:
        number *= 100.0

    return round(number, 4)


def normalize_confidence(value: Any) -> float | None:
    number = parse_float(value)

    if number is None:
        return None

    if 0 <= number <= 1:
        number *= 100.0

    if not 0 <= number <= 100:
        return None

    return round(number, 2)


def normalize_american_odds(value: Any) -> int | None:
    text = normalize_text(value)

    if text is None:
        return None

    lowered = text.lower()

    if lowered in {"even", "evens", "even money"}:
        return 100

    number = parse_float(text)

    if number is None:
        return None

    # Decimal odds accidentally supplied in the odds field.
    if 1.01 <= number < 20:
        if number >= 2:
            return int(round((number - 1) * 100))

        return int(round(-100 / (number - 1)))

    odds = int(round(number))

    if -100 < odds < 100:
        return None

    return odds


def american_to_decimal(odds: int | None) -> float | None:
    if odds is None:
        return None

    if odds > 0:
        return round(1 + odds / 100, 4)

    if odds < 0:
        return round(1 + 100 / abs(odds), 4)

    return None


def american_to_implied_probability(
    odds: int | None,
) -> float | None:
    if odds is None:
        return None

    if odds > 0:
        probability = 100 / (odds + 100)
    elif odds < 0:
        probability = abs(odds) / (abs(odds) + 100)
    else:
        return None

    return round(probability, 6)


def normalize_date_string(value: Any, fallback: date) -> str:
    text = normalize_text(value)

    if text is None:
        return fallback.isoformat()

    parsed = pd.to_datetime(text, errors="coerce")

    if pd.isna(parsed):
        return fallback.isoformat()

    return parsed.date().isoformat()


def normalize_datetime_string(value: Any) -> str | None:
    text = normalize_text(value)

    if text is None:
        return None

    parsed = pd.to_datetime(text, errors="coerce")

    if pd.isna(parsed):
        return None

    if isinstance(parsed, pd.Timestamp):
        if parsed.tzinfo is None:
            parsed = parsed.tz_localize(LOCAL_TIMEZONE)
        else:
            parsed = parsed.tz_convert(LOCAL_TIMEZONE)

        return parsed.isoformat()

    return None


def normalize_team(value: Any) -> str | None:
    text = normalize_text(value)

    if text is None:
        return None

    text = re.sub(r"\s+", " ", text).strip()

    if 2 <= len(text) <= 4 and text.replace(".", "").isalpha():
        return text.replace(".", "").upper()

    return text


def split_game_teams(
    game: str | None,
) -> tuple[str | None, str | None]:
    if not game:
        return None, None

    patterns = [
        r"^\s*(.+?)\s+@\s+(.+?)\s*$",
        r"^\s*(.+?)\s+at\s+(.+?)\s*$",
        r"^\s*(.+?)\s+vs\.?\s+(.+?)\s*$",
        r"^\s*(.+?)\s+-\s+(.+?)\s*$",
    ]

    for pattern in patterns:
        match = re.match(pattern, game, flags=re.IGNORECASE)

        if not match:
            continue

        first = normalize_team(match.group(1))
        second = normalize_team(match.group(2))

        return first, second

    return None, None


def infer_game(
    game: str | None,
    away_team: str | None,
    home_team: str | None,
) -> str | None:
    if game:
        return game

    if away_team and home_team:
        return f"{away_team} @ {home_team}"

    return None


def slugify(value: Any) -> str:
    text = normalize_text(value) or ""
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    return text.strip("-")


def build_event_id(
    league: str,
    run_date: str,
    game: str | None,
    away_team: str | None,
    home_team: str | None,
    supplied_event_id: str | None,
) -> str | None:
    if supplied_event_id:
        return supplied_event_id

    game_slug = slugify(game)

    if game_slug:
        return f"{league}-{run_date}-{game_slug}"

    if away_team or home_team:
        return (
            f"{league}-{run_date}-"
            f"{slugify(away_team)}-AT-{slugify(home_team)}"
        )

    return None


def build_recommendation_id(
    run_date: str,
    league: str,
    source_family: str,
    market: str | None,
    selection: str | None,
    game: str | None,
    sportsbook: str | None,
) -> str:
    components = [
        run_date,
        league,
        source_family,
        market or "UNKNOWN-MARKET",
        selection or "UNKNOWN-SELECTION",
        game or "UNKNOWN-GAME",
        sportsbook or "NO-BOOK",
    ]

    human_slug = "-".join(
        filter(
            None,
            [
                slugify(run_date),
                slugify(league),
                slugify(source_family),
                slugify(market),
                slugify(selection),
            ],
        )
    )

    digest = hashlib.sha1(
        "|".join(components).encode("utf-8")
    ).hexdigest()[:10].upper()

    return f"{human_slug}-{digest}"


def dedupe_tags(tags: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for tag in tags:
        normalized = slugify(tag).lower().replace("-", "_")

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        output.append(normalized)

    return output


def normalized_row(row: pd.Series) -> dict[str, Any]:
    output: dict[str, Any] = {}

    for column, value in row.items():
        output[normalize_column_name(column)] = value

    return output


# =============================================================================
# FILE DISCOVERY AND READING
# =============================================================================


def should_skip_file(path: Path) -> bool:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return True

    if path.name.lower() in EXCLUDED_FILENAMES:
        return True

    lowered_parts = {part.lower() for part in path.parts}

    if lowered_parts.intersection(EXCLUDED_DIRECTORIES):
        return True

    return False


def discover_input_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []

    files = [
        path
        for path in input_dir.rglob("*")
        if path.is_file() and not should_skip_file(path)
    ]

    return sorted(files, key=lambda item: str(item).lower())


def read_json_file(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return pd.json_normalize(payload)

    if isinstance(payload, dict):
        for key in (
            "recommendations",
            "records",
            "data",
            "picks",
            "results",
            "rows",
        ):
            value = payload.get(key)

            if isinstance(value, list):
                return pd.json_normalize(value)

        return pd.json_normalize([payload])

    return pd.DataFrame()


def read_source_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        attempts = [
            {"encoding": "utf-8-sig"},
            {"encoding": "utf-8"},
            {"encoding": "latin-1"},
        ]

        last_error: Exception | None = None

        for kwargs in attempts:
            try:
                return pd.read_csv(
                    path,
                    low_memory=False,
                    **kwargs,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if last_error:
            raise last_error

    if path.suffix.lower() == ".json":
        return read_json_file(path)

    return pd.DataFrame()


# =============================================================================
# SOURCE IDENTIFICATION
# =============================================================================


def identify_source_family(
    path: Path,
    columns: Iterable[Any],
) -> str | None:
    searchable_path = normalize_column_name(
        " ".join(path.parts[-4:])
    )

    normalized_columns = {
        normalize_column_name(column)
        for column in columns
    }

    # Filename/path recognition gets first priority.
    for family, patterns in SOURCE_PATTERNS:
        for pattern in patterns:
            if normalize_column_name(pattern) in searchable_path:
                return family

    # Column-signature fallback.
    if {
        "result",
        "outcome",
        "profit_units",
    }.intersection(normalized_columns) and {
        "pick",
        "selection",
        "bet",
        "recommendation",
    }.intersection(normalized_columns):
        return "recommendation_tracker"

    if {
        "bomb_score",
        "hr_score",
        "hr_match_score",
    }.intersection(normalized_columns):
        return "bomb_lab"

    if {
        "market_edge",
        "market_probability",
        "implied_probability",
    }.intersection(normalized_columns) and {
        "first5",
        "f5",
        "first_5",
    }.intersection(normalized_columns):
        return "first5_market_edge"

    if {
        "starter_score",
        "f5_score",
        "first5_score",
    }.intersection(normalized_columns):
        return "first5_lab"

    if {
        "model_win_pct",
        "model_win_probability",
        "kbo",
    }.intersection(normalized_columns):
        return "kbo"

    if {
        "stack_rank",
        "attack_score",
        "power_score",
        "hr_score",
        "hitter",
        "batter",
    }.intersection(normalized_columns):
        return "mlb_signal"

    return None


# =============================================================================
# SOURCE-SPECIFIC DEFAULTS
# =============================================================================


def source_defaults(
    source_family: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    explicit_market = normalize_text(get_value(row, "market"))
    explicit_model = normalize_text(get_value(row, "model"))

    defaults: dict[str, Any] = {
        "sport": "baseball",
        "league": "MLB",
        "market": explicit_market,
        "market_scope": None,
        "model_name": explicit_model,
        "record_type": "signal",
    }

    if source_family == "recommendation_tracker":
        defaults.update(
            {
                "model_name": explicit_model or "Recommendation Tracker",
                "record_type": "recommendation",
            }
        )

    elif source_family == "bomb_lab":
        defaults.update(
            {
                "model_name": explicit_model or "Bomb Lab",
                "market": explicit_market or "player_home_run",
                "market_scope": "full_game",
                "record_type": "recommendation",
            }
        )

    elif source_family == "first5_market_edge":
        defaults.update(
            {
                "model_name": explicit_model or "First 5 Market Edge",
                "market_scope": "first_5_innings",
                "record_type": "recommendation",
            }
        )

    elif source_family == "first5_lab":
        defaults.update(
            {
                "model_name": explicit_model or "First 5 Lab",
                "market_scope": "first_5_innings",
                "record_type": "recommendation",
            }
        )

    elif source_family == "kbo":
        defaults.update(
            {
                "league": "KBO",
                "model_name": explicit_model or "KBO Model",
                "market": explicit_market or "moneyline",
                "market_scope": "full_game",
                "record_type": "recommendation",
            }
        )

    elif source_family == "mlb_signal":
        has_player = normalize_text(get_value(row, "player")) is not None
        has_team = normalize_text(get_value(row, "team")) is not None

        inferred_market = explicit_market

        if not inferred_market and has_player:
            inferred_market = "player_home_run_signal"
        elif not inferred_market and has_team:
            inferred_market = "team_stack_signal"

        defaults.update(
            {
                "model_name": explicit_model or "MLB Model",
                "market": inferred_market,
                "market_scope": "full_game",
                "record_type": "signal",
            }
        )

    return defaults


def infer_market(
    source_family: str,
    row: dict[str, Any],
    default_market: str | None,
) -> str | None:
    market = normalize_text(get_value(row, "market"))

    if market:
        token = normalize_token(market)

        replacements = {
            "ml": "moneyline",
            "money line": "moneyline",
            "f5 ml": "first_5_moneyline",
            "first 5 ml": "first_5_moneyline",
            "first five ml": "first_5_moneyline",
            "f5 moneyline": "first_5_moneyline",
            "first 5 moneyline": "first_5_moneyline",
            "first five moneyline": "first_5_moneyline",
            "f5 total": "first_5_total",
            "first 5 total": "first_5_total",
            "first five total": "first_5_total",
            "hr": "player_home_run",
            "home run": "player_home_run",
            "homer": "player_home_run",
        }

        return replacements.get(token, slugify(token).lower().replace("-", "_"))

    selection = normalize_token(get_value(row, "selection"))

    if source_family in {"first5_lab", "first5_market_edge"}:
        if "over" in selection or "under" in selection:
            return "first_5_total"

        if "run line" in selection or "-0.5" in selection or "+0.5" in selection:
            return "first_5_run_line"

        return default_market or "first_5_moneyline"

    return default_market


def infer_selection(
    source_family: str,
    row: dict[str, Any],
    team: str | None,
    player: str | None,
    market: str | None,
) -> str | None:
    explicit_selection = normalize_text(get_value(row, "selection"))

    if explicit_selection:
        return explicit_selection

    if source_family == "bomb_lab":
        return player

    if source_family == "mlb_signal":
        return player or team

    if market and market.startswith("player_"):
        return player

    return team or player


def infer_selection_side(
    row: dict[str, Any],
    selection: str | None,
) -> str | None:
    explicit_side = normalize_text(get_value(row, "side"))

    if explicit_side:
        return explicit_side.lower()

    token = normalize_token(selection)

    for side in ("over", "under"):
        if re.search(rf"\b{side}\b", token):
            return side

    if "moneyline" in token or token.endswith(" ml"):
        return "moneyline"

    return None


def normalize_recommendation_label(value: Any) -> str | None:
    text = normalize_text(value)

    if text is None:
        return None

    token = normalize_token(text)

    if token in NEGATIVE_RECOMMENDATION_WORDS:
        return "NO PLAY"

    if token in POSITIVE_RECOMMENDATION_WORDS:
        if token == "lean":
            return "LEAN"

        return "BET"

    if "no play" in token or "no bet" in token:
        return "NO PLAY"

    if "strong" in token and (
        "bet" in token or "play" in token
    ):
        return "STRONG BET"

    if "lean" in token:
        return "LEAN"

    if "bet" in token or "play" in token or "recommend" in token:
        return "BET"

    return text.upper()


def normalize_outcome(value: Any) -> str | None:
    text = normalize_text(value)

    if text is None:
        return None

    token = normalize_token(text)

    mappings = {
        "w": "WIN",
        "win": "WIN",
        "won": "WIN",
        "l": "LOSS",
        "loss": "LOSS",
        "lost": "LOSS",
        "p": "PUSH",
        "push": "PUSH",
        "void": "VOID",
        "cancelled": "VOID",
        "canceled": "VOID",
        "pending": "PENDING",
    }

    return mappings.get(token, text.upper())


def infer_record_type(
    source_family: str,
    row: dict[str, Any],
    default_type: str,
    recommendation: str | None,
    odds: int | None,
    selection: str | None,
) -> str:
    explicit = normalize_token(get_value(row, "record_type"))

    if explicit in {"recommendation", "signal"}:
        return explicit

    if source_family == "mlb_signal":
        # Upgrade an MLB signal only when the source clearly labels it as a
        # recommendation or supplies a directly bettable price.
        if recommendation and recommendation not in {"NO PLAY", "PASS"}:
            return "recommendation"

        if odds is not None and selection:
            return "recommendation"

        return "signal"

    if recommendation in {"NO PLAY", "PASS"}:
        # Keep no-play rows as signals. They remain available for analysis but
        # will not pollute the formal recommendation list.
        return "signal"

    return default_type


# =============================================================================
# ROW ADAPTER
# =============================================================================


def collect_supporting_signals(
    row: dict[str, Any],
) -> dict[str, Any]:
    signals: dict[str, Any] = {}

    for output_name, aliases in SIGNAL_ALIASES.items():
        value = first_present(row, aliases)
        text = normalize_text(value)

        if text is None:
            continue

        number = parse_float(value)

        if number is not None:
            signals[output_name] = number
        else:
            signals[output_name] = text

    return signals


def build_tags(
    source_family: str,
    row: dict[str, Any],
    market: str | None,
    recommendation: str | None,
    odds: int | None,
    confidence: float | None,
    edge: float | None,
    rank: int | None,
    signals: dict[str, Any],
) -> list[str]:
    tags: list[str] = [source_family]

    if market:
        tags.append(market)

    if recommendation:
        tags.append(recommendation)

    if odds is not None:
        tags.append("plus_money" if odds > 0 else "favorite")

        if odds >= 350:
            tags.append("longshot")

    if confidence is not None:
        if confidence >= 85:
            tags.append("elite_confidence")
        elif confidence >= 75:
            tags.append("high_confidence")

    if edge is not None:
        if edge >= 10:
            tags.append("double_digit_edge")
        elif edge >= 5:
            tags.append("positive_edge")

    if rank is not None:
        if rank == 1:
            tags.append("top_ranked")
        elif rank <= 3:
            tags.append("top_three")
        elif rank <= 10:
            tags.append("top_ten")

    for signal_name in signals:
        if signal_name in {
            "barrel_rate",
            "hard_hit_rate",
            "weather_score",
            "park_factor",
            "starter_edge",
            "stack_score",
            "attack_score",
        }:
            tags.append(signal_name)

    # Optional preexisting tags from source.
    raw_tags = first_present(row, ["tags", "tag", "labels"])

    if raw_tags is not None:
        if isinstance(raw_tags, list):
            tags.extend(str(item) for item in raw_tags)
        else:
            tags.extend(
                item
                for item in re.split(r"[,;|]", str(raw_tags))
                if item.strip()
            )

    return dedupe_tags(tags)


def row_has_meaningful_content(
    selection: str | None,
    game: str | None,
    market: str | None,
    recommendation: str | None,
    signals: dict[str, Any],
) -> bool:
    return any(
        [
            selection,
            game,
            market,
            recommendation,
            bool(signals),
        ]
    )


def adapt_row(
    source_family: str,
    path: Path,
    row_number: int,
    row: dict[str, Any],
    build_date: date,
    build_timestamp: datetime,
) -> ExplorerRecord | None:
    defaults = source_defaults(source_family, row)

    run_date = normalize_date_string(
        get_value(row, "date"),
        fallback=build_date,
    )

    created_at = (
        normalize_datetime_string(get_value(row, "created_at"))
        or build_timestamp.isoformat()
    )

    sport = (
        normalize_text(get_value(row, "sport"))
        or defaults["sport"]
    )

    league = (
        normalize_text(get_value(row, "league"))
        or defaults["league"]
    ).upper()

    game = normalize_text(get_value(row, "game"))

    away_team = normalize_team(get_value(row, "away_team"))
    home_team = normalize_team(get_value(row, "home_team"))

    parsed_away, parsed_home = split_game_teams(game)

    away_team = away_team or parsed_away
    home_team = home_team or parsed_home

    game = infer_game(game, away_team, home_team)

    team = normalize_team(get_value(row, "team"))
    opponent = normalize_team(get_value(row, "opponent"))

    player = normalize_text(get_value(row, "player"))
    pitcher = normalize_text(get_value(row, "pitcher"))

    market = infer_market(
        source_family,
        row,
        defaults["market"],
    )

    market_scope = (
        normalize_text(get_value(row, "market_scope"))
        or defaults["market_scope"]
    )

    selection = infer_selection(
        source_family,
        row,
        team=team,
        player=player,
        market=market,
    )

    selection_side = infer_selection_side(row, selection)

    sportsbook = normalize_text(get_value(row, "sportsbook"))

    odds = normalize_american_odds(get_value(row, "odds"))
    decimal_odds = american_to_decimal(odds)

    market_probability = normalize_probability(
        get_value(row, "market_probability")
    )

    if market_probability is None:
        market_probability = american_to_implied_probability(odds)

    model_probability = normalize_probability(
        get_value(row, "model_probability")
    )

    edge = normalize_edge(get_value(row, "edge"))

    if (
        edge is None
        and model_probability is not None
        and market_probability is not None
    ):
        edge = round(
            (model_probability - market_probability) * 100,
            4,
        )

    confidence = normalize_confidence(
        get_value(row, "confidence")
    )

    recommendation = normalize_recommendation_label(
        get_value(row, "recommendation")
    )

    rank = parse_int(get_value(row, "rank"))

    outcome = normalize_outcome(get_value(row, "result"))
    profit_units = parse_float(get_value(row, "profit_units"))

    notes = normalize_text(get_value(row, "notes"))

    model_name = (
        normalize_text(get_value(row, "model"))
        or defaults["model_name"]
    )

    model_version = normalize_text(
        get_value(row, "model_version")
    )

    signals = collect_supporting_signals(row)

    record_type = infer_record_type(
        source_family=source_family,
        row=row,
        default_type=defaults["record_type"],
        recommendation=recommendation,
        odds=odds,
        selection=selection,
    )

    if not row_has_meaningful_content(
        selection=selection,
        game=game,
        market=market,
        recommendation=recommendation,
        signals=signals,
    ):
        return None

    event_time = normalize_datetime_string(
        get_value(row, "event_time")
    )

    supplied_event_id = normalize_text(
        get_value(row, "event_id")
    )

    event_id = build_event_id(
        league=league,
        run_date=run_date,
        game=game,
        away_team=away_team,
        home_team=home_team,
        supplied_event_id=supplied_event_id,
    )

    tags = build_tags(
        source_family=source_family,
        row=row,
        market=market,
        recommendation=recommendation,
        odds=odds,
        confidence=confidence,
        edge=edge,
        rank=rank,
        signals=signals,
    )

    recommendation_id = build_recommendation_id(
        run_date=run_date,
        league=league,
        source_family=source_family,
        market=market,
        selection=selection,
        game=game,
        sportsbook=sportsbook,
    )

    return ExplorerRecord(
        recommendation_id=recommendation_id,
        run_date=run_date,
        created_at=created_at,
        record_type=record_type,
        sport=sport.lower(),
        league=league,
        event_id=event_id,
        event_time=event_time,
        game=game,
        away_team=away_team,
        home_team=home_team,
        market=market,
        market_scope=market_scope,
        selection=selection,
        selection_side=selection_side,
        opponent=opponent,
        pitcher=pitcher,
        sportsbook=sportsbook,
        american_odds=odds,
        decimal_odds=decimal_odds,
        market_probability=market_probability,
        model_probability=model_probability,
        edge=edge,
        confidence_score=confidence,
        model_name=model_name,
        model_version=model_version,
        recommendation=recommendation,
        rank=rank,
        outcome=outcome,
        profit_units=profit_units,
        tags=tags,
        notes=notes,
        supporting_signals=signals,
        source_family=source_family,
        source_file=str(path.relative_to(ROOT)),
        source_row=row_number,
    )


# =============================================================================
# DEDUPLICATION
# =============================================================================


def completeness_score(record: ExplorerRecord) -> float:
    score = 0.0

    important_fields = {
        "selection": 3,
        "market": 3,
        "game": 2,
        "american_odds": 3,
        "model_probability": 2,
        "market_probability": 2,
        "edge": 2,
        "confidence_score": 2,
        "recommendation": 2,
        "event_time": 1,
        "sportsbook": 1,
        "outcome": 1,
        "profit_units": 1,
        "notes": 1,
    }

    for field_name, weight in important_fields.items():
        if getattr(record, field_name) is not None:
            score += weight

    score += min(len(record.supporting_signals), 8) * 0.25
    score += min(len(record.tags), 8) * 0.10

    return score


def dedupe_key(record: ExplorerRecord) -> tuple[Any, ...]:
    return (
        record.run_date,
        record.league,
        normalize_token(record.market),
        normalize_token(record.selection),
        normalize_token(record.game),
        record.american_odds,
        normalize_token(record.sportsbook),
        record.record_type,
    )


def merge_records(
    preferred: ExplorerRecord,
    other: ExplorerRecord,
) -> ExplorerRecord:
    preferred_score = completeness_score(preferred)
    other_score = completeness_score(other)

    if other_score > preferred_score:
        preferred, other = other, preferred

    preferred.tags = dedupe_tags(
        [*preferred.tags, *other.tags]
    )

    preferred.supporting_signals = {
        **other.supporting_signals,
        **preferred.supporting_signals,
    }

    optional_fields = [
        "event_id",
        "event_time",
        "game",
        "away_team",
        "home_team",
        "market",
        "market_scope",
        "selection",
        "selection_side",
        "opponent",
        "pitcher",
        "sportsbook",
        "american_odds",
        "decimal_odds",
        "market_probability",
        "model_probability",
        "edge",
        "confidence_score",
        "model_name",
        "model_version",
        "recommendation",
        "rank",
        "outcome",
        "profit_units",
        "notes",
    ]

    for field_name in optional_fields:
        if (
            getattr(preferred, field_name) is None
            and getattr(other, field_name) is not None
        ):
            setattr(
                preferred,
                field_name,
                getattr(other, field_name),
            )

    return preferred


def deduplicate_records(
    records: list[ExplorerRecord],
) -> list[ExplorerRecord]:
    by_key: dict[tuple[Any, ...], ExplorerRecord] = {}

    for record in records:
        key = dedupe_key(record)

        if key not in by_key:
            by_key[key] = record
            continue

        by_key[key] = merge_records(by_key[key], record)

    return list(by_key.values())


# =============================================================================
# SORTING AND FILTERING
# =============================================================================


def recommendation_sort_key(
    record: ExplorerRecord,
) -> tuple[Any, ...]:
    recommendation_priority = {
        "STRONG BET": 0,
        "BET": 1,
        "LEAN": 2,
        "NO PLAY": 9,
        None: 5,
    }

    return (
        recommendation_priority.get(record.recommendation, 4),
        record.rank if record.rank is not None else 9999,
        -(
            record.confidence_score
            if record.confidence_score is not None
            else -9999
        ),
        -(record.edge if record.edge is not None else -9999),
        record.league,
        record.game or "",
        record.selection or "",
    )


def signal_sort_key(record: ExplorerRecord) -> tuple[Any, ...]:
    return (
        record.rank if record.rank is not None else 9999,
        -(
            record.confidence_score
            if record.confidence_score is not None
            else -9999
        ),
        -(record.edge if record.edge is not None else -9999),
        record.league,
        record.market or "",
        record.selection or "",
    )


def apply_filters(
    records: list[ExplorerRecord],
    target_date: str | None,
    league: str | None,
    minimum_confidence: float | None,
    minimum_edge: float | None,
) -> list[ExplorerRecord]:
    output: list[ExplorerRecord] = []

    for record in records:
        if target_date and record.run_date != target_date:
            continue

        if league and record.league.upper() != league.upper():
            continue

        if minimum_confidence is not None:
            if record.confidence_score is None:
                continue

            if record.confidence_score < minimum_confidence:
                continue

        if minimum_edge is not None:
            if record.edge is None:
                continue

            if record.edge < minimum_edge:
                continue

        output.append(record)

    return output


# =============================================================================
# OUTPUT WRITERS
# =============================================================================


def record_to_json_dict(record: ExplorerRecord) -> dict[str, Any]:
    return sanitize_json_value(asdict(record))


def record_to_csv_dict(record: ExplorerRecord) -> dict[str, Any]:
    payload = record_to_json_dict(record)

    payload["tags"] = "|".join(record.tags)
    payload["supporting_signals"] = json.dumps(
        sanitize_json_value(record.supporting_signals),
        ensure_ascii=False,
        sort_keys=True,
    )

    return payload


def write_json_records(
    path: Path,
    records: list[ExplorerRecord],
) -> None:
    payload = [record_to_json_dict(record) for record in records]

    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
        )


def write_csv_records(
    path: Path,
    records: list[ExplorerRecord],
) -> None:
    payload = [record_to_csv_dict(record) for record in records]
    frame = pd.DataFrame(payload)

    if frame.empty:
        frame = pd.DataFrame(
            columns=list(ExplorerRecord.__dataclass_fields__.keys())
        )

    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_inventory(
    path: Path,
    inventory: list[SourceInventory],
) -> None:
    frame = pd.DataFrame(
        [sanitize_json_value(asdict(item)) for item in inventory]
    )

    if frame.empty:
        frame = pd.DataFrame(
            columns=list(SourceInventory.__dataclass_fields__.keys())
        )

    frame.to_csv(path, index=False, encoding="utf-8-sig")


# =============================================================================
# CONSOLE / TEXT EXPLORER
# =============================================================================


def display_value(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback

    return str(value)


def format_odds(odds: int | None) -> str:
    if odds is None:
        return "—"

    if odds > 0:
        return f"+{odds}"

    return str(odds)


def format_percentage(
    value: float | None,
    decimals: int = 1,
) -> str:
    if value is None:
        return "—"

    return f"{value:.{decimals}f}"


def format_probability(value: float | None) -> str:
    if value is None:
        return "—"

    return f"{value * 100:.1f}%"


def truncate(value: Any, length: int) -> str:
    text = display_value(value)

    if len(text) <= length:
        return text

    return text[: max(length - 1, 1)] + "…"


def build_table(
    headers: list[str],
    rows: list[list[Any]],
    widths: list[int],
) -> list[str]:
    header_line = "  ".join(
        truncate(header, width).ljust(width)
        for header, width in zip(headers, widths)
    )

    separator = "  ".join("-" * width for width in widths)

    output = [header_line, separator]

    for row in rows:
        output.append(
            "  ".join(
                truncate(value, width).ljust(width)
                for value, width in zip(row, widths)
            )
        )

    return output


def consensus_groups(
    records: list[ExplorerRecord],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[ExplorerRecord]] = defaultdict(list)

    for record in records:
        if record.record_type != "recommendation":
            continue

        game_key = normalize_token(record.game or record.event_id)
        selection_key = normalize_token(record.selection)

        if not selection_key:
            continue

        grouped[(game_key, selection_key)].append(record)

    output: list[dict[str, Any]] = []

    for (_, _), group in grouped.items():
        model_names = sorted(
            {
                record.model_name or record.source_family or "Unknown"
                for record in group
            }
        )

        if len(model_names) < 2:
            continue

        confidences = [
            record.confidence_score
            for record in group
            if record.confidence_score is not None
        ]

        edges = [
            record.edge
            for record in group
            if record.edge is not None
        ]

        output.append(
            {
                "game": group[0].game,
                "selection": group[0].selection,
                "models": model_names,
                "model_count": len(model_names),
                "average_confidence": (
                    sum(confidences) / len(confidences)
                    if confidences
                    else None
                ),
                "average_edge": (
                    sum(edges) / len(edges)
                    if edges
                    else None
                ),
            }
        )

    return sorted(
        output,
        key=lambda item: (
            -item["model_count"],
            -(
                item["average_confidence"]
                if item["average_confidence"] is not None
                else -9999
            ),
        ),
    )


def build_report(
    build_timestamp: datetime,
    files_found: int,
    inventory: list[SourceInventory],
    recommendations: list[ExplorerRecord],
    signals: list[ExplorerRecord],
) -> str:
    lines: list[str] = []

    lines.extend(
        [
            "=" * 92,
            "CHEEK SPLITTERS — RECOMMENDATION EXPLORER",
            "=" * 92,
            f"Built: {build_timestamp.strftime('%Y-%m-%d %I:%M:%S %p %Z')}",
            f"Files scanned: {files_found}",
            f"Recommendations: {len(recommendations)}",
            f"Supporting signals: {len(signals)}",
            "",
        ]
    )

    successful_sources = [
        item
        for item in inventory
        if item.status == "loaded"
    ]

    family_counts = Counter(
        item.source_family
        for item in successful_sources
    )

    lines.append("SOURCE COVERAGE")
    lines.append("-" * 92)

    if family_counts:
        for family, count in sorted(family_counts.items()):
            rows = sum(
                item.output_records
                for item in successful_sources
                if item.source_family == family
            )

            lines.append(
                f"{family:<28} files={count:<3} records={rows}"
            )
    else:
        lines.append("No recognized source files were loaded.")

    errors = [
        item
        for item in inventory
        if item.status == "error"
    ]

    if errors:
        lines.extend(["", "SOURCE ERRORS", "-" * 92])

        for item in errors:
            lines.append(
                f"{item.source_file}: {item.error}"
            )

    lines.extend(["", "TOP RECOMMENDATIONS", "-" * 92])

    recommendation_rows: list[list[Any]] = []

    for index, record in enumerate(recommendations[:25], start=1):
        recommendation_rows.append(
            [
                index,
                record.league,
                record.model_name,
                record.game,
                record.selection,
                record.market,
                format_odds(record.american_odds),
                format_percentage(record.confidence_score),
                format_percentage(record.edge),
                record.recommendation,
            ]
        )

    if recommendation_rows:
        lines.extend(
            build_table(
                headers=[
                    "#",
                    "LG",
                    "MODEL",
                    "GAME",
                    "SELECTION",
                    "MARKET",
                    "ODDS",
                    "CONF",
                    "EDGE",
                    "REC",
                ],
                rows=recommendation_rows,
                widths=[3, 4, 18, 18, 21, 18, 7, 6, 6, 10],
            )
        )
    else:
        lines.append("No formal recommendations found.")

    plus_money = [
        record
        for record in recommendations
        if record.american_odds is not None
        and record.american_odds > 0
    ]

    lines.extend(["", "PLUS-MONEY BOARD", "-" * 92])

    plus_rows: list[list[Any]] = []

    for index, record in enumerate(plus_money[:15], start=1):
        plus_rows.append(
            [
                index,
                record.model_name,
                record.game,
                record.selection,
                format_odds(record.american_odds),
                format_percentage(record.confidence_score),
                format_percentage(record.edge),
            ]
        )

    if plus_rows:
        lines.extend(
            build_table(
                headers=[
                    "#",
                    "MODEL",
                    "GAME",
                    "SELECTION",
                    "ODDS",
                    "CONF",
                    "EDGE",
                ],
                rows=plus_rows,
                widths=[3, 18, 20, 24, 7, 7, 7],
            )
        )
    else:
        lines.append("No plus-money recommendations found.")

    consensus = consensus_groups(recommendations)

    lines.extend(["", "CONSENSUS WATCH", "-" * 92])

    if consensus:
        consensus_rows: list[list[Any]] = []

        for index, item in enumerate(consensus[:15], start=1):
            consensus_rows.append(
                [
                    index,
                    item["game"],
                    item["selection"],
                    item["model_count"],
                    ", ".join(item["models"]),
                    format_percentage(item["average_confidence"]),
                    format_percentage(item["average_edge"]),
                ]
            )

        lines.extend(
            build_table(
                headers=[
                    "#",
                    "GAME",
                    "SELECTION",
                    "N",
                    "MODELS",
                    "AVG CONF",
                    "AVG EDGE",
                ],
                rows=consensus_rows,
                widths=[3, 20, 23, 3, 35, 8, 8],
            )
        )
    else:
        lines.append(
            "No same-selection multi-model consensus found yet."
        )

    lines.extend(["", "TOP SUPPORTING SIGNALS", "-" * 92])

    signal_rows: list[list[Any]] = []

    for index, record in enumerate(signals[:20], start=1):
        top_signals = ", ".join(
            f"{key}={value}"
            for key, value in list(
                record.supporting_signals.items()
            )[:3]
        )

        signal_rows.append(
            [
                index,
                record.league,
                record.model_name,
                record.game,
                record.selection,
                record.market,
                record.rank,
                top_signals,
            ]
        )

    if signal_rows:
        lines.extend(
            build_table(
                headers=[
                    "#",
                    "LG",
                    "MODEL",
                    "GAME",
                    "TARGET",
                    "SIGNAL",
                    "RANK",
                    "DETAILS",
                ],
                rows=signal_rows,
                widths=[3, 4, 18, 18, 22, 20, 5, 38],
            )
        )
    else:
        lines.append("No supporting signals found.")

    lines.extend(
        [
            "",
            "=" * 92,
            "OUTPUT FILES",
            "=" * 92,
            str(EXPLORER_DIR.relative_to(ROOT)),
            "",
        ]
    )

    return "\n".join(lines)


# =============================================================================
# BUILD PROCESS
# =============================================================================


def process_source_file(
    path: Path,
    build_date: date,
    build_timestamp: datetime,
) -> tuple[list[ExplorerRecord], SourceInventory]:
    try:
        frame = read_source_file(path)
    except Exception as exc:  # noqa: BLE001
        return [], SourceInventory(
            source_file=str(path.relative_to(ROOT)),
            source_family="unknown",
            status="error",
            input_rows=0,
            output_records=0,
            recommendations=0,
            signals=0,
            skipped_rows=0,
            error=str(exc),
        )

    source_family = identify_source_family(path, frame.columns)

    if source_family is None:
        return [], SourceInventory(
            source_file=str(path.relative_to(ROOT)),
            source_family="unrecognized",
            status="ignored",
            input_rows=len(frame),
            output_records=0,
            recommendations=0,
            signals=0,
            skipped_rows=len(frame),
        )

    records: list[ExplorerRecord] = []
    skipped_rows = 0

    for row_index, (_, series) in enumerate(
        frame.iterrows(),
        start=2,
    ):
        row = normalized_row(series)

        try:
            record = adapt_row(
                source_family=source_family,
                path=path,
                row_number=row_index,
                row=row,
                build_date=build_date,
                build_timestamp=build_timestamp,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"[WARN] {path.name} row {row_index}: {exc}",
                file=sys.stderr,
            )
            skipped_rows += 1
            continue

        if record is None:
            skipped_rows += 1
            continue

        records.append(record)

    recommendation_count = sum(
        record.record_type == "recommendation"
        for record in records
    )

    signal_count = sum(
        record.record_type == "signal"
        for record in records
    )

    inventory = SourceInventory(
        source_file=str(path.relative_to(ROOT)),
        source_family=source_family,
        status="loaded",
        input_rows=len(frame),
        output_records=len(records),
        recommendations=recommendation_count,
        signals=signal_count,
        skipped_rows=skipped_rows,
    )

    return records, inventory


def build_explorer(
    input_dir: Path,
    output_dir: Path,
    target_date: str | None = None,
    league: str | None = None,
    minimum_confidence: float | None = None,
    minimum_edge: float | None = None,
    verbose: bool = False,
) -> int:
    build_timestamp = datetime.now(LOCAL_TIMEZONE)
    build_date = build_timestamp.date()

    output_dir.mkdir(parents=True, exist_ok=True)

    input_files = discover_input_files(input_dir)

    print("=" * 78)
    print("CHEEK SPLITTERS — BUILD RECOMMENDATION EXPLORER")
    print("=" * 78)
    print(f"Input directory : {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Files discovered: {len(input_files)}")
    print()

    all_records: list[ExplorerRecord] = []
    inventory: list[SourceInventory] = []

    for path in input_files:
        records, source_result = process_source_file(
            path=path,
            build_date=build_date,
            build_timestamp=build_timestamp,
        )

        inventory.append(source_result)
        all_records.extend(records)

        if verbose or source_result.status in {"loaded", "error"}:
            print(
                f"[{source_result.status.upper():7}] "
                f"{source_result.source_family:<24} "
                f"rows={source_result.input_rows:<5} "
                f"records={source_result.output_records:<5} "
                f"{source_result.source_file}"
            )

    before_dedupe = len(all_records)
    all_records = deduplicate_records(all_records)
    duplicates_removed = before_dedupe - len(all_records)

    all_records = apply_filters(
        records=all_records,
        target_date=target_date,
        league=league,
        minimum_confidence=minimum_confidence,
        minimum_edge=minimum_edge,
    )

    recommendations = sorted(
        [
            record
            for record in all_records
            if record.record_type == "recommendation"
            and record.recommendation not in {"NO PLAY", "PASS"}
        ],
        key=recommendation_sort_key,
    )

    signals = sorted(
        [
            record
            for record in all_records
            if record.record_type == "signal"
            or record.recommendation in {"NO PLAY", "PASS"}
        ],
        key=signal_sort_key,
    )

    sorted_all_records = [
        *recommendations,
        *signals,
    ]

    write_json_records(
        output_dir / "recommendations_today.json",
        recommendations,
    )
    write_csv_records(
        output_dir / "recommendations_today.csv",
        recommendations,
    )

    write_json_records(
        output_dir / "signals_today.json",
        signals,
    )
    write_csv_records(
        output_dir / "signals_today.csv",
        signals,
    )

    write_json_records(
        output_dir / "all_records_today.json",
        sorted_all_records,
    )
    write_csv_records(
        output_dir / "all_records_today.csv",
        sorted_all_records,
    )

    write_inventory(
        output_dir / "source_inventory.csv",
        inventory,
    )

    report = build_report(
        build_timestamp=build_timestamp,
        files_found=len(input_files),
        inventory=inventory,
        recommendations=recommendations,
        signals=signals,
    )

    report_path = output_dir / "recommendation_explorer.txt"
    report_path.write_text(report, encoding="utf-8")

    print()
    print(report)
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Explorer report: {report_path}")
    print()

    loaded_files = sum(
        item.status == "loaded"
        for item in inventory
    )

    if loaded_files == 0:
        print(
            "[WARN] No recognized model files were loaded. "
            "Review source_inventory.csv and filename patterns."
        )

        return 1

    return 0


# =============================================================================
# COMMAND-LINE INTERFACE
# =============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Combine Cheek Splitters model outputs into a normalized "
            "Recommendation Explorer dataset."
        )
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory recursively scanned for CSV and JSON files.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXPLORER_DIR,
        help="Directory where Explorer outputs are written.",
    )

    parser.add_argument(
        "--date",
        dest="target_date",
        help="Only include records matching YYYY-MM-DD.",
    )

    parser.add_argument(
        "--league",
        help="Only include one league, such as MLB or KBO.",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        help="Only include records at or above this confidence score.",
    )

    parser.add_argument(
        "--min-edge",
        type=float,
        help="Only include records at or above this percentage-point edge.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print ignored and unrecognized files during the build.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    return build_explorer(
        input_dir=args.input_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        target_date=args.target_date,
        league=args.league,
        minimum_confidence=args.min_confidence,
        minimum_edge=args.min_edge,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
