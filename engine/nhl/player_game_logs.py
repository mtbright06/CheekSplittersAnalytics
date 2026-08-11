from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from engine.nhl.goalies import fetch_game_boxscore
from engine.nhl.models import NHLPlayer, NHLPlayerGameLog
from engine.nhl.players import normalize_nhl_position
from engine.nhl.teams import normalize_nhl_abbreviation


PLAYER_GAME_LOG_URL = "https://api-web.nhle.com/v1/player"
SOURCE = "nhl_player_game_log"
REGULAR_SEASON = "REG"
POSTSEASON = "POST"
GAME_TYPE_IDS = {
    REGULAR_SEASON: 2,
    POSTSEASON: 3,
}
GAME_TYPES_BY_ID = {
    2: REGULAR_SEASON,
    3: POSTSEASON,
}


class NHLPlayerGameLogProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        boxscore_fetcher=fetch_game_boxscore,
        players: list[NHLPlayer] | dict[int, NHLPlayer] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._boxscore_fetcher = boxscore_fetcher
        self._players = _player_index(players)
        self._game_log_cache: dict[tuple[int, int, int], dict[str, Any]] = {}
        self._boxscore_cache: dict[int, dict[str, Any] | None] = {}

    def load_player_game_logs(
        self,
        *,
        player_id: int,
        season_id: int,
        game_type: str | int = REGULAR_SEASON,
    ) -> list[NHLPlayerGameLog]:
        game_type_id = _game_type_id(game_type)
        if game_type_id is None:
            return []
        player = self._players.get(int(player_id)) if self._players else None
        raw = self._load_game_log(int(player_id), int(season_id), game_type_id)
        logs = normalize_player_game_logs(
            raw,
            player_id=int(player_id),
            player=player,
            season_id=int(season_id),
            game_type=GAME_TYPES_BY_ID[game_type_id],
        )
        if not logs or _position_for_logs(player, logs) != "G":
            return logs
        return [
            self._with_goalie_saves(log)
            for log in logs
        ]

    def _load_game_log(
        self,
        player_id: int,
        season_id: int,
        game_type_id: int,
    ) -> dict[str, Any]:
        key = (player_id, season_id, game_type_id)
        if key not in self._game_log_cache:
            try:
                response = self._fetcher(
                    (
                        f"{PLAYER_GAME_LOG_URL}/{player_id}/game-log/"
                        f"{season_id}/{game_type_id}"
                    ),
                    timeout=30,
                )
                response.raise_for_status()
                self._game_log_cache[key] = response.json()
            except Exception:
                self._game_log_cache[key] = {}
        return dict(self._game_log_cache[key])

    def _load_boxscore(
        self,
        game_id: int,
    ) -> dict[str, Any] | None:
        if game_id not in self._boxscore_cache:
            try:
                self._boxscore_cache[game_id] = self._boxscore_fetcher(game_id)
            except Exception:
                self._boxscore_cache[game_id] = None
        return self._boxscore_cache[game_id]

    def _with_goalie_saves(
        self,
        log: NHLPlayerGameLog,
    ) -> NHLPlayerGameLog:
        boxscore = self._load_boxscore(log.game_id)
        saves, shots_against = _goalie_saves_from_boxscore(
            boxscore,
            player_id=log.player_id,
        )
        if saves is None:
            return _replace_log(
                log,
                shots_against=log.shots_against,
                concerns=log.concerns + ("goalie_saves_unavailable",),
            )
        return _replace_log(
            log,
            saves=saves,
            shots_against=shots_against if shots_against is not None else log.shots_against,
        )


def load_nhl_player_game_logs(
    *,
    player_id: int,
    season_id: int,
    game_type: str | int = REGULAR_SEASON,
    raw_game_log: dict[str, Any] | None = None,
    raw_boxscores: dict[int, dict[str, Any]] | None = None,
    players: list[NHLPlayer] | dict[int, NHLPlayer] | None = None,
) -> list[NHLPlayerGameLog]:
    player_index = _player_index(players)
    player = player_index.get(int(player_id)) if player_index else None
    game_type_id = _game_type_id(game_type)
    if game_type_id is None:
        return []
    if raw_game_log is None:
        return NHLPlayerGameLogProvider(players=players).load_player_game_logs(
            player_id=player_id,
            season_id=season_id,
            game_type=game_type,
        )
    logs = normalize_player_game_logs(
        raw_game_log,
        player_id=int(player_id),
        player=player,
        season_id=int(season_id),
        game_type=GAME_TYPES_BY_ID[game_type_id],
    )
    if _position_for_logs(player, logs) != "G":
        return logs
    enriched = []
    for log in logs:
        saves, shots_against = _goalie_saves_from_boxscore(
            (raw_boxscores or {}).get(log.game_id),
            player_id=log.player_id,
        )
        enriched.append(
            _replace_log(
                log,
                saves=saves,
                shots_against=shots_against or log.shots_against,
                concerns=(
                    log.concerns
                    if saves is not None
                    else log.concerns + ("goalie_saves_unavailable",)
                ),
            )
        )
    return enriched


def normalize_player_game_logs(
    raw_game_log: dict[str, Any] | None,
    *,
    player_id: int,
    player: NHLPlayer | None = None,
    season_id: int,
    game_type: str,
) -> list[NHLPlayerGameLog]:
    if not isinstance(raw_game_log, dict):
        return []
    if _optional_int(raw_game_log.get("seasonId")) not in {None, int(season_id)}:
        return []
    raw_type = _optional_int(raw_game_log.get("gameTypeId"))
    if raw_type is not None and GAME_TYPES_BY_ID.get(raw_type) != game_type:
        return []
    rows = raw_game_log.get("gameLog") or []
    if not isinstance(rows, list):
        return []
    logs = []
    seen = set()
    for row in rows:
        log = _game_log_from_row(
            row,
            player_id=player_id,
            player=player,
            season_id=season_id,
            game_type=game_type,
        )
        if log is None or log.game_id in seen:
            continue
        seen.add(log.game_id)
        logs.append(log)
    return sorted(logs, key=lambda log: log.game_date)


def _game_log_from_row(
    row: Any,
    *,
    player_id: int,
    player: NHLPlayer | None,
    season_id: int,
    game_type: str,
) -> NHLPlayerGameLog | None:
    if not isinstance(row, dict):
        return None
    game_id = _optional_int(row.get("gameId"))
    game_date = _parse_date(row.get("gameDate"))
    if game_id is None or game_date is None:
        return None
    concerns = []
    if player is None:
        concerns.append("player_identity_unresolved")
    home_away = _home_away(row.get("homeRoadFlag"))
    if home_away is None:
        concerns.append("home_away_unknown")
    position = player.position if player else normalize_nhl_position(row.get("positionCode"))
    return NHLPlayerGameLog(
        player_id=player_id,
        player=player,
        game_id=game_id,
        game_date=game_date,
        season_id=season_id,
        game_type=game_type,
        team_abbreviation=normalize_nhl_abbreviation(row.get("teamAbbrev")) or None,
        opponent_abbreviation=(
            normalize_nhl_abbreviation(row.get("opponentAbbrev"))
            or None
        ),
        home_away=home_away,
        position=position,
        goals=_optional_int(row.get("goals")),
        assists=_optional_int(row.get("assists")),
        points=_optional_int(row.get("points")),
        shots_on_goal=_optional_int(row.get("shots")),
        shots_against=_optional_int(row.get("shotsAgainst")),
        concerns=tuple(concerns),
    )


def _goalie_saves_from_boxscore(
    raw_boxscore: dict[str, Any] | None,
    *,
    player_id: int,
) -> tuple[int | None, int | None]:
    if not isinstance(raw_boxscore, dict):
        return None, None
    stats = raw_boxscore.get("playerByGameStats")
    if not isinstance(stats, dict):
        return None, None
    for side in ("awayTeam", "homeTeam"):
        side_stats = stats.get(side)
        if not isinstance(side_stats, dict):
            continue
        for goalie in side_stats.get("goalies") or []:
            if _optional_int(goalie.get("playerId")) == int(player_id):
                return (
                    _optional_int(goalie.get("saves")),
                    _optional_int(goalie.get("shotsAgainst")),
                )
    return None, None


def _replace_log(
    log: NHLPlayerGameLog,
    *,
    saves: int | None = None,
    shots_against: int | None = None,
    concerns: tuple[str, ...] | None = None,
) -> NHLPlayerGameLog:
    return NHLPlayerGameLog(
        player_id=log.player_id,
        player=log.player,
        game_id=log.game_id,
        game_date=log.game_date,
        season_id=log.season_id,
        game_type=log.game_type,
        team_abbreviation=log.team_abbreviation,
        opponent_abbreviation=log.opponent_abbreviation,
        home_away=log.home_away,
        position=log.position,
        goals=log.goals,
        assists=log.assists,
        points=log.points,
        shots_on_goal=log.shots_on_goal,
        saves=saves if saves is not None else log.saves,
        shots_against=(
            shots_against
            if shots_against is not None
            else log.shots_against
        ),
        concerns=tuple(dict.fromkeys(concerns if concerns is not None else log.concerns)),
    )


def _position_for_logs(
    player: NHLPlayer | None,
    logs: list[NHLPlayerGameLog],
) -> str | None:
    if player and player.position:
        return player.position
    for log in logs:
        if log.shots_against is not None:
            return "G"
    return logs[0].position if logs else None


def _player_index(
    players: list[NHLPlayer] | dict[int, NHLPlayer] | None,
) -> dict[int, NHLPlayer]:
    if players is None:
        return {}
    if isinstance(players, dict):
        return players
    return {
        player.source_player_id: player
        for player in players
    }


def _game_type_id(value: str | int) -> int | None:
    if isinstance(value, int):
        return value if value in GAME_TYPES_BY_ID else None
    text = str(value or "").strip().upper()
    if text in GAME_TYPE_IDS:
        return GAME_TYPE_IDS[text]
    try:
        parsed = int(text)
    except ValueError:
        return None
    return parsed if parsed in GAME_TYPES_BY_ID else None


def _home_away(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if text == "H":
        return "HOME"
    if text == "R":
        return "AWAY"
    return None


def _parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10])
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None
