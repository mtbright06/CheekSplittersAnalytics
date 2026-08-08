from __future__ import annotations

from datetime import datetime
import math
from typing import Any

import requests

from engine.bomb_lab.constants import PARK_FACTORS
from engine.mlb.schedule import fetch_mlb_schedule
from engine.mlb.pitchers import (
    PitcherGameLogCache,
    fetch_pitcher_stats,
)
from engine.model.pitcher_stabilization import (
    stabilize_pitcher_metrics,
)


MLB_API = "https://statsapi.mlb.com/api/v1"

LEAGUE_RUNS_PER_GAME = 4.45
LEAGUE_F5_TEAM_RUNS = LEAGUE_RUNS_PER_GAME * (5 / 9)
LEAGUE_ERA = 4.20
LEAGUE_WHIP = 1.28
LEAGUE_HR9 = 1.15
LEAGUE_K_MINUS_BB9 = 5.0

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
            "gameType": "R",
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


def fetch_pitcher_metrics(
    pitcher_id: int | None,
    *,
    as_of=None,
    game_log_cache: PitcherGameLogCache | None = None,
) -> dict:
    if not pitcher_id:
        return DEFAULT_PITCHER_METRICS.copy()

    profile = fetch_pitcher_stats(
        pitcher_id,
        as_of=as_of,
        game_log_cache=game_log_cache,
    )

    if profile:
        return pitcher_metrics_from_starter_profile(profile)

    year = datetime.now().year
    url = f"{MLB_API}/people/{pitcher_id}/stats"

    data = request_json(
        url,
        params={
            "stats": "season",
            "group": "pitching",
            "season": year,
            "gameType": "R",
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

    metrics = {
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
        "data_source": "season_pitching_profile",
    }

    if innings <= 0:
        return metrics

    stabilized = stabilize_pitcher_metrics(
        metrics,
        innings_key="innings",
        metric_keys={
            "era": "era",
            "whip": "whip",
            "k9": "k9",
            "bb9": "bb9",
            "hr9": "hr9",
        },
    )

    metrics.update(
        {
            "era": round(stabilized["era"], 2),
            "whip": round(stabilized["whip"], 2),
            "k9": round(stabilized["k9"], 2),
            "bb9": round(stabilized["bb9"], 2),
            "hr9": round(stabilized["hr9"], 2),
        }
    )
    metrics["k_minus_bb9"] = round(
        metrics["k9"] - metrics["bb9"],
        2,
    )

    return metrics


def pitcher_metrics_from_starter_profile(profile: dict) -> dict:
    innings = safe_float(
        profile.get("ip"),
        0.0,
    )
    k9 = safe_float(
        profile.get("k_rate"),
        DEFAULT_PITCHER_METRICS["k9"],
    )
    bb9 = safe_float(
        profile.get("bb_rate"),
        DEFAULT_PITCHER_METRICS["bb9"],
    )

    return {
        "era": safe_float(profile.get("era"), DEFAULT_PITCHER_METRICS["era"]),
        "whip": safe_float(profile.get("whip"), DEFAULT_PITCHER_METRICS["whip"]),
        "innings": innings,
        "strikeouts": safe_int(profile.get("so")),
        "walks": safe_int(profile.get("bb")),
        "home_runs": safe_int(profile.get("hr_allowed")),
        "k9": k9,
        "bb9": bb9,
        "hr9": safe_float(profile.get("hr9"), DEFAULT_PITCHER_METRICS["hr9"]),
        "k_minus_bb9": round(k9 - bb9, 2),
        "available": True,
        "previous_start_date": profile.get("previous_start_date"),
        "days_rest": profile.get("days_rest"),
        "previous_start_ip": profile.get("previous_start_ip"),
        "previous_start_pitch_count": profile.get("previous_start_pitch_count"),
        "last_two_starts_ip": profile.get("last_two_starts_ip"),
        "last_two_starts_pitch_count": profile.get("last_two_starts_pitch_count"),
        "last14_start_ip": profile.get("last14_start_ip"),
        "average_start_ip": profile.get("average_start_ip"),
        "role_context": profile.get("role_context"),
        "data_source": profile.get("data_source", "starter_game_log"),
    }


def offense_factor(stats: dict) -> float:
    runs_per_game = safe_float(
        stats.get("runs_per_game"),
        LEAGUE_RUNS_PER_GAME,
    )

    return clamp(
        runs_per_game / LEAGUE_RUNS_PER_GAME,
        0.78,
        1.24,
    )


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


def starter_run_factor(
    pitcher: dict,
) -> float:
    era = safe_float(
        pitcher.get("era"),
        LEAGUE_ERA,
    )
    whip = safe_float(
        pitcher.get("whip"),
        LEAGUE_WHIP,
    )
    hr9 = safe_float(
        pitcher.get("hr9"),
        LEAGUE_HR9,
    )
    k_minus_bb9 = safe_float(
        pitcher.get("k_minus_bb9"),
        LEAGUE_K_MINUS_BB9,
    )

    log_factor = (
        ((era - LEAGUE_ERA) * 0.045)
        + ((whip - LEAGUE_WHIP) * 0.13)
        + ((hr9 - LEAGUE_HR9) * 0.055)
        - ((k_minus_bb9 - LEAGUE_K_MINUS_BB9) * 0.014)
    )

    return clamp(
        math.exp(log_factor),
        0.78,
        1.28,
    )


def starter_context_adjustment(
    pitcher: dict,
) -> dict:
    adjustment = 0.0
    reasons = []

    days_rest = safe_float(pitcher.get("days_rest"), None)
    previous_ip = safe_float(pitcher.get("previous_start_ip"), None)
    previous_pitches = safe_float(pitcher.get("previous_start_pitch_count"), None)
    average_start_ip = safe_float(pitcher.get("average_start_ip"), None)
    role_context = pitcher.get("role_context")

    if days_rest is not None:
        if days_rest <= 3:
            adjustment += 0.035
            reasons.append("very_short_rest")
        elif days_rest == 4:
            adjustment += 0.02
            reasons.append("short_rest")
        elif days_rest == 7:
            adjustment -= 0.01
            reasons.append("extra_rest")

    if previous_pitches is not None and days_rest is not None:
        if previous_pitches >= 110 and days_rest <= 5:
            adjustment += 0.025
            reasons.append("heavy_previous_pitch_count")
        elif previous_pitches >= 100 and days_rest <= 4:
            adjustment += 0.015
            reasons.append("elevated_pitch_count_on_short_rest")

    if (
        previous_ip is not None
        and previous_ip >= 7.0
        and days_rest is not None
        and days_rest <= 5
    ):
        adjustment += 0.015
        reasons.append("deep_previous_start")

    if role_context == "opener_risk":
        adjustment += 0.10
        reasons.append("opener_risk")
    elif role_context == "short_start_role_risk":
        adjustment += 0.065
        reasons.append("short_start_role_risk")
    elif role_context == "limited_starting_role":
        adjustment += 0.035
        reasons.append("limited_starting_role")

    if (
        average_start_ip is not None
        and average_start_ip < 4.0
        and role_context == "established_starter"
    ):
        adjustment += 0.03
        reasons.append("limited_average_start_length")

    adjustment = round(
        max(
            -0.02,
            min(0.12, adjustment),
        ),
        3,
    )

    return {
        "adjustment": adjustment,
        "factor": round(1.0 + adjustment, 3),
        "reasons": sorted(set(reasons)),
    }


def project_team_f5_runs(
    offense_stats: dict,
    opposing_pitcher: dict,
    park_factor: float,
    *,
    is_home: bool = False,
) -> float:
    park_multiplier = 1.0 + ((park_factor - 1.0) * 0.55)
    home_multiplier = 1.018 if is_home else 1.0

    projected = (
        LEAGUE_F5_TEAM_RUNS
        * offense_factor(offense_stats)
        * starter_run_factor(opposing_pitcher)
        * starter_context_adjustment(opposing_pitcher)["factor"]
        * park_multiplier
        * home_multiplier
    )

    return round(clamp(projected, 0.5, 6.5), 2)


def build_reliability(
    away_pitcher: dict,
    home_pitcher: dict,
    away_offense: dict,
    home_offense: dict,
    *,
    park_factor: float | None = None,
) -> dict:
    score = 100.0
    concerns: list[str] = []
    future_unavailable_context = [
        "lineup_quality_not_evaluated",
        "handedness_splits_not_evaluated",
        "expected_workload_not_evaluated",
    ]

    for side, pitcher in (
        ("away", away_pitcher),
        ("home", home_pitcher),
    ):
        innings = safe_float(
            pitcher.get("innings"),
            0.0,
        )

        if not pitcher.get("available"):
            score -= 30
            concerns.append(f"{side}_starter_unconfirmed")
        elif innings < 20:
            score -= 20
            concerns.append(f"{side}_starter_very_limited_sample")
        elif innings < 45:
            score -= 12
            concerns.append(f"{side}_starter_limited_sample")

        if pitcher.get("data_source") not in (None, "starter_game_log"):
            score -= 8
            concerns.append(f"{side}_starter_profile_fallback")

        if (
            pitcher.get("data_source") == "starter_game_log"
            and pitcher.get("previous_start_date") is None
        ):
            score -= 5
            concerns.append(f"{side}_missing_starter_rest_context")

        if (
            pitcher.get("data_source") == "starter_game_log"
            and (
                pitcher.get("previous_start_ip") is None
                or pitcher.get("previous_start_pitch_count") is None
            )
        ):
            score -= 5
            concerns.append(f"{side}_missing_starter_workload_context")

        role_context = pitcher.get("role_context")
        if role_context in {
            "opener_risk",
            "short_start_role_risk",
            "limited_starting_role",
        }:
            score -= 8
            concerns.append(f"{side}_{role_context}")

    for side, offense in (
        ("away", away_offense),
        ("home", home_offense),
    ):
        if safe_int(offense.get("games")) <= 0:
            score -= 25
            concerns.append(f"{side}_core_offense_unavailable")

    if park_factor is None:
        score -= 5
        concerns.append("park_factor_unavailable")

    reliability = round(clamp(score, 35, 100), 1)

    if reliability < 55:
        tier_cap = "PASS"
    elif reliability < 70:
        tier_cap = "LEAN"
    elif reliability < 82:
        tier_cap = "PLAYABLE"
    elif reliability < 92:
        tier_cap = "PLAY"
    else:
        tier_cap = "STRONG PLAY"

    return {
        "score": reliability,
        "tier_cap": tier_cap,
        "active_concerns": concerns,
        "concerns": concerns,
        "future_unavailable_context": future_unavailable_context,
    }


def margin_tier(
    model_strength: float,
) -> str:
    if model_strength < 0.25:
        return "PASS"
    if model_strength < 0.45:
        return "LEAN"
    if model_strength < 0.65:
        return "PLAYABLE"
    if model_strength < 0.90:
        return "PLAY"
    return "STRONG PLAY"


def apply_tier_cap(
    tier: str,
    cap: str,
) -> str:
    order = {
        "PASS": 0,
        "LEAN": 1,
        "PLAYABLE": 2,
        "PLAY": 3,
        "STRONG PLAY": 4,
    }

    if order[tier] <= order[cap]:
        return tier

    for label, value in order.items():
        if value == order[cap]:
            return label

    return tier


def moneyline_recommendation(
    away_team: str,
    home_team: str,
    away_runs: float,
    home_runs: float,
    reliability: dict,
) -> dict:
    margin = round(home_runs - away_runs, 2)
    model_strength = round(abs(margin), 2)
    base_tier = margin_tier(model_strength)
    final_tier = apply_tier_cap(
        base_tier,
        reliability["tier_cap"],
    )

    if final_tier == "PASS" or margin == 0:
        lean = "PASS"
        side = "PASS"
    elif margin > 0:
        lean = home_team
        side = "HOME"
    else:
        lean = away_team
        side = "AWAY"

    return {
        "lean": lean,
        "side": side,
        "projected_margin": margin,
        "model_strength": model_strength,
        "base_tier": base_tier,
        "recommendation": final_tier,
        "recommendation_tier": final_tier,
        "tier_cap": reliability["tier_cap"],
        "changed_by_reliability": final_tier != base_tier,
    }


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
        "recommendation": lean,
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
    reliability: dict,
    away_pitcher_context: dict | None = None,
    home_pitcher_context: dict | None = None,
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

    if home_pitcher_context and home_pitcher_context.get("adjustment", 0) > 0:
        reasons.append(
            f"{home_pitcher_name}'s starter context increases projected "
            f"first-five scoring for {away_team}."
        )

    if away_pitcher_context and away_pitcher_context.get("adjustment", 0) > 0:
        reasons.append(
            f"{away_pitcher_name}'s starter context increases projected "
            f"first-five scoring for {home_team}."
        )

    if f5_ml["lean"] != "PASS":
        reasons.append(
            f"{f5_ml['lean']} rates as {f5_ml['recommendation']} with a "
            f"{abs(f5_ml['projected_margin']):.2f}-run projected margin "
            "through five."
        )
    elif f5_ml.get("base_tier") != "PASS" and f5_ml.get(
        "changed_by_reliability"
    ):
        reasons.append(
            "The projected margin cleared the model tier ladder, but input "
            f"reliability capped the recommendation at {f5_ml['recommendation']}."
        )

    if reliability.get("concerns"):
        reasons.append(
            "Reliability reflects currently implemented First 5 inputs only; "
            "future lineup, handedness, and workload context is diagnostic."
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
    game_log_cache = PitcherGameLogCache()
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
                away_pitcher_id,
                as_of=game.get("game_date"),
                game_log_cache=game_log_cache,
            )

        if home_pitcher_id not in pitcher_cache:
            pitcher_cache[home_pitcher_id] = fetch_pitcher_metrics(
                home_pitcher_id,
                as_of=game.get("game_date"),
                game_log_cache=game_log_cache,
            )

        away_offense = team_cache[away_team_id]
        home_offense = team_cache[home_team_id]
        away_pitcher = pitcher_cache[away_pitcher_id]
        home_pitcher = pitcher_cache[home_pitcher_id]

        away_offense_rating = offense_score(away_offense)
        home_offense_rating = offense_score(home_offense)
        away_pitcher_rating = pitcher_quality_score(away_pitcher)
        home_pitcher_rating = pitcher_quality_score(home_pitcher)
        away_pitcher_context = starter_context_adjustment(away_pitcher)
        home_pitcher_context = starter_context_adjustment(home_pitcher)

        park_factor = park_factor_for_game(game.get("home_team"))

        away_projected_runs = project_team_f5_runs(
            offense_stats=away_offense,
            opposing_pitcher=home_pitcher,
            park_factor=park_factor,
            is_home=False,
        )

        home_projected_runs = project_team_f5_runs(
            offense_stats=home_offense,
            opposing_pitcher=away_pitcher,
            park_factor=park_factor,
            is_home=True,
        )

        projected_total = round(
            away_projected_runs + home_projected_runs,
            2,
        )

        reliability = build_reliability(
            away_pitcher=away_pitcher,
            home_pitcher=home_pitcher,
            away_offense=away_offense,
            home_offense=home_offense,
            park_factor=park_factor,
        )

        f5_ml = moneyline_recommendation(
            away_team=game["away_team"],
            home_team=game["home_team"],
            away_runs=away_projected_runs,
            home_runs=home_projected_runs,
            reliability=reliability,
        )

        f5_total = total_lean(projected_total)

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
            reliability=reliability,
            away_pitcher_context=away_pitcher_context,
            home_pitcher_context=home_pitcher_context,
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
                        "starter_context": away_pitcher_context,
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
                        "starter_context": home_pitcher_context,
                        **home_pitcher,
                    },
                },
                "f5_ml": f5_ml,
                "f5_total": f5_total,
                "model_strength": f5_ml["model_strength"],
                "reliability": reliability["score"],
                "reliability_tier_cap": reliability["tier_cap"],
                "reliability_concerns": reliability["concerns"],
                "active_reliability_concerns": reliability[
                    "active_concerns"
                ],
                "future_unavailable_context": reliability[
                    "future_unavailable_context"
                ],
                "recommendation": f5_ml["recommendation"],
                "recommendation_tier": f5_ml["recommendation_tier"],
                # Compatibility aliases for existing consumers.
                "confidence": reliability["score"],
                "reasons": reasons,
            }
        )

    game_cards.sort(
        key=lambda item: (
            {
                "STRONG PLAY": 4,
                "PLAY": 3,
                "PLAYABLE": 2,
                "LEAN": 1,
                "PASS": 0,
            }.get(item.get("recommendation_tier"), 0),
            item.get("model_strength", 0),
            item.get("reliability", 0),
        ),
        reverse=True,
    )

    actionable_ml = [
        game for game in game_cards
        if game.get("f5_ml", {}).get("lean") != "PASS"
    ]
    tier_counts = {
        "PASS": 0,
        "LEAN": 0,
        "PLAYABLE": 0,
        "PLAY": 0,
        "STRONG PLAY": 0,
    }

    for game in game_cards:
        tier = game.get("recommendation_tier", "PASS")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

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
            "recommendation_distribution": tier_counts,
            "pass": tier_counts["PASS"],
            "lean": tier_counts["LEAN"],
            "playable": tier_counts["PLAYABLE"],
            "play": tier_counts["PLAY"],
            "strong_play": tier_counts["STRONG PLAY"],
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
            "recommendation_distribution": {
                "PASS": 0,
                "LEAN": 0,
                "PLAYABLE": 0,
                "PLAY": 0,
                "STRONG PLAY": 0,
            },
            "pass": 0,
            "lean": 0,
            "playable": 0,
            "play": 0,
            "strong_play": 0,
            "f5_total_leans": 0,
            "top_ml_play": "PASS",
            "top_total_play": "PASS",
        },
        "games": [],
        "message": message,
    }
