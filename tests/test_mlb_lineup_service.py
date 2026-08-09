from unittest.mock import patch

from engine.lineups.mlb_provider import (
    fetch_game_lineup_state,
    parse_game_lineup_state,
)
from engine.lineups.models import (
    GameLineupStatus,
    LineupActionability,
    PlayerLineupStatus,
)
from engine.lineups.service import MLBLineupService
from engine.hitters.target_hitters import hitter_lineup_actionability


def player(player_id, order=None, team_id=1):
    blob = {
        "person": {"id": player_id, "fullName": f"Player {player_id}"},
        "position": {"abbreviation": "OF"},
        "parentTeamId": team_id,
    }
    if order is not None:
        blob["battingOrder"] = str(order * 100)
    return blob


def team_blob(team_id, *, posted=True, duplicate=False, malformed=False):
    starters = list(range(team_id * 100 + 1, team_id * 100 + 10)) if posted else []
    if duplicate:
        starters[-1] = starters[0]
    bench = list(range(team_id * 100 + 20, team_id * 100 + 24))
    players = {}
    for index, player_id in enumerate(starters, 1):
        order = 10 if index == 9 and malformed else index
        players[f"ID{player_id}"] = player(player_id, order, team_id)
    for player_id in bench:
        players[f"ID{player_id}"] = player(player_id, None, team_id)
    return {
        "team": {"id": team_id, "name": f"Team {team_id}"},
        "players": players,
        "batters": starters,
        "bench": bench,
        "battingOrder": [str(i * 100) for i in range(1, 10)] if posted else [],
    }


def feed(*, away_posted=True, home_posted=True, **kwargs):
    return {
        "gameData": {
            "status": {"detailedState": "Pre-Game"},
            "datetime": {"dateTime": "2026-08-08T20:00:00Z"},
        },
        "liveData": {
            "boxscore": {
                "teams": {
                    "away": team_blob(
                        1,
                        posted=away_posted,
                        duplicate=kwargs.get("away_duplicate", False),
                        malformed=kwargs.get("away_malformed", False),
                    ),
                    "home": team_blob(
                        2,
                        posted=home_posted,
                        duplicate=kwargs.get("home_duplicate", False),
                        malformed=kwargs.get("home_malformed", False),
                    ),
                }
            }
        },
    }


def test_neither_lineup_posted():
    state = parse_game_lineup_state(
        feed(away_posted=False, home_posted=False),
        game_id=1,
    )

    assert state.status == GameLineupStatus.NOT_POSTED


def test_one_lineup_posted_is_partial():
    state = parse_game_lineup_state(
        feed(away_posted=True, home_posted=False),
        game_id=1,
    )

    assert state.status == GameLineupStatus.PARTIAL
    assert state.away_lineup.status == GameLineupStatus.CONFIRMED
    assert state.home_lineup.status == GameLineupStatus.NOT_POSTED


def test_both_lineups_posted_are_confirmed():
    state = parse_game_lineup_state(feed(), game_id=1)

    assert state.status == GameLineupStatus.CONFIRMED
    assert len(state.away_lineup.starters) == 9
    assert state.away_lineup.starters[0].batting_order == 1


def test_duplicate_batter_is_not_confirmed():
    state = parse_game_lineup_state(feed(away_duplicate=True), game_id=1)

    assert state.status == GameLineupStatus.PARTIAL
    assert "duplicate_lineup_player" in state.away_lineup.concerns


def test_malformed_batting_order_is_not_confirmed():
    state = parse_game_lineup_state(feed(away_malformed=True), game_id=1)

    assert state.status == GameLineupStatus.PARTIAL
    assert "malformed_batting_order" in state.away_lineup.concerns


def test_hitter_confirmed_starting_bench_and_not_listed():
    state = parse_game_lineup_state(feed(), game_id=1)
    lineup = state.away_lineup

    starter = lineup.player_status(101)
    bench = lineup.player_status(120)
    absent = lineup.player_status(199)

    assert starter.lineup_status == PlayerLineupStatus.CONFIRMED_STARTER
    assert bench.lineup_status == PlayerLineupStatus.BENCH
    assert absent.lineup_status == PlayerLineupStatus.NOT_LISTED


def test_active_roster_does_not_confirm_lineup():
    state = parse_game_lineup_state(
        feed(away_posted=False, home_posted=False),
        game_id=1,
    )
    actionability = hitter_lineup_actionability(
        {"batter_id": 101, "position": "OF"},
        state.away_lineup,
    )

    assert actionability["lineup_status"] == PlayerLineupStatus.UNKNOWN.value
    assert actionability["actionability"] == LineupActionability.PENDING_LINEUP.value


def test_confirmed_bench_hitter_is_not_actionable():
    state = parse_game_lineup_state(feed(), game_id=1)
    actionability = hitter_lineup_actionability(
        {"batter_id": 120, "position": "OF"},
        state.away_lineup,
    )

    assert actionability["lineup_status"] == PlayerLineupStatus.BENCH.value
    assert actionability["actionability"] == LineupActionability.NOT_STARTING.value
    assert actionability["official_candidate"] is False


def test_late_lineup_update_is_detected():
    original = parse_game_lineup_state(feed(), game_id=1)
    changed = feed()
    away = changed["liveData"]["boxscore"]["teams"]["away"]
    away["batters"][0], away["batters"][1] = away["batters"][1], away["batters"][0]
    away["players"]["ID101"]["battingOrder"] = "200"
    away["players"]["ID102"]["battingOrder"] = "100"

    updated = parse_game_lineup_state(
        changed,
        game_id=1,
        previous_state=original,
    )

    assert updated.status == GameLineupStatus.UPDATED
    assert "lineup_changed_since_previous_fetch" in updated.concerns


def test_service_cache_preserves_freshness_and_can_refresh():
    calls = []

    def provider(game_id, previous_state=None):
        calls.append(previous_state)
        return parse_game_lineup_state(
            feed(),
            game_id=game_id,
            previous_state=previous_state,
        )

    service = MLBLineupService(provider=provider)
    first = service.get_game_lineup(1)
    cached = service.get_game_lineup(1)
    refreshed = service.get_game_lineup(1, refresh=True)

    assert first is cached
    assert refreshed is not first
    assert calls == [None, first]
    assert first.freshness_seconds >= 0
    assert first.is_stale is False


def test_provider_failure_returns_unknown():
    class Response:
        def raise_for_status(self):
            raise RuntimeError("boom")

    with patch(
        "engine.lineups.mlb_provider.requests.get",
        lambda *args, **kwargs: Response(),
    ):
        state = fetch_game_lineup_state(1)

    assert state.status == GameLineupStatus.UNKNOWN
    assert "lineup_provider_failure" in state.concerns


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
