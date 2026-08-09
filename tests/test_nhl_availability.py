from __future__ import annotations

import json
from datetime import UTC, datetime

from engine.nhl.availability import (
    DailyFaceoffAvailabilityProvider,
    NHLAvailabilityLine,
    NHLGameAvailability,
    NHLTeamAvailability,
    resolve_player_identity,
)
from engine.nhl.game_builder import build_nhl_games
from engine.nhl.goalies import CONFIRMED, PROJECTED, UNKNOWN
from engine.nhl.goalies import UNAVAILABLE
from engine.nhl.models import NHLPlayer, NHLTeam
from engine.nhl.players import NHLRosterService


FUTURE_DATE = "2099-11-10"


class FakeResponse:
    def __init__(self, payload: dict):
        self.text = (
            '<html><script id="__NEXT_DATA__" type="application/json">'
            f"{json.dumps({'props': {'pageProps': payload}})}"
            "</script></html>"
        )

    def raise_for_status(self) -> None:
        return None


def _player(
    player_id: int,
    name: str,
    team: str,
    position: str = "C",
) -> NHLPlayer:
    return NHLPlayer(
        source_player_id=player_id,
        name=name,
        team_abbreviation=team,
        position=position,
        position_code=position,
        position_name="Goalie" if position == "G" else None,
    )


def _roster(team: str) -> dict:
    return {
        "forwards": [
            _raw_player(1, "Forward", "One", "C"),
            _raw_player(2, "Forward", "Two", "L"),
            _raw_player(3, "Forward", "Three", "R"),
            _raw_player(4, "Forward", "Four", "C"),
            _raw_player(5, "Forward", "Five", "L"),
            _raw_player(6, "Forward", "Six", "R"),
        ],
        "defensemen": [
            _raw_player(7, "Defense", "One", "D"),
            _raw_player(8, "Defense", "Two", "D"),
        ],
        "goalies": [
            _raw_player(9, f"{team}", "Goalie", "G"),
        ],
    }


def _raw_player(
    player_id: int,
    first: str,
    last: str,
    position: str,
) -> dict:
    return {
        "id": player_id,
        "firstName": {"default": first},
        "lastName": {"default": last},
        "positionCode": position,
    }


def _line_payload(team: str) -> dict:
    return {
        "combinations": {
            "teamName": f"{team} Team",
            "teamAbbreviation": team,
            "sourceName": "Projected",
            "updatedAt": "2099-11-09T16:00:00.000Z",
            "players": [
                _df_player("Forward Two", "lw", "f1", "Forwards 1", "ev"),
                _df_player("Forward One", "c", "f1", "Forwards 1", "ev"),
                _df_player("Forward Three", "rw", "f1", "Forwards 1", "ev"),
                _df_player("Defense One", "ld", "d1", "Defense 1", "ev"),
                _df_player("Defense Two", "rd", "d1", "Defense 1", "ev"),
                _df_player("Forward One", "sk1", "pp1", "1st Powerplay Unit", "pp"),
                _df_player("Forward Two", "sk2", "pp1", "1st Powerplay Unit", "pp"),
                _df_player("Defense One", "sk3", "pp1", "1st Powerplay Unit", "pp"),
            ],
        }
    }


def _df_player(
    name: str,
    position: str,
    group: str,
    group_name: str,
    category: str,
) -> dict:
    return {
        "name": name,
        "positionIdentifier": position,
        "groupIdentifier": group,
        "groupName": group_name,
        "categoryIdentifier": category,
        "injuryStatus": None,
    }


def _goalie_payload(
    *,
    home_strength: str = "Confirmed",
    away_strength: str = "Unconfirmed",
) -> dict:
    return {
        "data": [
            {
                "awayTeamName": "Boston Bruins",
                "homeTeamName": "New York Rangers",
                "awayGoalieName": "BOS Goalie",
                "homeGoalieName": "NYR Goalie",
                "awayNewsStrengthName": away_strength,
                "homeNewsStrengthName": home_strength,
                "awayNewsCreatedAt": "2099-11-09T15:00:00.000Z",
                "homeNewsCreatedAt": "2099-11-09T15:05:00.000Z",
            }
        ]
    }


def _schedule() -> dict:
    return _schedule_for_date(FUTURE_DATE)


def _schedule_for_date(schedule_date: str) -> dict:
    return {
        "gameWeek": [
            {
                "date": schedule_date,
                "games": [
                    {
                        "id": 2099020001,
                        "startTimeUTC": f"{schedule_date}T00:00:00Z",
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


def _provider(
    *,
    fail_team: str | None = None,
    goalie_payload: dict | None = None,
) -> DailyFaceoffAvailabilityProvider:
    def fetcher(url: str, **kwargs):
        if "starting-goalies" in url:
            return FakeResponse(goalie_payload or _goalie_payload())
        if fail_team and fail_team in url:
            raise RuntimeError("provider down")
        if "boston-bruins" in url:
            return FakeResponse(_line_payload("BOS"))
        if "new-york-rangers" in url:
            return FakeResponse(_line_payload("NYR"))
        raise RuntimeError(url)

    return DailyFaceoffAvailabilityProvider(fetcher=fetcher)


def _game(provider=None):
    return build_nhl_games(
        FUTURE_DATE,
        raw_schedule=_schedule(),
        teams=_teams(),
        roster_service=NHLRosterService(fetcher=_roster),
        goalie_status_loader=None,
    )[0]


def test_confirmed_and_projected_goalie_mapping():
    availability = _provider().load_game_availability(
        _game()
    )

    assert availability.away.goalie_assignment.status == PROJECTED
    assert availability.home.goalie_assignment.status == CONFIRMED
    assert availability.away.goalie_assignment.player.name == "BOS Goalie"
    assert availability.home.goalie_assignment.player.name == "NYR Goalie"


def test_unknown_goalie_when_no_goalie_info():
    availability = _provider(
        goalie_payload={"data": []}
    ).load_game_availability(_game())

    assert availability.away.goalie_assignment.status == UNKNOWN
    assert "goalie_game_not_found" in availability.away.goalie_assignment.concerns


def test_forward_defense_and_power_play_units_parse_to_structures():
    availability = _provider().load_game_availability(
        _game()
    )

    assert isinstance(availability, NHLGameAvailability)
    assert isinstance(availability.away, NHLTeamAvailability)
    assert isinstance(availability.away.forward_lines[0], NHLAvailabilityLine)
    assert availability.away.forward_lines[0].label == "Forwards 1"
    assert [player.name for player in availability.away.forward_lines[0].players] == [
        "Forward Two",
        "Forward One",
        "Forward Three",
    ]
    assert [player.name for player in availability.away.defense_pairs[0].players] == [
        "Defense One",
        "Defense Two",
    ]
    assert availability.away.power_play_units[0].label == "1st Powerplay Unit"


def test_exact_identity_resolution_and_ambiguous_failure():
    roster = (
        _player(1, "Sam Example", "BOS"),
        _player(2, "Sam Example", "BOS"),
    )

    player, concern = resolve_player_identity(
        "Sam Example",
        roster,
    )

    assert player is None
    assert concern == "ambiguous"

    player, concern = resolve_player_identity(
        "Unknown Player",
        roster,
    )
    assert player is None
    assert concern == "unmatched"


def test_one_team_partial_failure_does_not_break_availability():
    availability = _provider(
        fail_team="new-york-rangers"
    ).load_game_availability(_game())

    assert availability.away.forward_lines
    assert availability.home.state == "PARTIAL"
    assert "line_combinations_unavailable" in availability.home.concerns


def test_goalie_provider_failure_keeps_lines_available():
    def fetcher(url: str, **kwargs):
        if "starting-goalies" in url:
            raise RuntimeError("goalie source down")
        if "boston-bruins" in url:
            return FakeResponse(_line_payload("BOS"))
        if "new-york-rangers" in url:
            return FakeResponse(_line_payload("NYR"))
        raise RuntimeError(url)

    availability = DailyFaceoffAvailabilityProvider(
        fetcher=fetcher
    ).load_game_availability(_game())

    assert availability.away.goalie_assignment.status == UNAVAILABLE
    assert availability.home.goalie_assignment.status == UNAVAILABLE
    assert availability.away.forward_lines
    assert "goalie_source_unavailable" in (
        availability.away.goalie_assignment.concerns
    )


def test_freshness_metadata_is_present():
    availability = _provider().load_game_availability(
        _game()
    )

    assert availability.retrieved_at is not None
    assert availability.away.retrieved_at is not None
    assert availability.away.source_timestamp == datetime(
        2099,
        11,
        9,
        16,
        tzinfo=UTC,
    )
    assert availability.home.goalie_assignment.source_timestamp == datetime(
        2099,
        11,
        9,
        15,
        5,
        tzinfo=UTC,
    )


def test_provider_specific_payload_does_not_leak_beyond_adapter():
    availability = _provider().load_game_availability(
        _game()
    )

    assert not isinstance(availability.away.forward_lines[0].players[0], dict)
    assert not hasattr(availability.away, "combinations")
    assert not hasattr(availability.away, "pageProps")


def test_historical_current_availability_is_omitted():
    historical = build_nhl_games(
        "2023-11-10",
        raw_schedule=_schedule_for_date("2023-11-10"),
        teams=_teams(),
        goalie_status_loader=None,
    )[0]

    availability = _provider().load_game_availability(historical)

    assert availability.away.state == "UNKNOWN"
    assert availability.home.state == "UNKNOWN"
    assert "historical_availability_omitted" in availability.concerns
