from engine.mlb.totals.recommendation import build_totals_recommendation
from engine.mlb.totals.totals_model import reliability_from_current_inputs


def market_payload(**overrides):
    payload = {
        "available": True,
        "line": 8.5,
        "real_market_loaded": True,
        "over_odds": -110,
        "under_odds": -110,
        "stale": False,
        "pregame_eligible": True,
        "pregame_eligibility_reason": "GAME_NOT_STARTED",
    }
    payload.update(overrides)
    return payload


def totals_recommendation(**overrides):
    data = {
        "direction": "OVER",
        "model_separation": 1.30,
        "model_confidence": 90.0,
        "data_quality": "EXCELLENT",
        "bullpen_confidence": 90.0,
        "market_payload": market_payload(),
        "reliability": 90.0,
        "reliability_concerns": [],
    }
    data.update(overrides)
    return build_totals_recommendation(**data)


def test_totals_uses_model_separation_not_market_edge_labeling():
    result = totals_recommendation()

    assert result.selection == "OVER"
    assert result.recommendation == "STRONG BET OVER"
    assert result.actionable is True
    assert result.to_dict()["score_components"]["model_separation"] > 0
    assert "market_quality" not in result.to_dict()["score_components"]
    assert "edge" not in result.to_dict()["score_components"]


def test_totals_market_price_quality_and_staleness_do_not_change_conviction():
    baseline = totals_recommendation()
    changed_market = totals_recommendation(
        market_payload=market_payload(
            real_market_loaded=False,
            over_odds=250,
            under_odds=-300,
            stale=True,
        )
    )

    assert changed_market.recommendation_score == baseline.recommendation_score
    assert changed_market.recommendation == baseline.recommendation
    assert changed_market.confidence == baseline.confidence


def test_totals_distance_from_line_controls_model_separation():
    weak = totals_recommendation(model_separation=0.30)
    lean = totals_recommendation(model_separation=0.50)

    assert weak.recommendation == "PASS"
    assert weak.actionable is False
    assert lean.recommendation == "LEAN OVER"
    assert lean.actionable is True


def test_totals_still_requires_verified_pregame_line():
    result = totals_recommendation(
        market_payload=market_payload(
            pregame_eligible=False,
            pregame_eligibility_reason="GAME_STARTED",
        )
    )

    assert result.recommendation == "PASS"
    assert result.actionable is False
    assert result.model_separation_score == 0.0


def test_totals_recommendation_score_does_not_gate_authority():
    result = totals_recommendation(
        model_separation=1.30,
        model_confidence=1.0,
        data_quality="LIMITED",
        bullpen_confidence=1.0,
        reliability=100.0,
    )

    assert result.recommendation == "STRONG BET OVER"
    assert result.actionable is True
    assert result.recommendation_score == result.model_separation_score


def test_old_confidence_does_not_gate_authority_when_reliability_is_clean():
    result = totals_recommendation(
        model_separation=0.80,
        model_confidence=1.0,
        reliability=100.0,
    )

    assert result.recommendation == "BET OVER"
    assert result.actionable is True


def test_reliability_can_downgrade_but_never_promote():
    downgraded = totals_recommendation(
        model_separation=1.30,
        reliability=62.0,
        reliability_concerns=["bullpen_inputs_partial"],
    )
    weak = totals_recommendation(
        model_separation=0.30,
        reliability=100.0,
    )

    assert downgraded.base_recommendation == "STRONG BET OVER"
    assert downgraded.recommendation == "LEAN OVER"
    assert downgraded.changed_by_reliability is True
    assert weak.recommendation == "PASS"


def test_clean_current_totals_inputs_can_reach_reliability_100():
    projection = type(
        "Projection",
        (),
        {"data_points": 7},
    )()
    park = type(
        "Park",
        (),
        {"available": True},
    )()
    bullpen = type(
        "Bullpen",
        (),
        {"confidence": 95.0},
    )()

    reliability, concerns = reliability_from_current_inputs(
        away_projection=projection,
        home_projection=projection,
        park=park,
        bullpen_adjustment=bullpen,
    )

    assert reliability == 100.0
    assert concerns == []


def test_future_totals_context_absence_does_not_reduce_reliability():
    projection = type(
        "Projection",
        (),
        {"data_points": 7},
    )()
    park = type(
        "Park",
        (),
        {"available": True},
    )()
    bullpen = type(
        "Bullpen",
        (),
        {"confidence": 95.0},
    )()

    reliability, concerns = reliability_from_current_inputs(
        away_projection=projection,
        home_projection=projection,
        park=park,
        bullpen_adjustment=bullpen,
    )

    assert reliability == 100.0
    assert not any(
        "lineup" in concern
        or "handedness" in concern
        or "weather" in concern
        for concern in concerns
    )


def test_market_price_edge_ev_and_sportsbook_do_not_change_totals_authority():
    baseline = totals_recommendation()
    changed = totals_recommendation(
        market_payload=market_payload(
            over_odds=220,
            under_odds=-260,
            sportsbook="ChangedBook",
            edge=99.0,
            expected_value=99.0,
            implied_probability=0.99,
        )
    )

    assert changed.recommendation == baseline.recommendation
    assert changed.selection == baseline.selection
    assert changed.recommendation_score == baseline.recommendation_score
