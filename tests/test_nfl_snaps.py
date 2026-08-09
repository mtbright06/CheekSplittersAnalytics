from __future__ import annotations

from engine.nfl.models import NFLPlayer
from engine.nfl.snaps import (
    NFLSnapCountsProvider,
    load_nfl_snap_counts,
    normalize_nfl_snap_counts,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


SNAP_CSV = """game_id,pfr_game_id,season,game_type,week,player,pfr_player_id,position,team,opponent,offense_snaps,offense_pct,defense_snaps,defense_pct,st_snaps,st_pct
2025_01_ARI_NO,202509070nor,2025,REG,1,Kelvin Banks,BankKe01,T,NO,ARI,75,1,0,0,5,0.19
2025_01_ARI_NO,202509070nor,2025,REG,1,Bijan Robinson,RobiBi01,RB,ATL,TB,45,0.62,0,0,0,0
2025_02_ATL_MIN,202509140min,2025,REG,2,Bijan Robinson,RobiBi01,RB,ATL,MIN,52,0.71,0,0,0,0
2025_01_ARI_NO,202509070nor,2025,REG,1,Josh Sweat,SweaJo00,DE,ARI,NO,0,0,61,0.91,6,0.22
2025_01_ARI_NO,202509070nor,2025,REG,1,Missing ID,,WR,KC,LAC,20,0.3,0,0,1,0.04
"""


def test_snap_row_normalization_and_pfr_identity_resolution():
    snaps = load_nfl_snap_counts(
        season=2025,
        raw_rows=_rows(SNAP_CSV),
        players=[_player("00-0040001", "Kelvin Banks", "BankKe01")],
        team="NO",
    )

    snap = snaps[0]
    assert snap.player_id == "00-0040001"
    assert snap.player.name == "Kelvin Banks"
    assert snap.pfr_player_id == "BankKe01"
    assert snap.team_abbreviation == "NO"
    assert snap.opponent_abbreviation == "ARI"
    assert snap.season == 2025
    assert snap.week == 1
    assert snap.game_type == "REG"
    assert snap.source_game_id == "2025_01_ARI_NO"
    assert snap.offense_snaps == 75
    assert snap.offense_pct == 1.0
    assert snap.defense_snaps == 0
    assert snap.special_teams_snaps == 5
    assert snap.special_teams_pct == 0.19


def test_game_level_rows_remain_distinct_across_weeks():
    snaps = load_nfl_snap_counts(
        season=2025,
        raw_rows=_rows(SNAP_CSV),
        players=[_player("00-0038542", "Bijan Robinson", "RobiBi01")],
        player_id="00-0038542",
    )

    assert [snap.week for snap in snaps] == [1, 2]
    assert [snap.offense_snaps for snap in snaps] == [45, 52]


def test_defense_and_team_alias_normalization():
    snap = load_nfl_snap_counts(
        season=2025,
        raw_rows=_rows(SNAP_CSV),
        team="ARI",
    )[0]

    assert snap.player_name == "Josh Sweat"
    assert snap.defense_snaps == 61
    assert snap.defense_pct == 0.91
    assert snap.team_abbreviation == "ARI"


def test_unresolved_and_missing_identity_are_safe_concerns():
    snaps = load_nfl_snap_counts(
        season=2025,
        raw_rows=_rows(SNAP_CSV),
        team="KC",
    )

    snap = snaps[0]
    assert snap.player_id is None
    assert snap.player is None
    assert "snap_count_pfr_id_missing" in snap.concerns

    unresolved = load_nfl_snap_counts(
        season=2025,
        raw_rows=_rows(SNAP_CSV),
        team="ARI",
    )[0]
    assert "snap_count_identity_unresolved" in unresolved.concerns


def test_missing_optional_malformed_empty_unavailable_and_failure_are_safe():
    rows = _rows(SNAP_CSV)
    rows.append({"season": "2025"})
    assert normalize_nfl_snap_counts(rows, season=2025)
    assert load_nfl_snap_counts(season=2025, raw_rows=[]) == []
    assert load_nfl_snap_counts(season=2026, raw_rows=[]) == []
    provider = NFLSnapCountsProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
        players=[],
    )
    assert provider.load_snap_counts(season=2026) == []


def test_provider_caches_bulk_downloads_and_does_not_fallback_seasons():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(SNAP_CSV if "2025" in url else "")

    provider = NFLSnapCountsProvider(fetcher=fetcher, players=[])
    assert provider.load_snap_counts(season=2025)
    assert provider.load_snap_counts(season=2025)
    assert provider.load_snap_counts(season=2026) == []
    assert provider.load_snap_counts(season=2026) == []
    assert len(calls) == 2


def _player(gsis_id, name, pfr_id):
    return NFLPlayer(
        gsis_id=gsis_id,
        name=name,
        position="RB",
        position_group="RB",
        pfr_id=pfr_id,
    )


def _rows(text):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text)))
