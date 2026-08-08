from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from engine.lineups.models import (
    GameLineupState,
    GameLineupStatus,
    LineupPlayer,
    PlayerLineupStatus,
    TeamLineup,
    unknown_lineup_state,
)


BASE_URL = "https://statsapi.mlb.com/api/v1.1/game"
SOURCE = "mlb_statsapi_feed_live"
MIN_VALID_STARTERS = 9


def fetch_game_lineup_state(
    game_id: int | None,
    *,
    previous_state: GameLineupState | None = None,
) -> GameLineupState:
    if not game_id:
        return unknown_lineup_state(game_id, "missing_game_id")

    try:
        response = requests.get(
            f"{BASE_URL}/{game_id}/feed/live",
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return unknown_lineup_state(game_id, "lineup_provider_failure")

    return parse_game_lineup_state(
        data,
        game_id=game_id,
        previous_state=previous_state,
    )


def parse_game_lineup_state(
    data: dict[str, Any],
    *,
    game_id: int | None = None,
    previous_state: GameLineupState | None = None,
) -> GameLineupState:
    retrieved_at = datetime.now(UTC)
    game_data = data.get("gameData") or {}
    live_data = data.get("liveData") or {}
    status_blob = game_data.get("status") or {}
    game_status = status_blob.get("detailedState")
    source_timestamp = (
        data.get("metaData", {}).get("timeStamp")
        or game_data.get("datetime", {}).get("dateTime")
    )

    boxscore = live_data.get("boxscore") or {}
    teams = boxscore.get("teams") or {}

    try:
        away = _parse_team_lineup(teams.get("away") or {}, side="away")
        home = _parse_team_lineup(teams.get("home") or {}, side="home")
    except Exception:
        return unknown_lineup_state(game_id, "lineup_source_malformed")

    status = _game_status_from_teams(away, home)
    concerns = list(away.concerns + home.concerns)

    signature = _lineup_signature(away, home)
    previous_signature = previous_state.signature if previous_state else None
    if (
        previous_state
        and previous_state.status
        in {GameLineupStatus.CONFIRMED, GameLineupStatus.UPDATED}
        and status == GameLineupStatus.CONFIRMED
        and previous_signature
        and signature != previous_signature
    ):
        status = GameLineupStatus.UPDATED
        concerns.append("lineup_changed_since_previous_fetch")

    return GameLineupState(
        game_id=game_id,
        away_team=away.team_name,
        home_team=home.team_name,
        status=status,
        source=SOURCE,
        retrieved_at=retrieved_at,
        game_status=game_status,
        source_timestamp=source_timestamp,
        away_lineup=away,
        home_lineup=home,
        concerns=tuple(concerns),
        previous_signature=previous_signature,
        signature=signature,
    )


def _parse_team_lineup(team_blob: dict[str, Any], *, side: str) -> TeamLineup:
    team = team_blob.get("team") or {}
    team_id = team.get("id")
    team_name = team.get("name")
    players = team_blob.get("players") or {}
    batter_ids = [
        _safe_int(player_id)
        for player_id in (team_blob.get("batters") or [])
        if _safe_int(player_id) is not None
    ]
    bench_ids = [
        _safe_int(player_id)
        for player_id in (team_blob.get("bench") or [])
        if _safe_int(player_id) is not None
    ]
    batting_order = team_blob.get("battingOrder") or []
    concerns = []

    starter_candidates = []
    for player_id in batter_ids:
        player_blob = players.get(f"ID{player_id}") or {}
        order = _batting_order(player_blob)
        starter_candidates.append(
            _lineup_player(
                player_blob,
                player_id=player_id,
                team_id=team_id,
                team_name=team_name,
                side=side,
                status=PlayerLineupStatus.CONFIRMED_STARTER,
                batting_order=order,
            )
        )

    starters = [
        player
        for player in starter_candidates
        if player.batting_order is not None
        and 1 <= player.batting_order <= 9
    ]

    bench = []
    starter_ids = {p.player_id for p in starters}
    for player_id in bench_ids:
        if player_id in starter_ids:
            concerns.append("player_listed_as_starter_and_bench")
            continue
        player_blob = players.get(f"ID{player_id}") or {}
        bench.append(
            _lineup_player(
                player_blob,
                player_id=player_id,
                team_id=team_id,
                team_name=team_name,
                side=side,
                status=PlayerLineupStatus.BENCH,
            )
        )

    valid = _valid_starters(
        starters,
        batting_order,
        team_id=team_id,
        concerns=concerns,
    )

    if valid:
        status = GameLineupStatus.CONFIRMED
    elif batter_ids or batting_order:
        status = GameLineupStatus.PARTIAL
    else:
        status = GameLineupStatus.NOT_POSTED

    return TeamLineup(
        team_id=team_id,
        team_name=team_name,
        side=side,
        status=status,
        starters=tuple(starters if valid else ()),
        bench=tuple(bench),
        concerns=tuple(concerns),
    )


def _valid_starters(
    starters: list[LineupPlayer],
    batting_order: list[Any],
    *,
    team_id: int | None,
    concerns: list[str],
) -> bool:
    if not batting_order:
        return False

    if len(starters) < MIN_VALID_STARTERS:
        if starters:
            concerns.append("lineup_too_few_starters")
        return False

    player_ids = [p.player_id for p in starters]
    if len(player_ids) != len(set(player_ids)):
        concerns.append("duplicate_lineup_player")
        return False

    orders = [p.batting_order for p in starters]
    if any(order is None for order in orders):
        return False

    if sorted(orders[:9]) != list(range(1, 10)):
        concerns.append("malformed_batting_order")
        return False

    if any(p.team_id != team_id for p in starters):
        concerns.append("lineup_player_team_mismatch")
        return False

    return True


def _game_status_from_teams(
    away: TeamLineup,
    home: TeamLineup,
) -> GameLineupStatus:
    confirmed = {
        GameLineupStatus.CONFIRMED,
        GameLineupStatus.UPDATED,
    }

    if away.status in confirmed and home.status in confirmed:
        return GameLineupStatus.CONFIRMED
    if away.status == GameLineupStatus.NOT_POSTED and home.status == GameLineupStatus.NOT_POSTED:
        return GameLineupStatus.NOT_POSTED
    if away.status == GameLineupStatus.UNKNOWN or home.status == GameLineupStatus.UNKNOWN:
        return GameLineupStatus.UNKNOWN
    return GameLineupStatus.PARTIAL


def _lineup_signature(
    away: TeamLineup,
    home: TeamLineup,
) -> tuple:
    return (
        tuple((p.player_id, p.batting_order) for p in away.starters),
        tuple((p.player_id, p.batting_order) for p in home.starters),
    )


def _lineup_player(
    player_blob: dict[str, Any],
    *,
    player_id: int | None,
    team_id: int | None,
    team_name: str | None,
    side: str,
    status: PlayerLineupStatus,
    batting_order: int | None = None,
) -> LineupPlayer:
    person = player_blob.get("person") or {}
    position = player_blob.get("position") or {}
    return LineupPlayer(
        player_id=player_id,
        player_name=person.get("fullName"),
        team_id=team_id or player_blob.get("parentTeamId"),
        team_name=team_name,
        side=side,
        lineup_status=status,
        batting_order=batting_order,
        position=position.get("abbreviation"),
    )


def _batting_order(player_blob: dict[str, Any]) -> int | None:
    value = player_blob.get("battingOrder")
    try:
        if value is None:
            return None
        return int(str(value)[:1])
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None
