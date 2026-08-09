from engine.mlb.totals.totals_model import reliability_from_current_inputs


class Projection:
    def __init__(self, data_points):
        self.data_points = data_points


class Park:
    def __init__(self, available=True):
        self.available = available


class BullpenAdjustment:
    def __init__(self, confidence=95.0):
        self.confidence = confidence


FULL_BASELINES = {
    "offense": {
        "runs_per_team": 4.5,
        "sample_size": 30,
    },
    "starter": {
        "era": 4.0,
        "whip": 1.25,
        "hr9": 1.1,
        "sample_size": 30,
    },
    "bullpen": {
        "era": 4.1,
        "whip": 1.28,
        "sample_size": 30,
    },
}


def test_totals_reliability_truth_layer_preserves_legacy_tuple_contract():
    reliability, concerns = reliability_from_current_inputs(
        away_projection=Projection(7),
        home_projection=Projection(7),
        park=Park(True),
        bullpen_adjustment=BullpenAdjustment(95.0),
        league_baselines=FULL_BASELINES,
    )

    assert reliability == 100.0
    assert concerns == []


def test_totals_reliability_truth_layer_exposes_structured_deductions():
    reliability, concerns, deductions = reliability_from_current_inputs(
        away_projection=Projection(3),
        home_projection=Projection(7),
        park=Park(False),
        bullpen_adjustment=BullpenAdjustment(60.0),
        league_baselines=FULL_BASELINES,
        include_deductions=True,
    )

    assert reliability == 77.0
    assert concerns == [
        "away_projection_inputs_partial",
        "park_factor_unavailable",
        "bullpen_inputs_partial",
    ]
    assert deductions == [
        {
            "code": "away_projection_inputs_partial",
            "severity": "medium",
            "deduction": 10.0,
            "source": "totals_projection_inputs",
            "message": (
                "Away projection is built from partial current offense, "
                "starter, or park inputs."
            ),
            "visibility": "user",
        },
        {
            "code": "park_factor_unavailable",
            "severity": "low",
            "deduction": 5.0,
            "source": "park_factor",
            "message": (
                "Park factor was unavailable, so a neutral park context was used."
            ),
            "visibility": "user",
        },
        {
            "code": "bullpen_inputs_partial",
            "severity": "medium",
            "deduction": 8.0,
            "source": "bullpen_provider",
            "message": "Bullpen inputs are partial for today's totals projection.",
            "visibility": "user",
        },
    ]


def test_totals_dynamic_baseline_fallback_is_reliability_only():
    reliability, concerns, deductions = reliability_from_current_inputs(
        away_projection=Projection(7),
        home_projection=Projection(7),
        park=Park(True),
        bullpen_adjustment=BullpenAdjustment(95.0),
        league_baselines={
            "offense": FULL_BASELINES["offense"],
        },
        include_deductions=True,
    )

    assert reliability == 90.0
    assert concerns == [
        "starter_league_baseline_static_fallback",
        "bullpen_league_baseline_static_fallback",
    ]
    assert [entry["source"] for entry in deductions] == [
        "league_baselines",
        "league_baselines",
    ]


def test_totals_starter_profile_fallback_reduces_trust_not_strength():
    reliability, concerns, deductions = reliability_from_current_inputs(
        away_projection=Projection(7),
        home_projection=Projection(7),
        park=Park(True),
        bullpen_adjustment=BullpenAdjustment(95.0),
        away_pitcher={"data_source": "season_fallback"},
        home_pitcher={
            "data_source": "starter_game_log",
            "previous_start_date": "2026-08-01",
            "previous_start_ip": 6.0,
            "previous_start_pitch_count": 92,
        },
        league_baselines=FULL_BASELINES,
        include_deductions=True,
    )

    assert reliability == 95.0
    assert concerns == ["away_starter_profile_fallback"]
    assert deductions[0]["source"] == "starter_profile"


def test_totals_missing_rest_context_reduces_reliability_not_strength():
    reliability, concerns, _deductions = reliability_from_current_inputs(
        away_projection=Projection(7),
        home_projection=Projection(7),
        park=Park(True),
        bullpen_adjustment=BullpenAdjustment(95.0),
        away_pitcher={
            "data_source": "starter_game_log",
        },
        home_pitcher={
            "data_source": "starter_game_log",
        },
        league_baselines=FULL_BASELINES,
        include_deductions=True,
    )

    assert reliability == 84.0
    assert concerns == [
        "away_missing_starter_rest_context",
        "away_missing_starter_workload_context",
        "home_missing_starter_rest_context",
        "home_missing_starter_workload_context",
    ]
