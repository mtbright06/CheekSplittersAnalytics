from __future__ import annotations

from datetime import UTC, datetime

from engine.nfl.availability import (
    NFLDepthChartProvider,
    build_team_availability_context,
    normalize_nfl_depth_chart_entries,
    select_team_depth_chart_as_of,
)
from engine.nfl.models import NFLPlayer, NFLRosterEntry


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


DEPTH_CSV = """dt,team,player_name,espn_id,gsis_id,pos_grp_id,pos_grp,pos_id,pos_name,pos_abb,pos_slot,pos_rank
2026-08-01T12:00:00Z,KC,Patrick Mahomes,3139477,00-0033873,1,Offense,1,Quarterback,QB,1,1
2026-08-01T12:00:00Z,KC,Isiah Pacheco,4361529,00-0037197,1,Offense,2,Running Back,RB,1,1
2026-08-05T12:00:00Z,KC,Patrick Mahomes,3139477,00-0033873,1,Offense,1,Quarterback,QB,1,1
2026-08-05T12:00:00Z,KC,Rashee Rice,4430878,00-0038617,1,Offense,3,Wide Receiver,WR,1,1
2026-08-05T12:00:00Z,JAC,Trevor Lawrence,4360310,00-0036971,1,Offense,1,Quarterback,QB,1,1
"""


def test_current_post_2024_schema_normalization_preserves_depth_fields():
    entries = normalize_nfl_depth_chart_entries(
        _rows(DEPTH_CSV),
        players=[_player("00-0033873", "Patrick Mahomes")],
    )
    entry = entries[0]

    assert entry.team_abbreviation == "KC"
    assert entry.player_id == "00-0033873"
    assert entry.player.name == "Patrick Mahomes"
    assert entry.espn_id == "3139477"
    assert entry.position_group == "Offense"
    assert entry.position == "QB"
    assert entry.position_name == "Quarterback"
    assert entry.position_slot == 1
    assert entry.depth_rank == 1
    assert entry.snapshot_time == datetime(2026, 8, 1, 12, tzinfo=UTC)


def test_latest_and_historical_as_of_selection_rejects_future_snapshots():
    entries = normalize_nfl_depth_chart_entries(_rows(DEPTH_CSV))

    early = select_team_depth_chart_as_of(
        entries,
        team="KC",
        as_of=datetime(2026, 8, 3, tzinfo=UTC),
    )
    late = select_team_depth_chart_as_of(
        entries,
        team="KC",
        as_of=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert {entry.player_name for entry in early} == {
        "Patrick Mahomes",
        "Isiah Pacheco",
    }
    assert {entry.player_name for entry in late} == {
        "Patrick Mahomes",
        "Rashee Rice",
    }
    assert select_team_depth_chart_as_of(
        entries,
        team="KC",
        as_of=datetime(2026, 7, 31, tzinfo=UTC),
    ) == []


def test_unresolved_and_missing_gsis_are_descriptive_concerns():
    rows = [
        {
            "dt": "2026-08-01T12:00:00Z",
            "team": "KC",
            "player_name": "Unresolved Player",
            "espn_id": "1",
            "gsis_id": "00-0000001",
            "pos_grp": "Offense",
            "pos_name": "Wide Receiver",
            "pos_abb": "WR",
            "pos_slot": "1",
            "pos_rank": "2",
        },
        {
            "dt": "2026-08-01T12:00:00Z",
            "team": "KC",
            "player_name": "Missing ID",
            "espn_id": "2",
            "gsis_id": "",
            "pos_grp": "Offense",
            "pos_name": "Wide Receiver",
            "pos_abb": "WR",
            "pos_slot": "1",
            "pos_rank": "3",
        },
    ]

    entries = normalize_nfl_depth_chart_entries(rows, players=[])

    assert entries[0].player is None
    assert "depth_chart_identity_unresolved" in entries[0].concerns
    assert entries[1].player_id is None
    assert "depth_chart_gsis_id_missing" in entries[1].concerns


def test_malformed_rows_empty_data_and_provider_failure_are_safe():
    rows = _rows(DEPTH_CSV)
    rows.append({"dt": "bad", "team": "KC", "player_name": "Bad"})

    assert len(normalize_nfl_depth_chart_entries(rows)) == 5
    assert normalize_nfl_depth_chart_entries([]) == []
    provider = NFLDepthChartProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
        players=[],
    )
    assert provider.load_depth_chart_snapshots(season=2026) == []
    assert provider.get_team_depth_chart_as_of(
        season=2026,
        team="KC",
        as_of=datetime(2026, 8, 1, tzinfo=UTC),
    ) == []


def test_roster_status_injury_and_gameday_status_remain_separate():
    depth = normalize_nfl_depth_chart_entries(
        _rows(DEPTH_CSV),
        players=[_player("00-0033873", "Patrick Mahomes")],
    )
    roster = NFLRosterEntry(
        player_id="00-0033873",
        player=depth[0].player,
        team_abbreviation="KC",
        season=2026,
        week=1,
        roster_status="ACT",
    )

    context = build_team_availability_context(
        team="KC",
        depth_chart=[depth[0]],
        roster_entries=[roster],
        query_time=datetime(2026, 8, 2, tzinfo=UTC),
    )

    player = context.players[0]
    assert player.roster_entry.roster_status == "ACT"
    assert player.depth_chart_entry.depth_rank == 1
    assert player.injury_status == "UNKNOWN"
    assert player.gameday_status == "UNKNOWN"


def test_provider_caches_bulk_depth_chart_download():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(DEPTH_CSV)

    provider = NFLDepthChartProvider(
        fetcher=fetcher,
        players=[],
    )

    assert provider.load_depth_chart_snapshots(season=2026)
    assert provider.load_depth_chart_snapshots(season=2026)
    assert len(calls) == 1


def _player(gsis_id, name):
    return NFLPlayer(
        gsis_id=gsis_id,
        name=name,
        position="QB",
        position_group="QB",
    )


def _rows(text):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text)))
