from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from engine.nhl.models import NHLGoalie, NHLGoalieAssignment, NHLPlayer
from engine.nhl.players import _player_name, normalize_nhl_position
from engine.nhl.teams import normalize_nhl_abbreviation


GAMECENTER_URL = "https://api-web.nhle.com/v1/gamecenter"
SOURCE = "nhl_gamecenter_boxscore"

CONFIRMED = "CONFIRMED"
PROJECTED = "PROJECTED"
UNKNOWN = "UNKNOWN"
UNAVAILABLE = "UNAVAILABLE"


def nhl_goalie_from_provider(
    goalie: dict[str, Any],
    *,
    team_id: int | None = None,
) -> NHLGoalie:
    return NHLGoalie(
        source_player_id=int(
            goalie.get("id")
            or goalie.get("playerId")
            or 0
        ),
        name=_player_name(goalie),
        team_id=team_id,
        catches=(
            str(
                goalie.get("catches")
                or goalie.get("shootsCatches")
                or ""
            ).strip()
            or None
        ),
        jersey_number=_optional_int(
            goalie.get("sweaterNumber")
            or goalie.get("jerseyNumber")
        ),
    )


def fetch_game_boxscore(
    game_id: int,
) -> dict[str, Any]:
    response = requests.get(
        f"{GAMECENTER_URL}/{game_id}/boxscore",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def load_game_goalie_assignments(
    game,
    *,
    raw_boxscore: dict[str, Any] | None = None,
    fetcher=fetch_game_boxscore,
    retrieved_at: datetime | None = None,
) -> tuple[NHLGoalieAssignment, NHLGoalieAssignment]:
    retrieved = retrieved_at or datetime.now(UTC)
    try:
        raw = (
            raw_boxscore
            if raw_boxscore is not None
            else fetcher(game.source_game_id)
        )
    except Exception:
        return (
            _assignment(
                UNAVAILABLE,
                retrieved,
                game.game_date,
                concerns=("goalie_status_source_unavailable",),
            ),
            _assignment(
                UNAVAILABLE,
                retrieved,
                game.game_date,
                concerns=("goalie_status_source_unavailable",),
            ),
        )

    return normalize_game_goalie_assignments(
        raw,
        away_roster=game.away_roster,
        home_roster=game.home_roster,
        away_team_abbreviation=game.away_team.abbreviation,
        home_team_abbreviation=game.home_team.abbreviation,
        game_start_time=game.game_date,
        retrieved_at=retrieved,
    )


def normalize_game_goalie_assignments(
    raw_boxscore: dict[str, Any] | None,
    *,
    away_roster: tuple[NHLPlayer, ...] = (),
    home_roster: tuple[NHLPlayer, ...] = (),
    away_team_abbreviation: str | None = None,
    home_team_abbreviation: str | None = None,
    game_start_time: datetime | None = None,
    retrieved_at: datetime | None = None,
) -> tuple[NHLGoalieAssignment, NHLGoalieAssignment]:
    retrieved = retrieved_at or datetime.now(UTC)
    if not isinstance(raw_boxscore, dict):
        return (
            _assignment(
                UNKNOWN,
                retrieved,
                game_start_time,
                concerns=("goalie_status_missing_boxscore",),
            ),
            _assignment(
                UNKNOWN,
                retrieved,
                game_start_time,
                concerns=("goalie_status_missing_boxscore",),
            ),
        )

    stats = raw_boxscore.get("playerByGameStats")
    if not isinstance(stats, dict):
        return (
            _assignment(
                UNKNOWN,
                retrieved,
                game_start_time,
                source_timestamp=_parse_timestamp(raw_boxscore.get("startTimeUTC")),
                concerns=("goalie_status_not_exposed_pregame",),
            ),
            _assignment(
                UNKNOWN,
                retrieved,
                game_start_time,
                source_timestamp=_parse_timestamp(raw_boxscore.get("startTimeUTC")),
                concerns=("goalie_status_not_exposed_pregame",),
            ),
        )

    source_timestamp = _parse_timestamp(
        raw_boxscore.get("startTimeUTC")
    )
    return (
        _side_assignment(
            stats.get("awayTeam"),
            roster=away_roster,
            team_abbreviation=away_team_abbreviation,
            retrieved_at=retrieved,
            source_timestamp=source_timestamp,
            game_start_time=game_start_time,
        ),
        _side_assignment(
            stats.get("homeTeam"),
            roster=home_roster,
            team_abbreviation=home_team_abbreviation,
            retrieved_at=retrieved,
            source_timestamp=source_timestamp,
            game_start_time=game_start_time,
        ),
    )


def _side_assignment(
    side_stats: Any,
    *,
    roster: tuple[NHLPlayer, ...],
    team_abbreviation: str | None,
    retrieved_at: datetime,
    source_timestamp: datetime | None,
    game_start_time: datetime | None,
) -> NHLGoalieAssignment:
    if not isinstance(side_stats, dict):
        return _assignment(
            UNKNOWN,
            retrieved_at,
            game_start_time,
            source_timestamp=source_timestamp,
            concerns=("goalie_status_missing_team_stats",),
        )

    goalies = side_stats.get("goalies")
    if not isinstance(goalies, list) or not goalies:
        return _assignment(
            UNKNOWN,
            retrieved_at,
            game_start_time,
            source_timestamp=source_timestamp,
            concerns=("goalie_status_no_goalies_listed",),
        )

    starters = [
        goalie
        for goalie in goalies
        if goalie.get("starter") is True
    ]
    if len(starters) != 1:
        concern = (
            "goalie_status_ambiguous_starters"
            if len(starters) > 1
            else "goalie_status_no_confirmed_starter"
        )
        return _assignment(
            UNKNOWN,
            retrieved_at,
            game_start_time,
            source_timestamp=source_timestamp,
            concerns=(concern,),
        )

    player, concerns = _match_goalie_player(
        starters[0],
        roster=roster,
        team_abbreviation=team_abbreviation,
    )
    if player is None:
        return _assignment(
            UNKNOWN,
            retrieved_at,
            game_start_time,
            source_timestamp=source_timestamp,
            concerns=tuple(concerns) or ("goalie_status_player_unmatched",),
        )

    return _assignment(
        CONFIRMED,
        retrieved_at,
        game_start_time,
        player=player,
        source_timestamp=source_timestamp,
        concerns=tuple(concerns),
    )


def _match_goalie_player(
    goalie: dict[str, Any],
    *,
    roster: tuple[NHLPlayer, ...],
    team_abbreviation: str | None,
) -> tuple[NHLPlayer | None, list[str]]:
    player_id = _optional_int(
        goalie.get("playerId")
        or goalie.get("id")
    )
    if player_id is not None:
        for player in roster:
            if player.source_player_id == player_id:
                return player, []
        return _player_from_goalie_stat(
            goalie,
            player_id=player_id,
            team_abbreviation=team_abbreviation,
        ), ["goalie_status_player_not_in_current_roster"]

    name = _player_name(goalie)
    matches = [
        player
        for player in roster
        if player.position == "G"
        and _clean_name(player.name) == _clean_name(name)
    ]
    if len(matches) == 1:
        return matches[0], ["goalie_status_matched_by_name"]
    if len(matches) > 1:
        return None, ["goalie_status_ambiguous_name_match"]
    return None, ["goalie_status_player_unmatched"]


def _player_from_goalie_stat(
    goalie: dict[str, Any],
    *,
    player_id: int,
    team_abbreviation: str | None,
) -> NHLPlayer | None:
    name = _player_name(goalie)
    if not name:
        return None
    return NHLPlayer(
        source_player_id=player_id,
        name=name,
        team_abbreviation=(
            normalize_nhl_abbreviation(team_abbreviation)
            or None
        ),
        position="G",
        position_code="G",
        position_name="Goalie",
        sweater_number=_optional_int(goalie.get("sweaterNumber")),
        shoots_catches=None,
        active=True,
    )


def _assignment(
    status: str,
    retrieved_at: datetime,
    game_start_time: datetime | None,
    *,
    player: NHLPlayer | None = None,
    source_timestamp: datetime | None = None,
    concerns: tuple[str, ...] = (),
) -> NHLGoalieAssignment:
    return NHLGoalieAssignment(
        status=status,
        player=player,
        source=SOURCE,
        retrieved_at=retrieved_at,
        source_timestamp=source_timestamp,
        game_start_time=game_start_time,
        concerns=concerns,
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_name(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace(".", "")
        .split()
    )


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
