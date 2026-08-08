from engine.model.component_scores import (
    offense_score,
    offense_breakdown,
    starting_pitcher_breakdown,
    bullpen_breakdown,
    home_field_score,
)
from engine.model.confidence import calculate_confidence
from engine.model.recommendations import (
    market_value_classification,
    mlb_moneyline_v2_candidate_recommendation,
    mlb_moneyline_conviction_recommendation,
    mlb_moneyline_v2_recommendation,
    mlb_moneyline_explanation,
)
from engine.odds.market_edge import calculate_market_edge, market_edge_to_dict


WEIGHTS = {
    "offense": 0.40,
    "starting_pitching": 0.40,
    "bullpen": 0.15,
    "home_field": 0.05,
}


def calculate_team_score(
    offense,
    pitcher,
    bullpen,
    is_home,
    *,
    league_baselines=None,
):
    offense_details = offense_breakdown(
        offense,
        league_baselines=league_baselines,
    )
    starter_details = starting_pitcher_breakdown(
        pitcher,
        league_baselines=league_baselines,
    )
    bullpen_details = bullpen_breakdown(
        bullpen,
        league_baselines=league_baselines,
    )
    components = {
        "offense": offense_details["offense_score"],
        "starting_pitching": starter_details["starting_pitching_score"],
        "bullpen": bullpen_details["bullpen_score"],
        "home_field": home_field_score(is_home),
        "offense_breakdown": offense_details,
        "starting_pitcher_breakdown": starter_details,
        "bullpen_breakdown": bullpen_details,
    }

    total = (
        components["offense"] * WEIGHTS["offense"]
        + components["starting_pitching"] * WEIGHTS["starting_pitching"]
        + components["bullpen"] * WEIGHTS["bullpen"]
        + components["home_field"] * WEIGHTS["home_field"]
    )

    return round(total, 1), components


def strength_score_from_scores(selected_score, opponent_score):
    diff = selected_score - opponent_score
    strength_score = 50 + diff * 0.75
    return round(max(40, min(70, strength_score)), 1)


def probability_from_scores(selected_score, opponent_score):
    """Compatibility alias for the historical pseudo-probability field."""
    return strength_score_from_scores(selected_score, opponent_score)


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
    league_baselines=None,
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
        league_baselines=league_baselines,
    )

    home_score, home_components = calculate_team_score(
        home_offense,
        home_pitcher,
        home_bullpen,
        True,
        league_baselines=league_baselines,
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

    model_strength_score = strength_score_from_scores(
        selected_score,
        opponent_score,
    )
    sharpscore_gap = round(
        selected_score - opponent_score,
        1,
    )

    market_edge = {}
    edge = None

    if quote:
        calculated = calculate_market_edge(model_strength_score, quote)
        market_edge = market_edge_to_dict(calculated)
        edge = market_edge.get("edge")

    legacy_confidence, legacy_confidence_breakdown = calculate_confidence(
        abs(selected_score - opponent_score),
        away_pitcher,
        home_pitcher,
        quote_to_odds_dict(quote),
        away_offense,
        home_offense,
    )

    model_recommendation = (
        mlb_moneyline_conviction_recommendation(
            model_strength_score,
            legacy_confidence,
        )
    )
    v2_reliability = mlb_moneyline_v2_reliability(
        away_offense=away_offense,
        home_offense=home_offense,
        away_pitcher=away_pitcher,
        home_pitcher=home_pitcher,
        away_bullpen=away_bullpen,
        home_bullpen=home_bullpen,
    )
    v2_authority = mlb_moneyline_v2_recommendation(
        sharpscore_gap,
        v2_reliability,
    )
    v2_candidate_authority = (
        mlb_moneyline_v2_candidate_recommendation(
            sharpscore_gap,
            v2_reliability,
        )
    )
    official_recommendation = v2_candidate_authority["recommendation"]
    reliability_score = v2_reliability["score"]
    market_value_label, market_value_tone = (
        market_value_classification(edge)
    )

    model = {
        "play": play,
        "market": "Moneyline",
        "model_strength": sharpscore_gap,
        "model_strength_score": model_strength_score,
        # Compatibility alias for downstream consumers that still expect the
        # historical percent-like strength score.
        "model_win_strength": model_strength_score,
        # Compatibility alias for downstream consumers that still expect the
        # historical probability-looking field. Do not calculate separately.
        "model_probability": model_strength_score,
        "model_reliability": reliability_score,
        "reliability": reliability_score,
        "reliability_breakdown": v2_reliability,
        # Compatibility aliases: MLB model confidence now means input
        # reliability, not SharpScore separation or win probability.
        "model_confidence": reliability_score,
        "sharpscore_gap": sharpscore_gap,
        "edge": edge,
        "confidence": reliability_score,
        "confidence_breakdown": v2_reliability,
        "legacy_confidence": legacy_confidence,
        "legacy_model_confidence": legacy_confidence,
        "legacy_confidence_breakdown": legacy_confidence_breakdown,
        "recommendation": official_recommendation,
        "model_recommendation": official_recommendation,
        "v1_shadow_recommendation": model_recommendation,
        "v1_shadow_tier": model_recommendation,
        "v2_recommendation": v2_authority["recommendation"],
        "v2_authority": v2_authority,
        "v2_candidate_recommendation": (
            v2_candidate_authority["recommendation"]
        ),
        "v2_candidate_authority": v2_candidate_authority,
        "market_value_label": market_value_label,
        "market_value_tone": market_value_tone,
        "recommendation_explanation": (
            mlb_moneyline_explanation(
                team=play,
                recommendation=official_recommendation,
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
            "sharpscore_gap": sharpscore_gap,
            "league_baselines": league_baselines,
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


def mlb_moneyline_v2_reliability(
    *,
    away_offense,
    home_offense,
    away_pitcher,
    home_pitcher,
    away_bullpen,
    home_bullpen,
):
    concerns = []
    concern_details = []

    def add_concern(
        code,
        *,
        deduction,
        severity,
        source,
        message,
        visibility="user",
    ):
        if code in concerns:
            return
        concerns.append(code)
        concern_details.append(
            {
                "code": code,
                "deduction": deduction,
                "severity": severity,
                "source": source,
                "message": message,
                "visibility": visibility,
            }
        )

    core_values = [
        away_pitcher.get("era"),
        away_pitcher.get("whip"),
        home_pitcher.get("era"),
        home_pitcher.get("whip"),
        away_offense.get("ops"),
        home_offense.get("ops"),
    ]
    present_core = len(
        [
            value
            for value in core_values
            if value is not None
        ]
    )

    unknown_starters = []
    for pitcher in [away_pitcher, home_pitcher]:
        if not pitcher:
            unknown_starters.append("Unknown Starter")
        elif pitcher.get("name") == "Unknown Starter":
            unknown_starters.append("Unknown Starter")

    if unknown_starters:
        add_concern(
            "unknown_starter",
            deduction=20.0,
            severity="high",
            source="starter",
            message="One or more probable starters are unknown.",
        )

    if away_offense.get("ops") is None or home_offense.get("ops") is None:
        add_concern(
            "missing_core_offense",
            deduction=25.0,
            severity="high",
            source="offense",
            message="Required team offense OPS is missing.",
        )

    offense_source_qualities = [
        offense.get("source_quality")
        for offense in (away_offense, home_offense)
        if offense and offense.get("source_quality") is not None
    ]
    if (
        offense_source_qualities
        and any(quality != "COMPLETE" for quality in offense_source_qualities)
        and "missing_core_offense" not in concerns
    ):
        add_concern(
            "degraded_offense_source",
            deduction=8.0,
            severity="medium",
            source="offense",
            message="Team offense source quality is degraded.",
        )

    starter_fields = [
        away_pitcher.get("era"),
        away_pitcher.get("whip"),
        home_pitcher.get("era"),
        home_pitcher.get("whip"),
    ]
    if any(value is None for value in starter_fields):
        add_concern(
            "missing_core_starter_data",
            deduction=25.0,
            severity="high",
            source="starter",
            message="Required starter ERA or WHIP is missing.",
        )

    role_contexts = [
        pitcher.get("role_context")
        for pitcher in (away_pitcher, home_pitcher)
        if pitcher
    ]
    if any(
        role in {
            "no_prior_starts",
            "limited_starting_role",
            "opener_risk",
            "short_start_role_risk",
        }
        for role in role_contexts
    ):
        add_concern(
            "starter_role_uncertainty",
            deduction=8.0,
            severity="medium",
            source="starter",
            message="Starter role profile is uncertain or abbreviated.",
        )

    if any(
        pitcher
        and pitcher.get("data_source") == "season_fallback"
        for pitcher in (away_pitcher, home_pitcher)
    ):
        add_concern(
            "starter_profile_fallback",
            deduction=6.0,
            severity="medium",
            source="starter",
            message="Starter profile fell back to season-level pitcher data.",
        )

    if any(
        pitcher
        and pitcher.get("data_source") == "starter_game_log"
        and pitcher.get("previous_start_date") is None
        for pitcher in (away_pitcher, home_pitcher)
    ):
        add_concern(
            "missing_starter_rest_context",
            deduction=4.0,
            severity="low",
            source="starter",
            message="Starter rest context is missing.",
        )

    if any(
        pitcher
        and pitcher.get("data_source") == "starter_game_log"
        and pitcher.get("previous_start_date") is not None
        and (
            pitcher.get("previous_start_ip") is None
            or pitcher.get("previous_start_pitch_count") is None
        )
        for pitcher in (away_pitcher, home_pitcher)
    ):
        add_concern(
            "missing_starter_workload_context",
            deduction=3.0,
            severity="low",
            source="starter",
            message="Previous starter workload context is incomplete.",
        )

    if not away_bullpen or not home_bullpen:
        add_concern(
            "missing_bullpen_data",
            deduction=10.0,
            severity="medium",
            source="bullpen",
            message="Bullpen profile is missing.",
        )

    bullpen_source_qualities = [
        bullpen.get("source_quality")
        for bullpen in (away_bullpen, home_bullpen)
        if bullpen and bullpen.get("source_quality") is not None
    ]
    if (
        bullpen_source_qualities
        and any(quality == "UNAVAILABLE" for quality in bullpen_source_qualities)
        and "missing_bullpen_data" not in concerns
    ):
        add_concern(
            "degraded_bullpen_source",
            deduction=10.0,
            severity="medium",
            source="bullpen",
            message="Bullpen source returned an unavailable profile.",
        )
    elif (
        bullpen_source_qualities
        and any(quality in {"PARTIAL", "EMPTY"} for quality in bullpen_source_qualities)
        and "missing_bullpen_data" not in concerns
    ):
        add_concern(
            "partial_bullpen_source",
            deduction=6.0,
            severity="low",
            source="bullpen",
            message="Bullpen source is partial or lacks active relief appearances.",
        )

    if present_core < 4:
        tier_cap = "PASS"
        add_concern(
            "severe_data_incompleteness",
            deduction=65.0,
            severity="critical",
            source="core",
            message="Too few required model inputs are present.",
        )
    elif (
        "missing_core_offense" in concerns
        or "missing_core_starter_data" in concerns
    ):
        tier_cap = "LEAN"
    elif (
        unknown_starters
        or "missing_bullpen_data" in concerns
        or "starter_role_uncertainty" in concerns
    ):
        tier_cap = "PLAYABLE"
    else:
        tier_cap = "STRONG PLAY"

    score = 100.0

    if "severe_data_incompleteness" in concerns:
        score = 35.0
    else:
        score -= sum(
            detail["deduction"]
            for detail in concern_details
        )

    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "score": score,
        "core_fields_present": present_core,
        "core_fields_total": len(core_values),
        "concerns": concerns,
        "concern_details": concern_details,
        "tier_cap": tier_cap,
        "definition": "Reliability measures trust in current production inputs only; it does not measure SharpScore strength, win probability, market agreement, edge, EV, odds, or Hammer.",
        "input_groups": {
            "strength_inputs": [
                "team offense OPS",
                "starter ERA",
                "starter WHIP",
                "bullpen season ERA",
                "bullpen season WHIP",
                "home field",
            ],
            "reliability_inputs": [
                "probable starter availability",
                "starter stat completeness",
                "starter role context",
                "starter profile source",
                "starter rest context",
                "starter workload context",
                "team offense source quality",
                "bullpen profile presence",
                "bullpen source quality",
            ],
            "excluded_inputs": [
                "SharpScore gap",
                "model win strength",
                "Hammer",
                "edge",
                "EV",
                "odds",
                "implied probability",
                "sportsbook",
            ],
        },
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
