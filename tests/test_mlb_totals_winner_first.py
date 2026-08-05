from engine.mlb.totals.recommendation import build_totals_recommendation


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
