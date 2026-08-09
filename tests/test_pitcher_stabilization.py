from engine.first5.first5_model import (
    pitcher_quality_score,
)
from engine.mlb.totals.expected_runs import (
    calculate_starter_adjustment,
)
from engine.model.component_scores import (
    starting_pitcher_score,
)
from engine.model.pitcher_stabilization import (
    PITCHER_BASELINES,
    stabilize_pitcher_metrics,
)


def pitcher(ip):
    return {
        "name": "Sample Starter",
        "ip": ip,
        "era": 1.50,
        "whip": 0.80,
        "k_rate": 12.0,
        "bb_rate": 1.5,
        "hr9": 0.3,
    }


def test_low_innings_regress_toward_baselines():
    stabilized = stabilize_pitcher_metrics(pitcher(5.0))

    assert stabilized["era"] > 4.0
    assert stabilized["whip"] > 1.2
    assert stabilized["k9"] < 9.0
    assert stabilized["bb9"] > 3.0
    assert stabilized["hr9"] > 1.0


def test_medium_innings_blend_raw_and_baseline():
    stabilized = stabilize_pitcher_metrics(pitcher(50.0))

    assert abs(stabilized["era"] - 3.0) < 0.0001
    assert abs(stabilized["whip"] - 1.075) < 0.0001
    assert abs(stabilized["k9"] - 10.25) < 0.0001
    assert abs(stabilized["bb9"] - 2.35) < 0.0001
    assert abs(stabilized["hr9"] - 0.75) < 0.0001


def test_established_starter_remains_closer_to_observed_value():
    established = stabilize_pitcher_metrics(pitcher(200.0))
    low_sample = stabilize_pitcher_metrics(pitcher(5.0))

    assert abs(established["era"] - 1.5) < abs(low_sample["era"] - 1.5)
    assert abs(established["whip"] - 0.8) < abs(low_sample["whip"] - 0.8)


def test_unknown_starter_remains_neutral():
    assert starting_pitcher_score({"name": "Unknown Starter"}) == 50


def test_missing_innings_preserve_raw_stat_fallbacks():
    stabilized = stabilize_pitcher_metrics(pitcher(None))

    assert stabilized["era"] == 1.50
    assert stabilized["whip"] == 0.80


def test_totals_and_sharpscore_use_stabilized_starter_inputs():
    low_sample = pitcher(5.0)
    established = pitcher(200.0)

    low_adjustment, _, low_reasons = calculate_starter_adjustment(low_sample)
    established_adjustment, _, _ = calculate_starter_adjustment(established)

    assert abs(low_adjustment) < abs(established_adjustment)
    assert "Stabilized opposing starter ERA" in low_reasons[0]
    assert starting_pitcher_score(low_sample) < starting_pitcher_score(established)


def test_first_five_quality_accepts_shared_stabilized_metrics():
    stabilized = stabilize_pitcher_metrics(
        {
            "innings": 5.0,
            "era": 1.50,
            "whip": 0.80,
            "k9": 12.0,
            "bb9": 1.5,
            "hr9": 0.3,
        },
        innings_key="innings",
        metric_keys={
            "era": "era",
            "whip": "whip",
            "k9": "k9",
            "bb9": "bb9",
            "hr9": "hr9",
        },
    )

    assert stabilized["era"] < PITCHER_BASELINES["era"]
    assert pitcher_quality_score(
        {
            "era": stabilized["era"],
            "whip": stabilized["whip"],
            "k_minus_bb9": stabilized["k9"] - stabilized["bb9"],
            "hr9": stabilized["hr9"],
        }
    ) > 0
