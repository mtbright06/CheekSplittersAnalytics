from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from engine.bomb_lab.constants import PARK_FACTORS
from engine.mlb.schedule import fetch_mlb_schedule


MLB_API = "https://statsapi.mlb.com/api/v1"

DEFAULT_TEAM_METRICS = {
    "games": 0,
    "runs": 0,
    "runs_per_game": 4.35,
    "home_runs": 0,
    "hr_per_game": 1.10,
    "avg": 0.245,
    "obp": 0.315,
    "slg": 0.400,
    "ops": 0.715,
    "walks": 0,
    "strikeouts": 0,
    "plate_appearances": 0,
    "bb_pct": 0.082,
    "k_pct": 0.225,
}

DEFAULT_PITCHER_METRICS = {
    "era": 4.25,
    "whip": 1.30,
    "innings": 0.0,
    "strikeouts": 0,
    "walks": 0,
    "home_runs": 0,
    "k9": 8.30,
    "bb9": 3.10,
    "hr9": 1.20,
    "k_minus_bb9": 5.20,
    "available": False,
}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in [None, "", "-", "--", ".---"]:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in [None, "", "-", "--"]:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def innings_to_float(value: Any) -> float:
    if value in [None, "", "-"]:
        return 0.0

    text = str(value).strip()

    if "." not in text:
        return safe_float(text)

    whole, remainder = text.split(".", 1)

    try:
        whole_number = int(whole)
        remainder_number = int(remainder)
    except ValueError:
        return safe_float(text)

    if remainder_number == 1:
        return whole_number + (1 / 3)

    if remainder_number == 2:
        return whole_number + (2 / 3)

    return safe_float(text)


def request_json(url: str, params: dict | None = None) -> dict:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=20,
            headers={"User-Agent": "SharpStack/1.0"},
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"First 5 API warning: {exc}")
        return {}


def fetch_team_hitting(team_id: int | None) -> dict:
    if not team_id:
        return DEFAULT_TEAM_METRICS.copy()

    year = datetime.now().year
    url = f"{MLB_API}/teams/{team_id}/stats"

    data = request_json(
        url,
        params={
            "stats": "season",
            "group": "hitting",
            "season": year,
        },
    )

    stats_list = data.get("stats", [])

    if not stats_list:
        return DEFAULT_TEAM_METRICS.copy()

    splits = stats_list[0].get("splits", [])

    if not splits:
        return DEFAULT_TEAM_METRICS.copy()

    stat = splits[0].get("stat", {})

    games = safe_int(stat.get("gamesPlayed"))
    runs = safe_int(stat.get("runs"))
    home_runs = safe_int(stat.get("homeRuns"))
    walks = safe_int(stat.get("baseOnBalls"))
    strikeouts = safe_int(stat.get("strikeOuts"))
    plate_appearances = safe_int(stat.get("plateAppearances"))

    runs_per_game = runs / games if games else DEFAULT_TEAM_METRICS["runs_per_game"]
    hr_per_game = home_runs / games if games else DEFAULT_TEAM_METRICS["hr_per_game"]
    bb_pct = walks / plate_appearances if plate_appearances else DEFAULT_TEAM_METRICS["bb_pct"]
    k_pct = strikeouts / plate_appearances if plate_appearances else DEFAULT_TEAM_METRICS["k_pct"]

    return {
        "games": games,
        "runs": runs,
        "runs_per_game": round(runs_per_game, 3),
        "home_runs": home_runs,
        "hr_per_game": round(hr_per_game, 3),
        "avg": safe_float(stat.get("avg"), DEFAULT_TEAM_METRICS["avg"]),
        "obp": safe_float(stat.get("obp"), DEFAULT_TEAM_METRICS["obp"]),
        "slg": safe_float(stat.get("slg"), DEFAULT_TEAM_METRICS["slg"]),
        "ops": safe_float(stat.get("ops"), DEFAULT_TEAM_METRICS["ops"]),
        "walks": walks,
        "strikeouts": strikeouts,
        "plate_appearances": plate_appearances,
        "bb_pct": round(bb_pct, 4),
        "k_pct": round(k_pct, 4),
    }


def fetch_pitcher_metrics(pitcher_id: int | None) -> dict:
    if not pitcher_id:
        return DEFAULT_PITCHER_METRICS.copy()

    year = datetime.now().year
    url = f"{MLB_API}/people/{pitcher_id}/stats"

    data = request_json(
        url,
        params={
            "stats": "season",
            "group": "pitching",
            "season": year,
        },
    )

    stats_list = data.get("stats", [])

    if not stats_list:
        return DEFAULT_PITCHER_METRICS.copy()

    splits = stats_list[0].get("splits", [])

    if not splits:
        return DEFAULT_PITCHER_METRICS.copy()

    stat = splits[0].get("stat", {})

    innings = innings_to_float(stat.get("inningsPitched"))
    strikeouts = safe_int(stat.get("strikeOuts"))
    walks = safe_int(stat.get("baseOnBalls"))
    home_runs = safe_int(stat.get("homeRuns"))

    k9 = (strikeouts / innings) * 9 if innings else DEFAULT_PITCHER_METRICS["k9"]
    bb9 = (walks / innings) * 9 if innings else DEFAULT_PITCHER_METRICS["bb9"]
    hr9 = (home_runs / innings) * 9 if innings else DEFAULT_PITCHER_METRICS["hr9"]

    return {
        "era": safe_float(stat.get("era"), DEFAULT_PITCHER_METRICS["era"]),
        "whip": safe_float(stat.get("whip"), DEFAULT_PITCHER_METRICS["whip"]),
        "innings": round(innings, 2),
        "strikeouts": strikeouts,
        "walks": walks,
        "home_runs": home_runs,
        "k9": round(k9, 2),
        "bb9": round(bb9, 2),
        "hr9": round(hr9, 2),
        "k_minus_bb9": round(k9 - bb9, 2),
        "available": True,
    }


def offense_score(stats: dict) -> float:
    runs_component = clamp((stats["runs_per_game"] - 3.2) / 2.6 * 100)
    ops_component = clamp((stats["ops"] - 0.620) / 0.190 * 100)
    slug_component = clamp((stats["slg"] - 0.340) / 0.150 * 100)
    hr_component = clamp((stats["hr_per_game"] - 0.60) / 1.10 * 100)
    discipline_component = clamp(
        50
        + ((stats["bb_pct"] - 0.082) * 500)
        - ((stats["k_pct"] - 0.225) * 260)
    )

    score = (
        runs_component * 0.30
        + ops_component * 0.25
        + slug_component * 0.18
        + hr_component * 0.17
        + discipline_component * 0.10
    )

    return round(clamp(score), 1)


def pitcher_quality_score(stats: dict) -> float:
    era_component = clamp((6.25 - stats["era"]) / 4.60 * 100)
    whip_component = clamp((1.75 - stats["whip"]) / 0.80 * 100)
    kbb_component = clamp((stats["k_minus_bb9"] - 1.0) / 7.0 * 100)
    hr_component = clamp((2.10 - stats["hr9"]) / 1.75 * 100)

    score = (
        era_component * 0.34
        + whip_component * 0.26
        + kbb_component * 0.23
        + hr_component * 0.17
    )

    return round(clamp(score), 1)


def park_factor_for_game(home_team: str | None) -> float:
    return safe_float(PARK_FACTORS.get(home_team, 1.0), 1.0)


def project_team_f5_runs(
    offense_stats: dict,
    opposing_pitcher: dict,
    park_factor: float,
    home_adjustment: float = 0.0,
) -> float:
    base_runs = offense_stats["runs_per_game"] * (5 / 9)

    pitcher_multiplier = (
        1.0
        + ((opposing_pitcher["era"] - 4.20) * 0.055)
        + ((opposing_pitcher["whip"] - 1.28) * 0.18)
        + ((opposing_pitcher["hr9"] - 1.15) * 0.075)
        - ((opposing_pitcher["k_minus_bb9"] - 5.0) * 0.018)
    )

    pitcher_multiplier = max(0.70, min(1.38, pitcher_multiplier))

    park_multiplier = 1.0 + ((park_factor - 1.0) * 0.60)

    projected = (
        base_runs
        * pitcher_multiplier
        * park_multiplier
        + home_adjustment
    )

    return round(max(0.8, min(5.5, projected)), 2)


def confidence_grade(score: float) -> str:
    if score >= 88:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 72:
        return "B+"
    if score >= 64:
        return "B"
    if score >= 56:
        return "C+"
    return "PASS"


def build_confidence(
    away_pitcher: dict,
    home_pitcher: dict,
    run_margin: float,
    total_distance: float,
) -> float:
    score = 45.0

    if away_pitcher.get("available"):
        score += 12

    if home_pitcher.get("available"):
        score += 12

    minimum_innings = min(
        safe_float(away_pitcher.get("innings")),
        safe_float(home_pitcher.get("innings")),
    )

    if minimum_innings >= 80:
        score += 14
    elif minimum_innings >= 45:
        score += 9
    elif minimum_innings >= 20:
        score += 4

    score += min(abs(run_margin) * 11, 11)
    score += min(abs(total_distance) * 8, 6)

    return round(clamp(score, 35, 95), 1)


def total_lean(projected_total: float) -> dict:
    nearest_half = round(projected_total * 2) / 2

    if projected_total >= 5.25:
        lean = "OVER"
        model_line = nearest_half
    elif projected_total <= 4.15:
        lean = "UNDER"
        model_line = nearest_half
    else:
        lean = "PASS"
        model_line = nearest_half

    return {
        "lean": lean,
        "model_line": round(model_line, 1),
        "projected_total": round(projected_total, 2),
    }


def moneyline_lean(
    away_team: str,
    home_team: str,
    away_runs: float,
    home_runs: float,
) -> dict:
    margin = round(home_runs - away_runs, 2)

    if margin >= 0.45:
        lean = home_team
        side = "HOME"
    elif margin <= -0.45:
        lean = away_team
        side = "AWAY"
    else:
        lean = "PASS"
        side = "PASS"

    return {
        "lean": lean,
        "side": side,
        "projected_margin": margin,
    }


def build_reasons(
    away_team: str,
    home_team: str,
    away_pitcher_name: str,
    home_pitcher_name: str,
    away_offense_score: float,
    home_offense_score: float,
    away_pitcher_score: float,
    home_pitcher_score: float,
    f5_ml: dict,
    f5_total: dict,
    park_factor: float,
) -> list[str]:
    reasons = []

    if home_pitcher_score - away_pitcher_score >= 10:
        reasons.append(
            f"{home_team} owns the stronger starting-pitcher profile with "
            f"{home_pitcher_name} over {away_pitcher_name}."
        )
    elif away_pitcher_score - home_pitcher_score >= 10:
        reasons.append(
            f"{away_team} owns the stronger starting-pitcher profile with "
            f"{away_pitcher_name} over {home_pitcher_name}."
        )

    if home_offense_score - away_offense_score >= 10:
        reasons.append(f"{home_team} carries the stronger season-long offense.")
    elif away_offense_score - home_offense_score >= 10:
        reasons.append(f"{away_team} carries the stronger season-long offense.")

    if f5_total["lean"] == "OVER":
        reasons.append(
            f"The model projects {f5_total['projected_total']:.2f} combined runs "
            "through five innings, supporting an F5 over lean."
        )
    elif f5_total["lean"] == "UNDER":
        reasons.append(
            f"The model projects only {f5_total['projected_total']:.2f} combined "
            "runs through five innings, supporting an F5 under lean."
        )

    if park_factor >= 1.05:
        reasons.append("The venue provides a positive run-scoring adjustment.")
    elif park_factor <= 0.95:
        reasons.append("The venue provides a run-suppressing adjustment.")

    if f5_ml["lean"] != "PASS":
        reasons.append(
            f"{f5_ml['lean']} projects ahead by "
            f"{abs(f5_ml['projected_margin']):.2f} runs through five."
        )

    if not reasons:
        reasons.append(
            "The matchup is tightly graded and does not currently produce a "
            "strong First 5 edge."
        )

    return reasons[:5]


def parse_schedule_games() -> list[dict]:
    raw = fetch_mlb_schedule()
    games = []

    for date_blob in raw.get("dates", []):
        for game in date_blob.get("games", []):
            teams = game.get("teams", {})
            away_blob = teams.get("away", {})
            home_blob = teams.get("home", {})

            away_team_blob = away_blob.get("team", {})
            home_team_blob = home_blob.get("team", {})

            away_pitcher = away_blob.get("probablePitcher", {})
            home_pitcher = home_blob.get("probablePitcher", {})

            games.append(
                {
                    "game_pk": game.get("gamePk"),
                    "game_date": game.get("gameDate"),
                    "venue": game.get("venue", {}).get("name"),
                    "away_team": away_team_blob.get("name"),
                    "away_team_id": away_team_blob.get("id"),
                    "away_pitcher": away_pitcher.get("fullName") or "TBD",
                    "away_pitcher_id": away_pitcher.get("id"),
                    "home_team": home_team_blob.get("name"),
                    "home_team_id": home_team_blob.get("id"),
                    "home_pitcher": home_pitcher.get("fullName") or "TBD",
                    "home_pitcher_id": home_pitcher.get("id"),
                }
            )

    return games


def build_first5_card() -> dict:
    schedule_games = parse_schedule_games()

    if not schedule_games:
        return empty_first5_card("No MLB games found.")

    team_cache: dict[int, dict] = {}
    pitcher_cache: dict[int, dict] = {}
    game_cards = []

    for game in schedule_games:
        away_team_id = game.get("away_team_id")
        home_team_id = game.get("home_team_id")
        away_pitcher_id = game.get("away_pitcher_id")
        home_pitcher_id = game.get("home_pitcher_id")

        if away_team_id not in team_cache:
            team_cache[away_team_id] = fetch_team_hitting(away_team_id)

        if home_team_id not in team_cache:
            team_cache[home_team_id] = fetch_team_hitting(home_team_id)

        if away_pitcher_id not in pitcher_cache:
            pitcher_cache[away_pitcher_id] = fetch_pitcher_metrics(
                away_pitcher_id
            )

        if home_pitcher_id not in pitcher_cache:
            pitcher_cache[home_pitcher_id] = fetch_pitcher_metrics(
                home_pitcher_id
            )

        away_offense = team_cache[away_team_id]
        home_offense = team_cache[home_team_id]
        away_pitcher = pitcher_cache[away_pitcher_id]
        home_pitcher = pitcher_cache[home_pitcher_id]

        away_offense_rating = offense_score(away_offense)
        home_offense_rating = offense_score(home_offense)
        away_pitcher_rating = pitcher_quality_score(away_pitcher)
        home_pitcher_rating = pitcher_quality_score(home_pitcher)

        park_factor = park_factor_for_game(game.get("home_team"))

        away_projected_runs = project_team_f5_runs(
            offense_stats=away_offense,
            opposing_pitcher=home_pitcher,
            park_factor=park_factor,
            home_adjustment=0.0,
        )

        home_projected_runs = project_team_f5_runs(
            offense_stats=home_offense,
            opposing_pitcher=away_pitcher,
            park_factor=park_factor,
            home_adjustment=0.08,
        )

        projected_total = round(
            away_projected_runs + home_projected_runs,
            2,
        )

        f5_ml = moneyline_lean(
            away_team=game["away_team"],
            home_team=game["home_team"],
            away_runs=away_projected_runs,
            home_runs=home_projected_runs,
        )

        f5_total = total_lean(projected_total)

        total_distance = projected_total - 4.5

        confidence = build_confidence(
            away_pitcher=away_pitcher,
            home_pitcher=home_pitcher,
            run_margin=f5_ml["projected_margin"],
            total_distance=total_distance,
        )

        reasons = build_reasons(
            away_team=game["away_team"],
            home_team=game["home_team"],
            away_pitcher_name=game["away_pitcher"],
            home_pitcher_name=game["home_pitcher"],
            away_offense_score=away_offense_rating,
            home_offense_score=home_offense_rating,
            away_pitcher_score=away_pitcher_rating,
            home_pitcher_score=home_pitcher_rating,
            f5_ml=f5_ml,
            f5_total=f5_total,
            park_factor=park_factor,
        )

        decision_score = round(
            clamp(
                confidence * 0.55
                + abs(f5_ml["projected_margin"]) * 18
                + abs(total_distance) * 8
            ),
            1,
        )

        game_cards.append(
            {
                **game,
                "matchup": f"{game['away_team']} @ {game['home_team']}",
                "park_factor": round(park_factor, 3),
                "away": {
                    "team": game["away_team"],
                    "projected_f5_runs": away_projected_runs,
                    "offense_score": away_offense_rating,
                    "offense": away_offense,
                    "pitcher": {
                        "name": game["away_pitcher"],
                        "quality_score": away_pitcher_rating,
                        **away_pitcher,
                    },
                },
                "home": {
                    "team": game["home_team"],
                    "projected_f5_runs": home_projected_runs,
                    "offense_score": home_offense_rating,
                    "offense": home_offense,
                    "pitcher": {
                        "name": game["home_pitcher"],
                        "quality_score": home_pitcher_rating,
                        **home_pitcher,
                    },
                },
                "f5_ml": f5_ml,
                "f5_total": f5_total,
                "confidence": confidence,
                "confidence_grade": confidence_grade(confidence),
                "decision_score": decision_score,
                "reasons": reasons,
            }
        )

    game_cards.sort(
        key=lambda item: item.get("decision_score", 0),
        reverse=True,
    )

    actionable_ml = [
        game for game in game_cards
        if game.get("f5_ml", {}).get("lean") != "PASS"
    ]

    actionable_totals = [
        game for game in game_cards
        if game.get("f5_total", {}).get("lean") != "PASS"
    ]

    return {
        "sport": "MLB",
        "type": "first5",
        "version": "0.1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "games_loaded": len(game_cards),
            "f5_ml_leans": len(actionable_ml),
            "f5_total_leans": len(actionable_totals),
            "top_ml_play": (
                actionable_ml[0]["f5_ml"]["lean"]
                if actionable_ml
                else "PASS"
            ),
            "top_total_play": (
                f"{actionable_totals[0]['f5_total']['lean']} "
                f"{actionable_totals[0]['f5_total']['model_line']}"
                if actionable_totals
                else "PASS"
            ),
        },
        "games": game_cards,
    }


def empty_first5_card(message: str) -> dict:
    return {
        "sport": "MLB",
        "type": "first5",
        "version": "0.1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "games_loaded": 0,
            "f5_ml_leans": 0,
            "f5_total_leans": 0,
            "top_ml_play": "PASS",
            "top_total_play": "PASS",
        },
        "games": [],
        "message": message,
    }
