from engine.mlb.totals.expected_runs import calculate_offense_adjustment


BASELINES = {
    "offense": {
        "runs_per_team": 4.50,
        "obp": 0.320,
        "slg": 0.400,
        "ops": 0.720,
        "iso": 0.160,
        "hr_per_game": 1.10,
        "bb_minus_k_rate": -14.0,
    }
}


def offense(**overrides):
    data = {
        "runs_per_game": 4.50,
        "obp": 0.320,
        "slg": 0.400,
        "ops": 0.720,
        "iso": 0.160,
        "hr_per_game": 1.10,
        "bb_rate": 8.0,
        "k_rate": 22.0,
    }
    data.update(overrides)
    return {
        "offense": data,
    }


def adjustment(profile):
    return calculate_offense_adjustment(
        profile,
        league_baselines=BASELINES,
    )[0]


def test_elite_average_and_weak_offenses_order_correctly():
    elite = adjustment(
        offense(
            runs_per_game=5.50,
            obp=0.350,
            iso=0.210,
            bb_rate=10.0,
            k_rate=19.0,
        )
    )
    average = adjustment(offense())
    weak = adjustment(
        offense(
            runs_per_game=3.70,
            obp=0.295,
            iso=0.120,
            bb_rate=6.5,
            k_rate=25.0,
        )
    )

    assert elite > average > weak


def test_dynamic_centers_make_league_average_offense_neutral():
    assert adjustment(offense()) == 0.0


def test_rpg_is_primary_but_skill_can_temper_realized_runs():
    high_rpg_average_skill = adjustment(
        offense(
            runs_per_game=5.30,
        )
    )
    high_rpg_poor_skill = adjustment(
        offense(
            runs_per_game=5.30,
            obp=0.295,
            iso=0.120,
            bb_rate=6.5,
            k_rate=25.0,
        )
    )

    assert high_rpg_average_skill > high_rpg_poor_skill
    assert high_rpg_poor_skill > 0


def test_skill_composite_can_raise_average_realized_scoring():
    result = adjustment(
        offense(
            runs_per_game=4.50,
            obp=0.355,
            iso=0.215,
            bb_rate=11.0,
            k_rate=18.0,
        )
    )

    assert result > 0


def test_power_uses_iso_before_home_runs_to_avoid_duplicate_authority():
    with_iso, _points, iso_reasons = calculate_offense_adjustment(
        offense(
            iso=0.210,
            hr_per_game=0.70,
        ),
        league_baselines=BASELINES,
    )
    without_iso, _points, hr_reasons = calculate_offense_adjustment(
        offense(
            iso=None,
            hr_per_game=0.70,
        ),
        league_baselines=BASELINES,
    )

    assert with_iso > without_iso
    assert any("ISO" in reason for reason in iso_reasons)
    assert any("HR per game" in reason for reason in hr_reasons)


def test_ops_is_fallback_only_when_skill_parts_are_missing():
    rich, _points, rich_reasons = calculate_offense_adjustment(
        offense(
            ops=0.820,
        ),
        league_baselines=BASELINES,
    )
    fallback, _points, fallback_reasons = calculate_offense_adjustment(
        offense(
            obp=None,
            slg=None,
            iso=None,
            hr_per_game=None,
            bb_rate=None,
            k_rate=None,
            ops=0.820,
        ),
        league_baselines=BASELINES,
    )

    assert "OPS fallback" not in " ".join(rich_reasons)
    assert any("OPS fallback" in reason for reason in fallback_reasons)
    assert fallback > rich


def test_missing_metrics_renormalize_without_fabricating_strength():
    no_inputs = calculate_offense_adjustment(
        {"offense": {}},
        league_baselines=BASELINES,
    )
    rpg_only = calculate_offense_adjustment(
        offense(
            obp=None,
            slg=None,
            ops=None,
            iso=None,
            hr_per_game=None,
            bb_rate=None,
            k_rate=None,
        ),
        league_baselines=BASELINES,
    )

    assert no_inputs[0] == 0.0
    assert no_inputs[1] == 0
    assert rpg_only[0] == 0.0
    assert rpg_only[1] == 1


def test_offense_adjustment_is_bounded():
    extreme_good = adjustment(
        offense(
            runs_per_game=8.0,
            obp=0.450,
            iso=0.350,
            bb_rate=16.0,
            k_rate=10.0,
        )
    )
    extreme_bad = adjustment(
        offense(
            runs_per_game=2.0,
            obp=0.240,
            iso=0.050,
            bb_rate=3.0,
            k_rate=32.0,
        )
    )

    assert 0 < extreme_good <= 1.0
    assert -1.0 <= extreme_bad < 0


def test_market_fields_cannot_affect_offense_adjustment():
    baseline = adjustment(offense())
    with_market = adjustment(
        offense(
            odds=-150,
            edge=99,
            sportsbook="NoiseBook",
        )
    )

    assert with_market == baseline


def test_offense_adjustment_is_deterministic():
    profile = offense(
        runs_per_game=4.9,
        obp=0.330,
        iso=0.180,
        bb_rate=9.0,
        k_rate=21.0,
    )

    assert adjustment(profile) == adjustment(profile)
