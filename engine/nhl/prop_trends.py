from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from engine.nhl.models import NHLPlayerGameLog


SHOTS_ON_GOAL = "SHOTS_ON_GOAL"
GOALS = "GOALS"
ASSISTS = "ASSISTS"
POINTS = "POINTS"
SAVES = "SAVES"

HIT = "HIT"
MISS = "MISS"
PUSH = "PUSH"

LAST_5 = "LAST_5"
LAST_10 = "LAST_10"
LAST_20 = "LAST_20"
SEASON = "SEASON"
WINDOW_SIZES = {
    LAST_5: 5,
    LAST_10: 10,
    LAST_20: 20,
}
SUPPORTED_MARKETS = {
    SHOTS_ON_GOAL,
    GOALS,
    ASSISTS,
    POINTS,
    SAVES,
}


@dataclass(frozen=True)
class NHLPropTrendGameResult:
    player_id: int
    game_id: int
    game_date: object
    opponent_abbreviation: str | None
    home_away: str | None
    market: str
    line: float
    actual_value: int | float
    result: str
    source: str = "nhl_prop_trends"


@dataclass(frozen=True)
class NHLPropTrendSummary:
    player_id: int
    market: str
    line: float
    window: str
    games_considered: int
    hits: int
    misses: int
    pushes: int
    hit_rate: float | None
    game_results: tuple[NHLPropTrendGameResult, ...]
    source: str = "nhl_prop_trends"
    concerns: tuple[str, ...] = ()


def summarize_prop_trend(
    game_logs: Iterable[NHLPlayerGameLog],
    *,
    market: str,
    line: float,
    window: str = SEASON,
) -> NHLPropTrendSummary:
    logs = tuple(game_logs)
    normalized_market = _market(market)
    normalized_window = _window(window)
    player_id = _player_id(logs)
    if normalized_market is None:
        return _empty_summary(
            player_id=player_id,
            market=str(market or "").upper(),
            line=line,
            window=normalized_window or str(window or "").upper(),
            concern="unsupported_market",
        )
    if normalized_window is None:
        return _empty_summary(
            player_id=player_id,
            market=normalized_market,
            line=line,
            window=str(window or "").upper(),
            concern="unsupported_window",
        )

    qualifying = [
        log
        for log in logs
        if _actual_value(log, normalized_market) is not None
    ]
    ordered = sorted(
        qualifying,
        key=lambda log: (log.game_date, log.game_id),
        reverse=True,
    )
    if normalized_window in WINDOW_SIZES:
        ordered = ordered[:WINDOW_SIZES[normalized_window]]

    results = tuple(
        _game_result(log, market=normalized_market, line=float(line))
        for log in ordered
    )
    hits = sum(result.result == HIT for result in results)
    misses = sum(result.result == MISS for result in results)
    pushes = sum(result.result == PUSH for result in results)
    denominator = hits + misses
    return NHLPropTrendSummary(
        player_id=player_id,
        market=normalized_market,
        line=float(line),
        window=normalized_window,
        games_considered=len(results),
        hits=hits,
        misses=misses,
        pushes=pushes,
        hit_rate=(hits / denominator) if denominator else None,
        game_results=results,
    )


def summarize_prop_windows(
    game_logs: Iterable[NHLPlayerGameLog],
    *,
    market: str,
    line: float,
) -> dict[str, NHLPropTrendSummary]:
    logs = tuple(game_logs)
    return {
        window: summarize_prop_trend(
            logs,
            market=market,
            line=line,
            window=window,
        )
        for window in (LAST_5, LAST_10, LAST_20, SEASON)
    }


def summarize_prop_lines(
    game_logs: Iterable[NHLPlayerGameLog],
    *,
    market: str,
    lines: Iterable[float],
    window: str = SEASON,
) -> dict[float, NHLPropTrendSummary]:
    logs = tuple(game_logs)
    return {
        float(line): summarize_prop_trend(
            logs,
            market=market,
            line=float(line),
            window=window,
        )
        for line in lines
    }


def _game_result(
    log: NHLPlayerGameLog,
    *,
    market: str,
    line: float,
) -> NHLPropTrendGameResult:
    actual = _actual_value(log, market)
    if actual is None:
        raise ValueError("game result requires a qualifying actual value")
    if actual > line:
        result = HIT
    elif actual < line:
        result = MISS
    else:
        result = PUSH
    return NHLPropTrendGameResult(
        player_id=log.player_id,
        game_id=log.game_id,
        game_date=log.game_date,
        opponent_abbreviation=log.opponent_abbreviation,
        home_away=log.home_away,
        market=market,
        line=float(line),
        actual_value=actual,
        result=result,
    )


def _actual_value(
    log: NHLPlayerGameLog,
    market: str,
) -> int | float | None:
    if market == SHOTS_ON_GOAL:
        return log.shots_on_goal
    if market == GOALS:
        return log.goals
    if market == ASSISTS:
        return log.assists
    if market == POINTS:
        return log.points
    if market == SAVES:
        return log.saves
    return None


def _empty_summary(
    *,
    player_id: int,
    market: str,
    line: float,
    window: str,
    concern: str,
) -> NHLPropTrendSummary:
    return NHLPropTrendSummary(
        player_id=player_id,
        market=market,
        line=float(line),
        window=window,
        games_considered=0,
        hits=0,
        misses=0,
        pushes=0,
        hit_rate=None,
        game_results=(),
        concerns=(concern,),
    )


def _market(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    aliases = {
        "SOG": SHOTS_ON_GOAL,
        "SHOTS": SHOTS_ON_GOAL,
        "SHOTS_ON_GOAL": SHOTS_ON_GOAL,
        "GOALS": GOALS,
        "ASSISTS": ASSISTS,
        "POINTS": POINTS,
        "SAVES": SAVES,
    }
    if normalized in aliases:
        return aliases[normalized]
    return normalized if normalized in SUPPORTED_MARKETS else None


def _window(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in {LAST_5, LAST_10, LAST_20, SEASON} else None


def _player_id(game_logs: Iterable[NHLPlayerGameLog]) -> int:
    for log in game_logs:
        return log.player_id
    return 0
