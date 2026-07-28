from __future__ import annotations

from typing import Any

from engine.core import MarketQuote, Recommendation


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value

    return None


def _canonical_recommendation(value: Any) -> str:
    text = str(value or "").upper()

    for label in ("HAMMER", "BET", "LEAN"):
        if label in text:
            return label

    return "PASS"


def _selection(totals: dict) -> str:
    direction = str(
        totals.get("selection")
        or totals.get("direction")
        or ""
    ).upper()
    market_total = totals.get("market_total")

    if direction in {"OVER", "UNDER"} and market_total is not None:
        return f"{direction} {market_total:g}"

    return ""


def adapt_mlb_totals_game(
    game: dict,
    *,
    generated_at: str | None = None,
) -> Recommendation | None:
    totals = game.get("totals_model")

    if not isinstance(totals, dict):
        return None

    selection = _selection(totals)

    if not selection:
        return None

    odds = game.get("odds", {})
    if not isinstance(odds, dict):
        odds = {}

    total_quote = odds.get("totals", {})
    if not isinstance(total_quote, dict):
        total_quote = {}

    direction = str(totals.get("selection") or totals.get("direction") or "").upper()
    price_key = "over_odds" if direction == "OVER" else "under_odds"
    sportsbook = total_quote.get("sportsbook")
    price = total_quote.get(price_key)
    real_market_loaded = bool(total_quote.get("real_market_loaded"))

    market_quote = MarketQuote(
        sportsbook=sportsbook if real_market_loaded else None,
        odds=price if real_market_loaded else None,
        line=totals.get("market_total"),
        updated_at=total_quote.get("last_updated"),
        source="mlb_totals_card" if real_market_loaded else None,
    )

    betting = totals.get("betting_recommendation", {})
    if not isinstance(betting, dict):
        betting = {}

    return Recommendation(
        sport="BASEBALL",
        league="MLB",
        event_id=str(_first_present(game.get("game_id"), total_quote.get("event_id"), odds.get("event_id")) or ""),
        matchup=_matchup_text(game),
        event_time=_first_present(total_quote.get("commence_time"), odds.get("commence_time"), game.get("commence_time")),
        market="totals",
        selection=selection,
        model_probability=None,
        market_probability=None,
        edge_pct=None,
        expected_value_pct=None,
        hammer_score=float(betting.get("recommendation_score") or totals.get("recommendation_score") or 0),
        recommendation=_canonical_recommendation(betting.get("recommendation") or totals.get("recommendation")),
        confidence=betting.get("confidence") or totals.get("betting_confidence"),
        stars=betting.get("stars") or totals.get("stars"),
        market_quote=market_quote,
        reasons=totals.get("reasons", []),
        components=betting.get("score_components", {}),
        source_signals={
            "source": "mlb_totals_card",
            "totals_recommendation": totals.get("recommendation"),
            "totals_edge_runs": totals.get("edge"),
            "projected_total": totals.get("projected_total"),
            "market_total": totals.get("market_total"),
        },
        tags=["mlb", "totals", "real_market" if real_market_loaded else "model_only"],
        generated_at=generated_at or game.get("generated_at"),
    )


def adapt_mlb_totals_card(card: dict) -> list[Recommendation]:
    generated_at = card.get("generated_at")
    recommendations = []

    for game in card.get("games", []):
        if not isinstance(game, dict):
            continue

        recommendation = adapt_mlb_totals_game(
            game,
            generated_at=generated_at,
        )

        if recommendation is not None:
            recommendations.append(recommendation)

    return recommendations


def _matchup_text(game: dict) -> str:
    matchup = game.get("matchup", {})

    if isinstance(matchup, dict):
        away = matchup.get("away", "Away")
        home = matchup.get("home", "Home")
        return f"{away} @ {home}"

    return str(matchup or "Unknown MLB Matchup")
