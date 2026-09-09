from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from engine.nfl.models import NFLPlayerGameLog


PASSING_YARDS = "PASSING_YARDS"
PASSING_TOUCHDOWNS = "PASSING_TOUCHDOWNS"
RUSHING_YARDS = "RUSHING_YARDS"
RECEIVING_YARDS = "RECEIVING_YARDS"
RECEPTIONS = "RECEPTIONS"
ANYTIME_TOUCHDOWN = "ANYTIME_TOUCHDOWN"

HIT = "HIT"
MISS = "MISS"
PUSH = "PUSH"

LAST_5 = "LAST_5"
LAST_10 = "LAST_10"
LAST_20 = "LAST_20"
SEASON = "SEASON"
PREVIOUS_SEASON = "PREVIOUS_SEASON"
WINDOW_SIZES = {LAST_5: 5, LAST_10: 10, LAST_20: 20}
SUPPORTED_MARKETS = {
    PASSING_YARDS,
    PASSING_TOUCHDOWNS,
    RUSHING_YARDS,
    RECEIVING_YARDS,
    RECEPTIONS,
    ANYTIME_TOUCHDOWN,
}
SUPPORTED_WINDOWS = {*WINDOW_SIZES, SEASON, PREVIOUS_SEASON}


@dataclass(frozen=True)
class NFLPropTrendGameResult:
    player_id: str | None
    game_id: str
    game_date: date | None
    season: int
    week: int
    team_abbreviation: str | None
    opponent_abbreviation: str | None
    home_away: str | None
    market: str
    line: float
    actual_value: int | float
    result: str
    source: str = "nfl_prop_trends"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NFLPropTrendSummary:
    player_id: str | None
    market: str
    line: float
    window: str
    selected_season: int
    games_considered: int
    hits: int
    misses: int
    pushes: int
    hit_rate: float | None
    game_results: tuple[NFLPropTrendGameResult, ...]
    source: str = "nfl_prop_trends"
    concerns: tuple[str, ...] = ()


def summarize_prop_trend(
    game_logs: Iterable[NFLPlayerGameLog],
    *,
    market: str,
    line: float,
    selected_season: int,
    window: str = SEASON,
) -> NFLPropTrendSummary:
    logs = tuple(game_logs)
    normalized_market = _market(market)
    normalized_window = _window(window)
    player_id = _player_id(logs)
    if normalized_market is None:
        return _empty_summary(
            player_id=player_id,
            market=str(market or "").strip().upper(),
            line=line,
            window=normalized_window or str(window or "").strip().upper(),
            selected_season=selected_season,
            concern="unsupported_market",
        )
    if normalized_window is None:
        return _empty_summary(
            player_id=player_id,
            market=normalized_market,
            line=line,
            window=str(window or "").strip().upper(),
            selected_season=selected_season,
            concern="unsupported_window",
        )

    qualifying = [
        log
        for log in logs
        if log.game_type == "REG" and _actual_value(log, normalized_market) is not None
    ]
    if normalized_window == SEASON:
        qualifying = [log for log in qualifying if log.season == int(selected_season)]
    elif normalized_window == PREVIOUS_SEASON:
        qualifying = [
            log for log in qualifying if log.season == int(selected_season) - 1
        ]

    ordered = sorted(qualifying, key=_game_order, reverse=True)
    if normalized_window in WINDOW_SIZES:
        ordered = ordered[: WINDOW_SIZES[normalized_window]]

    results = tuple(
        _game_result(log, market=normalized_market, line=float(line))
        for log in ordered
    )
    hits = sum(result.result == HIT for result in results)
    misses = sum(result.result == MISS for result in results)
    pushes = sum(result.result == PUSH for result in results)
    denominator = hits + misses
    concerns = tuple(
        dict.fromkeys(
            concern
            for log in ordered
            for concern in log.concerns
        )
    )
    if not results:
        concerns += (_empty_window_concern(normalized_window),)
    return NFLPropTrendSummary(
        player_id=player_id,
        market=normalized_market,
        line=float(line),
        window=normalized_window,
        selected_season=int(selected_season),
        games_considered=len(results),
        hits=hits,
        misses=misses,
        pushes=pushes,
        hit_rate=(hits / denominator) if denominator else None,
        game_results=results,
        concerns=tuple(dict.fromkeys(concerns)),
    )


def summarize_prop_windows(
    game_logs: Iterable[NFLPlayerGameLog],
    *,
    market: str,
    line: float,
    selected_season: int,
) -> dict[str, NFLPropTrendSummary]:
    logs = tuple(game_logs)
    return {
        window: summarize_prop_trend(
            logs,
            market=market,
            line=line,
            selected_season=selected_season,
            window=window,
        )
        for window in (LAST_5, LAST_10, LAST_20, SEASON, PREVIOUS_SEASON)
    }


def summarize_prop_lines(
    game_logs: Iterable[NFLPlayerGameLog],
    *,
    market: str,
    lines: Iterable[float],
    selected_season: int,
    window: str = SEASON,
) -> dict[float, NFLPropTrendSummary]:
    logs = tuple(game_logs)
    return {
        float(line): summarize_prop_trend(
            logs,
            market=market,
            line=float(line),
            selected_season=selected_season,
            window=window,
        )
        for line in lines
    }


def _game_result(
    log: NFLPlayerGameLog,
    *,
    market: str,
    line: float,
) -> NFLPropTrendGameResult:
    actual = _actual_value(log, market)
    if actual is None:
        raise ValueError("game result requires a qualifying actual value")
    if actual > line:
        result = HIT
    elif actual < line:
        result = MISS
    else:
        result = PUSH
    return NFLPropTrendGameResult(
        player_id=log.player_id,
        game_id=log.game_id,
        game_date=log.game_date,
        season=log.season,
        week=log.week,
        team_abbreviation=log.team_abbreviation,
        opponent_abbreviation=log.opponent_abbreviation,
        home_away=log.home_away,
        market=market,
        line=float(line),
        actual_value=actual,
        result=result,
        concerns=log.concerns,
    )


def _actual_value(log: NFLPlayerGameLog, market: str) -> int | float | None:
    if market == PASSING_YARDS:
        return log.passing_yards
    if market == PASSING_TOUCHDOWNS:
        return log.passing_touchdowns
    if market == RUSHING_YARDS:
        return log.rushing_yards
    if market == RECEIVING_YARDS:
        return log.receiving_yards
    if market == RECEPTIONS:
        return log.receptions
    if market == ANYTIME_TOUCHDOWN:
        return log.anytime_touchdowns
    return None


def _game_order(log: NFLPlayerGameLog) -> tuple[date, int, int, str]:
    return (log.game_date or date.min, log.season, log.week, log.game_id)


def _empty_summary(
    *,
    player_id: str | None,
    market: str,
    line: float,
    window: str,
    selected_season: int,
    concern: str,
) -> NFLPropTrendSummary:
    return NFLPropTrendSummary(
        player_id=player_id,
        market=market,
        line=float(line),
        window=window,
        selected_season=int(selected_season),
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
        "PASS_YARDS": PASSING_YARDS,
        "PASSING_YARDS": PASSING_YARDS,
        "PASS_TDS": PASSING_TOUCHDOWNS,
        "PASSING_TDS": PASSING_TOUCHDOWNS,
        "PASSING_TOUCHDOWNS": PASSING_TOUCHDOWNS,
        "RUSH_YARDS": RUSHING_YARDS,
        "RUSHING_YARDS": RUSHING_YARDS,
        "REC_YARDS": RECEIVING_YARDS,
        "RECEIVING_YARDS": RECEIVING_YARDS,
        "RECEPTIONS": RECEPTIONS,
        "ANYTIME_TD": ANYTIME_TOUCHDOWN,
        "ANYTIME_TOUCHDOWN": ANYTIME_TOUCHDOWN,
    }
    return aliases.get(normalized)


def _window(value: str) -> str | None:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in SUPPORTED_WINDOWS else None


def _player_id(game_logs: Iterable[NFLPlayerGameLog]) -> str | None:
    for log in game_logs:
        return log.player_id
    return None


def _empty_window_concern(window: str) -> str:
    if window == SEASON:
        return "no_current_season_game_logs"
    if window == PREVIOUS_SEASON:
        return "no_previous_season_game_logs"
    return "no_recent_game_logs"
