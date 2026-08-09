from __future__ import annotations

from engine.nfl.models import NFLPlayer
from engine.nfl.player_stats import (
    NFLPlayerStatsProvider,
    load_nfl_player_stats,
    normalize_nfl_player_stats,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


PLAYER_STATS_CSV = """player_id,player_display_name,position,position_group,season,season_type,recent_team,week,games,completions,attempts,passing_yards,passing_tds,passing_interceptions,sacks_suffered,carries,rushing_yards,rushing_tds,rushing_first_downs,targets,receptions,receiving_yards,receiving_tds,receiving_first_downs,sack_fumbles_lost,rushing_fumbles_lost,receiving_fumbles_lost,fumbles_lost_total,fumbles_total,def_tackles_solo,def_tackles_for_loss,def_sacks,def_qb_hits,def_interceptions,def_pass_defended,def_fumbles_forced,def_tds,fg_made,fg_att,pat_made,pat_att
00-0033873,Patrick Mahomes,QB,QB,2025,REG,KC,,17,401,580,4300,32,11,28,60,350,4,25,0,0,0,0,0,1,2,0,3,4,,,,,,,,,,,,
00-0036264,Jonathan Taylor,RB,RB,2025,REG,IND,5,1,,,,,,20,120,2,8,3,2,15,0,1,,1,0,1,1,,,,,,,,,,,,
00-0036322,CeeDee Lamb,WR,WR,2025,REG,DAL,,17,,,,,,8,60,450,3,20,140,95,1300,10,62,,,1,1,2,,,,,,,,,,,,
00-0034381,Josh Sweat,DE,DL,2025,REG,ARI,,17,,,,,,,,,,,,,,,,,,,42,12,8.5,16,1,3,2,1,,,,
,Missing ID,WR,WR,2025,REG,KC,,1,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
00-0099999,Unknown Player,WR,WR,2025,POST,KC,,1,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
"""


def test_gsis_player_join_and_qb_stats():
    stats = load_nfl_player_stats(
        season=2025,
        season_type="REG",
        raw_rows=_rows(PLAYER_STATS_CSV),
        players=[_player("00-0033873", "Patrick Mahomes")],
        player_id="00-0033873",
    )

    stat = stats[0]
    assert stat.player.gsis_id == "00-0033873"
    assert stat.player_name == "Patrick Mahomes"
    assert stat.team_abbreviation == "KC"
    assert stat.completions == 401
    assert stat.attempts == 580
    assert stat.passing_yards == 4300
    assert stat.passing_touchdowns == 32
    assert stat.interceptions == 11
    assert stat.sacks_suffered == 28
    assert stat.fumbles_lost == 3


def test_rushing_receiving_and_derivations_preserve_week_context():
    stats = load_nfl_player_stats(
        season=2025,
        season_type="REG",
        raw_rows=[
            {
                "player_id": "00-0036264",
                "player_display_name": "Jonathan Taylor",
                "position": "RB",
                "position_group": "RB",
                "season": "2025",
                "season_type": "REG",
                "recent_team": "IND",
                "week": "5",
                "games": "1",
                "carries": "20",
                "rushing_yards": "120",
                "rushing_tds": "2",
                "rushing_first_downs": "8",
                "targets": "3",
                "receptions": "2",
                "receiving_yards": "15",
                "receiving_tds": "0",
                "receiving_first_downs": "1",
            }
        ],
        team="IND",
    )

    rb = stats[0]
    assert rb.week == 5
    assert rb.carries == 20
    assert rb.rushing_yards == 120
    assert rb.rushing_touchdowns == 2
    assert rb.rushing_first_downs == 8
    assert rb.yards_per_carry == 6.0
    assert rb.targets == 3
    assert rb.receptions == 2
    assert rb.receiving_yards == 15
    assert rb.catch_rate == 2 / 3
    assert rb.yards_per_reception == 7.5


def test_defensive_stats_normalize_when_supported():
    stat = load_nfl_player_stats(
        season=2025,
        season_type="REG",
        raw_rows=[
            {
                "player_id": "00-0034381",
                "player_display_name": "Josh Sweat",
                "position": "DE",
                "position_group": "DL",
                "season": "2025",
                "season_type": "REG",
                "recent_team": "ARI",
                "games": "17",
                "def_tackles_solo": "42",
                "def_tackles_for_loss": "12",
                "def_sacks": "8.5",
                "def_qb_hits": "16",
                "def_interceptions": "1",
                "def_pass_defended": "3",
                "def_fumbles_forced": "2",
                "def_tds": "1",
            }
        ],
        team="ARI",
    )[0]

    assert stat.defensive_solo_tackles == 42
    assert stat.defensive_tackles_for_loss == 12
    assert stat.defensive_sacks == 8.5
    assert stat.defensive_qb_hits == 16
    assert stat.defensive_interceptions == 1
    assert stat.defensive_passes_defended == 3
    assert stat.defensive_forced_fumbles == 2
    assert stat.defensive_touchdowns == 1


def test_reg_post_separation_unknown_and_missing_ids():
    post = load_nfl_player_stats(
        season=2025,
        season_type="POST",
        raw_rows=_rows(PLAYER_STATS_CSV),
    )
    reg = load_nfl_player_stats(
        season=2025,
        season_type="REG",
        raw_rows=_rows(PLAYER_STATS_CSV),
    )

    assert len(post) == 1
    assert post[0].season_type == "POST"
    missing = [stat for stat in reg if stat.player_name == "Missing ID"][0]
    unknown = post[0]
    assert "player_stats_gsis_id_missing" in missing.concerns
    assert "player_stats_identity_unresolved" in unknown.concerns


def test_multi_team_context_is_not_collapsed():
    rows = _rows(PLAYER_STATS_CSV)
    rows.append(
        {
            **rows[1],
            "recent_team": "KC",
            "week": "6",
        }
    )

    stats = normalize_nfl_player_stats(
        rows,
        season=2025,
        season_type="REG",
        player_id="00-0036264",
    )

    assert [stat.team_abbreviation for stat in stats] == ["IND", "KC"]
    assert [stat.week for stat in stats] == [5, 6]


def test_zero_denominator_missing_optional_malformed_empty_and_failure_are_safe():
    rows = _rows(PLAYER_STATS_CSV)
    rows.append({"season": "2025"})
    stats = load_nfl_player_stats(
        season=2025,
        season_type="REG",
        raw_rows=rows,
        team="DAL",
    )
    wr = stats[0]
    assert wr.yards_per_carry == 7.5
    assert load_nfl_player_stats(season=2025, raw_rows=[]) == []
    provider = NFLPlayerStatsProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
        players=[],
    )
    assert provider.load_player_stats(season=2025) == []


def test_provider_caches_bulk_downloads():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(PLAYER_STATS_CSV)

    provider = NFLPlayerStatsProvider(fetcher=fetcher, players=[])
    assert provider.load_player_stats(season=2025, season_type="REG")
    assert provider.load_player_stats(season=2025, season_type="REG")
    assert provider.load_player_stats(season=2025, season_type="POST")
    assert provider.load_player_stats(season=2025, season_type="POST")
    assert len(calls) == 2


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
