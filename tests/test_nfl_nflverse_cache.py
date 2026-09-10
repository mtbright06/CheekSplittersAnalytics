from __future__ import annotations

import os
import time

from engine.nfl.nflverse_cache import NFLVerseBulkCache
from engine.nfl.player_game_logs import NFLPlayerGameLogProvider
from engine.nfl.players import NFLPlayersProvider
from engine.nfl.rosters import NFLRostersProvider
from engine.nfl.schedule import NFLScheduleProvider


CSV = "game_id,gameday,away_team,home_team\n2026_01_A_B,2026-09-09,A,B\n"


class Response:
    def __init__(self, text=CSV, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def valid(text):
    return text.startswith("game_id,") and "2026_01_A_B" in text


def test_cold_population_then_new_instance_uses_disk(tmp_path):
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        return Response()

    first = NFLVerseBulkCache(cache_dir=tmp_path, fetcher=fetch)
    assert first.load_csv(key="schedule", url="schedule", validator=valid,
                          max_age_seconds=3600).source == "network"
    second = NFLVerseBulkCache(cache_dir=tmp_path, fetcher=fetch)
    result = second.load_csv(key="schedule", url="schedule", validator=valid,
                             max_age_seconds=3600)
    assert result.text == CSV
    assert result.source == "disk"
    assert calls == ["schedule"]


def test_unavailable_asset_is_negative_cached_and_expires(tmp_path):
    calls = []
    now = [time.time()]

    def fetch(url, **kwargs):
        calls.append(url)
        return Response(status_code=404)

    cache = NFLVerseBulkCache(
        cache_dir=tmp_path, fetcher=fetch, clock=lambda: now[0],
        negative_ttl_seconds=60,
    )
    assert cache.load_csv(key="stats_2026", url="stats", validator=valid,
                          max_age_seconds=60).text is None
    assert cache.load_csv(key="stats_2026", url="stats", validator=valid,
                          max_age_seconds=60).source == "negative_cache"
    assert len(calls) == 1
    now[0] += 61
    os.utime(tmp_path / "stats_2026.unavailable", (now[0] - 61, now[0] - 61))
    cache.load_csv(key="stats_2026", url="stats", validator=valid,
                   max_age_seconds=60)
    assert len(calls) == 2


def test_failed_or_invalid_refresh_preserves_known_good_cache(tmp_path):
    responses = [Response(), Response(status_code=503), Response("<html>bad</html>")]

    def fetch(url, **kwargs):
        return responses.pop(0)

    cache = NFLVerseBulkCache(cache_dir=tmp_path, fetcher=fetch)
    cache.load_csv(key="schedule", url="schedule", validator=valid, max_age_seconds=0)
    failed = cache.load_csv(key="schedule", url="schedule", validator=valid, max_age_seconds=0)
    malformed = cache.load_csv(key="schedule", url="schedule", validator=valid, max_age_seconds=0)
    assert failed.text == malformed.text == CSV
    assert failed.source == malformed.source == "stale_disk"
    assert (tmp_path / "schedule.csv").read_text(encoding="utf-8") == CSV


def test_cache_write_failure_keeps_downloaded_result(tmp_path, monkeypatch):
    cache = NFLVerseBulkCache(cache_dir=tmp_path, fetcher=lambda *a, **k: Response())
    monkeypatch.setattr(cache, "_atomic_write", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    result = cache.load_csv(key="schedule", url="schedule", validator=valid, max_age_seconds=60)
    assert result.text == CSV
    assert result.source == "network"


def test_shared_props_providers_download_schedule_and_players_once(tmp_path):
    schedule_csv = (
        "game_id,season,week,game_type,gameday,gametime,away_team,home_team\n"
        "2025_01_NE_SEA,2025,1,REG,2025-09-07,13:00,NE,SEA\n"
    )
    players_csv = "gsis_id,display_name,position\n00-0000001,Test Player,RB\n"
    roster_csv = (
        "gsis_id,team,season,week,position,status\n"
        "00-0000001,SEA,2026,1,RB,ACT\n"
    )
    stats_csv = (
        "season,week,season_type,game_id,player_id,player_display_name,team,opponent_team,position,rushing_yards\n"
        "2025,1,REG,2025_01_NE_SEA,00-0000001,Test Player,SEA,NE,RB,50\n"
    )
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        if "games.csv" in url:
            return Response(schedule_csv)
        if "players.csv" in url:
            return Response(players_csv)
        if "roster_weekly" in url:
            return Response(roster_csv)
        if "stats_player_week_2025" in url:
            return Response(stats_csv)
        return Response(status_code=404)

    def run_process():
        cache = NFLVerseBulkCache(cache_dir=tmp_path, fetcher=fetch)
        schedule = NFLScheduleProvider(bulk_cache=cache)
        players = NFLPlayersProvider(bulk_cache=cache).load_players()
        entries = NFLRostersProvider(players=players, bulk_cache=cache).load_weekly_roster(
            season=2026, week=1
        )
        logs = NFLPlayerGameLogProvider(
            players=players, schedule_provider=schedule, bulk_cache=cache
        )
        previous = logs.load_player_game_logs(season=2025, player_ids={"00-0000001"})
        current = logs.load_player_game_logs(season=2026, player_ids={"00-0000001"})
        return entries, previous, current

    entries, previous, current = run_process()
    assert entries and previous.game_logs and not current.game_logs
    assert len(calls) == 5
    assert sum("games.csv" in url for url in calls) == 1
    assert sum("players.csv" in url for url in calls) == 1

    calls.clear()
    entries, previous, current = run_process()
    assert entries and previous.game_logs and not current.game_logs
    assert calls == []
