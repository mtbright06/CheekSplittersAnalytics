from engine.decision.decision_builder import first5_score_for_team
from engine.first5.first5_model import (
    build_reliability,
    moneyline_recommendation,
    project_team_f5_runs,
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
):
    return {
        "available": available,
        "innings": innings,
        "era": era,
        "whip": whip,
        "hr9": hr9,
        "k_minus_bb9": k_minus_bb9,
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
    )
    missing = build_reliability(
        away_pitcher=pitcher(available=False),
        home_pitcher=pitcher(),
        away_offense=offense(games=0),
        home_offense=offense(),
        park_factor=1.0,
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
    )

    assert reliability["score"] == 100
    assert reliability["active_concerns"] == []
    assert "lineup_quality_not_evaluated" in reliability[
        "future_unavailable_context"
    ]
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
