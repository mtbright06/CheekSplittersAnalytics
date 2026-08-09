from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from engine.nhl.models import (
    NHLMoneyPuckGoalieStats,
    NHLMoneyPuckSkaterStats,
    NHLMoneyPuckTeamStats,
)
from engine.nhl.players import normalize_nhl_position
from engine.nhl.teams import normalize_nhl_abbreviation


BASE_URL = "https://moneypuck.com/moneypuck/playerData/seasonSummary"
SOURCE = "MoneyPuck.com"
DEFAULT_CACHE_DIR = Path("data/nhl/moneypuck")
USER_AGENT = "SharpStack/1.0 personal non-commercial analytics"
SUPPORTED_SITUATIONS = {
    "all": "ALL",
    "5on5": "5ON5",
    "5on4": "5ON4",
    "4on5": "4ON5",
    "other": "OTHER",
}
REQUIRED_COLUMNS = {
    "teams.csv": {
        "team",
        "season",
        "situation",
        "games_played",
        "xGoalsFor",
        "xGoalsAgainst",
    },
    "skaters.csv": {
        "playerId",
        "season",
        "name",
        "team",
        "situation",
        "games_played",
        "I_F_xGoals",
    },
    "goalies.csv": {
        "playerId",
        "season",
        "name",
        "team",
        "situation",
        "games_played",
        "xGoals",
        "goals",
    },
}


@dataclass(frozen=True)
class MoneyPuckRefreshResult:
    season: int
    season_type: str
    dataset: str
    source_url: str
    cache_path: Path
    success: bool
    status: str
    row_count: int = 0
    file_size: int = 0
    content_type: str | None = None
    final_url: str | None = None
    error: str | None = None


class MoneyPuckProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
    ) -> None:
        self._fetcher = fetcher
        self._cache_dir = Path(cache_dir)
        self._cache: dict[tuple[int, str, str], list[dict[str, str]]] = {}

    def load_team_advanced_stats(
        self,
        *,
        season: int,
        season_type: str = "regular",
    ) -> list[NHLMoneyPuckTeamStats]:
        rows = self._fetch_csv(
            season,
            season_type,
            "teams.csv",
        )
        return normalize_moneypuck_team_stats(rows)

    def load_skater_advanced_stats(
        self,
        *,
        season: int,
        season_type: str = "regular",
    ) -> list[NHLMoneyPuckSkaterStats]:
        rows = self._fetch_csv(
            season,
            season_type,
            "skaters.csv",
        )
        return normalize_moneypuck_skater_stats(rows)

    def load_goalie_advanced_stats(
        self,
        *,
        season: int,
        season_type: str = "regular",
    ) -> list[NHLMoneyPuckGoalieStats]:
        rows = self._fetch_csv(
            season,
            season_type,
            "goalies.csv",
        )
        return normalize_moneypuck_goalie_stats(rows)

    def _fetch_csv(
        self,
        season: int,
        season_type: str,
        filename: str,
    ) -> list[dict[str, str]]:
        key = (
            int(season),
            str(season_type),
            filename,
        )
        if key not in self._cache:
            self._cache[key] = self._load_csv_rows(
                int(season),
                str(season_type),
                filename,
            )
        return list(self._cache[key])

    def refresh_dataset(
        self,
        *,
        season: int,
        season_type: str = "regular",
        dataset: str,
    ) -> MoneyPuckRefreshResult:
        filename = _dataset_filename(dataset)
        url = _dataset_url(
            int(season),
            str(season_type),
            filename,
        )
        cache_path = self._cache_path(
            int(season),
            str(season_type),
            filename,
        )
        try:
            response = self._fetcher(
                url,
                timeout=30,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            text = str(response.text or "")
            content_type = _response_content_type(response)
            final_url = str(getattr(response, "url", url) or url)
            rows = validate_moneypuck_csv(
                text,
                filename,
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = cache_path.with_name(f".{cache_path.name}.tmp")
            temp_path.write_text(text, encoding="utf-8")
            os.replace(temp_path, cache_path)
            result = MoneyPuckRefreshResult(
                season=int(season),
                season_type=str(season_type),
                dataset=filename,
                source_url=url,
                cache_path=cache_path,
                success=True,
                status="success",
                row_count=len(rows),
                file_size=cache_path.stat().st_size,
                content_type=content_type,
                final_url=final_url,
            )
            self._write_metadata(result)
            self._cache.pop((int(season), str(season_type), filename), None)
            return result
        except Exception as exc:
            result = MoneyPuckRefreshResult(
                season=int(season),
                season_type=str(season_type),
                dataset=filename,
                source_url=url,
                cache_path=cache_path,
                success=False,
                status="failed",
                content_type=(
                    _response_content_type(response)
                    if "response" in locals()
                    else None
                ),
                final_url=(
                    str(getattr(response, "url", url) or url)
                    if "response" in locals()
                    else url
                ),
                error=str(exc),
            )
            self._write_metadata(result)
            return result

    def refresh_season(
        self,
        *,
        season: int,
        season_type: str = "regular",
    ) -> dict[str, MoneyPuckRefreshResult]:
        return {
            dataset: self.refresh_dataset(
                season=season,
                season_type=season_type,
                dataset=dataset,
            )
            for dataset in ("teams.csv", "skaters.csv", "goalies.csv")
        }

    def _load_csv_rows(
        self,
        season: int,
        season_type: str,
        filename: str,
    ) -> list[dict[str, str]]:
        cached = self._read_valid_cache(
            season,
            season_type,
            filename,
        )
        if cached is not None:
            return cached
        result = self.refresh_dataset(
            season=season,
            season_type=season_type,
            dataset=filename,
        )
        if result.success:
            cached = self._read_valid_cache(
                season,
                season_type,
                filename,
            )
            return cached or []
        return []

    def _read_valid_cache(
        self,
        season: int,
        season_type: str,
        filename: str,
    ) -> list[dict[str, str]] | None:
        path = self._cache_path(
            season,
            season_type,
            filename,
        )
        if not path.exists():
            return None
        try:
            return validate_moneypuck_csv(
                path.read_text(encoding="utf-8"),
                filename,
            )
        except Exception:
            return None

    def _cache_path(
        self,
        season: int,
        season_type: str,
        filename: str,
    ) -> Path:
        return self._cache_dir / str(int(season)) / str(season_type) / filename

    def _metadata_path(
        self,
        result: MoneyPuckRefreshResult,
    ) -> Path:
        return result.cache_path.with_suffix(result.cache_path.suffix + ".json")

    def _write_metadata(
        self,
        result: MoneyPuckRefreshResult,
    ) -> None:
        result.cache_path.parent.mkdir(parents=True, exist_ok=True)
        previous = {}
        path = self._metadata_path(result)
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        payload = {
            **previous,
            "source": SOURCE,
            "source_url": result.source_url,
            "season": result.season,
            "season_type": result.season_type,
            "dataset": result.dataset,
            "downloaded_at": (
                _utc_now_iso()
                if result.success
                else previous.get("downloaded_at")
            ),
            "last_refresh_at": _utc_now_iso(),
            "last_refresh_status": result.status,
            "file_size": result.file_size or previous.get("file_size", 0),
            "row_count": result.row_count or previous.get("row_count", 0),
            "content_type": result.content_type,
            "final_url": result.final_url,
            "error": result.error,
        }
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temp_path, path)


def normalize_moneypuck_team_stats(
    rows: list[dict[str, str]],
) -> list[NHLMoneyPuckTeamStats]:
    stats = []
    seen = set()
    for row in rows:
        team = normalize_nhl_abbreviation(row.get("team"))
        season = _optional_int(row.get("season"))
        situation = normalize_moneypuck_situation(row.get("situation"))
        games = _optional_int(row.get("games_played"))
        if not team or season is None or situation is None or games is None:
            continue
        key = (
            team,
            season,
            situation,
        )
        if key in seen:
            continue
        seen.add(key)
        stats.append(
            NHLMoneyPuckTeamStats(
                team_abbreviation=team,
                season=season,
                situation=situation,
                games_played=games,
                ice_time=_optional_float(row.get("iceTime")),
                x_goals_for=_optional_float(row.get("xGoalsFor")),
                x_goals_against=_optional_float(row.get("xGoalsAgainst")),
                x_goals_percentage=_optional_float(row.get("xGoalsPercentage")),
                shot_attempts_for=_optional_float(row.get("shotAttemptsFor")),
                shot_attempts_against=_optional_float(row.get("shotAttemptsAgainst")),
                shots_on_goal_for=_optional_float(row.get("shotsOnGoalFor")),
                shots_on_goal_against=_optional_float(row.get("shotsOnGoalAgainst")),
                goals_for=_optional_float(row.get("goalsFor")),
                goals_against=_optional_float(row.get("goalsAgainst")),
                high_danger_x_goals_for=_optional_float(
                    row.get("highDangerxGoalsFor")
                ),
                high_danger_x_goals_against=_optional_float(
                    row.get("highDangerxGoalsAgainst")
                ),
            )
        )
    return stats


def normalize_moneypuck_skater_stats(
    rows: list[dict[str, str]],
) -> list[NHLMoneyPuckSkaterStats]:
    stats = []
    seen = set()
    for row in rows:
        player_id = _optional_int(row.get("playerId"))
        name = str(row.get("name") or "").strip()
        team = normalize_nhl_abbreviation(row.get("team"))
        season = _optional_int(row.get("season"))
        situation = normalize_moneypuck_situation(row.get("situation"))
        games = _optional_int(row.get("games_played"))
        if (
            player_id is None
            or not name
            or not team
            or season is None
            or situation is None
            or games is None
        ):
            continue
        key = (
            player_id,
            team,
            season,
            situation,
        )
        if key in seen:
            continue
        seen.add(key)
        stats.append(
            NHLMoneyPuckSkaterStats(
                player_id=player_id,
                name=name,
                team_abbreviation=team,
                position=normalize_nhl_position(row.get("position")),
                season=season,
                situation=situation,
                games_played=games,
                ice_time=_optional_float(row.get("icetime")),
                shots_on_goal=_optional_float(row.get("I_F_shotsOnGoal")),
                shot_attempts=_optional_float(row.get("I_F_shotAttempts")),
                individual_x_goals=_optional_float(row.get("I_F_xGoals")),
                goals=_optional_float(row.get("I_F_goals")),
                points=_optional_float(row.get("I_F_points")),
                on_ice_x_goals_for=_optional_float(row.get("OnIce_F_xGoals")),
                on_ice_x_goals_against=_optional_float(row.get("OnIce_A_xGoals")),
                high_danger_shots=_optional_float(row.get("I_F_highDangerShots")),
                high_danger_x_goals=_optional_float(row.get("I_F_highDangerxGoals")),
            )
        )
    return stats


def normalize_moneypuck_goalie_stats(
    rows: list[dict[str, str]],
) -> list[NHLMoneyPuckGoalieStats]:
    stats = []
    seen = set()
    for row in rows:
        player_id = _optional_int(row.get("playerId"))
        name = str(row.get("name") or "").strip()
        team = normalize_nhl_abbreviation(row.get("team"))
        season = _optional_int(row.get("season"))
        situation = normalize_moneypuck_situation(row.get("situation"))
        games = _optional_int(row.get("games_played"))
        if (
            player_id is None
            or not name
            or not team
            or season is None
            or situation is None
            or games is None
        ):
            continue
        key = (
            player_id,
            team,
            season,
            situation,
        )
        if key in seen:
            continue
        seen.add(key)
        goals_against = _optional_float(row.get("goals"))
        expected_goals_against = _optional_float(row.get("xGoals"))
        stats.append(
            NHLMoneyPuckGoalieStats(
                player_id=player_id,
                name=name,
                team_abbreviation=team,
                season=season,
                situation=situation,
                games_played=games,
                ice_time=_optional_float(row.get("icetime")),
                shots_faced=_optional_float(row.get("ongoal")),
                goals_against=goals_against,
                expected_goals_against=expected_goals_against,
                goals_saved_above_expected=_goals_saved_above_expected(
                    expected_goals_against,
                    goals_against,
                ),
                high_danger_shots_against=_optional_float(
                    row.get("highDangerShots")
                ),
                high_danger_x_goals_against=_optional_float(
                    row.get("highDangerxGoals")
                ),
            )
        )
    return stats


def normalize_moneypuck_situation(value: Any) -> str | None:
    text = str(value or "").strip()
    return SUPPORTED_SITUATIONS.get(text)


def _csv_rows(text: str) -> list[dict[str, str]]:
    if not text or "<html" in text[:200].lower():
        return []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    return [
        row
        for row in reader
        if isinstance(row, dict)
    ]


def validate_moneypuck_csv(
    text: str,
    filename: str,
) -> list[dict[str, str]]:
    dataset = _dataset_filename(filename)
    if not text or "<html" in text[:500].lower():
        raise ValueError("MoneyPuck response is not CSV")
    rows = _csv_rows(text)
    if not rows:
        raise ValueError("MoneyPuck CSV has no useful rows")
    columns = set(rows[0].keys())
    missing = REQUIRED_COLUMNS[dataset] - columns
    if missing:
        raise ValueError(
            f"MoneyPuck {dataset} missing required columns: "
            f"{', '.join(sorted(missing))}"
        )
    useful_rows = [
        row
        for row in rows
        if any(str(value or "").strip() for value in row.values())
    ]
    if not useful_rows:
        raise ValueError("MoneyPuck CSV has no useful rows")
    return useful_rows


def _dataset_filename(dataset: str) -> str:
    filename = str(dataset or "").strip()
    if filename in {"teams", "skaters", "goalies"}:
        filename = f"{filename}.csv"
    if filename not in REQUIRED_COLUMNS:
        raise ValueError(f"unsupported MoneyPuck dataset: {dataset}")
    return filename


def _dataset_url(
    season: int,
    season_type: str,
    filename: str,
) -> str:
    return f"{BASE_URL}/{int(season)}/{season_type}/{filename}"


def _response_content_type(response) -> str | None:
    headers = getattr(response, "headers", None)
    if hasattr(headers, "get"):
        return headers.get("content-type") or headers.get("Content-Type")
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _goals_saved_above_expected(
    expected_goals_against: float | None,
    goals_against: float | None,
) -> float | None:
    if expected_goals_against is None or goals_against is None:
        return None
    return expected_goals_against - goals_against


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
