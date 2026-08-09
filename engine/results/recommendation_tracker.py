import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "output" / "results"
RESULTS_FILE = DATA_DIR / "recommendations.csv"


FIELDNAMES = [
    "date",
    "generated_at",
    "sport",
    "model_version",
    "game_id",
    "game",
    "market",
    "pick",
    "recommendation",
    "model_probability",
    "book_probability",
    "edge",
    "confidence",
    "odds",
    "sportsbook",
    "result",
    "notes",
]


def safe(value, default=""):
    if value is None:
        return default
    return value


def ensure_results_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not RESULTS_FILE.exists():
        with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def load_existing_keys():
    ensure_results_file()

    keys = set()

    with open(RESULTS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            key = (
                row.get("date"),
                row.get("sport"),
                row.get("game_id"),
                row.get("market"),
                row.get("pick"),
            )
            keys.add(key)

    return keys


def append_recommendations_from_card(card):
    ensure_results_file()

    existing = load_existing_keys()

    today = datetime.now().strftime("%Y-%m-%d")
    generated_at = card.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    sport = (card.get("sport") or "").upper()
    version = card.get("version") or ""

    rows = []

    for game in card.get("games", []):
        model = game.get("model", {})
        odds = game.get("odds", {})
        matchup = game.get("matchup", {})

        pick = model.get("play")
        market = model.get("market") or "Moneyline"

        if not pick or pick == "No Play":
            continue

        edge = model.get("edge") or 0
        confidence = model.get("confidence") or 0
        recommendation = model.get("recommendation") or ""

        if recommendation == "PASS":
            continue

        game_label = f"{matchup.get('away')} @ {matchup.get('home')}"

        row = {
            "date": today,
            "generated_at": generated_at,
            "sport": sport,
            "model_version": version,
            "game_id": safe(game.get("game_id")),
            "game": game_label,
            "market": market,
            "pick": pick,
            "recommendation": recommendation,
            "model_probability": safe(model.get("model_probability")),
            "book_probability": safe(
                odds.get("book_probability")
                or odds.get("implied_probability")
            ),
            "edge": edge,
            "confidence": confidence,
            "odds": safe(
                odds.get("moneyline")
                or odds.get("american_odds")
            ),
            "sportsbook": safe(odds.get("sportsbook")),
            "result": "PENDING",
            "notes": "",
        }

        key = (
            row["date"],
            row["sport"],
            str(row["game_id"]),
            row["market"],
            row["pick"],
        )

        if key not in existing:
            rows.append(row)
            existing.add(key)

    if not rows:
        return 0

    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerows(rows)

    return len(rows)


def append_from_card_file(path):
    path = Path(path)

    if not path.exists():
        return 0

    with open(path, "r", encoding="utf-8") as f:
        card = json.load(f)

    return append_recommendations_from_card(card)


def load_results():
    ensure_results_file()

    with open(RESULTS_FILE, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def update_result(date, sport, pick, result, notes=""):
    ensure_results_file()

    rows = load_results()
    updated = False

    for row in rows:
        if (
            row.get("date") == date
            and row.get("sport", "").upper() == sport.upper()
            and row.get("pick", "").lower() == pick.lower()
        ):
            row["result"] = result.upper()
            row["notes"] = notes
            updated = True

    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    return updated