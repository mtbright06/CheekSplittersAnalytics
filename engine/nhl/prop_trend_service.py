from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from engine.nhl.models import NHLPlayer, NHLPlayerGameLog
from engine.nhl.player_game_logs import (
    NHLPlayerGameLogProvider,
    REGULAR_SEASON,
)
from engine.nhl.prop_trends import (
    LAST_10,
    LAST_20,
    LAST_5,
    SEASON,
    NHLPropTrendSummary,
    summarize_prop_lines,
    summarize_prop_windows,
)


DEFAULT_WINDOWS = (LAST_5, LAST_10, LAST_20, SEASON)


@dataclass(frozen=True)
class NHLPropTrendRow:
    player_id: int
    player_name: str | None
    team_abbreviation: str | None
    position: str | None
    market: str
    selected_line: float
    last_5: NHLPropTrendSummary
    last_10: NHLPropTrendSummary
    last_20: NHLPropTrendSummary
    season: NHLPropTrendSummary
    alternate_lines: dict[float, NHLPropTrendSummary] = field(default_factory=dict)
    season_id: int | None = None
    game_type: str | int = REGULAR_SEASON
    source: str = "nhl_prop_trend_read_service"
    concerns: tuple[str, ...] = ()

    @property
    def sort_hit_rate(self) -> float:
        return self.last_10.hit_rate if self.last_10.hit_rate is not None else -1.0

    @property
    def sort_games_considered(self) -> int:
        return self.last_10.games_considered


class NHLPropTrendReadService:
    def __init__(
        self,
        *,
        game_log_provider: NHLPlayerGameLogProvider | None = None,
    ) -> None:
        self._game_log_provider = game_log_provider or NHLPlayerGameLogProvider()

    def build_rows(
        self,
        *,
        players: Iterable[NHLPlayer],
        markets: Iterable[str],
        selected_lines: dict[str, float] | float,
        season_id: int,
        game_type: str | int = REGULAR_SEASON,
        alternate_lines: dict[str, Iterable[float]] | None = None,
    ) -> list[NHLPropTrendRow]:
        player_list = tuple(players or ())
        market_list = tuple(markets or ())
        if not player_list or not market_list:
            return []

        rows: list[NHLPropTrendRow] = []
        for player in sorted(
            player_list,
            key=lambda item: (
                item.team_abbreviation or "",
                item.name or "",
                item.source_player_id,
            ),
        ):
            logs, log_concerns = self._load_logs(
                player=player,
                season_id=season_id,
                game_type=game_type,
            )
            for market in market_list:
                selected_line = _selected_line(selected_lines, market)
                row = _row_from_logs(
                    player=player,
                    logs=logs,
                    market=market,
                    selected_line=selected_line,
                    season_id=season_id,
                    game_type=game_type,
                    alternate_lines=(
                        _alternate_lines(alternate_lines, market)
                    ),
                    concerns=log_concerns,
                )
                rows.append(row)

        return sorted(
            rows,
            key=lambda row: (
                row.market,
                -(row.sort_hit_rate),
                -(row.sort_games_considered),
                row.player_name or "",
                row.player_id,
            ),
        )

    def _load_logs(
        self,
        *,
        player: NHLPlayer,
        season_id: int,
        game_type: str | int,
    ) -> tuple[tuple[NHLPlayerGameLog, ...], tuple[str, ...]]:
        try:
            logs = self._game_log_provider.load_player_game_logs(
                player_id=player.source_player_id,
                season_id=season_id,
                game_type=game_type,
            )
        except Exception:
            return (), ("game_log_provider_failed",)

        concerns = []
        if not logs:
            concerns.append("no_game_logs")
        return tuple(logs), tuple(concerns)


def _row_from_logs(
    *,
    player: NHLPlayer,
    logs: tuple[NHLPlayerGameLog, ...],
    market: str,
    selected_line: float,
    season_id: int,
    game_type: str | int,
    alternate_lines: tuple[float, ...],
    concerns: tuple[str, ...],
) -> NHLPropTrendRow:
    windows = summarize_prop_windows(
        logs,
        market=market,
        line=selected_line,
    )
    alternate = (
        summarize_prop_lines(
            logs,
            market=market,
            lines=alternate_lines,
        )
        if alternate_lines
        else {}
    )
    row_concerns = tuple(
        dict.fromkeys(
            concerns
            + tuple(
                concern
                for summary in windows.values()
                for concern in summary.concerns
            )
            + tuple(
                concern
                for summary in alternate.values()
                for concern in summary.concerns
            )
        )
    )

    return NHLPropTrendRow(
        player_id=player.source_player_id,
        player_name=player.name,
        team_abbreviation=player.team_abbreviation,
        position=player.position,
        market=windows[SEASON].market,
        selected_line=float(selected_line),
        last_5=windows[LAST_5],
        last_10=windows[LAST_10],
        last_20=windows[LAST_20],
        season=windows[SEASON],
        alternate_lines=alternate,
        season_id=season_id,
        game_type=game_type,
        concerns=row_concerns,
    )


def _selected_line(
    selected_lines: dict[str, float] | float,
    market: str,
) -> float:
    if isinstance(selected_lines, dict):
        return float(
            selected_lines.get(market)
            if market in selected_lines
            else selected_lines.get(str(market).upper(), 0.5)
        )
    return float(selected_lines)


def _alternate_lines(
    alternate_lines: dict[str, Iterable[float]] | None,
    market: str,
) -> tuple[float, ...]:
    if not alternate_lines:
        return ()
    values = (
        alternate_lines.get(market)
        if market in alternate_lines
        else alternate_lines.get(str(market).upper(), ())
    )
    return tuple(float(value) for value in values or ())
