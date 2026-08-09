from unittest.mock import patch

from engine.mlb.game_builder import build_mlb_card
from engine.mlb.game_builder import TeamProfileCache, pitcher_from_team, team_profile
from engine.mlb.pitchers import (
    PitcherGameLogCache,
    fetch_pitcher_game_log,
    fetch_pitcher_stats,
    fetch_starter_only_profile,
)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def game_log_payload():
    return {
        "stats": [
            {
                "splits": [
                    {
                        "date": "2026-08-01",
                        "stat": {
                            "gamesStarted": 1,
                            "outs": 18,
                            "earnedRuns": 2,
                            "hits": 5,
                            "strikeOuts": 7,
                            "baseOnBalls": 1,
                            "homeRuns": 1,
                        }
                    }
                ]
            }
        ]
    }


def season_payload():
    return {
        "stats": [
            {
                "splits": [
                    {
                        "stat": {
                            "inningsPitched": "10.0",
                            "era": "3.60",
                            "whip": "1.10",
                            "gamesStarted": 1,
                            "strikeOuts": 10,
                            "baseOnBalls": 2,
                            "homeRuns": 1,
                        }
                    }
                ]
            }
        ]
    }


def test_identical_starter_and_bullpen_game_log_requests_share_one_fetch():
    cache = PitcherGameLogCache()

    with patch(
        "engine.mlb.pitchers.requests.get",
        return_value=Response(game_log_payload()),
    ) as request:
        bullpen_log = fetch_pitcher_game_log(
            42,
            game_log_cache=cache,
            season=2026,
        )
        starter = fetch_starter_only_profile(
            42,
            game_log_cache=cache,
            season=2026,
        )

    assert request.call_count == 1
    assert bullpen_log == game_log_payload()["stats"][0]["splits"]
    assert starter["data_source"] == "starter_game_log"


def test_cache_does_not_change_starter_profile_output():
    cache = PitcherGameLogCache()

    with patch(
        "engine.mlb.pitchers.requests.get",
        return_value=Response(game_log_payload()),
    ) as request:
        uncached = fetch_starter_only_profile(42, season=2026)
        cached = fetch_starter_only_profile(
            42,
            game_log_cache=cache,
            season=2026,
        )

    assert cached == uncached


def test_game_log_cache_key_keeps_season_and_game_type_isolated():
    cache = PitcherGameLogCache()

    with patch(
        "engine.mlb.pitchers.requests.get",
        return_value=Response(game_log_payload()),
    ) as request:
        fetch_pitcher_game_log(42, game_log_cache=cache, season=2026)
        fetch_pitcher_game_log(42, game_log_cache=cache, season=2026)
        fetch_pitcher_game_log(42, game_log_cache=cache, season=2025)
        fetch_pitcher_game_log(
            42,
            game_log_cache=cache,
            season=2026,
            game_type="S",
        )
        fetch_pitcher_game_log(77, game_log_cache=cache, season=2026)

    assert request.call_count == 4


def test_empty_game_log_is_cached_as_an_empty_successful_result():
    cache = PitcherGameLogCache()

    with patch(
        "engine.mlb.pitchers.requests.get",
        return_value=Response({"stats": []}),
    ) as request:
        first = fetch_pitcher_game_log(42, game_log_cache=cache)
        second = fetch_pitcher_game_log(42, game_log_cache=cache)

    assert first == []
    assert second == []


def test_starter_profile_preserves_previous_start_context():
    payload = {
        "stats": [
            {
                "splits": [
                    {
                        "date": "2026-07-25",
                        "stat": {
                            "gamesStarted": 1,
                            "outs": 15,
                            "earnedRuns": 2,
                            "hits": 4,
                            "strikeOuts": 5,
                            "baseOnBalls": 1,
                            "homeRuns": 0,
                            "battersFaced": 20,
                            "numberOfPitches": 86,
                        },
                    },
                    {
                        "date": "2026-07-31",
                        "stat": {
                            "gamesStarted": 1,
                            "outs": 22,
                            "earnedRuns": 1,
                            "hits": 5,
                            "strikeOuts": 8,
                            "baseOnBalls": 1,
                            "homeRuns": 1,
                            "battersFaced": 28,
                            "numberOfPitches": 108,
                        },
                    },
                    {
                        "date": "2026-08-07",
                        "stat": {
                            "gamesStarted": 1,
                            "outs": 18,
                            "earnedRuns": 3,
                            "hits": 6,
                            "strikeOuts": 4,
                            "baseOnBalls": 2,
                            "homeRuns": 1,
                            "battersFaced": 25,
                            "numberOfPitches": 92,
                        },
                    },
                ]
            }
        ]
    }

    with patch(
        "engine.mlb.pitchers.requests.get",
        return_value=Response(payload),
    ) as request:
        starter = fetch_starter_only_profile(
            42,
            season=2026,
            as_of="2026-08-06T19:05:00Z",
        )

    assert starter["previous_start_date"] == "2026-07-31"
    assert starter["days_rest"] == 6
    assert starter["previous_start_ip"] == 7.3
    assert starter["previous_start_pitch_count"] == 108
    assert starter["last_two_starts_pitch_count"] == 194
    assert starter["role_context"] == "limited_starting_role"
    assert request.call_count == 1


def test_game_builder_pitcher_payload_preserves_starter_context():
    team_blob = {
        "probablePitcher": {
            "id": 42,
            "fullName": "Context Starter",
            "pitchHand": {"code": "R"},
        }
    }
    stats = {
        "era": 3.40,
        "whip": 1.12,
        "ip": 100.0,
        "starts": 18,
        "previous_start_date": "2026-07-31",
        "days_rest": 5,
        "previous_start_ip": 7.0,
        "previous_start_pitch_count": 104,
        "last_two_starts_ip": 13.0,
        "last_two_starts_pitch_count": 198,
        "last14_start_ip": 13.0,
        "average_start_ip": 5.6,
        "role_context": "established_starter",
        "data_source": "starter_game_log",
    }

    with patch(
        "engine.mlb.game_builder.fetch_pitcher_stats",
        return_value=stats,
    ):
        pitcher = pitcher_from_team(
            team_blob,
            game_date="2026-08-05T19:05:00Z",
        )

    assert pitcher["previous_start_date"] == "2026-07-31"
    assert pitcher["days_rest"] == 5
    assert pitcher["previous_start_pitch_count"] == 104
    assert pitcher["role_context"] == "established_starter"


def test_cached_game_log_failure_remains_a_failure_and_uses_existing_fallback():
    cache = PitcherGameLogCache()

    with patch(
        "engine.mlb.pitchers.requests.get",
        side_effect=[RuntimeError("game-log unavailable"), Response(season_payload())],
    ) as request:
        assert fetch_pitcher_game_log(42, game_log_cache=cache) is None
        profile = fetch_pitcher_stats(42, game_log_cache=cache)

    assert profile["data_source"] == "season_fallback"
    assert request.call_count == 2
    assert request.call_args_list[0].kwargs["params"]["stats"] == "gameLog"
    assert request.call_args_list[1].kwargs["params"]["stats"] == "season"


def test_mlb_card_build_injects_one_game_log_cache_into_bullpen_and_starter_paths():
    raw_games = [
        {
            "gamePk": 1,
            "gameDate": "2026-07-25T20:00:00Z",
            "status": {"detailedState": "Scheduled"},
            "teams": {
                "away": {
                    "team": {"id": 1, "name": "Away Club"},
                    "probablePitcher": {"id": 11, "fullName": "Away Starter"},
                },
                "home": {
                    "team": {"id": 2, "name": "Home Club"},
                    "probablePitcher": {"id": 22, "fullName": "Home Starter"},
                },
            },
        }
    ]
    profile = {"runs_per_game": 4.5, "ops": 0.700}
    pitcher = {"era": 3.5, "whip": 1.2, "ip": 50.0}
    cache_ids = []

    def bullpen(*args, game_log_cache=None, **kwargs):
        cache_ids.append(id(game_log_cache))
        return {}

    def starter(*args, game_log_cache=None, **kwargs):
        cache_ids.append(id(game_log_cache))
        return pitcher

    with (
        patch("engine.mlb.game_builder.fetch_market_quotes", return_value=([], [])),
        patch("engine.mlb.game_builder.fetch_team_batting_stats", return_value=profile),
        patch("engine.mlb.game_builder.fetch_bullpen_profile", side_effect=bullpen),
        patch("engine.mlb.game_builder.fetch_pitcher_stats", side_effect=starter),
        patch("engine.mlb.game_builder.build_totals_projection", return_value={}),
    ):
        card = build_mlb_card(raw_games)

    assert len(card["games"]) == 1
    assert len(cache_ids) == 4
    assert len(set(cache_ids)) == 1


def test_team_profile_cache_reuses_doubleheader_team_context():
    raw_games = [
        {
            "gamePk": game_id,
            "gameDate": f"2026-07-25T{hour}:00:00Z",
            "status": {"detailedState": "Scheduled"},
            "teams": {
                "away": {
                    "team": {"id": 1, "name": "Away Club"},
                    "probablePitcher": {"id": 11, "fullName": "Away Starter"},
                },
                "home": {
                    "team": {"id": 2, "name": "Home Club"},
                    "probablePitcher": {"id": 22, "fullName": "Home Starter"},
                },
            },
        }
        for game_id, hour in ((1, "20"), (2, "23"))
    ]
    offense = {"runs_per_game": 4.5, "ops": 0.700}
    bullpen = {"era": 3.8, "whip": 1.2}
    pitcher = {"era": 3.5, "whip": 1.2, "ip": 50.0}

    with (
        patch("engine.mlb.game_builder.fetch_market_quotes", return_value=([], [])),
        patch(
            "engine.mlb.game_builder.fetch_team_batting_stats",
            return_value=offense,
        ) as batting,
        patch(
            "engine.mlb.game_builder.fetch_bullpen_profile",
            return_value=bullpen,
        ) as bullpen_fetch,
        patch("engine.mlb.game_builder.fetch_pitcher_stats", return_value=pitcher),
        patch("engine.mlb.game_builder.build_totals_projection", return_value={}),
    ):
        card = build_mlb_card(raw_games)

    assert len(card["games"]) == 2
    assert batting.call_count == 2
    assert bullpen_fetch.call_count == 2
    assert {call.args[0] for call in batting.call_args_list} == {1, 2}
    assert {call.args[0] for call in bullpen_fetch.call_args_list} == {1, 2}


def test_team_profile_cache_keeps_teams_and_game_profiles_isolated():
    cache = TeamProfileCache()
    team_one = {"team": {"id": 1, "name": "Away Club"}}
    team_two = {"team": {"id": 2, "name": "Home Club"}}
    offense = {"runs_per_game": 4.5}
    bullpen = {"era": 3.8}

    with (
        patch(
            "engine.mlb.game_builder.fetch_team_batting_stats",
            return_value=offense,
        ) as batting,
        patch(
            "engine.mlb.game_builder.fetch_bullpen_profile",
            return_value=bullpen,
        ) as bullpen_fetch,
    ):
        first = team_profile(team_one, team_profile_cache=cache)
        repeated = team_profile(team_one, team_profile_cache=cache)
        other = team_profile(team_two, team_profile_cache=cache)

    assert batting.call_count == 2
    assert bullpen_fetch.call_count == 2
    assert first == repeated
    assert first["offense"] is not repeated["offense"]
    assert first["bullpen"] is not repeated["bullpen"]
    assert other["id"] == 2


def test_team_profile_cache_preserves_doubleheader_card_output():
    raw_games = [
        {
            "gamePk": game_id,
            "gameDate": f"2026-07-25T{hour}:00:00Z",
            "status": {"detailedState": "Scheduled"},
            "teams": {
                "away": {
                    "team": {"id": 1, "name": "Away Club"},
                    "probablePitcher": {"id": 11, "fullName": "Away Starter"},
                },
                "home": {
                    "team": {"id": 2, "name": "Home Club"},
                    "probablePitcher": {"id": 22, "fullName": "Home Starter"},
                },
            },
        }
        for game_id, hour in ((1, "20"), (2, "23"))
    ]
    offense = {"runs_per_game": 4.5, "ops": 0.700}
    bullpen = {"era": 3.8, "whip": 1.2}
    pitcher = {"era": 3.5, "whip": 1.2, "ip": 50.0}

    class NoTeamProfileCache:
        def get_or_fetch(self, _team_id, *, fetcher):
            return fetcher()

    with (
        patch("engine.mlb.game_builder.fetch_market_quotes", return_value=([], [])),
        patch("engine.mlb.game_builder.fetch_team_batting_stats", return_value=offense),
        patch("engine.mlb.game_builder.fetch_bullpen_profile", return_value=bullpen),
        patch("engine.mlb.game_builder.fetch_pitcher_stats", return_value=pitcher),
        patch("engine.mlb.game_builder.build_totals_projection", return_value={}),
    ):
        cached = build_mlb_card(raw_games)
        with patch(
            "engine.mlb.game_builder.TeamProfileCache",
            return_value=NoTeamProfileCache(),
        ):
            uncached = build_mlb_card(raw_games)

    cached.pop("generated_at")
    uncached.pop("generated_at")
    assert cached == uncached
