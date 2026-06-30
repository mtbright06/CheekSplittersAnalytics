from engine.model.component_scores import (
    offense_score,
    starting_pitcher_score,
    bullpen_score,
    market_score,
    home_field_score,
)
from engine.model.confidence import calculate_confidence
from engine.model.recommendations import recommendation
from engine.odds.market_edge import calculate_market_edge, market_edge_to_dict


WEIGHTS = {
    "offense": 0.35,
    "starting_pitching": 0.35,
    "bullpen": 0.10,
    "market": 0.15,
    "home_field": 0.05,
}


def calculate_team_score(
    offense,
    pitcher,
    bullpen,
    book_probability,
    provisional_model_probability,
    is_home,
):
    components = {
        "offense": offense_score(offense),
        "starting_pitching": starting_pitcher_score(pitcher),
        "bullpen": bullpen_score(bullpen),
        "market": market_score(book_probability, provisional_model_probability),
        "home_field": home_field_score(is_home),
    }

    total = (
        components["offense"] * WEIGHTS["offense"]
        + components["starting_pitching"] * WEIGHTS["starting_pitching"]
        + components["bullpen"] * WEIGHTS["bullpen"]
        + components["market"] * WEIGHTS["market"]
        + components["home_field"] * WEIGHTS["home_field"]
    )

    return round(total, 1), components


def probability_from_scores(selected_score, opponent_score):
    diff = selected_score - opponent_score
    probability = 50 + diff * 0.75
    return round(max(40, min(70, probability)), 1)


def choose_side(away_name, home_name, away_score, home_score):
    if away_score > home_score:
        return away_name

    return home_name


def build_sharpscore_decision(
    away_name,
    home_name,
    away_profile,
    home_profile,
    away_pitcher,
    home_pitcher,
    away_quote,
    home_quote,
):
    away_offense = away_profile.get("offense", {})
    home_offense = home_profile.get("offense", {})

    away_bullpen = away_profile.get("bullpen", {})
    home_bullpen = home_profile.get("bullpen", {})

    away_book_probability = away_quote.implied_probability if away_quote else None
    home_book_probability = home_quote.implied_probability if home_quote else None

    away_score, away_components = calculate_team_score(
        away_offense,
        away_pitcher,
        away_bullpen,
        away_book_probability,
        50,
        False,
    )

    home_score, home_components = calculate_team_score(
        home_offense,
        home_pitcher,
        home_bullpen,
        home_book_probability,
        50,
        True,
    )

    play = choose_side(away_name, home_name, away_score, home_score)

    if play == away_name:
        selected_score = away_score
        opponent_score = home_score
        quote = away_quote
        selected_components = away_components
        opponent_components = home_components
        selected_profile = away_profile
        opponent_profile = home_profile
        selected_pitcher = away_pitcher
        opponent_pitcher = home_pitcher
    else:
        selected_score = home_score
        opponent_score = away_score
        quote = home_quote
        selected_components = home_components
        opponent_components = away_components
        selected_profile = home_profile
        opponent_profile = away_profile
        selected_pitcher = home_pitcher
        opponent_pitcher = away_pitcher

    model_probability = probability_from_scores(
        selected_score,
        opponent_score,
    )

    market_edge = {}
    edge = 0

    if quote:
        calculated = calculate_market_edge(model_probability, quote)
        market_edge = market_edge_to_dict(calculated)
        edge = market_edge.get("edge") or 0

    confidence = calculate_confidence(
        abs(selected_score - opponent_score),
        away_pitcher,
        home_pitcher,
        quote_to_odds_dict(quote),
        away_offense,
        home_offense,
    )

    model = {
        "play": play,
        "market": "Moneyline",
        "model_probability": model_probability,
        "edge": edge,
        "confidence": confidence,
        "recommendation": recommendation(edge, confidence),
        "signals": [
            {"name": "Offense", "value": selected_components["offense"] / 100},
            {"name": "Starting Pitching", "value": selected_components["starting_pitching"] / 100},
            {"name": "Bullpen", "value": selected_components["bullpen"] / 100},
            {"name": "Market", "value": selected_components["market"] / 100},
            {"name": "Home Field", "value": selected_components["home_field"] / 100},
        ],
        "reasons": build_reasons(
            play,
            selected_score,
            opponent_score,
            selected_components,
            opponent_components,
            selected_profile,
            opponent_profile,
            selected_pitcher,
            opponent_pitcher,
        ),
        "component_scores": {
            "selected": selected_components,
            "opponent": opponent_components,
            "selected_total": selected_score,
            "opponent_total": opponent_score,
        },
    }

    return {
        "model": model,
        "quote": quote,
        "market_edge": market_edge,
    }


def quote_to_odds_dict(quote):
    if not quote:
        return {}

    return {
        "book_probability": quote.implied_probability,
        "moneyline": quote.american_odds,
        "sportsbook": quote.sportsbook,
    }


def build_reasons(
    play,
    selected_score,
    opponent_score,
    selected_components,
    opponent_components,
    selected_profile,
    opponent_profile,
    selected_pitcher,
    opponent_pitcher,
):
    reasons = []

    reasons.append(
        f"{play} grades higher overall ({selected_score:.1f} vs {opponent_score:.1f})."
    )

    if selected_components["offense"] > opponent_components["offense"]:
        reasons.append(
            f"{play} has the stronger offense score ({selected_components['offense']:.1f} vs {opponent_components['offense']:.1f})."
        )

    if selected_components["starting_pitching"] > opponent_components["starting_pitching"]:
        reasons.append(
            f"{play} has the stronger starting pitching score ({selected_components['starting_pitching']:.1f} vs {opponent_components['starting_pitching']:.1f})."
        )

    pitcher_name = selected_pitcher.get("name")
    if pitcher_name and pitcher_name != "Unknown Starter":
        reasons.append(
            f"Projected starter: {pitcher_name}."
        )

    reasons.append(
        "SharpScore v0.1 weighs offense, starting pitching, bullpen placeholder, market value, and home field."
    )

    return reasons
