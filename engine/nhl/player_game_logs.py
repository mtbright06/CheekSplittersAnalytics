from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import sleep, time
from typing import Any

import requests

from engine.nhl.goalies import fetch_game_boxscore
from engine.nhl.models import NHLPlayer, NHLPlayerGameLog
from engine.nhl.players import normalize_nhl_position
from engine.nhl.stats import current_nhl_season_id
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
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
CACHE_SCHEMA_VERSION = 1
DEFAULT_CACHE_DIR = Path("data/nhl/cache/player_game_logs")
ACTIVE_SEASON_CACHE_TTL_SECONDS = 6 * 60 * 60


class NHLPlayerGameLogProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        boxscore_fetcher=fetch_game_boxscore,
        players: list[NHLPlayer] | dict[int, NHLPlayer] | None = None,
        cache_dir: Path | str | None = DEFAULT_CACHE_DIR,
        active_cache_ttl_seconds: int = ACTIVE_SEASON_CACHE_TTL_SECONDS,
    ) -> None:
        self._fetcher = fetcher
        self._boxscore_fetcher = boxscore_fetcher
        self._players = _player_index(players)
        self._game_log_cache: dict[tuple[int, int, int], dict[str, Any]] = {}
        self._boxscore_cache: dict[int, dict[str, Any] | None] = {}
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._active_cache_ttl_seconds = int(active_cache_ttl_seconds)
        self._cache_lock = Lock()

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
        with self._cache_lock:
            cached = self._game_log_cache.get(key)
        if cached is not None:
            return dict(cached)

        cached_payload = self._load_persistent_game_log(
            player_id,
            season_id,
            game_type_id,
        )
        if cached_payload is not None:
            with self._cache_lock:
                self._game_log_cache.setdefault(key, cached_payload)
                return dict(self._game_log_cache[key])

        payload = self._fetch_game_log_payload(
            player_id,
            season_id,
            game_type_id,
        )
        self._write_persistent_game_log(
            player_id,
            season_id,
            game_type_id,
            payload,
        )
        with self._cache_lock:
            self._game_log_cache.setdefault(key, payload)
            return dict(self._game_log_cache[key])

    def _fetch_game_log_payload(
        self,
        player_id: int,
        season_id: int,
        game_type_id: int,
    ) -> dict[str, Any]:
        url = (
            f"{PLAYER_GAME_LOG_URL}/{player_id}/game-log/"
            f"{season_id}/{game_type_id}"
        )
        for attempt in range(3):
            try:
                response = self._fetcher(
                    url,
                    timeout=30,
                )
                if (
                    getattr(response, "status_code", None)
                    in TRANSIENT_STATUS_CODES
                    and attempt < 2
                ):
                    _sleep_before_retry(response, attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception:
                if attempt >= 2:
                    return {}
                sleep(0.25 * (2 ** attempt))
        return {}

    def _load_boxscore(
        self,
        game_id: int,
    ) -> dict[str, Any] | None:
        with self._cache_lock:
            cached = self._boxscore_cache.get(game_id)
        if cached is not None or game_id in self._boxscore_cache:
            return cached

        persistent = self._load_persistent_boxscore(game_id)
        if persistent is not None:
            with self._cache_lock:
                self._boxscore_cache.setdefault(game_id, persistent)
                return self._boxscore_cache[game_id]

        try:
            boxscore = self._boxscore_fetcher(game_id)
        except Exception:
            boxscore = None
        if boxscore is not None:
            self._write_persistent_boxscore(game_id, boxscore)
        with self._cache_lock:
            self._boxscore_cache.setdefault(game_id, boxscore)
            return self._boxscore_cache[game_id]

    def _load_persistent_game_log(
        self,
        player_id: int,
        season_id: int,
        game_type_id: int,
    ) -> dict[str, Any] | None:
        entry = _read_cache_entry(
            self._game_log_cache_path(
                player_id,
                season_id,
                game_type_id,
            )
        )
        if entry is None:
            return None
        if entry.get("player_id") != int(player_id):
            return None
        if entry.get("season_id") != int(season_id):
            return None
        if entry.get("game_type_id") != int(game_type_id):
            return None
        if _cache_entry_stale(
            entry,
            season_id=season_id,
            ttl_seconds=self._active_cache_ttl_seconds,
        ):
            return None
        payload = entry.get("payload")
        return dict(payload) if isinstance(payload, dict) else None

    def _write_persistent_game_log(
        self,
        player_id: int,
        season_id: int,
        game_type_id: int,
        payload: dict[str, Any],
    ) -> None:
        _write_cache_entry(
            self._game_log_cache_path(
                player_id,
                season_id,
                game_type_id,
            ),
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "source": SOURCE,
                "fetched_at": datetime.now(UTC).isoformat(),
                "player_id": int(player_id),
                "season_id": int(season_id),
                "game_type_id": int(game_type_id),
                "payload": payload,
            },
        )

    def _load_persistent_boxscore(
        self,
        game_id: int,
    ) -> dict[str, Any] | None:
        entry = _read_cache_entry(
            self._boxscore_cache_path(game_id)
        )
        if entry is None:
            return None
        if entry.get("game_id") != int(game_id):
            return None
        payload = entry.get("payload")
        return dict(payload) if isinstance(payload, dict) else None

    def _write_persistent_boxscore(
        self,
        game_id: int,
        payload: dict[str, Any],
    ) -> None:
        _write_cache_entry(
            self._boxscore_cache_path(game_id),
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "source": "nhl_game_boxscore",
                "fetched_at": datetime.now(UTC).isoformat(),
                "game_id": int(game_id),
                "payload": payload,
            },
        )

    def _game_log_cache_path(
        self,
        player_id: int,
        season_id: int,
        game_type_id: int,
    ) -> Path | None:
        if self._cache_dir is None:
            return None
        return (
            self._cache_dir
            / "players"
            / str(season_id)
            / str(game_type_id)
            / f"{int(player_id)}.json"
        )

    def _boxscore_cache_path(
        self,
        game_id: int,
    ) -> Path | None:
        if self._cache_dir is None:
            return None
        return (
            self._cache_dir
            / "boxscores"
            / f"{int(game_id)}.json"
        )

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


def _sleep_before_retry(response: Any, attempt: int) -> None:
    retry_after = None
    try:
        retry_after = response.headers.get("Retry-After")
    except Exception:
        retry_after = None

    try:
        delay = float(retry_after)
    except (TypeError, ValueError):
        delay = 0.25 * (2 ** attempt)

    sleep(max(0.0, min(delay, 2.0)))


def _read_cache_entry(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            entry = json.load(handle)
    except Exception:
        return None
    if not isinstance(entry, dict):
        return None
    if entry.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    return entry


def _write_cache_entry(
    path: Path | None,
    entry: dict[str, Any],
) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(
            f".{path.name}.{id(entry)}.tmp"
        )
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(
                entry,
                handle,
                separators=(",", ":"),
                sort_keys=True,
            )
        temp_path.replace(path)
    except Exception:
        return


def _cache_entry_stale(
    entry: dict[str, Any],
    *,
    season_id: int,
    ttl_seconds: int,
) -> bool:
    if int(season_id) < current_nhl_season_id():
        return False
    fetched_at = _parse_cache_timestamp(entry.get("fetched_at"))
    if fetched_at is None:
        return True
    return (time() - fetched_at) > max(0, int(ttl_seconds))


def _parse_cache_timestamp(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None
