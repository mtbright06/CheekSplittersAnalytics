from datetime import UTC, datetime

from engine.decision.decision_builder import first5_score_for_team
from engine.first5.first5_model import (
    LEAGUE_RUNS_PER_GAME,
    build_first5_league_baselines,
    build_reliability,
    moneyline_recommendation,
    offense_factor_with_baselines,
    project_team_f5_runs,
    starter_run_factor_with_baselines,
    starter_context_adjustment,
)
from engine.lineups.models import (
    GameLineupState,
    GameLineupStatus,
    unknown_lineup_state,
)


TEST_BASELINES = {
    "offense": {"runs_per_game": 4.45},
    "starter": {"era": 4.2},
}


def lineup(status=GameLineupStatus.CONFIRMED):
    return GameLineupState(
        game_id=1,
        away_team="Away",
        home_team="Home",
        status=status,
        source="test_lineups",
        retrieved_at=datetime.now(UTC),
    )


def offense(runs_per_game=4.45, games=100):
    return {
        "runs_per_game": runs_per_game,
        "games": games,
    }


def pitcher(
    *,
    available=True,
    innings=100.0,
    era=4.2,
    whip=1.28,
    hr9=1.15,
    k_minus_bb9=5.0,
    days_rest=5,
    previous_start_ip=6.0,
    previous_start_pitch_count=92,
    average_start_ip=5.8,
    role_context="established_starter",
    data_source="starter_game_log",
):
    return {
        "available": available,
        "innings": innings,
        "era": era,
        "whip": whip,
        "hr9": hr9,
        "k_minus_bb9": k_minus_bb9,
        "days_rest": days_rest,
        "previous_start_ip": previous_start_ip,
        "previous_start_pitch_count": previous_start_pitch_count,
        "average_start_ip": average_start_ip,
        "role_context": role_context,
        "previous_start_date": "2026-08-01" if days_rest is not None else None,
        "data_source": data_source,
    }


def rich_offense(runs_per_game):
    return {
        "games": 100,
        "runs_per_game": runs_per_game,
        "ops": 0.730,
        "hr_per_game": 1.10,
    }


def test_projected_margin_direction_determines_first5_side():
    reliability = {
        "score": 100,
        "tier_cap": "STRONG PLAY",
        "concerns": [],
    }

    home = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.1,
        home_runs=2.8,
        reliability=reliability,
    )
    away = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.8,
        home_runs=2.1,
        reliability=reliability,
    )
    neutral = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.4,
        home_runs=2.4,
        reliability=reliability,
    )

    assert home["lean"] == "Home"
    assert away["lean"] == "Away"
    assert neutral["lean"] == "PASS"


def test_margin_tier_is_capped_by_independent_reliability():
    low_reliability = {
        "score": 44,
        "tier_cap": "PASS",
        "concerns": ["away_starter_unconfirmed"],
    }

    recommendation = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.0,
        home_runs=3.1,
        reliability=low_reliability,
    )

    assert recommendation["base_tier"] == "STRONG PLAY"
    assert recommendation["recommendation_tier"] == "PASS"
    assert recommendation["lean"] == "PASS"
    assert recommendation["changed_by_reliability"] is True


def test_market_fields_cannot_change_first5_authority():
    reliability = {
        "score": 100,
        "tier_cap": "STRONG PLAY",
        "concerns": [],
    }
    base = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.0,
        home_runs=2.5,
        reliability=reliability,
    )
    market_polluted = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.0,
        home_runs=2.5,
        reliability={
            **reliability,
            "edge": -99,
            "ev": -99,
            "odds": 999,
            "sportsbook": "Book",
        },
    )

    assert market_polluted == base


def test_reliability_tracks_missing_inputs_without_using_margin_strength():
    full = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )
    missing = build_reliability(
        away_pitcher=pitcher(available=False),
        home_pitcher=pitcher(),
        away_offense=offense(games=0),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )

    assert full["score"] == 100
    assert full["tier_cap"] == "STRONG PLAY"
    assert missing["score"] < full["score"]
    assert "away_starter_unconfirmed" in missing["active_concerns"]
    assert "away_core_offense_unavailable" in missing["active_concerns"]


def test_future_context_unavailable_does_not_reduce_reliability():
    reliability = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )

    assert reliability["score"] == 100
    assert reliability["active_concerns"] == []
    assert "handedness_splits_not_evaluated" in reliability[
        "future_unavailable_context"
    ]
    assert "expected_workload_not_evaluated" in reliability[
        "future_unavailable_context"
    ]


def test_low_starter_sample_reduces_reliability():
    reliability = build_reliability(
        away_pitcher=pitcher(innings=12),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )

    assert reliability["score"] == 80
    assert reliability["tier_cap"] == "PLAYABLE"
    assert "away_starter_very_limited_sample" in reliability[
        "active_concerns"
    ]


def test_missing_park_factor_reduces_reliability():
    reliability = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )

    assert reliability["score"] == 95
    assert "park_factor_unavailable" in reliability["active_concerns"]


def test_clean_game_can_reach_play_and_strong_play():
    reliability = {
        "score": 100,
        "tier_cap": "STRONG PLAY",
        "concerns": [],
    }
    play = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.0,
        home_runs=2.8,
        reliability=reliability,
    )
    strong = moneyline_recommendation(
        away_team="Away",
        home_team="Home",
        away_runs=2.0,
        home_runs=3.0,
        reliability=reliability,
    )

    assert play["recommendation_tier"] == "PLAY"
    assert strong["recommendation_tier"] == "STRONG PLAY"


def test_projected_runs_have_expected_runs_shape():
    strong_offense = offense(runs_per_game=5.2)
    weak_offense = offense(runs_per_game=3.8)
    weak_pitcher = pitcher(era=5.3, whip=1.45, hr9=1.5, k_minus_bb9=3.5)
    strong_pitcher = pitcher(era=3.2, whip=1.05, hr9=0.8, k_minus_bb9=7.0)

    strong_projection = project_team_f5_runs(
        strong_offense,
        weak_pitcher,
        1.0,
    )
    weak_projection = project_team_f5_runs(
        weak_offense,
        strong_pitcher,
        1.0,
    )

    assert strong_projection > weak_projection


def test_unknown_starter_context_is_strength_neutral():
    baseline = pitcher()
    unknown = pitcher(
        days_rest=None,
        previous_start_ip=None,
        previous_start_pitch_count=None,
    )

    assert starter_context_adjustment(unknown)["adjustment"] == 0.0
    assert project_team_f5_runs(offense(), unknown, 1.0) == project_team_f5_runs(
        offense(),
        baseline,
        1.0,
    )


def test_short_rest_and_workload_increase_first5_run_projection():
    normal = pitcher(days_rest=5, previous_start_ip=6.0, previous_start_pitch_count=92)
    taxed = pitcher(days_rest=3, previous_start_ip=7.0, previous_start_pitch_count=112)

    assert starter_context_adjustment(taxed)["adjustment"] > 0
    assert project_team_f5_runs(offense(), taxed, 1.0) > project_team_f5_runs(
        offense(),
        normal,
        1.0,
    )


def test_opener_risk_has_first5_authority_but_remains_bounded():
    normal = pitcher(role_context="established_starter", average_start_ip=5.8)
    opener = pitcher(role_context="opener_risk", average_start_ip=2.5)
    context = starter_context_adjustment(opener)

    assert context["adjustment"] == 0.1
    assert "opener_risk" in context["reasons"]
    assert project_team_f5_runs(offense(), opener, 1.0) > project_team_f5_runs(
        offense(),
        normal,
        1.0,
    )


def test_missing_starter_context_reduces_reliability_not_strength():
    missing = pitcher(
        days_rest=None,
        previous_start_ip=None,
        previous_start_pitch_count=None,
    )
    reliability = build_reliability(
        away_pitcher=missing,
        home_pitcher=pitcher(days_rest=5, previous_start_ip=6.0, previous_start_pitch_count=92),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )

    assert starter_context_adjustment(missing)["adjustment"] == 0.0
    assert "away_missing_starter_rest_context" in reliability["active_concerns"]
    assert "away_missing_starter_workload_context" in reliability["active_concerns"]


def test_decision_builder_uses_projected_margin_not_removed_decision_score():
    game = {
        "away": {"team": "Away", "projected_f5_runs": 2.0},
        "home": {"team": "Home", "projected_f5_runs": 2.7},
        "f5_ml": {
            "lean": "Home",
            "projected_margin": 0.7,
        },
        "decision_score": 1,
        "confidence": 1,
    }

    assert first5_score_for_team(game, "Home") == 78
    assert first5_score_for_team(game, "Away") == 22


def test_lineup_state_reduces_reliability_only():
    confirmed = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(),
    )
    not_posted = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=lineup(GameLineupStatus.NOT_POSTED),
    )
    unknown = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines=TEST_BASELINES,
        lineup_state=unknown_lineup_state(1, "lineup_provider_failure"),
    )

    assert confirmed["score"] == 100
    assert not_posted["score"] == 95
    assert unknown["score"] == 90
    assert "lineup_not_posted" in not_posted["active_concerns"]
    assert "lineup_unknown" in unknown["active_concerns"]
    assert project_team_f5_runs(offense(), pitcher(), 1.0) == project_team_f5_runs(
        offense(),
        pitcher(),
        1.0,
    )


def test_missing_dynamic_baselines_reduce_reliability_not_projection_strength():
    reliability = build_reliability(
        away_pitcher=pitcher(),
        home_pitcher=pitcher(),
        away_offense=offense(),
        home_offense=offense(),
        park_factor=1.0,
        league_baselines={},
        lineup_state=lineup(),
    )

    assert reliability["score"] == 90
    assert "offense_baseline_sample_insufficient" in reliability[
        "active_concerns"
    ]
    assert "starter_baseline_sample_insufficient" in reliability[
        "active_concerns"
    ]


def test_first5_dynamic_offense_baseline_recenters_run_environment():
    league_baselines = {
        "offense": {
            "runs_per_game": 5.0,
            "source": "test",
            "sample_size": 30,
        },
        "first5": {
            "runs_per_game": 5.0,
            "source": "test",
            "sample_size": 30,
        },
    }

    assert offense_factor_with_baselines(
        offense(runs_per_game=5.0),
        league_baselines=league_baselines,
    ) == 1.0
    assert project_team_f5_runs(
        offense(runs_per_game=5.0),
        pitcher(),
        1.0,
        league_baselines=league_baselines,
    ) > project_team_f5_runs(
        offense(runs_per_game=LEAGUE_RUNS_PER_GAME),
        pitcher(),
        1.0,
    )


def test_first5_dynamic_starter_baselines_recenter_existing_shape():
    league_baselines = {
        "starter": {
            "era": 4.8,
            "whip": 1.35,
            "hr9": 1.3,
            "k_minus_bb9": 4.6,
            "source": "test",
            "sample_size": 30,
        },
    }

    average_pitcher = pitcher(
        era=4.8,
        whip=1.35,
        hr9=1.3,
        k_minus_bb9=4.6,
    )
    poor_pitcher = pitcher(
        era=5.8,
        whip=1.55,
        hr9=1.7,
        k_minus_bb9=2.6,
    )

    assert starter_run_factor_with_baselines(
        average_pitcher,
        league_baselines=league_baselines,
    ) == 1.0
    assert starter_run_factor_with_baselines(
        poor_pitcher,
        league_baselines=league_baselines,
    ) > starter_run_factor_with_baselines(
        average_pitcher,
        league_baselines=league_baselines,
    )


def test_first5_baselines_require_current_sample_before_replacing_static_centers():
    insufficient = build_first5_league_baselines(
        [rich_offense(5.0)] * 9,
        [pitcher()] * 9,
    )
    sufficient = build_first5_league_baselines(
        [rich_offense(5.0)] * 10,
        [pitcher()] * 10,
    )

    assert "offense" not in insufficient
    assert "starter" not in insufficient
    assert sufficient["offense"]["runs_per_game"] == 5.0
    assert sufficient["first5"]["runs_per_game"] == 5.0
    assert sufficient["starter"]["era"] == 4.2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
