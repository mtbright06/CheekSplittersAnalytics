from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from engine.nfl.models import NFLGame, NFLPlayer
from engine.nfl.player_game_logs import (
    NFLPlayerGameLogProvider,
    STATS_PLAYER_WEEKLY_URL,
    load_nfl_player_game_logs,
)
from engine.nfl.teams import nfl_team_from_abbreviation


def test_schedule_join_sets_date_home_away_and_canonical_opponent():
    batch = load_nfl_player_game_logs(
        season=2025,
        raw_rows=[_row()],
        games=[_game()],
        players=[_player()],
    )

    log = batch.game_logs[0]
    assert log.player_id == "00-0000001"
    assert log.player.name == "Test Quarterback"
    assert log.game_date == date(2025, 9, 7)
    assert log.home_away == "AWAY"
    assert log.opponent_abbreviation == "BUF"
    assert log.team_abbreviation == "KC"


def test_home_join_and_traded_player_row_team_context_are_factual():
    batch = load_nfl_player_game_logs(
        season=2025,
        raw_rows=[{**_row(), "team": "BUF", "opponent_team": "KC"}],
        games=[_game()],
        players=[_player()],
    )

    log = batch.game_logs[0]
    assert log.home_away == "HOME"
    assert log.team_abbreviation == "BUF"
    assert log.opponent_abbreviation == "KC"


def test_missing_schedule_join_and_unresolved_identity_are_explicit():
    batch = load_nfl_player_game_logs(
        season=2025,
        raw_rows=[_row()],
        games=[],
        players=[],
    )

    log = batch.game_logs[0]
    assert log.game_date is None
    assert log.home_away is None
    assert log.opponent_abbreviation == "BUF"
    assert "player_game_log_schedule_join_missing" in log.concerns
    assert "player_game_log_identity_unresolved" in log.concerns


def test_missing_gsis_id_is_preserved_as_missing_not_fabricated():
    batch = load_nfl_player_game_logs(
        season=2025,
        raw_rows=[{**_row(), "player_id": ""}],
        games=[_game()],
    )

    log = batch.game_logs[0]
    assert log.player_id is None
    assert "player_game_log_gsis_id_missing" in log.concerns


def test_postseason_rows_are_excluded_from_regular_season_load():
    batch = load_nfl_player_game_logs(
        season=2025,
        game_type="REG",
        raw_rows=[_row(), {**_row(), "season_type": "POST", "week": "19"}],
        games=[_game()],
    )

    assert len(batch.game_logs) == 1
    assert batch.game_logs[0].game_type == "REG"


def test_provider_bulk_cache_fetches_once_per_season():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return _Response(_csv(_row()))

    provider = NFLPlayerGameLogProvider(
        fetcher=fetcher,
        players=[_player()],
        schedule_provider=_ScheduleProvider([_game()]),
    )
    provider.load_player_game_logs(season=2025)
    provider.load_player_game_logs(season=2025, player_ids={"00-0000001"})

    assert calls == [STATS_PLAYER_WEEKLY_URL.format(season=2025)]


def test_successful_bulk_cache_expires_for_updated_weekly_data():
    calls, now = [], [0]
    def fetcher(url, **kwargs):
        calls.append(url)
        return _Response(_csv(_row()))
    provider = NFLPlayerGameLogProvider(fetcher=fetcher, players=[_player()],
        schedule_provider=_ScheduleProvider([_game()]), clock=lambda: now[0], cache_ttl=1800)
    provider.load_player_game_logs(season=2025)
    now[0] = 1799
    provider.load_player_game_logs(season=2025)
    assert len(calls) == 1
    now[0] = 1800
    provider.load_player_game_logs(season=2025)
    assert len(calls) == 2


def test_unavailable_release_is_explicit_but_can_recover_without_restart():
    calls = []

    def fetcher(url, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("not published")
        return _Response(_csv({**_row(), "season": "2026"}))

    provider = NFLPlayerGameLogProvider(
        fetcher=fetcher,
        players=[],
        schedule_provider=_ScheduleProvider([_game()]),
    )
    first = provider.load_player_game_logs(season=2026)
    second = provider.load_player_game_logs(season=2026)
    third = provider.load_player_game_logs(season=2026)

    assert first.game_logs == ()
    assert first.concerns == ("player_game_logs_source_unavailable:2026",)
    assert len(second.game_logs) == 1
    assert second.concerns == ()
    assert third == second
    assert len(calls) == 2


def test_empty_release_is_not_cached_permanently():
    responses = iter([_Response(""), _Response(_csv(_row()))])
    provider = NFLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: next(responses),
        players=[_player()],
        schedule_provider=_ScheduleProvider([_game()]),
    )

    first = provider.load_player_game_logs(season=2025)
    second = provider.load_player_game_logs(season=2025)

    assert first.concerns == ("player_game_logs_source_empty:2025",)
    assert len(second.game_logs) == 1
    assert second.concerns == ()


def _row():
    return {
        "player_id": "00-0000001",
        "player_display_name": "Test Quarterback",
        "position": "QB",
        "season": "2025",
        "week": "1",
        "season_type": "REG",
        "game_id": "2025_01_KC_BUF",
        "team": "KC",
        "opponent_team": "BUF",
        "passing_yards": "250",
        "passing_tds": "2",
        "carries": "4",
        "rushing_yards": "20",
        "rushing_tds": "1",
        "targets": "0",
        "receptions": "0",
        "receiving_yards": "0",
        "receiving_tds": "0",
        "special_teams_tds": "0",
    }


def _player():
    return NFLPlayer(gsis_id="00-0000001", name="Test Quarterback", position="QB")


def _game():
    return NFLGame(
        source_game_id="2025_01_KC_BUF",
        season=2025,
        week=1,
        game_type="REG",
        game_date=date(2025, 9, 7),
        start_time=datetime(2025, 9, 7, 13, tzinfo=ZoneInfo("America/New_York")),
        away_team=nfl_team_from_abbreviation("KC"),
        home_team=nfl_team_from_abbreviation("BUF"),
        game_status="FINAL",
    )


def _csv(row):
    fields = list(row)
    return ",".join(fields) + "\n" + ",".join(str(row[field]) for field in fields) + "\n"


class _Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _ScheduleProvider:
    def __init__(self, games):
        self.games = games

    def load_schedule(self, **kwargs):
        return list(self.games)
