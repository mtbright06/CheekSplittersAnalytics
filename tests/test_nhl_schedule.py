from __future__ import annotations

from datetime import UTC, datetime

from engine.nhl.schedule import (
    build_nhl_schedule,
    normalize_nhl_game,
    normalize_nhl_schedule,
    normalize_nhl_schedule_for_date,
)
from engine.nhl.teams import nhl_logo_key


def _team(
    team_id: int,
    abbreviation: str,
    place: str,
    common: str,
) -> dict:
    return {
        "id": team_id,
        "abbrev": abbreviation,
        "placeName": {"default": place},
        "commonName": {"default": common},
    }


def _raw_game() -> dict:
    return {
        "id": 2023020204,
        "startTimeUTC": "2023-11-10T00:00:00Z",
        "gameState": "FUT",
        "gameScheduleState": "OK",
        "venue": {"default": "TD Garden"},
        "awayTeam": _team(14, "TBL", "Tampa Bay", "Lightning"),
        "homeTeam": _team(6, "BOS", "Boston", "Bruins"),
    }


def test_valid_scheduled_game_normalization_preserves_contract():
    game = normalize_nhl_game(_raw_game())

    assert game is not None
    assert game.source_game_id == 2023020204
    assert game.game_date == datetime(2023, 11, 10, tzinfo=UTC)
    assert game.game_date.tzinfo is not None
    assert game.game_status == "SCHEDULED"
    assert game.venue == "TD Garden"
    assert game.away_team.source_team_id == 14
    assert game.away_team.full_name == "Tampa Bay Lightning"
    assert game.away_team.abbreviation == "TBL"
    assert game.home_team.source_team_id == 6
    assert game.home_team.full_name == "Boston Bruins"
    assert game.home_team.abbreviation == "BOS"
    assert nhl_logo_key(game.home_team) == "bos"


def test_status_normalization_handles_live_final_and_postponed():
    live = {
        **_raw_game(),
        "gameState": "LIVE",
    }
    final = {
        **_raw_game(),
        "gameState": "OFF",
    }
    postponed = {
        **_raw_game(),
        "gameState": "POST",
    }

    assert normalize_nhl_game(live).game_status == "LIVE"
    assert normalize_nhl_game(final).game_status == "FINAL"
    assert normalize_nhl_game(postponed).game_status == "POSTPONED"


def test_missing_optional_fields_do_not_crash():
    raw = _raw_game()
    raw.pop("venue")

    game = normalize_nhl_game(raw)

    assert game is not None
    assert game.venue is None
    assert game.away_goalie is None
    assert game.home_goalie is None


def test_malformed_required_fields_are_skipped():
    raw = _raw_game()
    raw.pop("homeTeam")

    assert normalize_nhl_game(raw) is None


def test_empty_schedule_is_safe():
    assert normalize_nhl_schedule({"gameWeek": []}) == []
    assert normalize_nhl_schedule(None) == []


def test_schedule_normalizes_all_games_in_game_week():
    raw = {
        "gameWeek": [
            {
                "date": "2023-11-10",
                "games": [
                    _raw_game(),
                    {
                        **_raw_game(),
                        "id": 2023020205,
                        "awayTeam": _team(8, "MTL", "Montréal", "Canadiens"),
                    },
                ],
            }
        ]
    }

    games = normalize_nhl_schedule(raw)

    assert [game.source_game_id for game in games] == [
        2023020204,
        2023020205,
    ]


def test_build_schedule_accepts_injected_raw_schedule():
    games = build_nhl_schedule(
        "2023-11-10",
        raw_schedule={
            "gameWeek": [
                {
                    "date": "2023-11-10",
                    "games": [_raw_game()],
                }
            ]
        }
    )

    assert len(games) == 1
    assert games[0].home_team.abbreviation == "BOS"


def test_public_schedule_filters_provider_week_to_requested_date():
    raw = {
        "gameWeek": [
            {
                "date": "2023-11-10",
                "games": [_raw_game()],
            },
            {
                "date": "2023-11-11",
                "games": [
                    {
                        **_raw_game(),
                        "id": 2023020205,
                        "startTimeUTC": "2023-11-11T00:00:00Z",
                    }
                ],
            },
        ]
    }

    week_games = normalize_nhl_schedule(raw)
    date_games = normalize_nhl_schedule_for_date(
        raw,
        "2023-11-10",
    )
    public_games = build_nhl_schedule(
        "2023-11-10",
        raw_schedule=raw,
    )

    assert [game.source_game_id for game in week_games] == [
        2023020204,
        2023020205,
    ]
    assert [game.source_game_id for game in date_games] == [2023020204]
    assert [game.source_game_id for game in public_games] == [2023020204]
