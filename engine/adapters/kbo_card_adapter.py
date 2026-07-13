from __future__ import annotations

from typing import Any

from engine.core import (
    MarketQuote,
    Recommendation,
)


def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    try:
        if value in [None, "", "None", "N/A", "-", "--"]:
            return default

        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_probability(
    value: Any,
) -> float | None:
    number = safe_float(value)

    if number is None:
        return None

    if number > 1:
        number = number / 100

    return max(
        0.0,
        min(1.0, number),
    )


def extract_games(card: dict) -> list[dict]:
    for key in [
        "games",
        "recommendations",
        "matchups",
    ]:
        rows = card.get(key)

        if isinstance(rows, list):
            return rows

    return []


def team_name(
    row: dict,
    side: str,
) -> str:
    blob = row.get(side)

    if isinstance(blob, dict):
        return str(
            blob.get("team")
            or blob.get("name")
            or ""
        )

    return str(
        row.get(f"{side}_team")
        or row.get(f"{side}_name")
        or ""
    )


def matchup_text(row: dict) -> str:
    explicit = (
        row.get("matchup")
        or row.get("game")
    )

    if explicit:
        return str(explicit)

    away = team_name(row, "away")
    home = team_name(row, "home")

    if away and home:
        return f"{away} @ {home}"

    return "Unknown KBO Matchup"


def extract_selection(row: dict) -> str:
    selection = (
        row.get("selection")
        or row.get("pick")
        or row.get("recommended_team")
        or row.get("recommendation")
    )

    if not selection:
        return ""

    selection_text = str(selection)

    away = team_name(row, "away")
    home = team_name(row, "home")

    if away and away.lower() in selection_text.lower():
        return away

    if home and home.lower() in selection_text.lower():
        return home

    return selection_text


def extract_model_probability(
    row: dict,
) -> float | None:
    direct = (
        row.get("model_probability")
        or row.get("model_win_probability")
        or row.get("model_win_pct")
        or row.get("win_probability")
    )

    probability = normalize_probability(direct)

    if probability is not None:
        return probability

    selection = extract_selection(row)

    for side in ["away", "home"]:
        blob = row.get(side)

        if not isinstance(blob, dict):
            continue

        blob_team = str(
            blob.get("team")
            or blob.get("name")
            or ""
        )

        if (
            selection
            and blob_team
            and blob_team.lower()
            not in selection.lower()
            and selection.lower()
            not in blob_team.lower()
        ):
            continue

        value = (
            blob.get("model_probability")
            or blob.get("model_win_probability")
            or blob.get("model_win_pct")
            or blob.get("win_probability")
        )

        probability = normalize_probability(value)

        if probability is not None:
            return probability

    return None


def extract_hammer_score(row: dict) -> float:
    for key in [
        "hammer_score",
        "confidence",
        "model_score",
        "stack_score",
        "score",
    ]:
        value = safe_float(row.get(key))

        if value is not None:
            return max(
                0.0,
                min(100.0, value),
            )

    probability = extract_model_probability(row)

    if probability is not None:
        return probability * 100

    return 0.0


def build_market_quote(row: dict) -> MarketQuote:
    sportsbook = (
        row.get("sportsbook")
        or row.get("book")
    )

    odds = (
        row.get("book_odds")
        or row.get("odds")
        or row.get("moneyline")
    )

    return MarketQuote(
        sportsbook=sportsbook,
        odds=odds,
        line=row.get("line"),
        implied_probability=row.get(
            "market_probability"
        ),
        no_vig_probability=row.get(
            "market_no_vig_probability"
        ),
        updated_at=row.get(
            "market_updated_at"
        ),
        is_live=bool(
            row.get("is_live", False)
        ),
        source=(
            "kbo_card"
            if sportsbook and odds is not None
            else None
        ),
    )


def build_reasons(row: dict) -> list[str]:
    reasons = row.get("reasons")

    if isinstance(reasons, list):
        return [
            str(reason)
            for reason in reasons
            if reason
        ]

    generated = []

    starter = safe_float(
        row.get("starter_score")
    )

    offense = safe_float(
        row.get("offense_score")
    )

    bullpen = safe_float(
        row.get("bullpen_score")
    )

    recent = safe_float(
        row.get("recent_score")
        or row.get("recent_form_score")
    )

    if starter is not None:
        generated.append(
            f"Starter score: {starter:.1f}."
        )

    if offense is not None:
        generated.append(
            f"Offense score: {offense:.1f}."
        )

    if bullpen is not None:
        generated.append(
            f"Bullpen score: {bullpen:.1f}."
        )

    if recent is not None:
        generated.append(
            f"Recent form score: {recent:.1f}."
        )

    if not generated:
        generated.append(
            "KBO model recommendation."
        )

    return generated


def adapt_kbo_row(
    row: dict,
    *,
    generated_at: str | None = None,
) -> Recommendation | None:
    selection = extract_selection(row)

    if not selection:
        return None

    market_quote = build_market_quote(row)

    event_id = (
        row.get("game_id")
        or row.get("event_id")
        or row.get("game_pk")
    )

    if event_id is not None:
        event_id = str(event_id)

    market = str(
        row.get("market_type")
        or row.get("market")
        or "moneyline"
    ).lower()

    recommendation = Recommendation(
        sport="BASEBALL",
        league="KBO",
        event_id=event_id,
        matchup=matchup_text(row),
        event_time=(
            row.get("commence_time")
            or row.get("game_time")
            or row.get("start_time")
        ),
        market=market,
        selection=selection,
        model_probability=(
            extract_model_probability(row)
        ),
        market_probability=(
            row.get("market_probability")
        ),
        edge_pct=(
            row.get("edge_pct")
            or row.get("edge")
        ),
        expected_value_pct=row.get(
            "expected_value_pct"
        ),
        hammer_score=(
            extract_hammer_score(row)
        ),
        recommendation=(
            row.get("recommendation_label")
            or row.get("bet_grade")
        ),
        confidence=row.get(
            "confidence_label"
        ),
        stars=row.get("stars"),
        units=row.get("units"),
        market_quote=market_quote,
        reasons=build_reasons(row),
        components={
            "starter": row.get(
                "starter_score"
            ),
            "offense": row.get(
                "offense_score"
            ),
            "bullpen": row.get(
                "bullpen_score"
            ),
            "recent": (
                row.get("recent_score")
                or row.get(
                    "recent_form_score"
                )
            ),
            "home": row.get(
                "home_score"
            ),
            "market": row.get(
                "market_score"
            ),
        },
        source_signals={
            "source": "kbo_card",
            "original_recommendation": (
                row.get("recommendation")
            ),
        },
        tags=[
            "kbo",
            "baseball",
            (
                "real_market"
                if market_quote.has_real_price
                else "model_only"
            ),
        ],
        status=(
            "live"
            if row.get("is_live")
            else "pregame"
        ),
        generated_at=(
            generated_at
            or row.get("generated_at")
        ),
    )

    return recommendation


def adapt_kbo_card(
    card: dict,
) -> list[Recommendation]:
    generated_at = card.get(
        "generated_at"
    )

    recommendations = []

    for row in extract_games(card):
        if not isinstance(row, dict):
            continue

        recommendation = adapt_kbo_row(
            row,
            generated_at=generated_at,
        )

        if recommendation is not None:
            recommendations.append(
                recommendation
            )

    return recommendations
