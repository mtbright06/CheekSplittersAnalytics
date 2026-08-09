from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterable, Mapping

import requests

from app.services.game_result_ingestion_service import GameResultInput


MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
MLB_RESULT_PROVIDER = "mlb_stats_api"


class MLBGameResultProviderError(RuntimeError):
    """Raised when MLB authoritative game results cannot be retrieved."""


@dataclass(frozen=True)
class MLBGameResultProvider:
    """Read-only MLB Stats API adapter that normalizes game truth for ingestion."""

    timeout_seconds: int = 30

    def fetch_recent(self, *, days_back: int = 7, today: date | None = None) -> tuple[GameResultInput, ...]:
        if days_back < 1:
            raise ValueError("days_back must be at least 1.")
        end = today or datetime.now(UTC).date()
        start = end - timedelta(days=days_back - 1)
        payload = self._fetch_schedule(start=start, end=end)
        return tuple(self._normalize_games(payload))

    def _fetch_schedule(self, *, start: date, end: date) -> Mapping[str, Any]:
        try:
            response = requests.get(
                MLB_SCHEDULE_URL,
                params={
                    "sportId": 1,
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                    "gameType": "R",
                    "hydrate": "linescore",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise MLBGameResultProviderError(
                "MLB Stats API result retrieval failed."
            ) from exc
        return payload if isinstance(payload, Mapping) else {}

    @classmethod
    def _normalize_games(
        cls,
        payload: Mapping[str, Any],
    ) -> Iterable[GameResultInput]:
        for game_date in payload.get("dates", []):
            if not isinstance(game_date, Mapping):
                continue
            for game in game_date.get("games", []):
                if not isinstance(game, Mapping):
                    continue
                normalized = cls._normalize_game(game)
                if normalized is not None:
                    yield normalized

    @staticmethod
    def _normalize_game(game: Mapping[str, Any]) -> GameResultInput | None:
        game_pk = game.get("gamePk")
        if game_pk in (None, ""):
            return None

        status_data = game.get("status")
        status_data = status_data if isinstance(status_data, Mapping) else {}
        detailed_state = str(status_data.get("detailedState") or "").strip()
        canonical_status = _canonical_status(
            str(status_data.get("abstractGameState") or ""),
            detailed_state,
        )
        teams = game.get("teams")
        teams = teams if isinstance(teams, Mapping) else {}
        away_score = _score(teams.get("away"))
        home_score = _score(teams.get("home"))
        winner_side = _winner_side(away_score, home_score, canonical_status)

        return GameResultInput(
            provider=MLB_RESULT_PROVIDER,
            league_code="MLB",
            provider_game_id=str(game_pk),
            status=canonical_status,
            source_status=detailed_state or None,
            away_score=away_score,
            home_score=home_score,
            winner_side=winner_side,
            went_extra_innings=_went_extra_innings(game),
            source_metadata={
                "endpoint": "statsapi_schedule",
                "game_type": game.get("gameType"),
                "double_header": game.get("doubleHeader"),
                "scheduled_game_date": game.get("gameDate"),
                "abstract_game_state": status_data.get("abstractGameState"),
                "coded_game_state": status_data.get("codedGameState"),
            },
        )


def _canonical_status(abstract_state: str, detailed_state: str) -> str:
    detailed = detailed_state.strip().upper()
    if "POSTPONED" in detailed:
        return "POSTPONED"
    if "CANCEL" in detailed:
        return "CANCELED"
    if "SUSPENDED" in detailed:
        return "SUSPENDED"
    if "FINAL" in detailed or detailed in {"GAME OVER", "COMPLETED EARLY"}:
        return "FINAL"

    abstract = abstract_state.strip().upper()
    if abstract == "FINAL":
        return "FINAL"
    if abstract == "LIVE":
        return "LIVE"
    return "SCHEDULED"


def _score(team: object) -> int | None:
    if not isinstance(team, Mapping):
        return None
    value = team.get("score")
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _winner_side(
    away_score: int | None,
    home_score: int | None,
    status: str,
) -> str | None:
    if status != "FINAL" or away_score is None or home_score is None:
        return None
    if away_score > home_score:
        return "AWAY"
    if home_score > away_score:
        return "HOME"
    return "TIE"


def _went_extra_innings(game: Mapping[str, Any]) -> bool | None:
    linescore = game.get("linescore")
    if not isinstance(linescore, Mapping):
        return None
    current_inning = linescore.get("currentInning")
    if isinstance(current_inning, int):
        return current_inning > 9
    return None
