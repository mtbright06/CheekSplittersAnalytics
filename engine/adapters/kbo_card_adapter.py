from __future__ import annotations

from datetime import UTC, datetime

from engine.core.consensus import (
    ConsensusSignal,
    build_consensus,
)

from typing import Any

from engine.core import (
    MarketQuote,
    Recommendation,
)
from engine.core.pregame_eligibility import PregameEligibilityReason


def _authoritative_scheduled_start(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None

    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_kbo_row(row: dict) -> dict:
    """Expose the current nested KBO card shape to the legacy registry adapter."""
    model = row.get("model")
    odds = row.get("odds")
    teams = row.get("teams")
    matchup = row.get("matchup")

    if not isinstance(model, dict):
        model = {}
    if not isinstance(odds, dict):
        odds = {}
    if not isinstance(teams, dict):
        teams = {}
    if not isinstance(matchup, dict):
        matchup = {}

    away = teams.get("away", {"name": matchup.get("away")})
    home = teams.get("home", {"name": matchup.get("home")})
    away_name = away.get("name") if isinstance(away, dict) else away
    home_name = home.get("name") if isinstance(home, dict) else home
    matchup_value = row.get("matchup")

    if isinstance(matchup_value, dict):
        matchup_value = f"{away_name or 'Away'} @ {home_name or 'Home'}"

    return {
        **row,
        "matchup": matchup_value,
        "away": away,
        "home": home,
        "selection": model.get("play"),
        "model_strength": (
            model.get("model_strength")
            if model.get("model_strength") is not None
            else model.get("model_probability")
        ),
        "model_probability": (
            model.get("model_probability")
            if model.get("model_probability") is not None
            else model.get("model_strength")
        ),
        "model_confidence": (
            model.get("model_confidence")
            if model.get("model_confidence") is not None
            else model.get("confidence")
        ),
        "hammer_score": model.get("confidence"),
        "confidence": model.get("confidence"),
        "recommendation_label": model.get("recommendation"),
        "reasons": model.get("reasons", row.get("reasons")),
        "market_type": model.get("market") or odds.get("market"),
        "sportsbook": odds.get("sportsbook"),
        "book": odds.get("provider"),
        "book_odds": odds.get("moneyline"),
        "market_probability": odds.get("book_probability"),
        "market_updated_at": odds.get("last_updated"),
    }


def score_supports(
    value: Any,
    threshold: float = 60.0,
) -> bool | None:
    number = safe_float(value)

    if number is None:
        return None

    return number >= threshold


def build_kbo_consensus(
    row: dict,
):
    signals = [
        ConsensusSignal(
            name="KBO Model",
            supports=score_supports(
                extract_hammer_score(row)
            ),
            score=extract_hammer_score(
                row
            ),
            weight=1.4,
            source="kbo_model",
        ),
        ConsensusSignal(
            name="Starter",
            supports=score_supports(
                row.get(
                    "starter_score"
                )
            ),
            score=row.get(
                "starter_score"
            ),
            weight=1.2,
            source="starter",
        ),
        ConsensusSignal(
            name="Offense",
            supports=score_supports(
                row.get(
                    "offense_score"
                )
            ),
            score=row.get(
                "offense_score"
            ),
            weight=1.0,
            source="offense",
        ),
        ConsensusSignal(
            name="Bullpen",
            supports=score_supports(
                row.get(
                    "bullpen_score"
                )
            ),
            score=row.get(
                "bullpen_score"
            ),
            weight=0.8,
            source="bullpen",
        ),
        ConsensusSignal(
            name="Recent Form",
            supports=score_supports(
                row.get(
                    "recent_score"
                )
                or row.get(
                    "recent_form_score"
                )
            ),
            score=(
                row.get(
                    "recent_score"
                )
                or row.get(
                    "recent_form_score"
                )
            ),
            weight=0.7,
            source="recent_form",
        ),
    ]

    return build_consensus(
        signals
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


def looks_like_time_or_venue(
    value: str,
) -> bool:
    text = str(value or "").strip().lower()

    if not text:
        return False

    time_markers = [
        "am",
        "pm",
        ":",
    ]

    venue_markers = [
        "stadium",
        "park",
        "field",
        "dome",
        "munhak",
        "jamsil",
        "suwon",
        "gocheok",
        "changwon",
        "daejeon",
        "daegu",
        "gwangju",
        "busan",
        "incheon",
    ]

    has_time = (
        any(marker in text for marker in time_markers)
        and any(character.isdigit() for character in text)
    )

    has_venue = any(
        marker in text
        for marker in venue_markers
    )

    return has_time or has_venue

def team_name(
    row: dict,
    side: str,
) -> str:
    nested_keys = [
        side,
        f"{side}_team",
        f"{side}Team",
    ]

    for key in nested_keys:
        blob = row.get(key)

        if isinstance(blob, dict):
            for name_key in [
                "team_name",
                "team",
                "name",
                "display_name",
                "displayName",
                "short_name",
                "shortName",
            ]:
                value = blob.get(name_key)

                if value:
                    return str(value).strip()

        elif isinstance(blob, str):
            value = blob.strip()

            if value and not looks_like_time_or_venue(value):
                return value

    flat_keys = [
        f"{side}_team_name",
        f"{side}_name",
        f"{side}_team",
        f"{side}TeamName",
        f"{side}Name",
    ]

    for key in flat_keys:
        value = row.get(key)

        if value:
            value = str(value).strip()

            if not looks_like_time_or_venue(value):
                return value

    return ""


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
    candidates = [
        row.get("selection"),
        row.get("pick"),
        row.get("recommended_team"),
        row.get("recommended_side"),
        row.get("bet_team"),
        row.get("team_pick"),
    ]

    away = team_name(row, "away")
    home = team_name(row, "home")

    for candidate in candidates:
        if not candidate:
            continue

        selection_text = str(candidate).strip()

        if looks_like_time_or_venue(selection_text):
            continue

        if away and (
            away.lower() in selection_text.lower()
            or selection_text.lower() in away.lower()
        ):
            return away

        if home and (
            home.lower() in selection_text.lower()
            or selection_text.lower() in home.lower()
        ):
            return home

    recommendation_text = str(
        row.get("recommendation")
        or ""
    ).strip()

    if recommendation_text:
        if away and away.lower() in recommendation_text.lower():
            return away

        if home and home.lower() in recommendation_text.lower():
            return home

    selected_side = str(
        row.get("side")
        or row.get("recommended_side")
        or ""
    ).strip().lower()

    if selected_side == "away":
        return away

    if selected_side == "home":
        return home

    return ""


def extract_model_probability(
    row: dict,
) -> float | None:
    direct = (
        row.get("model_strength")
        or row.get("model_probability")
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

    sportsbook_text = str(
        sportsbook or ""
    ).strip()

    is_mock = sportsbook_text.lower() in {
        "mock odds",
        "mock",
        "test book",
        "synthetic",
    }

    if is_mock:
        sportsbook = None
        odds = None

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
    row = canonical_kbo_row(row)

    scheduled_start_at = _authoritative_scheduled_start(
        row.get("scheduled_start_at")
        or row.get("commence_time")
    )
    pregame_eligible = (
        row.get("pregame_eligible")
        if row.get("pregame_eligible") is not None
        else scheduled_start_at is not None
    )
    pregame_eligibility_reason = (
        row.get("pregame_eligibility_reason")
        or (
            PregameEligibilityReason.GAME_NOT_STARTED.value
            if pregame_eligible
            else PregameEligibilityReason.UNVERIFIED.value
        )
    )

    if (
        pregame_eligible is not True
        or row.get("is_live")
        or str(pregame_eligibility_reason)
        != PregameEligibilityReason.GAME_NOT_STARTED.value
    ):
        return None

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

    consensus = build_kbo_consensus(
        row
    )

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
        scheduled_start_at=scheduled_start_at,
        market=market,
        selection=selection,
        model_probability=(
            extract_model_probability(row)
        ),
        model_win_strength=(
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
        model_confidence=row.get("model_confidence"),
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
            "model_strength": row.get("model_strength"),
            "model_confidence": row.get("model_confidence"),
        },

        source_signals={
            "source": "kbo_card",
            "original_recommendation": (
                row.get("recommendation")
            ),
            "consensus": (
                consensus.to_dict()
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
        pregame_eligible=pregame_eligible,
        pregame_eligibility_reason=pregame_eligibility_reason,
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
