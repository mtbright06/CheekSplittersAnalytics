from __future__ import annotations

from engine.nfl.models import NFLPlayer
from engine.nfl.play_by_play import (
    NFLPlayByPlayProvider,
    load_nfl_plays,
    normalize_nfl_plays,
)


PBP_ROWS = [
    {
        "game_id": "2025_01_DAL_PHI",
        "play_id": "101",
        "drive": "1",
        "season": "2025",
        "season_type": "REG",
        "week": "1",
        "home_team": "PHI",
        "away_team": "DAL",
        "posteam": "DAL",
        "defteam": "PHI",
        "qtr": "1",
        "time": "14:20",
        "game_seconds_remaining": "3560",
        "down": "1",
        "ydstogo": "10",
        "yardline_100": "75",
        "total_home_score": "0",
        "total_away_score": "0",
        "play_type": "pass",
        "desc": "Dak Prescott pass short right to CeeDee Lamb.",
        "yards_gained": "12",
        "first_down": "1",
        "touchdown": "0",
        "interception": "0",
        "fumble": "0",
        "fumble_lost": "0",
        "sack": "0",
        "complete_pass": "1",
        "incomplete_pass": "0",
        "passer_player_id": "00-0033077",
        "receiver_player_id": "00-0036358",
    },
    {
        "game_id": "2025_01_DAL_PHI",
        "play_id": "150",
        "drive": "2",
        "season": "2025",
        "season_type": "REG",
        "week": "1",
        "home_team": "PHI",
        "away_team": "DAL",
        "posteam": "PHI",
        "defteam": "DAL",
        "qtr": "1",
        "time": "11:40",
        "down": "2",
        "ydstogo": "4",
        "yardline_100": "40",
        "play_type": "run",
        "desc": "Saquon Barkley right guard for 8 yards.",
        "yards_gained": "8",
        "first_down": "1",
        "touchdown": "0",
        "interception": "0",
        "fumble": "0",
        "fumble_lost": "0",
        "sack": "0",
        "rusher_player_id": "00-0034844",
    },
    {
        "game_id": "2025_01_DAL_PHI",
        "play_id": "210",
        "drive": "3",
        "season": "2025",
        "season_type": "REG",
        "week": "1",
        "home_team": "PHI",
        "away_team": "DAL",
        "posteam": "DAL",
        "defteam": "PHI",
        "play_type": "pass",
        "desc": "Pass intercepted.",
        "yards_gained": "0",
        "first_down": "0",
        "touchdown": "0",
        "interception": "1",
        "fumble": "0",
        "fumble_lost": "0",
        "sack": "0",
        "complete_pass": "0",
        "incomplete_pass": "0",
        "passer_player_id": "00-0033077",
        "interception_player_id": "00-0099999",
    },
    {
        "game_id": "2025_01_DAL_PHI",
        "play_id": "260",
        "drive": "4",
        "season": "2025",
        "season_type": "REG",
        "week": "1",
        "home_team": "PHI",
        "away_team": "DAL",
        "posteam": "PHI",
        "defteam": "DAL",
        "play_type": "pass",
        "desc": "Quarterback sacked and fumbled.",
        "yards_gained": "-7",
        "first_down": "0",
        "touchdown": "0",
        "interception": "0",
        "fumble": "1",
        "fumble_lost": "1",
        "sack": "1",
        "complete_pass": "0",
        "incomplete_pass": "0",
        "passer_player_id": "00-0033873",
        "fumbled_1_player_id": "00-0033873",
    },
    {
        "game_id": "2025_01_DAL_PHI",
        "play_id": "310",
        "drive": "5",
        "season": "2025",
        "season_type": "REG",
        "week": "1",
        "home_team": "PHI",
        "away_team": "DAL",
        "posteam": "PHI",
        "defteam": "DAL",
        "play_type": "run",
        "desc": "Touchdown run.",
        "yards_gained": "4",
        "touchdown": "1",
        "rusher_player_id": "00-0034844",
    },
    {
        "game_id": "2025_01_DAL_PHI",
        "play_id": "400",
        "drive": "6",
        "season": "2025",
        "season_type": "REG",
        "week": "1",
        "home_team": "PHI",
        "away_team": "DAL",
        "posteam": "",
        "defteam": "",
        "qtr": "2",
        "time": "15:00",
        "down": "",
        "ydstogo": "",
        "play_type": "kickoff",
        "desc": "Kickoff to start second quarter.",
        "yards_gained": "0",
        "touchdown": "0",
    },
    {
        "game_id": "2025_02_DAL_NYG",
        "play_id": "100",
        "drive": "1",
        "season": "2025",
        "season_type": "REG",
        "week": "2",
        "home_team": "NYG",
        "away_team": "DAL",
        "posteam": "DAL",
        "defteam": "NYG",
        "play_type": "punt",
        "desc": "Punt.",
    },
    {"season": "2025", "play_id": "999"},
]


def test_pass_play_normalization_and_gsis_identity_resolution():
    plays = load_nfl_plays(
        season=2025,
        raw_rows=PBP_ROWS,
        players=[
            _player("00-0033077", "Dak Prescott", "QB"),
            _player("00-0036358", "CeeDee Lamb", "WR"),
        ],
        game_id="2025_01_DAL_PHI",
    )

    play = plays[0]
    assert (play.game_id, play.play_id) == ("2025_01_DAL_PHI", 101)
    assert play.drive_id == 1
    assert play.season == 2025
    assert play.week == 1
    assert play.season_type == "REG"
    assert play.home_team == "PHI"
    assert play.away_team == "DAL"
    assert play.possession_team == "DAL"
    assert play.defensive_team == "PHI"
    assert play.down == 1
    assert play.yards_to_go == 10
    assert play.yardline_100 == 75
    assert play.play_type == "pass"
    assert play.yards_gained == 12
    assert play.first_down is True
    assert play.complete_pass is True
    assert play.incomplete_pass is False
    assert play.passer.name == "Dak Prescott"
    assert play.receiver.name == "CeeDee Lamb"


def test_rush_touchdown_interception_fumble_sack_and_special_teams_are_preserved():
    plays = load_nfl_plays(season=2025, raw_rows=PBP_ROWS, players=[])
    by_id = {play.play_id: play for play in plays}

    assert by_id[150].play_type == "run"
    assert by_id[150].rusher_id == "00-0034844"
    assert "rusher_identity_unresolved" in by_id[150].concerns
    assert by_id[210].interception is True
    assert by_id[210].interceptor_id == "00-0099999"
    assert by_id[260].fumble is True
    assert by_id[260].fumble_lost is True
    assert by_id[260].sack is True
    assert by_id[310].touchdown is True
    assert by_id[400].play_type == "kickoff"
    assert by_id[400].down is None
    assert by_id[400].possession_team is None


def test_filtering_by_week_game_and_team_preserves_game_play_identity():
    plays = load_nfl_plays(
        season=2025,
        raw_rows=PBP_ROWS,
        week=2,
        team="NYG",
    )

    assert [(play.game_id, play.play_id) for play in plays] == [
        ("2025_02_DAL_NYG", 100),
    ]


def test_unresolved_player_id_preserves_play_with_concern():
    play = load_nfl_plays(
        season=2025,
        raw_rows=PBP_ROWS,
        players=[],
        game_id="2025_01_DAL_PHI",
    )[0]

    assert play.passer_id == "00-0033077"
    assert play.passer is None
    assert "passer_identity_unresolved" in play.concerns


def test_malformed_empty_unavailable_failure_and_no_season_fallback_are_safe():
    assert len(normalize_nfl_plays(PBP_ROWS, season=2025)) == 7
    assert normalize_nfl_plays([], season=2025) == []
    assert load_nfl_plays(season=2026, raw_rows=PBP_ROWS) == []

    provider = NFLPlayByPlayProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
        players=[],
    )
    assert provider.load_plays(season=2026) == []


def test_provider_caches_bulk_season_downloads():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return _Response(b"not parquet")

    provider = NFLPlayByPlayProvider(fetcher=fetcher, players=[])
    assert provider.load_plays(season=2025) == []
    assert provider.load_plays(season=2025) == []
    assert provider.load_plays(season=2026) == []
    assert len(calls) == 2


class _Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


def _player(gsis_id, name, position):
    return NFLPlayer(
        gsis_id=gsis_id,
        name=name,
        position=position,
        position_group=position,
    )
