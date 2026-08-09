from __future__ import annotations

from datetime import date

from engine.nfl.players import load_nfl_players, normalize_nfl_players
from engine.nfl.rosters import (
    NFLRostersProvider,
    load_nfl_season_roster,
    load_nfl_weekly_roster,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


PLAYER_CSV = """gsis_id,display_name,birth_date,position_group,position,height,weight,latest_team,status
00-0033873,Patrick Mahomes,1995-09-17,QB,QB,74,225,KC,ACT
00-0033874,Traded Player,1996-01-01,WR,WR,72,205,JAX,ACT
"""


ROSTER_CSV = """season,team,position,depth_chart_position,jersey_number,status,full_name,gsis_id,week,game_type
2026,KC,QB,QB,15,ACT,Patrick Mahomes,00-0033873,1,REG
2026,JAC,WR,WR,11,DEV,Traded Player,00-0033874,1,REG
2026,JAC,WR,WR,11,DEV,Traded Player,00-0033874,1,REG
2026,WSH,RB,RB,20,INA,Unknown Player,,1,REG
"""


TRADE_WEEKLY_CSV = """season,team,position,depth_chart_position,jersey_number,status,full_name,gsis_id,week,game_type
2026,JAC,WR,WR,11,ACT,Traded Player,00-0033874,1,REG
2026,KC,WR,WR,11,ACT,Traded Player,00-0033874,5,REG
"""


def test_player_normalization_uses_stable_gsis_identity():
    player = normalize_nfl_players(_rows(PLAYER_CSV))[0]

    assert player.gsis_id == "00-0033873"
    assert player.player_id == "00-0033873"
    assert player.name == "Patrick Mahomes"
    assert player.position == "QB"
    assert player.position_group == "QB"
    assert player.birth_date == date(1995, 9, 17)
    assert player.height == 74
    assert player.weight == 225


def test_player_normalization_skips_missing_identity_and_duplicates():
    rows = _rows(PLAYER_CSV)
    rows.append(rows[0])
    rows.append({"display_name": "No ID"})

    players = normalize_nfl_players(rows)

    assert [player.gsis_id for player in players] == [
        "00-0033873",
        "00-0033874",
    ]


def test_roster_normalization_preserves_status_and_joins_identity():
    players = load_nfl_players(raw_rows=_rows(PLAYER_CSV))

    entries = load_nfl_season_roster(
        season=2026,
        raw_rows=_rows(ROSTER_CSV),
        players=players,
    )

    assert len(entries) == 3
    mahomes = entries[0]
    assert mahomes.player_id == "00-0033873"
    assert mahomes.player.name == "Patrick Mahomes"
    assert mahomes.team_abbreviation == "KC"
    assert mahomes.roster_status == "ACT"
    assert mahomes.jersey_number == 15
    assert mahomes.position == "QB"
    assert mahomes.week == 1
    unknown = entries[-1]
    assert unknown.team_abbreviation == "WAS"
    assert unknown.player_id is None
    assert unknown.player is None


def test_weekly_context_and_team_alias_are_preserved():
    players = load_nfl_players(raw_rows=_rows(PLAYER_CSV))

    entries = load_nfl_weekly_roster(
        season=2026,
        week=1,
        team="JAX",
        raw_rows=_rows(ROSTER_CSV),
        players=players,
    )

    assert len(entries) == 1
    assert entries[0].team_abbreviation == "JAX"
    assert entries[0].roster_status == "DEV"
    assert entries[0].week == 1


def test_trade_multi_team_membership_does_not_mutate_identity():
    players = load_nfl_players(raw_rows=_rows(PLAYER_CSV))

    entries = load_nfl_weekly_roster(
        season=2026,
        raw_rows=_rows(TRADE_WEEKLY_CSV),
        players=players,
    )

    assert [entry.team_abbreviation for entry in entries] == ["JAX", "KC"]
    assert {id(entry.player) for entry in entries if entry.player}.__len__() == 1
    assert entries[0].player.gsis_id == entries[1].player.gsis_id


def test_empty_and_provider_failure_are_safe():
    assert load_nfl_players(raw_rows=[]) == []
    assert load_nfl_weekly_roster(season=2026, raw_rows=[]) == []

    provider = NFLRostersProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
        players=[],
    )
    assert provider.load_season_roster(season=2026) == []
    assert provider.load_weekly_roster(season=2026) == []


def test_provider_caches_bulk_downloads():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(ROSTER_CSV)

    provider = NFLRostersProvider(
        fetcher=fetcher,
        players=load_nfl_players(raw_rows=_rows(PLAYER_CSV)),
    )

    assert provider.load_weekly_roster(season=2026)
    assert provider.load_weekly_roster(season=2026)
    assert provider.load_season_roster(season=2026)
    assert provider.load_season_roster(season=2026)
    assert len(calls) == 2


def _rows(text):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text)))
