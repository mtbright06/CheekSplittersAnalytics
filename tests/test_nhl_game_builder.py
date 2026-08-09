from __future__ import annotations

from engine.nhl.game_builder import build_nhl_games
from engine.nhl.models import NHLTeam
from engine.nhl.players import NHLRosterService


FUTURE_DATE = "2099-11-10"


def _schedule_team(
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


def _raw_schedule(
    *,
    away: str = "BOS",
    home: str = "NYR",
    game_state: str = "FUT",
    date: str = FUTURE_DATE,
) -> dict:
    return {
        "gameWeek": [
            {
                "date": date,
                "games": [
                    {
                        "id": 2099020001,
                        "startTimeUTC": f"{date}T00:00:00Z",
                        "gameState": game_state,
                        "venue": {"default": "Madison Square Garden"},
                        "awayTeam": _schedule_team(
                            6,
                            away,
                            "Boston",
                            "Bruins",
                        ),
                        "homeTeam": _schedule_team(
                            3,
                            home,
                            "New York",
                            "Rangers",
                        ),
                    }
                ],
            }
        ]
    }


def _teams() -> list[NHLTeam]:
    return [
        NHLTeam(6, "Boston Bruins", "BOS", "bos", "Eastern", "Atlantic"),
        NHLTeam(3, "New York Rangers", "NYR", "nyr", "Eastern", "Metropolitan"),
    ]


def _player(
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
        "sweaterNumber": 30,
        "shootsCatches": "L",
    }


def _roster(abbreviation: str) -> dict:
    return {
        "forwards": [
            _player(
                1,
                abbreviation,
                "Forward",
                "C",
            )
        ],
        "defensemen": [
            _player(
                2,
                abbreviation,
                "Defense",
                "D",
            )
        ],
        "goalies": [
            _player(
                3,
                abbreviation,
                "Goalie",
                "G",
            )
        ],
    }


def test_build_enriched_game_with_both_rosters_and_goalies():
    games = build_nhl_games(
        FUTURE_DATE,
        raw_schedule=_raw_schedule(),
        teams=_teams(),
        roster_service=NHLRosterService(fetcher=_roster),
        team_loader=lambda: _teams(),
    )

    assert len(games) == 1
    game = games[0]
    assert game.source_game_id == 2099020001
    assert game.away_team.full_name == "Boston Bruins"
    assert game.home_team.full_name == "New York Rangers"
    assert game.game_status == "SCHEDULED"
    assert game.venue == "Madison Square Garden"
    assert game.source_state.away_roster_state == "LOADED"
    assert game.source_state.home_roster_state == "LOADED"
    assert len(game.away_roster) == 3
    assert len(game.home_roster) == 3
    assert [goalie.position for goalie in game.away_goalies] == ["G"]
    assert [goalie.position for goalie in game.home_goalies] == ["G"]


def test_build_uses_roster_cache_for_repeated_same_team_fetches():
    calls = []

    def fetcher(abbreviation: str) -> dict:
        calls.append(abbreviation)
        return _roster(abbreviation)

    service = NHLRosterService(fetcher=fetcher)
    raw = {
        "gameWeek": [
            {
                "date": FUTURE_DATE,
                "games": [
                    _raw_schedule()["gameWeek"][0]["games"][0],
                    {
                        **_raw_schedule()["gameWeek"][0]["games"][0],
                        "id": 2099020002,
                    },
                ],
            }
        ]
    }

    games = build_nhl_games(
        FUTURE_DATE,
        raw_schedule=raw,
        teams=_teams(),
        roster_service=service,
    )

    assert len(games) == 2
    assert calls == ["BOS", "NYR"]


def test_one_roster_unavailable_keeps_game_with_source_concern():
    def fetcher(abbreviation: str) -> dict:
        if abbreviation == "NYR":
            raise RuntimeError("provider down")
        return _roster(abbreviation)

    games = build_nhl_games(
        FUTURE_DATE,
        raw_schedule=_raw_schedule(),
        teams=_teams(),
        roster_service=NHLRosterService(fetcher=fetcher),
    )

    game = games[0]
    assert len(game.away_roster) == 3
    assert game.home_roster == ()
    assert game.source_state.away_roster_state == "LOADED"
    assert game.source_state.home_roster_state == "UNAVAILABLE"
    assert "home_roster_unavailable" in game.source_state.concerns


def test_both_rosters_unavailable_keeps_game():
    games = build_nhl_games(
        FUTURE_DATE,
        raw_schedule=_raw_schedule(),
        teams=_teams(),
        roster_service=NHLRosterService(
            fetcher=lambda _: (_ for _ in ()).throw(RuntimeError("down"))
        ),
    )

    game = games[0]
    assert game.away_roster == ()
    assert game.home_roster == ()
    assert game.source_state.away_roster_state == "UNAVAILABLE"
    assert game.source_state.home_roster_state == "UNAVAILABLE"
    assert set(game.source_state.concerns) == {
        "away_roster_unavailable",
        "home_roster_unavailable",
    }


def test_historical_schedule_omits_current_roster_context():
    games = build_nhl_games(
        "2023-11-10",
        raw_schedule=_raw_schedule(date="2023-11-10"),
        teams=_teams(),
        team_loader=lambda: _teams(),
    )

    game = games[0]
    assert game.away_roster == ()
    assert game.home_roster == ()
    assert game.source_state.roster_context == "CURRENT_ROSTER_OMITTED_HISTORICAL"
    assert game.source_state.away_roster_state == "OMITTED_HISTORICAL"
    assert "current_roster_not_attached_to_historical_game" in (
        game.source_state.concerns
    )


def test_empty_schedule_is_safe_for_game_builder():
    assert build_nhl_games(
        FUTURE_DATE,
        raw_schedule={"gameWeek": []},
        teams=_teams(),
    ) == []
