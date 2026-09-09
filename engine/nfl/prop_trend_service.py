from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from engine.nfl.models import NFLPlayerGameLog, NFLRosterEntry
from engine.nfl.player_game_logs import (
    NFLPlayerGameLogProvider,
    REGULAR_SEASON,
)
from engine.nfl.prop_trends import (
    LAST_10,
    LAST_20,
    LAST_5,
    PREVIOUS_SEASON,
    SEASON,
    NFLPropTrendSummary,
    summarize_prop_lines,
    summarize_prop_windows,
)


@dataclass(frozen=True)
class NFLPropTrendRow:
    player_id: str
    player_name: str
    team_abbreviation: str
    position: str | None
    market: str
    selected_line: float
    last_5: NFLPropTrendSummary
    last_10: NFLPropTrendSummary
    last_20: NFLPropTrendSummary
    season: NFLPropTrendSummary
    previous_season: NFLPropTrendSummary
    alternate_lines: dict[float, NFLPropTrendSummary] = field(default_factory=dict)
    selected_season: int | None = None
    game_type: str = REGULAR_SEASON
    source: str = "nfl_prop_trend_read_service"
    concerns: tuple[str, ...] = ()

    @property
    def sort_hit_rate(self) -> float:
        return self.last_10.hit_rate if self.last_10.hit_rate is not None else -1.0

    @property
    def sort_games_considered(self) -> int:
        return self.last_10.games_considered


@dataclass(frozen=True)
class NFLPropTrendReadResult:
    rows: tuple[NFLPropTrendRow, ...] = ()
    concerns: tuple[str, ...] = ()
    source: str = "nfl_prop_trend_read_service"


class NFLPropTrendReadService:
    def __init__(
        self,
        *,
        game_log_provider: NFLPlayerGameLogProvider | None = None,
    ) -> None:
        self._game_log_provider = game_log_provider or NFLPlayerGameLogProvider()

    def build_rows(
        self,
        *,
        roster_entries: Iterable[NFLRosterEntry],
        markets: Iterable[str],
        selected_lines: dict[str, float] | float,
        selected_season: int,
        game_type: str = REGULAR_SEASON,
        alternate_lines: dict[str, Iterable[float]] | None = None,
    ) -> NFLPropTrendReadResult:
        entries, roster_concerns = _resolved_roster_entries(roster_entries)
        market_list = tuple(markets or ())
        if not entries or not market_list:
            return NFLPropTrendReadResult(concerns=roster_concerns)

        player_ids = {entry.player_id for entry in entries if entry.player_id}
        logs, source_concerns = self._load_history(
            selected_season=int(selected_season),
            game_type=game_type,
            player_ids=player_ids,
        )
        logs_by_player: dict[str, list[NFLPlayerGameLog]] = {
            player_id: [] for player_id in player_ids
        }
        for log in logs:
            if log.player_id in logs_by_player:
                logs_by_player[log.player_id].append(log)

        rows = []
        for entry in entries:
            player_id = entry.player_id
            if player_id is None or entry.player is None:
                continue
            player_logs = tuple(logs_by_player.get(player_id, ()))
            for market in market_list:
                rows.append(
                    _row_from_logs(
                        entry=entry,
                        logs=player_logs,
                        market=market,
                        selected_line=_selected_line(selected_lines, market),
                        selected_season=int(selected_season),
                        game_type=game_type,
                        alternate_lines=_alternate_lines(alternate_lines, market),
                        concerns=source_concerns,
                    )
                )

        ordered = sorted(
            rows,
            key=lambda row: (
                row.market,
                -row.sort_hit_rate,
                -row.sort_games_considered,
                row.player_name,
                row.team_abbreviation,
                row.player_id,
            ),
        )
        return NFLPropTrendReadResult(
            rows=tuple(ordered),
            concerns=tuple(dict.fromkeys(roster_concerns + source_concerns)),
        )

    def build_player_detail(
        self,
        *,
        roster_entry: NFLRosterEntry,
        market: str,
        selected_line: float,
        selected_season: int,
        game_type: str = REGULAR_SEASON,
        alternate_lines: Iterable[float] | None = None,
    ) -> NFLPropTrendRow | None:
        if roster_entry.player_id is None or roster_entry.player is None:
            return None
        logs, concerns = self._load_history(
            selected_season=int(selected_season),
            game_type=game_type,
            player_ids={roster_entry.player_id},
        )
        return _row_from_logs(
            entry=roster_entry,
            logs=tuple(
                log for log in logs if log.player_id == roster_entry.player_id
            ),
            market=market,
            selected_line=float(selected_line),
            selected_season=int(selected_season),
            game_type=game_type,
            alternate_lines=tuple(float(line) for line in alternate_lines or ()),
            concerns=concerns,
        )

    def _load_history(
        self,
        *,
        selected_season: int,
        game_type: str,
        player_ids: set[str],
    ) -> tuple[tuple[NFLPlayerGameLog, ...], tuple[str, ...]]:
        batches = (
            self._game_log_provider.load_player_game_logs(
                season=selected_season - 1,
                game_type=game_type,
                player_ids=player_ids,
            ),
            self._game_log_provider.load_player_game_logs(
                season=selected_season,
                game_type=game_type,
                player_ids=player_ids,
            ),
        )
        logs = tuple(log for batch in batches for log in batch.game_logs)
        concerns = tuple(
            dict.fromkeys(concern for batch in batches for concern in batch.concerns)
        )
        return logs, concerns


def _row_from_logs(
    *,
    entry: NFLRosterEntry,
    logs: tuple[NFLPlayerGameLog, ...],
    market: str,
    selected_line: float,
    selected_season: int,
    game_type: str,
    alternate_lines: tuple[float, ...],
    concerns: tuple[str, ...],
) -> NFLPropTrendRow:
    windows = summarize_prop_windows(
        logs,
        market=market,
        line=selected_line,
        selected_season=selected_season,
    )
    alternate = (
        summarize_prop_lines(
            logs,
            market=market,
            lines=alternate_lines,
            selected_season=selected_season,
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
    return NFLPropTrendRow(
        player_id=entry.player_id or "",
        player_name=entry.player.name if entry.player else "",
        team_abbreviation=entry.team_abbreviation,
        position=entry.position or (entry.player.position if entry.player else None),
        market=windows[SEASON].market,
        selected_line=float(selected_line),
        last_5=windows[LAST_5],
        last_10=windows[LAST_10],
        last_20=windows[LAST_20],
        season=windows[SEASON],
        previous_season=windows[PREVIOUS_SEASON],
        alternate_lines=alternate,
        selected_season=selected_season,
        game_type=game_type,
        concerns=row_concerns,
    )


def _resolved_roster_entries(
    roster_entries: Iterable[NFLRosterEntry],
) -> tuple[tuple[NFLRosterEntry, ...], tuple[str, ...]]:
    resolved = []
    concerns = []
    seen = set()
    for entry in roster_entries or ():
        if not entry.player_id:
            concerns.append(
                f"roster_player_id_missing:{entry.team_abbreviation}:{entry.position or 'UNKNOWN'}"
            )
            continue
        if entry.player is None:
            concerns.append(f"roster_player_identity_unresolved:{entry.player_id}")
            continue
        key = (entry.player_id, entry.team_abbreviation)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(entry)
    return (
        tuple(
            sorted(
                resolved,
                key=lambda entry: (
                    entry.team_abbreviation,
                    entry.player.name if entry.player else "",
                    entry.player_id or "",
                ),
            )
        ),
        tuple(dict.fromkeys(concerns)),
    )


def _selected_line(selected_lines: dict[str, float] | float, market: str) -> float:
    if isinstance(selected_lines, dict):
        value = selected_lines.get(market)
        if value is None:
            value = selected_lines.get(str(market).upper(), 0.0)
        return float(value)
    return float(selected_lines)


def _alternate_lines(
    alternate_lines: dict[str, Iterable[float]] | None,
    market: str,
) -> tuple[float, ...]:
    if not alternate_lines:
        return ()
    return tuple(float(line) for line in alternate_lines.get(market, ()))
