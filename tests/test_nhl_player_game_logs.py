from __future__ import annotations

from engine.nhl.models import NHLPlayer
from engine.nhl.player_game_logs import (
    NHLPlayerGameLogProvider,
    load_nhl_player_game_logs,
    normalize_player_game_logs,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_skater_game_log_preserves_identity_game_context_and_markets():
    player = _player(8478402, "Connor McDavid", "C")
    logs = load_nhl_player_game_logs(
        player_id=8478402,
        season_id=20232024,
        game_type="REG",
        raw_game_log=_skater_log(),
        players=[player],
    )

    first = logs[0]
    assert first.player_id == 8478402
    assert first.player is player
    assert first.game_id == 2023020001
    assert first.game_date.date().isoformat() == "2023-10-11"
    assert first.season_id == 20232024
    assert first.game_type == "REG"
    assert first.team_abbreviation == "EDM"
    assert first.opponent_abbreviation == "VAN"
    assert first.home_away == "AWAY"
    assert first.position == "C"
    assert first.goals == 1
    assert first.assists == 2
    assert first.points == 3
    assert first.shots_on_goal == 4
    assert first.saves is None
    assert first.points == first.goals + first.assists


def test_postseason_and_requested_season_do_not_mix_or_fallback():
    assert load_nhl_player_game_logs(
        player_id=8478402,
        season_id=20232024,
        game_type="POST",
        raw_game_log={
            **_skater_log(),
            "gameTypeId": 3,
            "gameLog": [
                {
                    **_skater_row(),
                    "gameId": 2023030001,
                }
            ],
        },
    )[0].game_type == "POST"
    assert normalize_player_game_logs(
        {
            **_skater_log(),
            "seasonId": 20222023,
        },
        player_id=8478402,
        season_id=20232024,
        game_type="REG",
    ) == []


def test_goalie_saves_and_shots_against_use_official_boxscore_values():
    player = _player(8480280, "Jeremy Swayman", "G")
    logs = load_nhl_player_game_logs(
        player_id=8480280,
        season_id=20232024,
        game_type="REG",
        raw_game_log=_goalie_log(),
        raw_boxscores={
            2023021291: _boxscore(
                player_id=8480280,
                saves=23,
                shots_against=24,
            )
        },
        players=[player],
    )

    log = logs[0]
    assert log.position == "G"
    assert log.saves == 23
    assert log.shots_against == 24


def test_goalie_without_boxscore_preserves_row_with_concern():
    player = _player(8480280, "Jeremy Swayman", "G")
    log = load_nhl_player_game_logs(
        player_id=8480280,
        season_id=20232024,
        raw_game_log=_goalie_log(),
        raw_boxscores={},
        players=[player],
    )[0]

    assert log.game_id == 2023021291
    assert log.saves is None
    assert log.shots_against == 24
    assert "goalie_saves_unavailable" in log.concerns


def test_traded_historical_team_context_is_preserved_from_row():
    logs = load_nhl_player_game_logs(
        player_id=1,
        season_id=20232024,
        raw_game_log={
            **_skater_log(player_id=1),
            "gameLog": [
                _skater_row(teamAbbrev="CGY", opponentAbbrev="EDM", gameId=1),
                _skater_row(teamAbbrev="VAN", opponentAbbrev="SEA", gameId=2),
            ],
        },
        players=[_player(1, "Traded Player", "LW")],
    )

    assert [(log.team_abbreviation, log.opponent_abbreviation) for log in logs] == [
        ("CGY", "EDM"),
        ("VAN", "SEA"),
    ]


def test_malformed_missing_optional_empty_invalid_and_failure_are_safe():
    assert normalize_player_game_logs(None, player_id=1, season_id=20232024, game_type="REG") == []
    assert normalize_player_game_logs(
        {"seasonId": 20232024, "gameTypeId": 2, "gameLog": [{"gameDate": "2024-01-01"}]},
        player_id=1,
        season_id=20232024,
        game_type="REG",
    ) == []
    missing = load_nhl_player_game_logs(
        player_id=1,
        season_id=20232024,
        raw_game_log={
            **_skater_log(player_id=1),
            "gameLog": [_skater_row(shots=None)],
        },
    )[0]
    assert missing.shots_on_goal is None
    assert "player_identity_unresolved" in missing.concerns

    provider = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
        players=[],
        cache_dir=None,
    )
    assert provider.load_player_game_logs(player_id=1, season_id=20232024) == []


def test_provider_caches_player_season_and_boxscore_requests():
    calls = []
    boxscore_calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(_goalie_log())

    def boxscore_fetcher(game_id):
        boxscore_calls.append(game_id)
        return _boxscore(player_id=8480280, saves=23, shots_against=24)

    provider = NHLPlayerGameLogProvider(
        fetcher=fetcher,
        boxscore_fetcher=boxscore_fetcher,
        players=[_player(8480280, "Jeremy Swayman", "G")],
        cache_dir=None,
    )

    assert provider.load_player_game_logs(player_id=8480280, season_id=20232024)
    assert provider.load_player_game_logs(player_id=8480280, season_id=20232024)
    assert len(calls) == 1
    assert boxscore_calls == [2023021291]


def test_first_request_fetches_network_and_writes_cache(tmp_path):
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(_skater_log())

    provider = NHLPlayerGameLogProvider(
        fetcher=fetcher,
        cache_dir=tmp_path,
    )

    logs = provider.load_player_game_logs(
        player_id=8478402,
        season_id=20232024,
    )

    assert logs
    assert len(calls) == 1
    assert list(tmp_path.rglob("8478402.json"))


def test_second_provider_instance_reads_disk_cache_without_network(tmp_path):
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(_skater_log())

    first = NHLPlayerGameLogProvider(
        fetcher=fetcher,
        cache_dir=tmp_path,
    )
    assert first.load_player_game_logs(player_id=8478402, season_id=20232024)

    second = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network should not run")),
        cache_dir=tmp_path,
    )

    assert second.load_player_game_logs(player_id=8478402, season_id=20232024)
    assert len(calls) == 1


def test_fresh_active_season_cache_is_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "engine.nhl.player_game_logs.current_nhl_season_id",
        lambda: 20232024,
    )
    provider = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_skater_log()),
        cache_dir=tmp_path,
        active_cache_ttl_seconds=3600,
    )

    provider.load_player_game_logs(player_id=8478402, season_id=20232024)
    second = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network should not run")),
        cache_dir=tmp_path,
        active_cache_ttl_seconds=3600,
    )

    assert second.load_player_game_logs(player_id=8478402, season_id=20232024)


def test_stale_active_season_cache_refetches(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "engine.nhl.player_game_logs.current_nhl_season_id",
        lambda: 20232024,
    )
    NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_skater_log()),
        cache_dir=tmp_path,
        active_cache_ttl_seconds=0,
    ).load_player_game_logs(player_id=8478402, season_id=20232024)
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(_skater_log(player_id=8478402))

    logs = NHLPlayerGameLogProvider(
        fetcher=fetcher,
        cache_dir=tmp_path,
        active_cache_ttl_seconds=0,
    ).load_player_game_logs(player_id=8478402, season_id=20232024)

    assert logs
    assert len(calls) == 1


def test_historical_season_cache_is_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "engine.nhl.player_game_logs.current_nhl_season_id",
        lambda: 20242025,
    )
    NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_skater_log()),
        cache_dir=tmp_path,
        active_cache_ttl_seconds=0,
    ).load_player_game_logs(player_id=8478402, season_id=20232024)

    second = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network should not run")),
        cache_dir=tmp_path,
        active_cache_ttl_seconds=0,
    )

    assert second.load_player_game_logs(player_id=8478402, season_id=20232024)


def test_corrupt_cache_safely_refetches(tmp_path):
    path = tmp_path / "players" / "20232024" / "2" / "8478402.json"
    path.parent.mkdir(parents=True)
    path.write_text("{bad json", encoding="utf-8")
    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(_skater_log())

    logs = NHLPlayerGameLogProvider(
        fetcher=fetcher,
        cache_dir=tmp_path,
    ).load_player_game_logs(player_id=8478402, season_id=20232024)

    assert logs
    assert len(calls) == 1


def test_cache_write_failure_does_not_lose_fetched_result(tmp_path):
    blocker = tmp_path / "players"
    blocker.write_text("not a directory", encoding="utf-8")

    provider = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_skater_log()),
        cache_dir=tmp_path,
    )

    assert provider.load_player_game_logs(player_id=8478402, season_id=20232024)


def test_concurrent_writes_remain_valid(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    provider = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_skater_log()),
        cache_dir=tmp_path,
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(
            lambda _: provider.load_player_game_logs(
                player_id=8478402,
                season_id=20232024,
            ),
            range(4),
        ))

    assert all(result for result in results)
    assert NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network should not run")),
        cache_dir=tmp_path,
    ).load_player_game_logs(player_id=8478402, season_id=20232024)


def test_goalie_enriched_data_uses_persistent_boxscore_cache(tmp_path):
    boxscore_calls = []

    def boxscore_fetcher(game_id):
        boxscore_calls.append(game_id)
        return _boxscore(player_id=8480280, saves=23, shots_against=24)

    first = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_goalie_log()),
        boxscore_fetcher=boxscore_fetcher,
        players=[_player(8480280, "Jeremy Swayman", "G")],
        cache_dir=tmp_path,
    )
    assert first.load_player_game_logs(player_id=8480280, season_id=20232024)[0].saves == 23

    second = NHLPlayerGameLogProvider(
        fetcher=lambda *args, **kwargs: FakeResponse(_goalie_log()),
        boxscore_fetcher=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boxscore should not run")),
        players=[_player(8480280, "Jeremy Swayman", "G")],
        cache_dir=tmp_path,
    )

    assert second.load_player_game_logs(player_id=8480280, season_id=20232024)[0].saves == 23
    assert boxscore_calls == [2023021291]


def _player(player_id, name, position):
    return NHLPlayer(
        source_player_id=player_id,
        name=name,
        position=position,
        position_code=position,
    )


def _skater_log(player_id=8478402):
    return {
        "seasonId": 20232024,
        "gameTypeId": 2,
        "playerStatsSeasons": [],
        "gameLog": [
            _skater_row(player_id=player_id),
            _skater_row(
                player_id=player_id,
                gameId=2023020002,
                gameDate="2023-10-14",
                homeRoadFlag="H",
                goals=0,
                assists=1,
                points=1,
                shots=2,
                opponentAbbrev="NSH",
            ),
        ],
    }


def _skater_row(**overrides):
    row = {
        "gameId": 2023020001,
        "teamAbbrev": "EDM",
        "homeRoadFlag": "R",
        "gameDate": "2023-10-11",
        "goals": 1,
        "assists": 2,
        "points": 3,
        "shots": 4,
        "opponentAbbrev": "VAN",
    }
    row.update(overrides)
    return row


def _goalie_log():
    return {
        "seasonId": 20232024,
        "gameTypeId": 2,
        "playerStatsSeasons": [],
        "gameLog": [
            {
                "gameId": 2023021291,
                "teamAbbrev": "BOS",
                "homeRoadFlag": "R",
                "gameDate": "2024-04-15",
                "goals": 0,
                "assists": 0,
                "gamesStarted": 1,
                "shotsAgainst": 24,
                "goalsAgainst": 1,
                "opponentAbbrev": "WSH",
            }
        ],
    }


def _boxscore(*, player_id, saves, shots_against):
    return {
        "playerByGameStats": {
            "awayTeam": {
                "goalies": [
                    {
                        "playerId": player_id,
                        "shotsAgainst": shots_against,
                        "saves": saves,
                    }
                ]
            },
            "homeTeam": {
                "goalies": []
            },
        }
    }
