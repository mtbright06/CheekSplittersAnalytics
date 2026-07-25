from engine.model.component_scores import (
    offense_score,
    starting_pitcher_score,
    bullpen_score,
    home_field_score,
)
from engine.model.confidence import calculate_confidence
from engine.model.recommendations import (
    market_value_classification,
    mlb_moneyline_conviction_recommendation,
    mlb_moneyline_explanation,
)
from engine.odds.market_edge import calculate_market_edge, market_edge_to_dict


WEIGHTS = {
    "offense": 0.40,
    "starting_pitching": 0.45,
    "bullpen": 0.10,
    "home_field": 0.05,
}


def calculate_team_score(
    offense,
    pitcher,
    bullpen,
    is_home,
):
    components = {
        "offense": offense_score(offense),
        "starting_pitching": starting_pitcher_score(pitcher),
        "bullpen": bullpen_score(bullpen),
        "home_field": home_field_score(is_home),
    }

    total = (
        components["offense"] * WEIGHTS["offense"]
        + components["starting_pitching"] * WEIGHTS["starting_pitching"]
        + components["bullpen"] * WEIGHTS["bullpen"]
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

    away_score, away_components = calculate_team_score(
        away_offense,
        away_pitcher,
        away_bullpen,
        False,
    )

    home_score, home_components = calculate_team_score(
        home_offense,
        home_pitcher,
        home_bullpen,
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
    edge = None

    if quote:
        calculated = calculate_market_edge(model_probability, quote)
        market_edge = market_edge_to_dict(calculated)
        edge = market_edge.get("edge")

    confidence, confidence_breakdown = calculate_confidence(
        abs(selected_score - opponent_score),
        away_pitcher,
        home_pitcher,
        quote_to_odds_dict(quote),
        away_offense,
        home_offense,
    )

    model_recommendation = (
        mlb_moneyline_conviction_recommendation(
            model_probability,
            confidence,
        )
    )
    market_value_label, market_value_tone = (
        market_value_classification(edge)
    )

    model = {
        "play": play,
        "market": "Moneyline",
        "model_probability": model_probability,
        "edge": edge,
        "confidence": confidence,
        "confidence_breakdown": confidence_breakdown,
        "recommendation": model_recommendation,
        "market_value_label": market_value_label,
        "market_value_tone": market_value_tone,
        "recommendation_explanation": (
            mlb_moneyline_explanation(
                team=play,
                recommendation=model_recommendation,
                market_value_label=market_value_label,
                market_value_tone=market_value_tone,
            )
        ),
        "signals": [
            {"name": "Offense", "value": selected_components["offense"] / 100},
            {"name": "Starting Pitching", "value": selected_components["starting_pitching"] / 100},
            {"name": "Bullpen", "value": selected_components["bullpen"] / 100},
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

    market_edge.update(
        {
            "market_value_label": market_value_label,
            "market_value_tone": market_value_tone,
        }
    )

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
        reasons.append(f"Projected starter: {pitcher_name}.")

    if selected_components["bullpen"] > opponent_components["bullpen"]:
        reasons.append(
            f"{play} has the stronger bullpen score ({selected_components['bullpen']:.1f} vs {opponent_components['bullpen']:.1f})."
        )

    if selected_components["home_field"] > opponent_components["home_field"]:
        reasons.append(
            f"{play} benefits from home field advantage."
        )


    if (
        selected_pitcher.get("name") == "Unknown Starter"
        or opponent_pitcher.get("name") == "Unknown Starter"
    ):
        reasons.append(
            "Confidence reduced because one or more probable starters are unconfirmed."
        )

    reasons.append(
        "SharpScore v0.2 weighs offense, starting pitching, bullpen placeholder, and home field. Market value is evaluated separately after the model prediction."
    )

    return reasons
