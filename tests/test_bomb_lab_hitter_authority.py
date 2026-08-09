from unittest.mock import patch

from engine.hitters.target_hitters import (
    attach_target_hitters_to_pitchers,
    build_hitter_profiles,
    hitter_hr_ability_score,
    hitter_sample_reliability,
    hr_opportunity_score,
    side_matches,
)
from engine.hitters.team_abbreviations import statcast_team_abbreviations


POWER_HITTER = {
    "barrel_pct": 0.12,
    "hard_hit_pct": 0.50,
    "avg_ev": 94.0,
    "hr_vs_lhp": 4,
    "hr_vs_rhp": 12,
    "bbe": 200,
    "pa": 250,
}


WEAK_HITTER = {
    "barrel_pct": 0.02,
    "hard_hit_pct": 0.04,
    "avg_ev": 84.0,
    "hr_vs_lhp": 1,
    "hr_vs_rhp": 1,
    "bbe": 180,
    "pa": 220,
}


def test_hitter_hr_ability_uses_handedness_split():
    assert hitter_hr_ability_score(POWER_HITTER, "R") > hitter_hr_ability_score(
        POWER_HITTER,
        "L",
    )


def test_missing_pitcher_hand_does_not_fabricate_split_power():
    assert hitter_hr_ability_score(POWER_HITTER, None) < hitter_hr_ability_score(
        POWER_HITTER,
        "R",
    )
    reliability = hitter_sample_reliability(POWER_HITTER, None)
    assert "pitcher_hand_missing" in reliability["concerns"]


def test_switch_and_any_side_matching_remains_safe():
    assert side_matches("L", "BOTH") is True
    assert side_matches("R", "ANY") is True
    assert side_matches("L", "R") is False


def test_missing_hitter_sample_reduces_reliability_only():
    reliability = hitter_sample_reliability(
        {
            **POWER_HITTER,
            "bbe": 0,
            "pa": 0,
        },
        "R",
    )

    assert reliability["score"] == 45.0
    assert "hitter_batted_ball_sample_missing" in reliability["concerns"]
    assert "hitter_pa_sample_missing" in reliability["concerns"]


def test_pitcher_hitter_and_park_remain_separate_authority_inputs():
    vulnerable_pitcher_weak_hitter = hr_opportunity_score(
        pitcher_vulnerability=80.0,
        hitter_hr_ability=hitter_hr_ability_score(WEAK_HITTER, "R"),
        environment_score=50.0,
    )
    moderate_pitcher_elite_hitter = hr_opportunity_score(
        pitcher_vulnerability=45.0,
        hitter_hr_ability=hitter_hr_ability_score(POWER_HITTER, "R"),
        environment_score=50.0,
    )

    assert moderate_pitcher_elite_hitter > vulnerable_pitcher_weak_hitter


def test_hitter_hr_ability_centered_scale_has_neutral_meaning():
    average_hitter = {
        "barrel_pct": 0.04,
        "hard_hit_pct": 0.09,
        "avg_ev": 84.0,
        "hr_vs_rhp": 8,
        "hr_vs_lhp": 8,
    }

    assert hitter_hr_ability_score(average_hitter, "R") == 50.0
    assert hitter_hr_ability_score(POWER_HITTER, "R") == 95.0


def test_hr_opportunity_uses_corrected_top_level_weights():
    assert hr_opportunity_score(
        pitcher_vulnerability=80.0,
        hitter_hr_ability=60.0,
        environment_score=40.0,
    ) == 65.0


def test_park_context_cannot_change_hitter_ability():
    ability = hitter_hr_ability_score(POWER_HITTER, "R")

    assert hr_opportunity_score(
        pitcher_vulnerability=50.0,
        hitter_hr_ability=ability,
        environment_score=80.0,
    ) > hr_opportunity_score(
        pitcher_vulnerability=50.0,
        hitter_hr_ability=ability,
        environment_score=40.0,
    )
    assert hitter_hr_ability_score(POWER_HITTER, "R") == ability


def test_bomb_squad_display_order_uses_descending_target_score():
    hitters = [
        {
            "batter_id": 1,
            "name": "Higher Opportunity",
            "position": "OF",
            "bat_side": "L",
            "pa": 200,
            "bbe": 150,
            "hard_hit_pct": 0.09,
            "barrel_pct": 0.04,
            "avg_ev": 84.0,
            "hr": 10,
            "hr_vs_lhp": 0,
            "hr_vs_rhp": 1,
        },
        {
            "batter_id": 2,
            "name": "Higher Target",
            "position": "OF",
            "bat_side": "R",
            "pa": 200,
            "bbe": 150,
            "hard_hit_pct": 0.09,
            "barrel_pct": 0.04,
            "avg_ev": 84.0,
            "hr": 10,
            "hr_vs_lhp": 0,
            "hr_vs_rhp": 20,
        },
    ]

    with (
        patch(
            "engine.hitters.target_hitters.fetch_active_roster",
            lambda team_id: [{"player_id": 1}, {"player_id": 2}],
        ),
        patch(
            "engine.hitters.target_hitters.build_hitter_profiles",
            lambda **kwargs: hitters,
        ),
    ):
        [item] = attach_target_hitters_to_pitchers(
            [
                {
                    "opponent": "Test Team",
                    "opponent_team_id": 1,
                    "opponent_abbr": "TST",
                    "target_side": "R",
                    "pitcher_throw": "R",
                    "bomb_score": 50.0,
                    "pitcher_vulnerability": 80.0,
                    "environment_score": 50.0,
                    "bomb_reliability": 95.0,
                }
            ],
            season_statcast_df=object(),
        )

    target_scores = [hitter["target_score"] for hitter in item["top_hitters"]]

    assert target_scores == sorted(target_scores, reverse=True)
    assert item["recommended_hitter"] == item["top_hitters"][0]["name"]


def test_confirmed_nonstarter_is_excluded_and_next_starter_is_promoted():
    from engine.lineups.models import (
        GameLineupStatus,
        LineupPlayer,
        PlayerLineupStatus,
        TeamLineup,
    )

    hitters = [
        {
            "batter_id": 1,
            "name": "Bench Power",
            "position": "OF",
            "bat_side": "R",
            "pa": 250,
            "bbe": 180,
            "hard_hit_pct": 0.55,
            "barrel_pct": 0.18,
            "avg_ev": 96.0,
            "hr": 20,
            "hr_vs_lhp": 8,
            "hr_vs_rhp": 22,
        },
        {
            "batter_id": 2,
            "name": "Starting Power",
            "position": "1B",
            "bat_side": "R",
            "pa": 250,
            "bbe": 180,
            "hard_hit_pct": 0.42,
            "barrel_pct": 0.10,
            "avg_ev": 91.0,
            "hr": 16,
            "hr_vs_lhp": 6,
            "hr_vs_rhp": 16,
        },
    ]

    team_lineup = TeamLineup(
        team_id=1,
        team_name="Test Team",
        side="away",
        status=GameLineupStatus.CONFIRMED,
        starters=(
            LineupPlayer(
                player_id=2,
                player_name="Starting Power",
                team_id=1,
                team_name="Test Team",
                side="away",
                lineup_status=PlayerLineupStatus.CONFIRMED_STARTER,
                batting_order=4,
                position="1B",
            ),
        ),
        bench=(
            LineupPlayer(
                player_id=1,
                player_name="Bench Power",
                team_id=1,
                team_name="Test Team",
                side="away",
                lineup_status=PlayerLineupStatus.BENCH,
                position="OF",
            ),
        ),
    )

    class LineupState:
        def __init__(self, team_lineup):
            self.status = GameLineupStatus.CONFIRMED
            self.game_status = "Pre-Game"
            self.source = "test"
            self.concerns = ()
            self.retrieved_at = type(
                "RetrievedAt",
                (),
                {"isoformat": lambda self: "2026-08-08T00:00:00+00:00"},
            )()
            self.freshness_seconds = 0.0
            self.is_stale = False
            self.away_lineup = team_lineup
            self.home_lineup = None

        def team_lineup(self, team_id):
            return self.away_lineup if team_id == 1 else None

    class Service:
        def get_game_lineup(self, game_id):
            return LineupState(team_lineup)

    with (
        patch(
            "engine.hitters.target_hitters.fetch_active_roster",
            lambda team_id: [{"player_id": 1}, {"player_id": 2}],
        ),
        patch(
            "engine.hitters.target_hitters.build_hitter_profiles",
            lambda **kwargs: hitters,
        ),
    ):
        [item] = attach_target_hitters_to_pitchers(
            [
                {
                    "game_pk": 1,
                    "opponent": "Test Team",
                    "opponent_team_id": 1,
                    "opponent_abbr": "TST",
                    "target_side": "R",
                    "pitcher_throw": "R",
                    "bomb_score": 50.0,
                    "pitcher_vulnerability": 80.0,
                    "environment_score": 50.0,
                    "bomb_reliability": 95.0,
                }
            ],
            season_statcast_df=object(),
            lineup_service=Service(),
        )

    assert item["recommended_hitter"] == "Starting Power"
    assert [hitter["name"] for hitter in item["top_hitters"]] == [
        "Starting Power"
    ]
    assert item["top_hitters"][0]["lineup_actionability"] == "ACTIONABLE"


def test_arizona_statcast_alias_resolves_to_az():
    assert statcast_team_abbreviations("ARI") == ("ARI", "AZ")


def test_arizona_active_hitter_survives_statcast_team_alias():
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "batter": 682998,
                "stand": "L",
                "p_throws": "R",
                "events": "home_run",
                "launch_speed": 101.0,
                "launch_angle": 28.0,
                "launch_speed_angle": 6,
                "game_date": "2026-08-08",
                "inning_topbot": "Bot",
                "away_team": "LAD",
                "home_team": "AZ",
            }
        ]
    )

    hitters = build_hitter_profiles(
        statcast_df=df,
        team_abbr="ARI",
        roster_players=[
            {
                "player_id": 682998,
                "name": "Corbin Carroll",
                "position": "OF",
            }
        ],
    )

    assert len(hitters) == 1
    assert hitters[0]["name"] == "Corbin Carroll"


def test_not_posted_lineup_does_not_erase_arizona_candidates():
    hitters = [
        {
            "batter_id": 682998,
            "name": "Corbin Carroll",
            "position": "OF",
            "bat_side": "L",
            "pa": 200,
            "bbe": 150,
            "hard_hit_pct": 0.09,
            "barrel_pct": 0.04,
            "avg_ev": 84.0,
            "hr": 10,
            "hr_vs_lhp": 3,
            "hr_vs_rhp": 10,
        }
    ]

    class TeamLineup:
        from engine.lineups.models import GameLineupStatus

        status = GameLineupStatus.NOT_POSTED
        concerns = ()
        starters = ()
        bench = ()

        def player_status(self, player_id):
            from engine.lineups.models import LineupPlayer, PlayerLineupStatus

            return LineupPlayer(
                player_id=player_id,
                player_name=None,
                team_id=109,
                team_name="Arizona Diamondbacks",
                side="home",
                lineup_status=PlayerLineupStatus.UNKNOWN,
            )

    class LineupState:
        status = type("Status", (), {"value": "NOT_POSTED"})()
        game_status = "Scheduled"
        source = "test"
        concerns = ()
        retrieved_at = type(
            "RetrievedAt",
            (),
            {"isoformat": lambda self: "2026-08-08T00:00:00+00:00"},
        )()
        freshness_seconds = 0.0
        is_stale = False
        away_lineup = None
        home_lineup = TeamLineup()

        def team_lineup(self, team_id):
            return self.home_lineup if team_id == 109 else None

    class Service:
        def get_game_lineup(self, game_id):
            return LineupState()

    with (
        patch(
            "engine.hitters.target_hitters.fetch_active_roster",
            lambda team_id: [{"player_id": 682998}],
        ),
        patch(
            "engine.hitters.target_hitters.build_hitter_profiles",
            lambda **kwargs: hitters,
        ),
    ):
        [item] = attach_target_hitters_to_pitchers(
            [
                {
                    "game_pk": 1,
                    "opponent": "Arizona Diamondbacks",
                    "opponent_team_id": 109,
                    "opponent_abbr": "ARI",
                    "target_side": "R",
                    "pitcher_throw": "R",
                    "bomb_score": 50.0,
                    "pitcher_vulnerability": 80.0,
                    "environment_score": 50.0,
                    "bomb_reliability": 95.0,
                }
            ],
            season_statcast_df=object(),
            lineup_service=Service(),
        )

    assert item["top_hitters"][0]["name"] == "Corbin Carroll"
    assert item["top_hitters"][0]["lineup_actionability"] == "PENDING_LINEUP"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
