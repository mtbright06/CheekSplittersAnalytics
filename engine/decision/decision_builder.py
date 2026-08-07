from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.decision.hammer_score import (
    HammerInputs,
    calculate_hammer_score,
    clamp,
    normalize_probability,
    safe_float,
)

from engine.core.consensus import (
    ConsensusSignal,
    build_consensus,
)

ROOT = Path(__file__).resolve().parents[2]
CARDS_DIR = ROOT / "output" / "cards"
CONFIG_DIR = ROOT / "config"

MLB_CARD_PATH = CARDS_DIR / "mlb_card.json"
FIRST5_CARD_PATH = CARDS_DIR / "first5_card.json"
FIRST5_MARKET_PATH = CARDS_DIR / "first5_market_card.json"
BOMB_CARD_PATH = CARDS_DIR / "bomb_lab_card.json"
WEIGHTS_PATH = CONFIG_DIR / "decision_weights.json"
OUTPUT_PATH = CARDS_DIR / "decision_card.json"


def load_json(
    path: Path,
    default: Any,
) -> Any:
    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def normalized_text(value: Any) -> str:
    return " ".join(
        str(value or "")
        .lower()
        .replace("@", " ")
        .replace("vs", " ")
        .replace(".", "")
        .replace("-", " ")
        .split()
    )


def compact_team_name(value: Any) -> str:
    text = normalized_text(value)

    replacements = {
        "arizona diamondbacks": "diamondbacks",
        "atlanta braves": "braves",
        "baltimore orioles": "orioles",
        "boston red sox": "red sox",
        "chicago cubs": "cubs",
        "chicago white sox": "white sox",
        "cincinnati reds": "reds",
        "cleveland guardians": "guardians",
        "colorado rockies": "rockies",
        "detroit tigers": "tigers",
        "houston astros": "astros",
        "kansas city royals": "royals",
        "los angeles angels": "angels",
        "los angeles dodgers": "dodgers",
        "miami marlins": "marlins",
        "milwaukee brewers": "brewers",
        "minnesota twins": "twins",
        "new york mets": "mets",
        "new york yankees": "yankees",
        "athletics": "athletics",
        "philadelphia phillies": "phillies",
        "pittsburgh pirates": "pirates",
        "san diego padres": "padres",
        "san francisco giants": "giants",
        "seattle mariners": "mariners",
        "st louis cardinals": "cardinals",
        "tampa bay rays": "rays",
        "texas rangers": "rangers",
        "toronto blue jays": "blue jays",
        "washington nationals": "nationals",
    }

    return replacements.get(text, text)


def teams_match(
    left: Any,
    right: Any,
) -> bool:
    left_name = compact_team_name(left)
    right_name = compact_team_name(right)

    if not left_name or not right_name:
        return False

    return (
        left_name == right_name
        or left_name in right_name
        or right_name in left_name
    )


def matchup_text(game: dict) -> str:
    matchup = game.get("matchup")

    if isinstance(matchup, dict):
        away = matchup.get("away")
        home = matchup.get("home")

        if away and home:
            return f"{away} @ {home}"

    if matchup:
        return str(matchup)

    game_text = game.get("game")

    if game_text:
        return str(game_text)

    away = extract_team_name(game, "away")
    home = extract_team_name(game, "home")

    if away and home:
        return f"{away} @ {home}"

    return ""


def game_match(
    source_game: dict,
    target_game: dict,
) -> bool:
    source_pk = (
        source_game.get("game_pk")
        or source_game.get("game_id")
    )
    target_pk = (
        target_game.get("game_pk")
        or target_game.get("game_id")
    )

    if source_pk and target_pk and str(source_pk) == str(target_pk):
        return True

    source_matchup = normalized_text(matchup_text(source_game))
    target_matchup = normalized_text(matchup_text(target_game))

    return bool(
        source_matchup
        and target_matchup
        and (
            source_matchup == target_matchup
            or source_matchup in target_matchup
            or target_matchup in source_matchup
        )
    )


def find_matching_game(
    target: dict,
    candidates: list[dict],
) -> dict:
    for candidate in candidates:
        if game_match(target, candidate):
            return candidate

    return {}


def extract_team_blob(
    game: dict,
    side: str,
) -> dict:
    teams = game.get("teams", {})

    if isinstance(teams, dict):
        value = teams.get(side)

        if isinstance(value, dict):
            return value

    value = game.get(side)

    if isinstance(value, dict):
        return value

    return {}


def extract_team_name(
    game: dict,
    side: str,
) -> str:
    blob = extract_team_blob(game, side)

    if blob:
        name = blob.get("team") or blob.get("name")

        if name:
            return str(name)

    matchup = game.get("matchup")

    if isinstance(matchup, dict):
        name = matchup.get(side)

        if name:
            return str(name)

    return str(game.get(f"{side}_team") or "")


def extract_matchup(game: dict) -> str:
    return matchup_text(game) or "Unknown Matchup"


def extract_model_probability(
    game: dict,
    team_name: str,
) -> float | None:
    model = game.get("model", {})

    if not isinstance(model, dict):
        model = {}

    recommended = str(
        model.get("play")
        or model.get("selection")
        or model.get("recommended_team")
        or game.get("pick")
        or game.get("recommended_play")
        or game.get("recommendation")
        or ""
    )

    model_probability = (
        model.get("model_win_strength")
        or model.get("model_probability")
        or model.get("model_win_probability")
        or model.get("model_win_pct")
        or game.get("model_win_strength")
        or game.get("model_win_probability")
        or game.get("model_win_pct")
        or game.get("model_probability")
    )

    if model_probability is not None:
        probability = normalize_probability(model_probability)

        if probability is not None:
            if team_name and recommended:
                if teams_match(team_name, recommended):
                    return probability

                return 1 - probability

            return probability

    for side in ["away", "home"]:
        blob = extract_team_blob(game, side)
        blob_team = blob.get("team") or blob.get("name")

        if not teams_match(blob_team, team_name):
            continue

        probability = (
            blob.get("model_win_probability")
            or blob.get("model_win_pct")
            or blob.get("win_probability")
        )

        normalized = normalize_probability(probability)

        if normalized is not None:
            return normalized

    return None


def extract_component_score(
    game: dict,
    team_name: str,
    keys: list[str],
) -> float | None:
    model = game.get("model", {})

    if isinstance(model, dict):
        component_scores = model.get("component_scores", {})

        if isinstance(component_scores, dict):
            selected = component_scores.get("selected", {})
            opponent = component_scores.get("opponent", {})
            model_choice = extract_mlb_choice(game)

            selected_blob = (
                selected
                if teams_match(team_name, model_choice)
                else opponent
            )

            if isinstance(selected_blob, dict):
                for key in keys:
                    value = safe_float(selected_blob.get(key))

                    if value is not None:
                        return clamp(value)

    for side in ["away", "home"]:
        blob = extract_team_blob(game, side)
        blob_team = blob.get("team") or blob.get("name")

        if not teams_match(blob_team, team_name):
            continue

        for key in keys:
            value = safe_float(blob.get(key))

            if value is not None:
                return clamp(value)

    for key in keys:
        value = safe_float(game.get(key))

        if value is not None:
            return clamp(value)

    return None


def extract_mlb_choice(game: dict) -> str:
    model = game.get("model", {})

    if not isinstance(model, dict):
        model = {}

    market_edge = game.get("market_edge", {})

    if not isinstance(market_edge, dict):
        market_edge = {}

    explicit = (
        model.get("play")
        or model.get("selection")
        or model.get("recommended_team")
        or market_edge.get("selection")
        or game.get("pick")
        or game.get("recommended_team")
        or game.get("recommended_play")
        or game.get("recommendation")
    )

    if explicit:
        explicit_text = str(explicit)
        away = extract_team_name(game, "away")
        home = extract_team_name(game, "home")

        if teams_match(explicit_text, away):
            return away

        if teams_match(explicit_text, home):
            return home

    away_blob = extract_team_blob(game, "away")
    home_blob = extract_team_blob(game, "home")

    away_probability = normalize_probability(
        away_blob.get("model_win_probability")
        or away_blob.get("model_win_pct")
        or away_blob.get("win_probability")
    )

    home_probability = normalize_probability(
        home_blob.get("model_win_probability")
        or home_blob.get("model_win_pct")
        or home_blob.get("win_probability")
    )

    if (
        away_probability is not None
        and home_probability is not None
    ):
        if away_probability >= home_probability:
            return extract_team_name(game, "away")

        return extract_team_name(game, "home")

    return ""


def extract_first5_choice(game: dict) -> str:
    f5_ml = game.get("f5_ml", {})

    choice = (
        game.get("f5_ml_pick")
        or game.get("f5_moneyline_pick")
        or (
            f5_ml.get("lean")
            if isinstance(f5_ml, dict)
            else None
        )
        or game.get("recommended_team")
        or game.get("lean")
        or game.get("recommendation")
    )

    if choice:
        away = extract_team_name(game, "away")
        home = extract_team_name(game, "home")

        if teams_match(choice, away):
            return away

        if teams_match(choice, home):
            return home

    return ""


def first5_score_for_team(
    game: dict,
    team_name: str,
) -> float | None:
    explicit_score = (
        game.get("f5_score")
        or game.get("decision_score")
        or game.get("confidence")
    )

    score = safe_float(explicit_score)

    if score is not None:
        choice = extract_first5_choice(game)

        if not choice or teams_match(choice, team_name):
            return clamp(score)

        return clamp(100 - score)

    away_blob = extract_team_blob(game, "away")
    home_blob = extract_team_blob(game, "home")

    away_runs = safe_float(
        away_blob.get("projected_f5_runs")
    )

    home_runs = safe_float(
        home_blob.get("projected_f5_runs")
    )

    if away_runs is None or home_runs is None:
        return None

    run_difference = away_runs - home_runs
    away_score = clamp(50 + (run_difference * 13))
    home_score = clamp(50 - (run_difference * 13))

    if teams_match(team_name, away_blob.get("team")):
        return away_score

    if teams_match(team_name, home_blob.get("team")):
        return home_score

    return None


def find_bomb_for_team(
    team_name: str,
    bomb_pitchers: list[dict],
) -> dict:
    matches = [
        item
        for item in bomb_pitchers
        if teams_match(item.get("opponent"), team_name)
    ]

    if not matches:
        return {}

    matches.sort(
        key=lambda item: safe_float(
            item.get("bomb_score"),
            0,
        )
        or 0,
        reverse=True,
    )

    return matches[0]


def extract_market_for_team(
    market_game: dict,
    team_name: str,
) -> dict:
    if not market_game:
        return {}

    away_market = market_game.get("away_market", {})
    home_market = market_game.get("home_market", {})

    if teams_match(away_market.get("team"), team_name):
        return away_market

    if teams_match(home_market.get("team"), team_name):
        return home_market

    best = market_game.get("best_market_side", {})

    if teams_match(best.get("team"), team_name):
        return best

    return {}


def extract_mlb_market(
    game: dict,
    team_name: str,
) -> dict:
    odds = game.get("odds", {})
    market_edge = game.get("market_edge", {})

    if not isinstance(odds, dict):
        odds = {}

    if not isinstance(market_edge, dict):
        market_edge = {}

    selection = (
        market_edge.get("selection")
        or odds.get("selection")
    )

    if not teams_match(selection, team_name):
        return {}

    # A locked SSRP is the canonical quote for the MLB decision artifact.
    # Keep its book, price, probability, and timestamp together rather than
    # mixing it with the separately displayed current quote.
    reference_locked = (
        market_edge.get("reference_status")
        == "LOCKED"
    )

    if reference_locked:
        book_odds = (
            market_edge.get("american_odds")
            or market_edge.get("moneyline")
        )
        book_probability = (
            market_edge.get(
                "reference_implied_probability"
            )
            or normalize_probability(
                market_edge.get("book_probability")
            )
        )
        sportsbook = market_edge.get("sportsbook")
        market_updated_at = market_edge.get(
            "reference_captured_at"
        )
        quote_source = "sharpstack_reference_price"
    else:
        book_odds = (
            odds.get("american_odds")
            or odds.get("moneyline")
        )
        book_probability = (
            odds.get("book_probability")
            or odds.get("implied_probability")
        )
        sportsbook = odds.get("sportsbook")
        market_updated_at = (
            odds.get("quote_updated_at_utc")
            or odds.get("last_updated")
            or odds.get("updated_at")
        )
        quote_source = "current_quote"

    quote_identity = ":".join(
        str(value)
        for value in (
            quote_source,
            market_edge.get("provider_event_id")
            or odds.get("event_id"),
            selection,
            sportsbook,
            book_odds,
        )
        if value not in {None, ""}
    )

    return {
        "team": team_name,
        "recommendation": (
            game.get("model", {}).get("recommendation", "")
            if isinstance(game.get("model"), dict)
            else ""
        ),
        "book_odds": book_odds,
        "book_raw_implied_probability": book_probability,
        "book_no_vig_probability": book_probability,
        "edge_pct": (
            market_edge.get("edge")
            or odds.get("edge_pct")
        ),
        "expected_value_pct": (
            market_edge.get("expected_roi")
            or odds.get("expected_value_pct")
        ),
        "sportsbook": sportsbook,
        "market_updated_at": market_updated_at,
        "quote_identity": quote_identity or None,
        "quote_source": quote_source,
        # SSRP quote fields above are canonical for edge. Current-quote
        # freshness stays explicit display context and is never substituted
        # into the SSRP quote.
        "current_freshness_status": odds.get(
            "freshness_status"
        ),
        "current_freshness_reason": odds.get(
            "freshness_reason"
        ),
        "current_quote_age_minutes": odds.get(
            "quote_age_minutes"
        ),
    }


def module_vote(
    selected_team: str,
    module_team: str,
) -> int:
    if not selected_team or not module_team:
        return 0

    if teams_match(selected_team, module_team):
        return 1

    return -1

def consensus_signal_from_vote(
    name: str,
    vote: int,
    *,
    score: float | None = None,
    reason: str | None = None,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ConsensusSignal:
    supports: bool | None

    if vote == 1:
        supports = True
    elif vote == -1:
        supports = False
    else:
        supports = None

    return ConsensusSignal(
        name=name,
        supports=supports,
        score=score,
        reason=reason,
        source=source,
        metadata=metadata or {},
    )

def determine_primary_team(
    mlb_game: dict,
    first5_game: dict,
    bomb_pitchers: list[dict],
) -> str:
    mlb_choice = extract_mlb_choice(mlb_game)

    if mlb_choice:
        return mlb_choice

    first5_choice = extract_first5_choice(first5_game)

    if first5_choice:
        return first5_choice

    away = extract_team_name(mlb_game, "away")
    home = extract_team_name(mlb_game, "home")

    away_bomb = find_bomb_for_team(away, bomb_pitchers)
    home_bomb = find_bomb_for_team(home, bomb_pitchers)

    away_score = safe_float(away_bomb.get("bomb_score"), 0) or 0
    home_score = safe_float(home_bomb.get("bomb_score"), 0) or 0

    if away_score > home_score:
        return away

    if home:
        return home

    return away


def build_reasons(
    team_name: str,
    mlb_probability: float | None,
    first5_score: float | None,
    bomb: dict,
    market: dict,
    starter_score: float | None,
    offense_score: float | None,
    bullpen_score: float | None,
    agreement: int,
    contradictions: int,
) -> list[str]:
    reasons: list[str] = []

    if mlb_probability is not None:
        reasons.append(
            f"Full-game model gives {team_name} "
            f"{mlb_probability:.1%} win probability."
        )

    if first5_score is not None and first5_score >= 60:
        reasons.append(
            f"First 5 model supports the side "
            f"with a {first5_score:.1f} score."
        )

    bomb_score = safe_float(bomb.get("bomb_score"))

    if bomb_score is not None and bomb_score >= 55:
        reasons.append(
            f"Bomb Lab supports the offense "
            f"with a {bomb_score:.1f} attack score."
        )

    if starter_score is not None and starter_score >= 60:
        reasons.append(
            f"Starting-pitcher matchup grades positively "
            f"at {starter_score:.1f}."
        )

    if offense_score is not None and offense_score >= 60:
        reasons.append(
            f"Offensive profile grades positively "
            f"at {offense_score:.1f}."
        )

    if bullpen_score is not None and bullpen_score >= 60:
        reasons.append(
            f"Bullpen profile supports the full-game side "
            f"at {bullpen_score:.1f}."
        )

    market_edge = safe_float(market.get("edge_pct"))

    if market_edge is not None:
        reasons.append(
            f"Real market comparison shows "
            f"{market_edge:+.1f}% model edge."
        )

    if agreement >= 2:
        reasons.append(
            f"{agreement} SharpStack modules agree on this side."
        )

    if contradictions > 0:
        reasons.append(
            f"{contradictions} module signal"
            f"{'s' if contradictions != 1 else ''} disagree."
        )

    if not market:
        reasons.append(
            "Market price is unavailable; recommendation is model-only."
        )

    if not reasons:
        reasons.append(
            "Insufficient signal convergence for an actionable play."
        )

    return reasons[:7]


def build_decision_card() -> dict:
    mlb_card = load_json(MLB_CARD_PATH, {})
    first5_card = load_json(FIRST5_CARD_PATH, {})
    first5_market_card = load_json(FIRST5_MARKET_PATH, {})
    bomb_card = load_json(BOMB_CARD_PATH, {})
    weights = load_json(WEIGHTS_PATH, {})

    mlb_games = mlb_card.get("games", [])
    first5_games = first5_card.get("games", [])
    market_games = first5_market_card.get("games", [])
    bomb_pitchers = bomb_card.get("pitchers", [])

    decisions = []

    for mlb_game in mlb_games:
        first5_game = find_matching_game(
            mlb_game,
            first5_games,
        )

        market_game = find_matching_game(
            mlb_game,
            market_games,
        )

        selected_team = determine_primary_team(
            mlb_game,
            first5_game,
            bomb_pitchers,
        )

        if not selected_team:
            continue

        matchup = extract_matchup(mlb_game)
        away_team = extract_team_name(mlb_game, "away")
        home_team = extract_team_name(mlb_game, "home")

        mlb_choice = extract_mlb_choice(mlb_game)
        model_recommendation = str(
            mlb_game.get("model", {}).get(
                "recommendation",
            )
            if isinstance(mlb_game.get("model"), dict)
            else ""
        ).strip() or "PASS"
        v2_authority = (
            mlb_game.get("model", {}).get("v2_authority")
            if isinstance(mlb_game.get("model"), dict)
            else None
        )
        if not isinstance(v2_authority, dict):
            v2_authority = {}
        v2_candidate_authority = (
            mlb_game.get("model", {}).get("v2_candidate_authority")
            if isinstance(mlb_game.get("model"), dict)
            else None
        )
        if not isinstance(v2_candidate_authority, dict):
            v2_candidate_authority = {}
        first5_choice = extract_first5_choice(first5_game)

        bomb = find_bomb_for_team(
            selected_team,
            bomb_pitchers,
        )

        market = extract_market_for_team(
            market_game,
            selected_team,
        )

        first5_market_loaded = bool(
            market
            and market.get("book_odds") is not None
            and (
                market.get("book_no_vig_probability") is not None
                or market.get(
                    "book_raw_implied_probability"
                )
                is not None
            )
        )

        if not first5_market_loaded:
            market = extract_mlb_market(
                mlb_game,
                selected_team,
            )


        mlb_probability = extract_model_probability(
            mlb_game,
            selected_team,
        )

        mlb_model_score = (
            clamp(mlb_probability * 100)
            if mlb_probability is not None
            else None
        )

        first5_score = first5_score_for_team(
            first5_game,
            selected_team,
        )

        bomb_score = safe_float(
            bomb.get("bomb_score")
        )

        starter_score = extract_component_score(
            mlb_game,
            selected_team,
            [
                "starting_pitching",
                "starter_score",
                "pitcher_score",
                "starting_pitcher_score",
            ],
        )

        offense_score = extract_component_score(
            mlb_game,
            selected_team,
            [
                "offense",
                "offense_score",
                "hitting_score",
                "team_offense_score",
            ],
        )

        bullpen_score = extract_component_score(
            mlb_game,
            selected_team,
            [
                "bullpen",
                "bullpen_score",
                "relief_score",
            ],
        )

        park_score = safe_float(
            bomb.get("park_score")
            or mlb_game.get("park_score")
        )

        weather_score = safe_float(
            mlb_game.get("weather_score")
        )

        model_confidence = safe_float(
            (
                mlb_game.get("model", {}).get("model_confidence")
                if isinstance(mlb_game.get("model"), dict)
                else None
            )
            or (
                mlb_game.get("model", {}).get("confidence")
                if isinstance(mlb_game.get("model"), dict)
                else None
            )
            or mlb_game.get("model_confidence")
        )

        sample_confidence = safe_float(
            bomb.get("sample_confidence")
            or model_confidence
            or mlb_game.get("confidence")
        )

        market_edge = safe_float(
            market.get("edge_pct")
        )

        expected_value_pct = safe_float(
            market.get("expected_value_pct")
        )

        real_market_loaded = bool(
            market
            and market.get("book_odds") is not None
            and (
                market.get("book_no_vig_probability") is not None
                or market.get(
                    "book_raw_implied_probability"
                )
                is not None
            )
        )

        mlb_vote = module_vote(
            selected_team,
            mlb_choice,
        )

        first5_vote = module_vote(
            selected_team,
            first5_choice,
        )

        bomb_vote = 1 if bomb else 0

        consensus_signals = [
            consensus_signal_from_vote(
                "MLB Model",
                mlb_vote,
                score=mlb_model_score,
                reason=(
                    f"MLB model selects {mlb_choice}."
                    if mlb_choice
                    else "MLB model selection unavailable."
                ),
                source="mlb_model",
                metadata={
                    "selected_team": selected_team,
                    "module_team": mlb_choice,
                },
            ),
            consensus_signal_from_vote(
                "First 5",
                first5_vote,
                score=first5_score,
                reason=(
                    f"First 5 model selects {first5_choice}."
                    if first5_choice
                    else "First 5 selection unavailable."
                ),
                source="first5",
                metadata={
                    "selected_team": selected_team,
                    "module_team": first5_choice,
                },
            ),
            consensus_signal_from_vote(
                "Bomb Lab",
                bomb_vote,
                score=bomb_score,
                reason=(
                    f"Bomb Lab supports the {selected_team} offense."
                    if bomb
                    else "Bomb Lab signal unavailable."
                ),
                source="bomb_lab",
                metadata={
                    "selected_team": selected_team,
                    "module_team": bomb.get("opponent"),
                },
            ),
        ]

        consensus = build_consensus(
            consensus_signals
        )

        agreement = consensus.support_count
        contradictions = consensus.oppose_count

        hammer = calculate_hammer_score(
            HammerInputs(
                mlb_model_score=mlb_model_score,
                mlb_model_probability=mlb_probability,
                first5_score=first5_score,
                bomb_score=bomb_score,
                starter_score=starter_score,
                offense_score=offense_score,
                bullpen_score=bullpen_score,
                park_score=park_score,
                weather_score=weather_score,
                sample_confidence=sample_confidence,
                module_agreement=agreement,
                contradiction_count=contradictions,
                real_market_loaded=real_market_loaded,
            ),
            weights=weights,
        )

        reasons = build_reasons(
            team_name=selected_team,
            mlb_probability=mlb_probability,
            first5_score=first5_score,
            bomb=bomb,
            market=market,
            starter_score=starter_score,
            offense_score=offense_score,
            bullpen_score=bullpen_score,
            agreement=agreement,
            contradictions=contradictions,
        )

        decisions.append(
            {
                "game_pk": (
                    mlb_game.get("game_pk")
                    or mlb_game.get("game_id")
                ),
                "matchup": matchup,
                "away_team": away_team,
                "home_team": home_team,
                "selected_team": selected_team,
                "selection": selected_team,
                "market": "moneyline",
                "market_status": (
                    "REAL MARKET"
                    if real_market_loaded
                    else "MODEL ONLY"
                ),
                "hammer_score": hammer["hammer_score"],
                "base_score": hammer["base_score"],
                "agreement_bonus": hammer["agreement_bonus"],
                "contradiction_penalty": hammer[
                    "contradiction_penalty"
                ],
                "market_status_penalty": hammer[
                    "market_status_penalty"
                ],
                "real_market_loaded": hammer[
                    "real_market_loaded"
                ],
                # MLB model recommendations remain the betting authority.
                # Hammer is retained as a diagnostic validation layer.
                "recommendation": model_recommendation,
                "model_recommendation": model_recommendation,
                "v2_recommendation": v2_authority.get("recommendation"),
                "v2_authority": v2_authority,
                "v2_candidate_recommendation": (
                    v2_candidate_authority.get("recommendation")
                ),
                "v2_candidate_authority": v2_candidate_authority,
                "market_value_label": mlb_game.get(
                    "model", {}
                ).get("market_value_label"),
                "market_value_tone": mlb_game.get(
                    "model", {}
                ).get("market_value_tone"),
                "recommendation_explanation": mlb_game.get(
                    "model", {}
                ).get("recommendation_explanation", {}),
                "hammer_tier": hammer["recommendation"],
                "hammer_assessment": (
                    "Validated by Hammer"
                    if hammer["recommendation"]
                    in {"HAMMER", "BET", "LEAN"}
                    else (
                        "Below validation threshold / "
                        f"{hammer['confidence'].title()} confirmation"
                    )
                ),
                "model_win_strength": (
                    round(mlb_probability, 4)
                    if mlb_probability is not None
                    else None
                ),
                "model_confidence": model_confidence,
                "hammer_confidence": hammer["confidence"],
                # Compatibility alias for older consumers; authoritative
                # Hammer confidence is `hammer_confidence`.
                "confidence": hammer["confidence"],
                "stars": hammer["stars"],
                "consensus": consensus.to_dict(),
                "agreement_count": agreement,
                "contradiction_count": contradictions,
                "model_probability": (
                    round(mlb_probability, 4)
                    if mlb_probability is not None
                    else None
                ),
                "book_odds": market.get("book_odds"),
                "american_odds": market.get("book_odds"),
                "moneyline": market.get("book_odds"),
                "sportsbook": market.get("sportsbook"),
                "market_probability": market.get(
                    "book_raw_implied_probability"
                ),
                "market_no_vig_probability": market.get(
                    "book_no_vig_probability"
                ),
                "market_updated_at": market.get(
                    "market_updated_at"
                ),
                "quote_identity": market.get("quote_identity"),
                "quote_source": market.get("quote_source"),
                "commence_time": mlb_game.get("commence_time"),
                "scheduled_start_at": (
                    mlb_game.get("scheduled_start_at")
                    or mlb_game.get("commence_time")
                ),
                "pregame_eligible": mlb_game.get("pregame_eligible"),
                "pregame_eligibility_reason": mlb_game.get(
                    "pregame_eligibility_reason"
                ),
                "current_freshness_status": market.get(
                    "current_freshness_status"
                ),
                "current_freshness_reason": market.get(
                    "current_freshness_reason"
                ),
                "current_quote_age_minutes": market.get(
                    "current_quote_age_minutes"
                ),
                "market_edge_pct": market_edge,
                "expected_value_pct": expected_value_pct,
                "first5_score": (
                    round(first5_score, 1)
                    if first5_score is not None
                    else None
                ),
                "bomb_score": (
                    round(bomb_score, 1)
                    if bomb_score is not None
                    else None
                ),
                "starter_score": starter_score,
                "offense_score": offense_score,
                "bullpen_score": bullpen_score,
                "park_score": park_score,
                "weather_score": weather_score,
                "projected_total": (
                    mlb_game.get("totals_model", {}).get(
                        "projected_total"
                    )
                    if isinstance(
                        mlb_game.get("totals_model"),
                        dict,
                    )
                    else None
                ),
                "market_total": (
                    mlb_game.get("totals_model", {}).get(
                        "market_total"
                    )
                    if isinstance(
                        mlb_game.get("totals_model"),
                        dict,
                    )
                    else None
                ),
                "total_edge": (
                    mlb_game.get("totals_model", {}).get("edge")
                    if isinstance(
                        mlb_game.get("totals_model"),
                        dict,
                    )
                    else None
                ),
                "total_direction": (
                    mlb_game.get("totals_model", {}).get(
                        "direction"
                    )
                    if isinstance(
                        mlb_game.get("totals_model"),
                        dict,
                    )
                    else None
                ),
                "total_recommendation": (
                    mlb_game.get("totals_model", {}).get(
                        "recommendation"
                    )
                    if isinstance(
                        mlb_game.get("totals_model"),
                        dict,
                    )
                    else None
                ),
                "totals_model": mlb_game.get("totals_model", {}),
                "top_hr_targets": bomb.get(
                    "top_hitters",
                    [],
                )[:3],
                "reasons": reasons,
                "score_breakdown": hammer["breakdown"],
                "source_signals": [
                    signal.to_dict()
                    for signal in consensus_signals
                ],
            }
        )

    decisions.sort(
        key=lambda item: item.get("hammer_score", 0),
        reverse=True,
    )

    actionable = [
        item
        for item in decisions
        if str(item.get("model_recommendation", "")).upper()
        not in {"", "PASS", "NO PLAY", "❌ NO PLAY"}
    ]

    hammer_plays = [
        item
        for item in decisions
        if item.get("hammer_tier") == "HAMMER"
    ]

    bet_plays = [
        item
        for item in decisions
        if item.get("hammer_tier") == "BET"
    ]

    lean_plays = [
        item
        for item in decisions
        if item.get("hammer_tier") == "LEAN"
    ]

    real_market_games = [
        item
        for item in decisions
        if item.get("real_market_loaded")
    ]

    output = {
        "sport": "MLB",
        "type": "decision_engine",
        "version": "1.1.0",
        "generated_at": datetime.now(UTC).isoformat(
            timespec="seconds"
        ),
        "summary": {
            "games_loaded": len(decisions),
            "actionable": len(actionable),
            "hammer_plays": len(hammer_plays),
            "bets": len(bet_plays),
            "leans": len(lean_plays),
            "real_market_games": len(real_market_games),
            "model_only_games": (
                len(decisions) - len(real_market_games)
            ),
            "top_play": (
                decisions[0].get("selected_team")
                if decisions
                else "PASS"
            ),
            "top_score": (
                decisions[0].get("hammer_score")
                if decisions
                else 0
            ),
        },
        "decisions": decisions,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
        )

    return output
