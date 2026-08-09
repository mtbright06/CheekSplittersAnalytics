from __future__ import annotations

from engine.nfl.stats import (
    NFLTeamStatsProvider,
    load_nfl_team_stats,
    normalize_nfl_team_stats,
)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


TEAM_STATS_CSV = """season,team,season_type,games,passing_yards,rushing_yards,passing_tds,rushing_tds,passing_interceptions,fumbles_lost_total,passing_first_downs,rushing_first_downs,receiving_first_downs,def_sacks,def_interceptions,def_fumbles_forced,def_tds
2025,JAC,REG,17,4200,1800,30,15,10,6,210,100,210,42,14,12,2
2025,KC,POST,3,900,300,7,3,2,1,45,20,45,8,3,2,1
2025,WAS,REG,0,,,,,,,,,,,,,
"""


def test_team_stats_normalization_preserves_identity_season_and_reg_type():
    stats = load_nfl_team_stats(
        season=2025,
        season_type="REG",
        raw_rows=_rows(TEAM_STATS_CSV),
    )

    jax = stats[0]
    assert jax.team_abbreviation == "JAX"
    assert jax.season == 2025
    assert jax.season_type == "REG"
    assert jax.games_played == 17


def test_offensive_and_defensive_stats_normalize_when_supported():
    stat = load_nfl_team_stats(
        season=2025,
        season_type="REG",
        team="JAX",
        raw_rows=_rows(TEAM_STATS_CSV),
    )[0]

    assert stat.passing_yards == 4200
    assert stat.rushing_yards == 1800
    assert stat.total_yards == 6000
    assert stat.yards_per_game == 6000 / 17
    assert stat.passing_touchdowns == 30
    assert stat.rushing_touchdowns == 15
    assert stat.offensive_touchdowns == 45
    assert stat.turnovers == 16
    assert stat.defensive_sacks == 42.0
    assert stat.defensive_interceptions == 14
    assert stat.defensive_forced_fumbles == 12
    assert stat.defensive_touchdowns == 2


def test_postseason_is_separate_from_regular_season():
    post = load_nfl_team_stats(
        season=2025,
        season_type="POST",
        raw_rows=_rows(TEAM_STATS_CSV),
    )

    assert len(post) == 1
    assert post[0].team_abbreviation == "KC"
    assert post[0].season_type == "POST"
    assert post[0].games_played == 3


def test_zero_games_and_missing_optional_metrics_are_safe():
    stat = load_nfl_team_stats(
        season=2025,
        season_type="REG",
        team="WAS",
        raw_rows=_rows(TEAM_STATS_CSV),
    )[0]

    assert stat.games_played == 0
    assert stat.total_yards is None
    assert stat.yards_per_game is None
    assert stat.turnovers is None


def test_unknown_team_malformed_row_and_empty_dataset_are_safe():
    rows = _rows(TEAM_STATS_CSV)
    rows.append({"season": "2025"})

    assert normalize_nfl_team_stats(rows, season=2025)
    assert load_nfl_team_stats(season=2025, raw_rows=[]) == []


def test_provider_failure_and_build_local_cache_behavior():
    failure = NFLTeamStatsProvider(
        fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down"))
    )
    assert failure.load_team_stats(season=2025) == []

    calls = []

    def fetcher(url, **kwargs):
        calls.append(url)
        return FakeResponse(TEAM_STATS_CSV)

    provider = NFLTeamStatsProvider(fetcher=fetcher)
    assert provider.load_team_stats(season=2025, season_type="REG")
    assert provider.load_team_stats(season=2025, season_type="REG")
    assert provider.load_team_stats(season=2025, season_type="POST")
    assert provider.load_team_stats(season=2025, season_type="POST")
    assert len(calls) == 2


def _rows(text):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text)))
