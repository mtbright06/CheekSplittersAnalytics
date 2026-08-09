from __future__ import annotations

from datetime import date

from engine.nhl.stats import (
    NHLStatsProvider,
    current_nhl_season_id,
    normalize_goalie_stats,
    normalize_skater_stats,
    normalize_team_stats,
)


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _team_row(**overrides):
    row = {
        "teamId": 6,
        "teamFullName": "Boston Bruins",
        "seasonId": 20252026,
        "gamesPlayed": 82,
        "goalsFor": 250,
        "goalsAgainst": 220,
        "goalsForPerGame": 3.05,
        "goalsAgainstPerGame": 2.68,
        "shotsForPerGame": 30.1,
        "shotsAgainstPerGame": 28.4,
        "powerPlayPct": 0.22,
        "penaltyKillPct": 0.81,
    }
    row.update(overrides)
    return row


def _skater_row(**overrides):
    row = {
        "playerId": 8478402,
        "skaterFullName": "Connor McDavid",
        "seasonId": 20252026,
        "teamAbbrevs": "EDM",
        "positionCode": "C",
        "gamesPlayed": 82,
        "goals": 44,
        "assists": 88,
        "points": 132,
        "shots": 300,
        "timeOnIcePerGame": 1320.0,
    }
    row.update(overrides)
    return row


def _toi_row(**overrides):
    row = {
        "playerId": 8478402,
        "evTimeOnIcePerGame": 900.0,
        "ppTimeOnIcePerGame": 300.0,
        "shTimeOnIcePerGame": 20.0,
    }
    row.update(overrides)
    return row


def _goalie_row(**overrides):
    row = {
        "playerId": 8480280,
        "goalieFullName": "Jeremy Swayman",
        "seasonId": 20252026,
        "teamAbbrevs": "BOS",
        "gamesPlayed": 55,
        "gamesStarted": 54,
        "wins": 32,
        "losses": 18,
        "otLosses": 5,
        "shotsAgainst": 1500,
        "saves": 1375,
        "goalsAgainst": 125,
        "savePct": 0.91667,
        "goalsAgainstAverage": 2.31,
        "timeOnIce": 324000,
    }
    row.update(overrides)
    return row


def test_team_stats_normalization_preserves_canonical_team_id():
    stats = normalize_team_stats({"data": [_team_row()]})

    assert len(stats) == 1
    team = stats[0]
    assert team.team_id == 6
    assert team.team_name == "Boston Bruins"
    assert team.season_id == 20252026
    assert team.situation == "ALL"
    assert team.games_played == 82
    assert team.goals_for == 250
    assert team.power_play_pct == 0.22


def test_skater_stats_normalization_preserves_id_and_situation_splits():
    stats = normalize_skater_stats(
        {"data": [_skater_row()]},
        time_on_ice_report={"data": [_toi_row()]},
    )

    skater = stats[0]
    assert skater.player_id == 8478402
    assert skater.name == "Connor McDavid"
    assert skater.team_abbreviations == "EDM"
    assert skater.position == "C"
    assert skater.situation == "ALL"
    assert skater.goals == 44
    assert skater.ev_time_on_ice_per_game == 900.0
    assert skater.pp_time_on_ice_per_game == 300.0
    assert skater.sh_time_on_ice_per_game == 20.0


def test_goalie_stats_normalization_preserves_id_and_workload():
    stats = normalize_goalie_stats({"data": [_goalie_row()]})

    goalie = stats[0]
    assert goalie.player_id == 8480280
    assert goalie.name == "Jeremy Swayman"
    assert goalie.team_abbreviations == "BOS"
    assert goalie.games_started == 54
    assert goalie.shots_against == 1500
    assert goalie.save_pct == 0.91667
    assert goalie.situation == "ALL"


def test_missing_optional_fields_do_not_crash():
    team = normalize_team_stats(
        {"data": [_team_row(powerPlayPct=None)]}
    )[0]
    skater = normalize_skater_stats(
        {"data": [_skater_row(shots=None)]}
    )[0]
    goalie = normalize_goalie_stats(
        {"data": [_goalie_row(savePct=None)]}
    )[0]

    assert team.power_play_pct is None
    assert skater.shots is None
    assert goalie.save_pct is None


def test_malformed_rows_and_empty_reports_are_safe():
    assert normalize_team_stats(None) == []
    assert normalize_skater_stats({"data": []}) == []
    assert normalize_goalie_stats({"bad": []}) == []
    assert normalize_team_stats({"data": [{"teamFullName": "Missing ID"}]}) == []
    assert normalize_skater_stats({"data": [_skater_row(playerId=None)]}) == []
    assert normalize_goalie_stats({"data": [_goalie_row(goalieFullName="")]}) == []


def test_duplicate_rows_are_deduplicated_by_identity():
    teams = normalize_team_stats(
        {"data": [_team_row(), _team_row(goalsFor=999)]}
    )
    skaters = normalize_skater_stats(
        {"data": [_skater_row(), _skater_row(goals=99)]}
    )
    goalies = normalize_goalie_stats(
        {"data": [_goalie_row(), _goalie_row(wins=99)]}
    )

    assert len(teams) == 1
    assert teams[0].goals_for == 250
    assert len(skaters) == 1
    assert skaters[0].goals == 44
    assert len(goalies) == 1
    assert goalies[0].wins == 32


def test_provider_failure_propagates_for_source_visibility():
    provider = NHLStatsProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("provider down")
        )
    )

    try:
        provider.load_team_stats(season_id=20252026)
    except RuntimeError as exc:
        assert "provider down" in str(exc)
    else:
        raise AssertionError("expected provider failure")


def test_provider_uses_bulk_reports_and_build_local_cache():
    calls = []

    def fetcher(url, **kwargs):
        calls.append((url, kwargs.get("params", {})))
        if url.endswith("team/summary"):
            return FakeResponse({"data": [_team_row()]})
        if url.endswith("skater/summary"):
            return FakeResponse({"data": [_skater_row()]})
        if url.endswith("skater/timeonice"):
            return FakeResponse({"data": [_toi_row()]})
        if url.endswith("goalie/summary"):
            return FakeResponse({"data": [_goalie_row()]})
        raise AssertionError(url)

    provider = NHLStatsProvider(fetcher=fetcher)

    assert provider.load_team_stats(season_id=20252026)
    assert provider.load_team_stats(season_id=20252026)
    assert provider.load_skater_stats(season_id=20252026)
    assert provider.load_goalie_stats(season_id=20252026)

    assert [call[0].rsplit("/", 2)[-2:] for call in calls] == [
        ["team", "summary"],
        ["skater", "summary"],
        ["skater", "timeonice"],
        ["goalie", "summary"],
    ]
    assert all(call[1]["limit"] == -1 for call in calls)
    assert all("seasonId=20252026" in call[1]["cayenneExp"] for call in calls)


def test_current_season_id_uses_most_recent_completed_style_in_offseason():
    assert current_nhl_season_id(date(2026, 8, 9)) == 20252026
    assert current_nhl_season_id(date(2026, 10, 1)) == 20262027
