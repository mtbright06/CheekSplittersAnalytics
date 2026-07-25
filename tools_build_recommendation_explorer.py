from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"
OUTPUT_DIR = ROOT / "output" / "recommendations"
HISTORY_DIR = OUTPUT_DIR / "history"

MLB_CARD = CARDS_DIR / "mlb_card.json"
KBO_CARD = CARDS_DIR / "kbo_card.json"

JSON_OUTPUT = OUTPUT_DIR / "recommendations_today.json"
CSV_OUTPUT = OUTPUT_DIR / "recommendations_today.csv"
PERSISTENCE_OUTPUT = OUTPUT_DIR / "recommendation_run_payload.json"

MODEL_NAME = "sharpstack"
MODEL_VERSION = "0.1.0"

CSV_FIELDS = [
    "rank",
    "run_key",
    "sport",
    "game_id",
    "game",
    "away_team",
    "home_team",
    "market",
    "selection",
    "market_line",
    "recommendation",
    "confidence",
    "projection",
    "edge",
    "expected_roi",
    "model_probability",
    "book_probability",
    "odds",
    "sportsbook",
    "away_starting_pitcher",
    "away_pitcher_id",
    "home_starting_pitcher",
    "home_pitcher_id",
    "start_time",
    "status",
    "source",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_run_key(now: datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"WARNING: Card file not found: {path}")
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object in {path}, "
            f"found {type(data).__name__}."
        )

    return data


def to_float(value: Any, digits: int = 2) -> float | None:
    if value is None or value == "":
        return None

    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    number = to_float(value)

    if number is None:
        return None

    return int(round(number))


def normalize_probability(value: Any) -> float | None:
    number = to_float(value, 4)

    if number is None:
        return None

    if number > 1:
        number /= 100.0

    return round(number, 4)


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    for symbol in ("✅", "🔥", "👀", "⚠️", "❌", "⭐"):
        text = text.replace(symbol, "")

    return " ".join(text.split())


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value

    return None


def get_games(card: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    if not card:
        return []

    games = card.get("games", [])

    if not isinstance(games, list):
        raise ValueError(f"'games' must be a list in {path}")

    return [game for game in games if isinstance(game, dict)]


def matchup_fields(game: dict[str, Any]) -> tuple[str | None, str | None, str]:
    matchup = game.get("matchup") or {}
    teams = game.get("teams") or {}

    away_team = first_not_none(
        matchup.get("away"),
        (teams.get("away") or {}).get("name"),
        game.get("away_team"),
    )
    home_team = first_not_none(
        matchup.get("home"),
        (teams.get("home") or {}).get("name"),
        game.get("home_team"),
    )

    if away_team and home_team:
        game_name = f"{away_team} @ {home_team}"
    else:
        game_name = str(game.get("game_id") or "Unknown Game")

    return away_team, home_team, game_name


def pitcher_context(game: dict[str, Any]) -> dict[str, Any]:
    pitching = game.get("pitching") or {}
    away = pitching.get("away") or {}
    home = pitching.get("home") or {}

    return {
        "away_starting_pitcher": first_not_none(
            away.get("name"),
            game.get("away_pitcher"),
        ),
        "away_pitcher_id": first_not_none(
            away.get("id"),
            game.get("away_pitcher_id"),
        ),
        "home_starting_pitcher": first_not_none(
            home.get("name"),
            game.get("home_pitcher"),
        ),
        "home_pitcher_id": first_not_none(
            home.get("id"),
            game.get("home_pitcher_id"),
        ),
    }


def game_start_time(game: dict[str, Any]) -> str | None:
    return first_not_none(
        game.get("commence_time"),
        game.get("start_time"),
        game.get("game_time"),
        game.get("game_date"),
    )


def base_record(
    game: dict[str, Any],
    source_name: str,
    run_key: str,
) -> dict[str, Any]:
    away_team, home_team, game_name = matchup_fields(game)

    record = {
        "rank": None,
        "run_key": run_key,
        "sport": str(game.get("sport") or source_name).upper(),
        "game_id": game.get("game_id"),
        "game": game_name,
        "away_team": away_team,
        "home_team": home_team,
        "start_time": game_start_time(game),
        "status": game.get("status"),
        "source": source_name,
    }

    record.update(pitcher_context(game))
    return record


def build_moneyline_record(
    game: dict[str, Any],
    source_name: str,
    run_key: str,
) -> dict[str, Any]:
    model = game.get("model") or {}
    odds = game.get("odds") or {}
    market_edge = game.get("market_edge") or {}

    record = base_record(game, source_name, run_key)

    selection = first_not_none(
        model.get("play"),
        market_edge.get("selection"),
        odds.get("selection"),
    )

    sportsbook = first_not_none(
        market_edge.get("sportsbook"),
        odds.get("sportsbook"),
        "Unavailable",
    )

    edge = to_float(
        first_not_none(
            market_edge.get("edge"),
            model.get("edge"),
            odds.get("edge_pct"),
        )
    )

    expected_roi = to_float(
        first_not_none(
            market_edge.get("expected_roi"),
            odds.get("expected_value_pct"),
        )
    )

    model_probability = normalize_probability(
        first_not_none(
            market_edge.get("model_probability"),
            model.get("model_probability"),
        )
    )

    book_probability = normalize_probability(
        first_not_none(
            market_edge.get("book_probability"),
            odds.get("book_probability"),
            odds.get("implied_probability"),
        )
    )

    american_odds = to_int(
        first_not_none(
            market_edge.get("american_odds"),
            market_edge.get("moneyline"),
            odds.get("american_odds"),
            odds.get("moneyline"),
        )
    )

    record.update(
        {
            "market": "MONEYLINE",
            "selection": selection,
            "market_line": None,
            "recommendation": clean_text(model.get("recommendation")) or "UNRATED",
            "confidence": to_float(model.get("confidence")),
            "projection": model_probability,
            "edge": edge,
            "expected_roi": expected_roi,
            "model_probability": model_probability,
            "book_probability": book_probability,
            "odds": american_odds,
            "sportsbook": sportsbook,
            "components": {
                "signals": model.get("signals") or [],
                "component_scores": model.get("component_scores") or {},
                "reasons": model.get("reasons") or [],
                "recommendation_explanation": (
                    model.get("recommendation_explanation") or {}
                ),
                "market_value_label": model.get(
                    "market_value_label"
                ),
                "market_value_tone": model.get(
                    "market_value_tone"
                ),
                "odds_snapshot": odds,
                "market_edge_snapshot": market_edge,
            },
        }
    )

    return record


def totals_recommendation_label(
    raw_recommendation: Any,
    direction: Any,
    edge: float | None,
) -> tuple[str, str]:
    raw = clean_text(raw_recommendation).upper()
    side = clean_text(direction).upper()

    if "OVER" in raw:
        side = "OVER"
    elif "UNDER" in raw:
        side = "UNDER"

    if side not in {"OVER", "UNDER"}:
        return "PASS", "NONE"

    if raw in {"NO MARKET LINE", "MODEL ONLY", "NO PLAY", "PASS"}:
        return "PASS", side

    if raw:
        return raw, side

    if edge is None or abs(edge) < 0.50:
        return "PASS", side

    if abs(edge) >= 1.00:
        return f"STRONG BET {side}", side

    return f"LEAN {side}", side


def build_totals_record(
    game: dict[str, Any],
    source_name: str,
    run_key: str,
) -> dict[str, Any] | None:
    totals = game.get("totals_model")

    if not isinstance(totals, dict) or not totals:
        return None

    market = totals.get("market") or {}
    totals_edge = totals.get("market_edge") or {}

    projected_total = to_float(
        first_not_none(
            totals.get("projected_total"),
            totals_edge.get("model_total"),
            totals.get("starter_based_total"),
        )
    )

    market_total = to_float(
        first_not_none(
            totals.get("market_total"),
            totals_edge.get("market_total"),
            market.get("total"),
        )
    )

    edge = to_float(
        first_not_none(
            totals.get("edge"),
            totals_edge.get("edge"),
        )
    )

    if edge is None and projected_total is not None and market_total is not None:
        edge = round(projected_total - market_total, 2)

    recommendation, selection = totals_recommendation_label(
        first_not_none(
            totals.get("recommendation"),
            totals_edge.get("recommendation"),
        ),
        first_not_none(
            totals.get("direction"),
            totals_edge.get("direction"),
        ),
        edge,
    )

    odds_block = game.get("odds") or {}
    totals_odds = totals.get("odds") or {}

    market_available = bool(
        market.get("available")
        or market_total is not None
        or totals_odds.get("american_odds") is not None
        or totals_odds.get("price") is not None
    )

    sportsbook = (
        first_not_none(
            totals_odds.get("sportsbook"),
            market.get("sportsbook"),
            "Unavailable",
        )
        if market_available
        else "Unavailable"
    )

    american_odds = to_int(
        first_not_none(
            totals_odds.get("american_odds"),
            totals_odds.get("price"),
            market.get("american_odds"),
        )
    )

    record = base_record(game, source_name, run_key)
    record.update(
        {
            "market": "TOTAL",
            "selection": selection,
            "market_line": market_total,
            "recommendation": recommendation,
            "confidence": to_float(totals.get("confidence")),
            "projection": projected_total,
            "edge": edge,
            "expected_roi": to_float(totals.get("expected_roi")),
            "model_probability": None,
            "book_probability": None,
            "odds": american_odds,
            "sportsbook": sportsbook,
            "components": {
                "away_expected_runs": totals.get("away_expected_runs"),
                "home_expected_runs": totals.get("home_expected_runs"),
                "starter_based_total": totals.get("starter_based_total"),
                "bullpen_adjustment": totals.get("bullpen_adjustment"),
                "data_quality": totals.get("data_quality"),
                "market_status": totals.get("market_status"),
                "park": totals.get("park") or {},
                "market_snapshot": market,
                "market_edge_snapshot": totals_edge,
                "reasons": totals.get("reasons") or [],
            },
        }
    )

    return record


def load_recommendations(
    path: Path,
    source_name: str,
    run_key: str,
) -> list[dict[str, Any]]:
    card = load_json(path)
    games = get_games(card, path)
    recommendations: list[dict[str, Any]] = []

    for game in games:
        recommendations.append(
            build_moneyline_record(game, source_name, run_key)
        )

        totals_record = build_totals_record(
            game,
            source_name,
            run_key,
        )

        if totals_record is not None:
            recommendations.append(totals_record)

    return recommendations


def sort_value(value: Any) -> float:
    number = to_float(value)
    return number if number is not None else -999999.0


def recommendation_priority(value: Any) -> int:
    text = clean_text(value).upper()

    if "STRONG BET" in text or "HAMMER" in text:
        return 5
    if text.startswith("BET"):
        return 4
    if "LEAN" in text:
        return 3
    if text == "PASS":
        return 1

    return 2


def rank_recommendations(
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recommendations.sort(
        key=lambda item: (
            recommendation_priority(item.get("recommendation")),
            sort_value(item.get("confidence")),
            abs(sort_value(item.get("edge"))),
            sort_value(item.get("expected_roi")),
        ),
        reverse=True,
    )

    for index, recommendation in enumerate(recommendations, start=1):
        recommendation["rank"] = index

    return recommendations


def persistence_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_game_id": str(item.get("game_id") or ""),
        "sport": item.get("sport"),
        "scheduled_start": item.get("start_time"),
        "market_type": item.get("market"),
        "selection": item.get("selection"),
        "market_line": item.get("market_line"),
        "projection": item.get("projection"),
        "edge": item.get("edge"),
        "confidence": (
            round(float(item["confidence"]) / 100.0, 4)
            if item.get("confidence") is not None
            and float(item["confidence"]) > 1
            else item.get("confidence")
        ),
        "source": item.get("source"),
        "explanation": item.get("recommendation"),
        "components": {
            **(item.get("components") or {}),
            "game": item.get("game"),
            "away_team": item.get("away_team"),
            "home_team": item.get("home_team"),
            "sportsbook": item.get("sportsbook"),
            "american_odds": item.get("odds"),
            "expected_roi": item.get("expected_roi"),
            "model_probability": item.get("model_probability"),
            "book_probability": item.get("book_probability"),
            "away_starting_pitcher": item.get("away_starting_pitcher"),
            "away_pitcher_id": item.get("away_pitcher_id"),
            "home_starting_pitcher": item.get("home_starting_pitcher"),
            "home_pitcher_id": item.get("home_pitcher_id"),
            "status": item.get("status"),
            "run_key": item.get("run_key"),
        },
    }


def build_payload(
    recommendations: list[dict[str, Any]],
    run_key: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "run": {
            "run_key": run_key,
            "started_at": generated_at,
            "completed_at": generated_at,
            "status": "completed",
            "source": "recommendation_explorer",
            "run_label": f"SharpStack recommendations {run_key}",
            "notes": (
                "Immutable MLB/KBO recommendation snapshot. "
                "Each execution represents the information, odds, "
                "lines, and probable pitchers available at run time."
            ),
            "run_metadata": {
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "recommendation_count": len(recommendations),
            },
        },
        "recommendations": [
            persistence_record(item)
            for item in recommendations
        ],
    }


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def write_csv(
    path: Path,
    recommendations: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(recommendations)


def archive_outputs(
    run_key: str,
    recommendation_payload: dict[str, Any],
    persistence_payload: dict[str, Any],
) -> tuple[Path, Path]:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    history_recommendations = (
        HISTORY_DIR / f"recommendations_{run_key}.json"
    )
    history_persistence = (
        HISTORY_DIR / f"persistence_payload_{run_key}.json"
    )

    write_json(history_recommendations, recommendation_payload)
    write_json(history_persistence, persistence_payload)

    return history_recommendations, history_persistence


def format_number(value: Any, suffix: str = "") -> str:
    number = to_float(value)

    if number is None:
        return "N/A"

    return f"{number:.2f}{suffix}"


def format_odds(value: Any) -> str:
    odds = to_int(value)

    if odds is None:
        return "N/A"

    return f"+{odds}" if odds > 0 else str(odds)


def format_play(item: dict[str, Any]) -> str:
    market = item.get("market")
    selection = item.get("selection") or "No selection"

    if market == "TOTAL":
        line = item.get("market_line")
        line_text = f" {line:g}" if isinstance(line, (int, float)) else ""
        return f"{selection}{line_text}"

    return str(selection)


def print_report(
    recommendations: list[dict[str, Any]],
    counts: dict[str, int],
    run_key: str,
    history_path: Path,
) -> None:
    print()
    print("=" * 78)
    print("SHARPSTACK RECOMMENDATION EXPLORER")
    print("=" * 78)
    print(f"Run key: {run_key}")
    print()

    for label, count in counts.items():
        print(f"{label}: {count}")

    print(f"Total recommendations: {len(recommendations)}")
    print()

    if recommendations:
        print("-" * 78)
        print("TOP RECOMMENDATIONS")
        print("-" * 78)

    for item in recommendations[:20]:
        print(
            f"{item['rank']:>2}. "
            f"[{item['sport']}] "
            f"{item['market']} | "
            f"{format_play(item)}"
        )
        print(
            f"    {item['recommendation']} | "
            f"Confidence: {format_number(item.get('confidence'), '%')} | "
            f"Edge: {format_number(item.get('edge'))} | "
            f"Odds: {format_odds(item.get('odds'))}"
        )
        print(
            f"    {item['game']} | "
            f"{item.get('away_starting_pitcher') or 'Unknown'} vs "
            f"{item.get('home_starting_pitcher') or 'Unknown'}"
        )

    print()
    print("-" * 78)
    print(f"Latest JSON        : {JSON_OUTPUT}")
    print(f"Latest CSV         : {CSV_OUTPUT}")
    print(f"Persistence payload: {PERSISTENCE_OUTPUT}")
    print(f"Immutable snapshot : {history_path}")
    print("-" * 78)


def main() -> int:
    now = utc_now()
    generated_at = iso_utc(now)
    run_key = build_run_key(now)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        mlb = load_recommendations(
            MLB_CARD,
            "mlb_card",
            run_key,
        )
        kbo = load_recommendations(
            KBO_CARD,
            "kbo_card",
            run_key,
        )

        recommendations = rank_recommendations(mlb + kbo)

        recommendation_payload = {
            "run_key": run_key,
            "generated_at": generated_at,
            "generated_by": Path(__file__).name,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations,
        }

        persistence_payload = build_payload(
            recommendations,
            run_key,
            generated_at,
        )

        write_json(JSON_OUTPUT, recommendation_payload)
        write_csv(CSV_OUTPUT, recommendations)
        write_json(PERSISTENCE_OUTPUT, persistence_payload)

        history_recommendations, _ = archive_outputs(
            run_key,
            recommendation_payload,
            persistence_payload,
        )

        counts = {
            "MLB moneylines": sum(
                1
                for item in mlb
                if item.get("market") == "MONEYLINE"
            ),
            "MLB totals": sum(
                1
                for item in mlb
                if item.get("market") == "TOTAL"
            ),
            "KBO moneylines": sum(
                1
                for item in kbo
                if item.get("market") == "MONEYLINE"
            ),
            "KBO totals": sum(
                1
                for item in kbo
                if item.get("market") == "TOTAL"
            ),
        }

        print_report(
            recommendations,
            counts,
            run_key,
            history_recommendations,
        )

        return 0

    except Exception as exc:
        print()
        print("=" * 78)
        print("RECOMMENDATION EXPLORER FAILED")
        print("=" * 78)
        print(f"{type(exc).__name__}: {exc}")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
