from engine.mlb.bullpen.bullpen_model import build_bullpen_projection
from engine.mlb.bullpen.game_adjustment import build_game_bullpen_adjustment


BASELINES = {
    "bullpen": {
        "era": 4.10,
        "whip": 1.30,
    }
}


def high_leverage_entry(role):
    return {
        "availability_evidence": {
            "status": "OBSERVED_WORKLOAD_CONCERN",
            "confidence": "HIGH",
            "source_quality": "COMPLETE",
        },
        "role_evidence": {
            "candidate_roles": [
                {
                    "role": role,
                    "confidence": "HIGH",
                    "evidence": ["test evidence"],
                }
            ],
        },
    }


def bullpen(**overrides):
    data = {
        "team": "TST",
        "season_era": 4.10,
        "season_whip": 1.30,
        "last7_era": 4.10,
        "innings_last3": 1.0,
        "innings_last5": 2.0,
        "innings_last7": 12.0,
        "closer_available": True,
        "setup_available": True,
        "evidence_ledger": [],
        "league_baselines": BASELINES,
    }
    data.update(overrides)
    return build_bullpen_projection(**data)


def test_elite_and_poor_quality_move_expected_runs_in_opposite_directions():
    elite = bullpen(
        season_era=2.70,
        season_whip=1.05,
        last7_era=2.50,
        innings_last7=18.0,
    )
    poor = bullpen(
        season_era=5.60,
        season_whip=1.55,
        last7_era=5.80,
        innings_last7=18.0,
    )

    assert elite.quality_adjustment < 0
    assert poor.quality_adjustment > 0
    assert elite.total_run_adjustment < poor.total_run_adjustment


def test_last7_era_is_sample_stabilized_for_totals_authority():
    tiny_sample = bullpen(last7_era=8.00, innings_last7=2.0)
    full_sample = bullpen(last7_era=8.00, innings_last7=24.0)

    assert tiny_sample.quality.last7_sample_weight < full_sample.quality.last7_sample_weight
    assert tiny_sample.quality.stabilized_last7_era < full_sample.quality.stabilized_last7_era
    assert tiny_sample.total_run_adjustment < full_sample.total_run_adjustment


def test_fresh_and_fatigued_bullpens_separate_workload_from_quality():
    fresh = bullpen(
        season_era=3.20,
        season_whip=1.10,
        innings_last3=1.0,
        innings_last5=2.0,
    )
    exhausted = bullpen(
        season_era=3.20,
        season_whip=1.10,
        innings_last3=7.0,
        innings_last5=9.0,
        evidence_ledger=[
            high_leverage_entry("CLOSER"),
            high_leverage_entry("SETUP"),
        ],
    )

    assert fresh.quality_adjustment == exhausted.quality_adjustment
    assert exhausted.fatigue_adjustment > fresh.fatigue_adjustment
    assert exhausted.total_run_adjustment > fresh.total_run_adjustment


def test_unavailable_closer_and_setup_add_bounded_availability_only():
    available = bullpen()
    unavailable = bullpen(
        closer_available=False,
        setup_available=False,
    )

    assert unavailable.quality_adjustment == available.quality_adjustment
    assert unavailable.fatigue_adjustment == available.fatigue_adjustment
    assert unavailable.availability_adjustment == 0.13


def test_missing_source_stays_neutral_strength_with_limited_status():
    missing = bullpen(
        season_era=None,
        season_whip=None,
        last7_era=None,
        innings_last3=0.0,
        innings_last5=None,
        innings_last7=None,
    )

    assert missing.quality_adjustment == 0.0
    assert missing.total_run_adjustment == 0.0
    assert missing.status == "PARTIAL"


def test_dynamic_baseline_changes_center_not_scale():
    static = bullpen(season_era=4.10, season_whip=1.30)
    dynamic = bullpen(
        season_era=4.10,
        season_whip=1.30,
        league_baselines={
            "bullpen": {
                "era": 3.70,
                "whip": 1.20,
            }
        },
    )

    assert static.quality_adjustment == 0.0
    assert dynamic.quality_adjustment > 0.0


def test_bullpen_adjustment_is_bounded_at_team_and_game_level():
    terrible = bullpen(
        season_era=9.50,
        season_whip=2.20,
        last7_era=12.00,
        innings_last7=24.0,
        innings_last3=9.0,
        innings_last5=12.0,
        closer_available=False,
        setup_available=False,
        evidence_ledger=[
            high_leverage_entry("CLOSER"),
            high_leverage_entry("SETUP"),
        ],
    )
    other = bullpen(
        season_era=9.50,
        season_whip=2.20,
        last7_era=12.00,
        innings_last7=24.0,
        innings_last3=9.0,
        innings_last5=12.0,
        closer_available=False,
        setup_available=False,
    )
    game = build_game_bullpen_adjustment(terrible, other)

    assert terrible.total_run_adjustment == 0.85
    assert game.combined_adjustment == 1.7


def test_deterministic_projection_for_identical_inputs():
    first = bullpen(
        season_era=3.60,
        season_whip=1.22,
        last7_era=4.80,
        innings_last7=14.0,
        innings_last3=4.0,
        innings_last5=5.0,
        evidence_ledger=[high_leverage_entry("CLOSER")],
    )
    second = bullpen(
        season_era=3.60,
        season_whip=1.22,
        last7_era=4.80,
        innings_last7=14.0,
        innings_last3=4.0,
        innings_last5=5.0,
        evidence_ledger=[high_leverage_entry("CLOSER")],
    )

    assert first == second
