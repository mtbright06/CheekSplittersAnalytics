from __future__ import annotations

from datetime import date

from engine.nfl.schedule import load_nfl_schedule, normalize_nfl_game
from engine.nfl.teams import (
    load_nfl_teams,
    nfl_logo_key,
    normalize_nfl_abbreviation,
)


def test_current_team_registry_has_32_teams_and_logo_keys():
    teams = load_nfl_teams()

    assert len(teams) == 32
    assert len({team.abbreviation for team in teams}) == 32
    assert all(team.logo_key == team.abbreviation.lower() for team in teams)


def test_alias_handling_is_boundary_scoped():
    assert normalize_nfl_abbreviation("JAC") == "JAX"
    assert normalize_nfl_abbreviation("WSH") == "WAS"
    assert normalize_nfl_abbreviation("JAC", current_franchise=False) == "JAC"
    assert nfl_logo_key("JAC") == "jax"


def test_scheduled_game_normalization_preserves_identity_and_time():
    game = normalize_nfl_game(
        _row(
            game_id="2026_01_DAL_PHI",
            season=2026,
            week=1,
            game_type="REG",
            gameday="2026-09-10",
            gametime="20:20",
            away_team="DAL",
            home_team="PHI",
        )
    )

    assert game.source_game_id == "2026_01_DAL_PHI"
    assert game.season == 2026
    assert game.week == 1
    assert game.game_type == "REG"
    assert game.game_date == date(2026, 9, 10)
    assert game.start_time.tzinfo is not None
    assert game.start_time.tzname() in {"EDT", "EST"}
    assert game.away_team.abbreviation == "DAL"
    assert game.home_team.abbreviation == "PHI"
    assert game.game_status == "SCHEDULED"


def test_completed_game_normalization_preserves_scores():
    game = normalize_nfl_game(
        _row(
            away_score=21,
            home_score=24,
            result=3,
        )
    )

    assert game.game_status == "FINAL"
    assert game.away_score == 21
    assert game.home_score == 24


def test_game_type_semantics_are_preserved():
    assert normalize_nfl_game(_row(game_type="PRE")).game_type == "PRE"
    assert normalize_nfl_game(_row(game_type="REG")).game_type == "REG"
    assert normalize_nfl_game(_row(game_type="POST")).game_type == "POST"
    assert normalize_nfl_game(_row(game_type="WC")).game_type == "POST"


def test_season_and_calendar_year_remain_separate():
    game = normalize_nfl_game(
        _row(
            season=2026,
            week=19,
            game_type="POST",
            gameday="2027-01-16",
        )
    )

    assert game.season == 2026
    assert game.game_date == date(2027, 1, 16)
    assert game.game_type == "POST"


def test_missing_optional_fields_are_safe():
    game = normalize_nfl_game(
        _row(
            gametime="",
            away_score="",
            home_score="",
            location="",
        )
    )

    assert game is not None
    assert game.start_time.tzinfo is not None
    assert game.location is None
    assert game.away_score is None
    assert game.home_score is None


def test_malformed_row_is_skipped_and_empty_schedule_is_safe():
    assert normalize_nfl_game({"season": 2026}) is None
    assert load_nfl_schedule(raw_rows=[]) == []
    assert load_nfl_schedule(raw_rows=[{"season": 2026}]) == []


def test_schedule_filtering_by_season_week_type_and_date():
    rows = [
        _row(game_id="a", season=2026, week=1, game_type="REG", gameday="2026-09-10"),
        _row(game_id="b", season=2026, week=2, game_type="REG", gameday="2026-09-17"),
        _row(game_id="c", season=2025, week=1, game_type="REG", gameday="2025-09-04"),
        _row(game_id="d", season=2026, week=1, game_type="PRE", gameday="2026-08-10"),
    ]

    games = load_nfl_schedule(
        raw_rows=rows,
        season=2026,
        week=1,
        game_type="REG",
        target_date="2026-09-10",
    )

    assert [game.source_game_id for game in games] == ["a"]


def _row(**overrides):
    row = {
        "game_id": "2026_01_DAL_PHI",
        "season": "2026",
        "week": "1",
        "game_type": "REG",
        "gameday": "2026-09-10",
        "gametime": "20:20",
        "away_team": "DAL",
        "home_team": "PHI",
        "location": "Home",
        "away_score": "",
        "home_score": "",
        "result": "",
    }
    row.update({key: str(value) for key, value in overrides.items()})
    return row
