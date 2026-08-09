from __future__ import annotations

from engine.nhl.models import NHLTeam
from engine.nhl.players import (
    NHLRosterService,
    load_all_nhl_rosters,
    load_team_roster,
    normalize_nhl_position,
    normalize_roster_player,
    normalize_team_roster,
)
from engine.nhl.teams import (
    load_nhl_teams,
    nhl_logo_key,
    normalize_nhl_team_registry,
)


def _standings_row(
    abbreviation: str,
    name: str,
    conference: str = "Eastern",
    division: str = "Atlantic",
) -> dict:
    return {
        "teamAbbrev": {"default": abbreviation},
        "teamName": {"default": name},
        "conferenceName": conference,
        "divisionName": division,
    }


def _stats_team(
    team_id: int,
    abbreviation: str,
    full_name: str,
) -> dict:
    return {
        "id": team_id,
        "triCode": abbreviation,
        "fullName": full_name,
    }


def _player(
    player_id: int,
    first: str,
    last: str,
    position: str,
    *,
    sweater: int | None = 88,
    shoots_catches: str | None = "L",
) -> dict:
    payload = {
        "id": player_id,
        "firstName": {"default": first},
        "lastName": {"default": last},
        "positionCode": position,
    }
    if sweater is not None:
        payload["sweaterNumber"] = sweater
    if shoots_catches is not None:
        payload["shootsCatches"] = shoots_catches
    return payload


def _roster() -> dict:
    return {
        "forwards": [
            _player(8478402, "Connor", "McDavid", "C"),
            _player(8477934, "Leon", "Draisaitl", "L"),
        ],
        "defensemen": [
            _player(8476454, "Darnell", "Nurse", "D"),
        ],
        "goalies": [
            _player(8479973, "Stuart", "Skinner", "G", sweater=74),
        ],
    }


def test_team_registry_uses_current_standings_with_official_ids():
    teams = normalize_nhl_team_registry(
        {
            "standings": [
                _standings_row("BOS", "Boston Bruins"),
                _standings_row("SEA", "Seattle Kraken", "Western", "Pacific"),
            ]
        },
        {
            "data": [
                _stats_team(6, "BOS", "Boston Bruins"),
                _stats_team(55, "SEA", "Seattle Kraken"),
                _stats_team(32, "QUE", "Quebec Nordiques"),
            ]
        },
    )

    assert [team.abbreviation for team in teams] == ["BOS", "SEA"]
    assert teams[0].source_team_id == 6
    assert teams[0].logo_key == "bos"
    assert teams[1].conference == "Western"
    assert teams[1].division == "Pacific"


def test_load_nhl_teams_accepts_injected_provider_payloads():
    teams = load_nhl_teams(
        raw_standings={
            "standings": [_standings_row("BOS", "Boston Bruins")]
        },
        raw_stats_teams={
            "data": [_stats_team(6, "BOS", "Boston Bruins")]
        },
    )

    assert len(teams) == 1
    assert teams[0].source_team_id == 6
    assert nhl_logo_key(teams[0]) == "bos"


def test_valid_player_normalization_preserves_stable_identity():
    player = normalize_roster_player(
        _player(8478402, "Connor", "McDavid", "C"),
        team_id=22,
        team_abbreviation="EDM",
    )

    assert player.source_player_id == 8478402
    assert player.name == "Connor McDavid"
    assert player.team_id == 22
    assert player.team_abbreviation == "EDM"
    assert player.position == "C"
    assert player.position_code == "C"
    assert player.position_name == "Center"
    assert player.sweater_number == 88
    assert player.shoots_catches == "L"
    assert player.active is True


def test_goalie_identification_uses_canonical_position_g():
    roster = normalize_team_roster(
        _roster(),
        team_id=22,
        team_abbreviation="EDM",
    )

    goalies = [
        player
        for player in roster
        if player.position == "G"
    ]

    assert len(goalies) == 1
    assert goalies[0].name == "Stuart Skinner"
    assert goalies[0].position_name == "Goalie"


def test_missing_optional_player_fields_do_not_crash():
    player = normalize_roster_player(
        _player(
            8478402,
            "Connor",
            "McDavid",
            "C",
            sweater=None,
            shoots_catches=None,
        ),
        team_abbreviation="EDM",
    )

    assert player is not None
    assert player.sweater_number is None
    assert player.shoots_catches is None


def test_malformed_roster_entries_are_skipped():
    roster = normalize_team_roster(
        {
            "forwards": [
                _player(8478402, "Connor", "McDavid", "C"),
                {"firstName": {"default": "Missing"}, "positionCode": "C"},
                _player(8479999, "Unknown", "Position", "X"),
            ],
            "defensemen": "bad",
            "goalies": [],
        },
        team_abbreviation="EDM",
    )

    assert [player.source_player_id for player in roster] == [8478402]


def test_empty_and_unknown_rosters_are_safe():
    assert normalize_team_roster({}) == []
    assert normalize_team_roster(None) == []
    assert load_team_roster("", fetcher=lambda _: _roster()) == []
    assert load_team_roster(
        "BAD",
        fetcher=lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
    ) == []


def test_all_team_roster_iteration_deduplicates_within_team_response():
    teams = [
        NHLTeam(6, "Boston Bruins", "BOS", "bos"),
        NHLTeam(22, "Edmonton Oilers", "EDM", "edm"),
    ]

    def fetcher(abbreviation: str) -> dict:
        return {
            "forwards": [
                _player(1, abbreviation, "Forward", "C"),
                _player(1, abbreviation, "Forward", "C"),
            ],
            "defensemen": [],
            "goalies": [],
        }

    rosters = load_all_nhl_rosters(
        teams,
        fetcher=fetcher,
    )

    assert sorted(rosters) == ["BOS", "EDM"]
    assert [player.source_player_id for player in rosters["BOS"]] == [1]
    assert [player.source_player_id for player in rosters["EDM"]] == [1]


def test_roster_service_caches_identical_team_requests():
    calls = []

    def fetcher(abbreviation: str) -> dict:
        calls.append(abbreviation)
        return _roster()

    service = NHLRosterService(fetcher=fetcher)

    first = service.load_team_roster("EDM")
    second = service.load_team_roster("EDM")

    assert len(first) == len(second)
    assert calls == ["EDM"]


def test_position_normalization_preserves_source_ambiguity():
    assert normalize_nhl_position("L") == "LW"
    assert normalize_nhl_position("R") == "RW"
    assert normalize_nhl_position("D") == "D"
    assert normalize_nhl_position("G") == "G"
    assert normalize_nhl_position("F") == "F"
    assert normalize_nhl_position("unknown") is None
