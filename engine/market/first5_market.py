from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from engine.market.odds_math import (
    american_to_implied_probability,
    edge_percentage,
    expected_value,
    implied_probability_to_american,
    remove_two_way_vig,
    safe_float,
)


ROOT = Path(__file__).resolve().parents[2]
FIRST5_CARD_PATH = ROOT / "output" / "cards" / "first5_card.json"
MARKET_LINES_PATH = ROOT / "config" / "first5_market_lines.json"
OUTPUT_PATH = ROOT / "output" / "cards" / "first5_market_card.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def poisson_probability(goals: int, expectation: float) -> float:
    if expectation < 0:
        return 0.0

    return math.exp(-expectation) * (expectation ** goals) / math.factorial(goals)


def projected_result_probabilities(
    away_runs: float,
    home_runs: float,
    max_runs: int = 12,
) -> dict[str, float]:
    """
    Uses independent Poisson run distributions as an MVP approximation.

    Returns regulation First 5:
    - away win probability
    - home win probability
    - tie probability
    """
    away_win = 0.0
    home_win = 0.0
    tie = 0.0

    for away_score in range(max_runs + 1):
        away_probability = poisson_probability(away_score, away_runs)

        for home_score in range(max_runs + 1):
            home_probability = poisson_probability(home_score, home_runs)
            joint_probability = away_probability * home_probability

            if away_score > home_score:
                away_win += joint_probability
            elif home_score > away_score:
                home_win += joint_probability
            else:
                tie += joint_probability

    total = away_win + home_win + tie

    if total <= 0:
        return {
            "away_win": 0.3333,
            "home_win": 0.3333,
            "tie": 0.3334,
        }

    return {
        "away_win": round(away_win / total, 6),
        "home_win": round(home_win / total, 6),
        "tie": round(tie / total, 6),
    }


def draw_no_bet_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    """
    Removes the tie probability and compares only away/home winning outcomes.

    This is useful as an initial way to compare First 5 moneyline prices,
    while preserving the actual tie probability separately.
    """
    away = probabilities.get("away_win", 0.0)
    home = probabilities.get("home_win", 0.0)
    decision_total = away + home

    if decision_total <= 0:
        return {
            "away_dnb": 0.5,
            "home_dnb": 0.5,
        }

    return {
        "away_dnb": round(away / decision_total, 6),
        "home_dnb": round(home / decision_total, 6),
    }


def market_key(game: dict) -> str:
    game_pk = game.get("game_pk")

    if game_pk:
        return str(game_pk)

    return str(game.get("matchup", "")).strip()


def get_market_entry(
    game: dict,
    market_lines: dict,
) -> dict:
    key = market_key(game)

    entry = market_lines.get(key)

    if isinstance(entry, dict):
        return entry

    matchup = str(game.get("matchup", "")).strip()

    fallback = market_lines.get(matchup)

    if isinstance(fallback, dict):
        return fallback

    return {}


def confidence_grade(edge: float | None, ev: float | None) -> str:
    if edge is None:
        return "NO MARKET"

    ev_pct = (ev or 0.0) * 100

    if edge >= 10 and ev_pct >= 8:
        return "A+"

    if edge >= 7 and ev_pct >= 5:
        return "A"

    if edge >= 4.5 and ev_pct >= 2:
        return "B+"

    if edge >= 2.5:
        return "B"

    if edge >= 1:
        return "C"

    return "PASS"


def recommendation_label(
    side: str,
    edge: float | None,
    ev: float | None,
) -> str:
    if edge is None:
        return "NO MARKET"

    ev_pct = (ev or 0.0) * 100

    if edge >= 7 and ev_pct >= 5:
        return f"BET {side}"

    if edge >= 3:
        return f"LEAN {side}"

    return "PASS"


def build_side_market(
    team_name: str,
    model_probability: float,
    book_odds: Any,
    no_vig_probability: float | None,
) -> dict:
    raw_implied = american_to_implied_probability(book_odds)

    comparison_probability = (
        no_vig_probability
        if no_vig_probability is not None
        else raw_implied
    )

    edge = edge_percentage(model_probability, comparison_probability)
    ev = expected_value(model_probability, book_odds)

    return {
        "team": team_name,
        "model_probability": round(model_probability, 6),
        "model_fair_odds": implied_probability_to_american(model_probability),
        "book_odds": safe_float(book_odds),
        "book_raw_implied_probability": raw_implied,
        "book_no_vig_probability": no_vig_probability,
        "edge_pct": edge,
        "expected_value": ev,
        "expected_value_pct": (
            round(ev * 100, 2)
            if ev is not None
            else None
        ),
        "grade": confidence_grade(edge, ev),
        "recommendation": recommendation_label(team_name, edge, ev),
    }


def total_market_analysis(
    model_total: float,
    market: dict,
) -> dict:
    book_line = safe_float(market.get("f5_total"))
    over_odds = safe_float(market.get("f5_over_odds"))
    under_odds = safe_float(market.get("f5_under_odds"))

    if book_line is None:
        return {
            "book_line": None,
            "model_total": round(model_total, 2),
            "run_edge": None,
            "lean": "NO MARKET",
            "over_odds": over_odds,
            "under_odds": under_odds,
            "grade": "NO MARKET",
        }

    run_edge = round(model_total - book_line, 2)

    if run_edge >= 0.65:
        lean = "OVER"
        grade = "A"
    elif run_edge >= 0.35:
        lean = "OVER"
        grade = "B"
    elif run_edge <= -0.65:
        lean = "UNDER"
        grade = "A"
    elif run_edge <= -0.35:
        lean = "UNDER"
        grade = "B"
    else:
        lean = "PASS"
        grade = "PASS"

    return {
        "book_line": book_line,
        "model_total": round(model_total, 2),
        "run_edge": run_edge,
        "lean": lean,
        "over_odds": over_odds,
        "under_odds": under_odds,
        "grade": grade,
    }


def best_side(away_market: dict, home_market: dict) -> dict:
    candidates = [away_market, home_market]

    candidates.sort(
        key=lambda item: (
            item.get("edge_pct")
            if item.get("edge_pct") is not None
            else -999
        ),
        reverse=True,
    )

    return candidates[0]


def build_first5_market_card() -> dict:
    first5_card = load_json(FIRST5_CARD_PATH, {})
    market_lines = load_json(MARKET_LINES_PATH, {})

    games = first5_card.get("games", [])
    enriched_games = []

    for game in games:
        away = game.get("away", {})
        home = game.get("home", {})

        away_runs = safe_float(away.get("projected_f5_runs"), 0.0) or 0.0
        home_runs = safe_float(home.get("projected_f5_runs"), 0.0) or 0.0

        probabilities = projected_result_probabilities(
            away_runs=away_runs,
            home_runs=home_runs,
        )

        dnb_probabilities = draw_no_bet_probabilities(probabilities)
        market = get_market_entry(game, market_lines)

        away_odds = market.get("away_f5_ml")
        home_odds = market.get("home_f5_ml")

        no_vig = remove_two_way_vig(away_odds, home_odds)

        away_market = build_side_market(
            team_name=away.get("team", "Away"),
            model_probability=dnb_probabilities["away_dnb"],
            book_odds=away_odds,
            no_vig_probability=no_vig.get("side_a_no_vig"),
        )

        home_market = build_side_market(
            team_name=home.get("team", "Home"),
            model_probability=dnb_probabilities["home_dnb"],
            book_odds=home_odds,
            no_vig_probability=no_vig.get("side_b_no_vig"),
        )

        total_analysis = total_market_analysis(
            model_total=away_runs + home_runs,
            market=market,
        )

        top_side = best_side(away_market, home_market)

        decision_score = 0.0

        if top_side.get("edge_pct") is not None:
            decision_score += max(top_side["edge_pct"], 0) * 6

        if top_side.get("expected_value_pct") is not None:
            decision_score += max(top_side["expected_value_pct"], 0) * 2

        if total_analysis.get("run_edge") is not None:
            decision_score += abs(total_analysis["run_edge"]) * 12

        decision_score = round(min(decision_score, 100), 1)

        reasons = list(game.get("reasons", []))

        if top_side.get("edge_pct") is not None:
            reasons.insert(
                0,
                (
                    f"{top_side['team']} carries a "
                    f"{top_side['edge_pct']:+.1f}% First 5 market edge."
                ),
            )

        if total_analysis.get("run_edge") is not None:
            reasons.insert(
                1,
                (
                    f"SharpStack projects {total_analysis['model_total']:.2f} "
                    f"F5 runs versus a market line of "
                    f"{total_analysis['book_line']:.1f}."
                ),
            )

        enriched_games.append(
            {
                **game,
                "market_input": market,
                "model_probabilities": {
                    **probabilities,
                    **dnb_probabilities,
                },
                "market_hold": no_vig.get("hold"),
                "away_market": away_market,
                "home_market": home_market,
                "best_market_side": top_side,
                "f5_total_market": total_analysis,
                "market_decision_score": decision_score,
                "market_reasons": reasons[:6],
            }
        )

    enriched_games.sort(
        key=lambda item: item.get("market_decision_score", 0),
        reverse=True,
    )

    bets = [
        game
        for game in enriched_games
        if str(
            game.get("best_market_side", {}).get("recommendation", "")
        ).startswith("BET")
    ]

    leans = [
        game
        for game in enriched_games
        if str(
            game.get("best_market_side", {}).get("recommendation", "")
        ).startswith("LEAN")
    ]

    total_edges = [
        game
        for game in enriched_games
        if game.get("f5_total_market", {}).get("lean")
        in {"OVER", "UNDER"}
    ]

    output = {
        "sport": "MLB",
        "type": "first5_market",
        "version": "0.1.0",
        "generated_at": first5_card.get("generated_at"),
        "summary": {
            "games_loaded": len(enriched_games),
            "market_bets": len(bets),
            "market_leans": len(leans),
            "total_edges": len(total_edges),
            "top_side": (
                bets[0]["best_market_side"]["team"]
                if bets
                else (
                    leans[0]["best_market_side"]["team"]
                    if leans
                    else "PASS"
                )
            ),
        },
        "games": enriched_games,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    return output
