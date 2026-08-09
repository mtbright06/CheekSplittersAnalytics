from __future__ import annotations

from datetime import UTC, datetime

from engine.nhl.game_builder import build_nhl_games
from engine.nhl.goalies import (
    CONFIRMED,
    UNKNOWN,
    UNAVAILABLE,
    load_game_goalie_assignments,
    normalize_game_goalie_assignments,
)
from engine.nhl.models import NHLGoalieAssignment, NHLPlayer, NHLTeam
from engine.nhl.players import NHLRosterService


RETRIEVED_AT = datetime(2026, 1, 1, tzinfo=UTC)
GAME_START = datetime(2026, 1, 2, tzinfo=UTC)
FUTURE_DATE = "2099-11-10"


def _goalie(
    player_id: int | None,
    name: str,
    *,
    starter: bool,
) -> dict:
    payload = {
        "name": {"default": name},
        "position": "G",
        "starter": starter,
        "sweaterNumber": 30,
    }
    if player_id is not None:
        payload["playerId"] = player_id
    return payload


def _boxscore() -> dict:
    return {
        "startTimeUTC": "2026-01-02T00:00:00Z",
        "playerByGameStats": {
            "awayTeam": {
                "goalies": [
                    _goalie(1, "Away Backup", starter=False),
                    _goalie(2, "Away Starter", starter=True),
                ]
            },
            "homeTeam": {
                "goalies": [
                    _goalie(3, "Home Starter", starter=True),
                ]
            },
        },
    }


def _player(
    player_id: int,
    name: str,
    team: str,
) -> NHLPlayer:
    return NHLPlayer(
        source_player_id=player_id,
        name=name,
        team_abbreviation=team,
        position="G",
        position_code="G",
        position_name="Goalie",
    )


def _schedule() -> dict:
    return {
        "gameWeek": [
            {
                "date": FUTURE_DATE,
                "games": [
                    {
                        "id": 2099020001,
                        "startTimeUTC": f"{FUTURE_DATE}T00:00:00Z",
                        "gameState": "FUT",
                        "awayTeam": {
                            "id": 6,
                            "abbrev": "BOS",
                            "placeName": {"default": "Boston"},
                            "commonName": {"default": "Bruins"},
                        },
                        "homeTeam": {
                            "id": 3,
                            "abbrev": "NYR",
                            "placeName": {"default": "New York"},
                            "commonName": {"default": "Rangers"},
                        },
                    }
                ],
            }
        ]
    }


def _teams() -> list[NHLTeam]:
    return [
        NHLTeam(6, "Boston Bruins", "BOS", "bos"),
        NHLTeam(3, "New York Rangers", "NYR", "nyr"),
    ]


def test_confirmed_goalie_normalization_matches_player_id():
    away, home = normalize_game_goalie_assignments(
        _boxscore(),
        away_roster=(
            _player(2, "Away Starter", "BOS"),
        ),
        home_roster=(
            _player(3, "Home Starter", "NYR"),
        ),
        away_team_abbreviation="BOS",
        home_team_abbreviation="NYR",
        game_start_time=GAME_START,
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == CONFIRMED
    assert away.player.source_player_id == 2
    assert away.source == "nhl_gamecenter_boxscore"
    assert away.retrieved_at == RETRIEVED_AT
    assert away.source_timestamp == GAME_START
    assert away.game_start_time == GAME_START
    assert home.status == CONFIRMED
    assert home.player.name == "Home Starter"


def test_unknown_status_when_pregame_boxscore_has_no_player_stats():
    away, home = normalize_game_goalie_assignments(
        {
            "startTimeUTC": "2026-01-02T00:00:00Z",
            "gameState": "FUT",
        },
        game_start_time=GAME_START,
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == UNKNOWN
    assert home.status == UNKNOWN
    assert "goalie_status_not_exposed_pregame" in away.concerns


def test_unavailable_source_is_safe():
    class Game:
        source_game_id = 1
        game_date = GAME_START

    away, home = load_game_goalie_assignments(
        Game(),
        fetcher=lambda _: (_ for _ in ()).throw(RuntimeError("down")),
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == UNAVAILABLE
    assert home.status == UNAVAILABLE
    assert "goalie_status_source_unavailable" in away.concerns


def test_player_id_not_in_current_roster_creates_stable_game_specific_identity():
    away, _ = normalize_game_goalie_assignments(
        _boxscore(),
        away_roster=(),
        home_roster=(),
        away_team_abbreviation="BOS",
        game_start_time=GAME_START,
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == CONFIRMED
    assert away.player.source_player_id == 2
    assert away.player.team_abbreviation == "BOS"
    assert away.player.position == "G"
    assert "goalie_status_player_not_in_current_roster" in away.concerns


def test_name_fallback_matching_if_player_id_missing():
    raw = _boxscore()
    raw["playerByGameStats"]["awayTeam"]["goalies"][1].pop("playerId")

    away, _ = normalize_game_goalie_assignments(
        raw,
        away_roster=(
            _player(22, "Away Starter", "BOS"),
        ),
        game_start_time=GAME_START,
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == CONFIRMED
    assert away.player.source_player_id == 22
    assert "goalie_status_matched_by_name" in away.concerns


def test_ambiguous_name_match_fails_safely():
    raw = _boxscore()
    raw["playerByGameStats"]["awayTeam"]["goalies"][1].pop("playerId")

    away, _ = normalize_game_goalie_assignments(
        raw,
        away_roster=(
            _player(22, "Away Starter", "BOS"),
            _player(23, "Away Starter", "BOS"),
        ),
        game_start_time=GAME_START,
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == UNKNOWN
    assert away.player is None
    assert "goalie_status_ambiguous_name_match" in away.concerns


def test_multiple_starters_are_ambiguous():
    raw = _boxscore()
    raw["playerByGameStats"]["awayTeam"]["goalies"][0]["starter"] = True

    away, _ = normalize_game_goalie_assignments(
        raw,
        game_start_time=GAME_START,
        retrieved_at=RETRIEVED_AT,
    )

    assert away.status == UNKNOWN
    assert "goalie_status_ambiguous_starters" in away.concerns


def test_builder_attaches_goalie_assignment_without_guessing():
    status = NHLGoalieAssignment(
        status=CONFIRMED,
        player=_player(2, "Away Starter", "BOS"),
        source="test",
        retrieved_at=RETRIEVED_AT,
    )

    games = build_nhl_games(
        FUTURE_DATE,
        raw_schedule=_schedule(),
        teams=_teams(),
        roster_service=NHLRosterService(fetcher=lambda _: {"goalies": []}),
        goalie_status_loader=lambda game: (status, NHLGoalieAssignment()),
    )

    assert games[0].away_goalie_status.status == CONFIRMED
    assert games[0].away_goalie_status.player.source_player_id == 2
    assert games[0].home_goalie_status.status == UNKNOWN
