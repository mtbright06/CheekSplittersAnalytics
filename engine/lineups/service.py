from __future__ import annotations

from collections.abc import Callable

from engine.lineups.mlb_provider import fetch_game_lineup_state
from engine.lineups.models import GameLineupState


class MLBLineupService:
    def __init__(
        self,
        provider: Callable[..., GameLineupState] = fetch_game_lineup_state,
    ) -> None:
        self._provider = provider
        self._cache: dict[int, GameLineupState] = {}

    def get_game_lineup(
        self,
        game_id: int | None,
        *,
        refresh: bool = False,
    ) -> GameLineupState:
        if game_id is None:
            return self._provider(game_id)

        if not refresh and game_id in self._cache:
            return self._cache[game_id]

        state = self._provider(
            game_id,
            previous_state=self._cache.get(game_id),
        )
        self._cache[game_id] = state
        return state
