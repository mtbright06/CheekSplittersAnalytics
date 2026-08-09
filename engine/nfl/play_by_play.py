from __future__ import annotations

import io
from typing import Any

import pandas as pd
import requests

from engine.nfl.models import NFLPlay, NFLPlayer
from engine.nfl.players import load_nfl_players
from engine.nfl.schedule import normalize_game_type
from engine.nfl.teams import normalize_nfl_abbreviation


PBP_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "pbp/play_by_play_{season}.parquet"
)
SOURCE = "nflverse_play_by_play"


class NFLPlayByPlayProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        players: list[NFLPlayer] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._players = players
        self._cache: dict[int, list[dict[str, Any]]] = {}

    def load_plays(
        self,
        *,
        season: int,
        week: int | None = None,
        game_id: str | None = None,
        team: str | None = None,
        season_type: str | None = None,
    ) -> list[NFLPlay]:
        rows = self._load_rows(int(season))
        return normalize_nfl_plays(
            rows,
            players=self._player_index(),
            season=season,
            week=week,
            game_id=game_id,
            team=team,
            season_type=season_type,
        )

    def _load_rows(self, season: int) -> list[dict[str, Any]]:
        if season not in self._cache:
            try:
                response = self._fetcher(
                    PBP_URL.format(season=season),
                    timeout=45,
                    headers={
                        "User-Agent": "SharpStack/1.0 personal analytics",
                    },
                )
                response.raise_for_status()
                self._cache[season] = _parquet_rows(response.content)
            except Exception:
                self._cache[season] = []
        return list(self._cache[season])

    def _player_index(self) -> dict[str, NFLPlayer]:
        if self._players is None:
            self._players = load_nfl_players()
        return {
            player.gsis_id: player
            for player in self._players
        }


def load_nfl_plays(
    *,
    season: int,
    week: int | None = None,
    game_id: str | None = None,
    team: str | None = None,
    season_type: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None = None,
) -> list[NFLPlay]:
    if raw_rows is not None:
        return normalize_nfl_plays(
            raw_rows,
            players=_players_index(players),
            season=season,
            week=week,
            game_id=game_id,
            team=team,
            season_type=season_type,
        )
    return NFLPlayByPlayProvider(
        players=list(players.values()) if isinstance(players, dict) else players,
    ).load_plays(
        season=season,
        week=week,
        game_id=game_id,
        team=team,
        season_type=season_type,
    )


def normalize_nfl_plays(
    rows: list[dict[str, Any]] | None,
    *,
    players: dict[str, NFLPlayer] | None = None,
    season: int | None = None,
    week: int | None = None,
    game_id: str | None = None,
    team: str | None = None,
    season_type: str | None = None,
) -> list[NFLPlay]:
    requested_team = normalize_nfl_abbreviation(team) if team else None
    requested_type = normalize_game_type(season_type) if season_type else None
    plays = []
    seen = set()
    for row in rows or []:
        play = nfl_play_from_provider(row, players=players or {})
        if play is None:
            continue
        if season is not None and play.season != int(season):
            continue
        if week is not None and play.week != int(week):
            continue
        if requested_type and play.season_type != requested_type:
            continue
        if game_id and play.game_id != game_id:
            continue
        if requested_team and requested_team not in {
            play.home_team,
            play.away_team,
            play.possession_team,
            play.defensive_team,
        }:
            continue
        key = (play.game_id, play.drive_id, play.play_id)
        if key in seen:
            continue
        seen.add(key)
        plays.append(play)
    return sorted(
        plays,
        key=lambda play: (
            play.season,
            play.week,
            play.game_id,
            play.play_id,
        ),
    )


def nfl_play_from_provider(
    row: dict[str, Any],
    *,
    players: dict[str, NFLPlayer] | None = None,
) -> NFLPlay | None:
    game_id = _text(row.get("game_id"))
    play_id = _optional_int(row.get("play_id"))
    season = _optional_int(row.get("season"))
    week = _optional_int(row.get("week"))
    season_type = normalize_game_type(row.get("season_type"))
    if not game_id or play_id is None or season is None or week is None or season_type is None:
        return None

    passer_id, passer, passer_concerns = _player(
        row.get("passer_player_id") or row.get("passer_id"),
        players,
        "passer",
    )
    rusher_id, rusher, rusher_concerns = _player(
        row.get("rusher_player_id") or row.get("rusher_id"),
        players,
        "rusher",
    )
    receiver_id, receiver, receiver_concerns = _player(
        row.get("receiver_player_id") or row.get("receiver_id"),
        players,
        "receiver",
    )
    interceptor_id, interceptor, interceptor_concerns = _player(
        row.get("interception_player_id"),
        players,
        "interceptor",
    )
    fumbler_id, fumbler, fumbler_concerns = _player(
        row.get("fumbled_1_player_id") or row.get("fumbler_player_id"),
        players,
        "fumbler",
    )
    concerns = (
        passer_concerns
        + rusher_concerns
        + receiver_concerns
        + interceptor_concerns
        + fumbler_concerns
    )

    return NFLPlay(
        game_id=game_id,
        play_id=play_id,
        drive_id=_optional_int(row.get("drive")),
        season=season,
        season_type=season_type,
        week=week,
        home_team=_team(row.get("home_team")),
        away_team=_team(row.get("away_team")),
        possession_team=_team(row.get("posteam")),
        defensive_team=_team(row.get("defteam")),
        quarter=_optional_int(row.get("qtr")),
        clock=_text(row.get("time")),
        game_seconds_remaining=_optional_int(row.get("game_seconds_remaining")),
        down=_optional_int(row.get("down")),
        yards_to_go=_optional_int(row.get("ydstogo")),
        yardline_100=_optional_int(row.get("yardline_100")),
        home_score=_optional_int(row.get("total_home_score")),
        away_score=_optional_int(row.get("total_away_score")),
        play_type=_text(row.get("play_type")),
        description=_text(row.get("desc")),
        yards_gained=_optional_int(row.get("yards_gained")),
        drive_result=_text(row.get("fixed_drive_result")),
        drive_quarter_start=_optional_int(row.get("drive_quarter_start")),
        drive_quarter_end=_optional_int(row.get("drive_quarter_end")),
        drive_start_yard_line=_text(row.get("drive_start_yard_line")),
        drive_end_yard_line=_text(row.get("drive_end_yard_line")),
        drive_play_count=_optional_int(row.get("drive_play_count")),
        first_down=_optional_bool(row.get("first_down")),
        touchdown=_bool(row.get("touchdown")),
        interception=_bool(row.get("interception")),
        fumble=_bool(row.get("fumble")),
        fumble_lost=_bool(row.get("fumble_lost")),
        sack=_bool(row.get("sack")),
        complete_pass=_optional_bool(row.get("complete_pass")),
        incomplete_pass=_optional_bool(row.get("incomplete_pass")),
        passer_id=passer_id,
        passer=passer,
        rusher_id=rusher_id,
        rusher=rusher,
        receiver_id=receiver_id,
        receiver=receiver,
        interceptor_id=interceptor_id,
        interceptor=interceptor,
        fumbler_id=fumbler_id,
        fumbler=fumbler,
        concerns=tuple(dict.fromkeys(concerns)),
    )


def _parquet_rows(content: bytes) -> list[dict[str, Any]]:
    if not content:
        return []
    try:
        frame = pd.read_parquet(io.BytesIO(content))
    except Exception:
        return []
    return frame.where(pd.notna(frame), None).to_dict("records")


def _player(
    player_id_value: Any,
    players: dict[str, NFLPlayer] | None,
    role: str,
) -> tuple[str | None, NFLPlayer | None, list[str]]:
    player_id = _text(player_id_value)
    if not player_id:
        return None, None, []
    player = players.get(player_id) if players else None
    if player is None:
        return player_id, None, [f"{role}_identity_unresolved"]
    return player_id, player, []


def _players_index(
    players: list[NFLPlayer] | dict[str, NFLPlayer] | None,
) -> dict[str, NFLPlayer] | None:
    if players is None:
        return None
    if isinstance(players, dict):
        return players
    return {
        player.gsis_id: player
        for player in players
    }


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _team(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    return normalize_nfl_abbreviation(text)


def _optional_int(value: Any) -> int | None:
    try:
        text = _text(value)
        if text is None:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    return bool(_optional_bool(value))


def _optional_bool(value: Any) -> bool | None:
    text = _text(value)
    if text is None:
        return None
    if text.lower() in {"true", "t", "yes"}:
        return True
    try:
        return float(text) != 0.0
    except ValueError:
        return False
