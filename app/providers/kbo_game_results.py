from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from app.services.game_result_ingestion_service import GameResultInput
from parsers.schedule_parser import ScheduleParser


KBO_RESULT_PROVIDER = "mykbostats"
KBO_HOME_URL = "https://mykbostats.com/"
KBO_TIMEZONE = ZoneInfo("Asia/Seoul")


class KBOGameResultProviderError(RuntimeError):
    """Raised when MyKBOStats result retrieval cannot be normalized safely."""


@dataclass(frozen=True)
class KBOGameResultProvider:
    timeout_seconds: int = 30

    def fetch_recent(
        self,
        *,
        days_back: int = 7,
        today: date | None = None,
    ) -> tuple[GameResultInput, ...]:
        if days_back < 1:
            raise ValueError("days_back must be at least 1.")
        end = today or datetime.now(KBO_TIMEZONE).date()
        start = end - timedelta(days=days_back - 1)
        payload = self._fetch_home()
        return tuple(
            item
            for item in self._normalize_home(payload)
            if _date_in_range(item.source_metadata.get("game_date"), start, end)
        )

    def _fetch_home(self) -> str:
        try:
            response = requests.get(
                KBO_HOME_URL,
                headers=ScheduleParser.HEADERS,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise KBOGameResultProviderError(
                "MyKBOStats result retrieval failed."
            ) from exc
        return response.text

    @classmethod
    def _normalize_home(cls, html: str) -> Iterable[GameResultInput]:
        soup = BeautifulSoup(html or "", "html.parser")
        for link in soup.find_all("a", href=True):
            href = str(link.get("href") or "").strip()
            if not href.startswith("/games/"):
                continue
            full_url = f"https://mykbostats.com{href}"
            lines = [
                value.strip()
                for value in link.get_text("\n", strip=True).splitlines()
                if value.strip()
            ]
            result = cls._normalize_game_link(
                provider_game_id=full_url,
                href=href,
                lines=lines,
            )
            if result is not None:
                yield result

    @classmethod
    def _normalize_game_link(
        cls,
        *,
        provider_game_id: str,
        href: str,
        lines: list[str],
    ) -> GameResultInput | None:
        teams = _teams_from_lines(lines)
        if teams is None:
            return None
        away, home = teams
        final = any("final" == line.lower() for line in lines)
        away_score, home_score = _scores_from_lines(lines)
        if not final or away_score is None or home_score is None:
            return None

        return GameResultInput(
            provider=KBO_RESULT_PROVIDER,
            league_code="KBO",
            provider_game_id=provider_game_id,
            status="FINAL",
            source_status="Final",
            away_score=away_score,
            home_score=home_score,
            winner_side=_winner_side(away_score, home_score),
            source_metadata={
                "source": "mykbostats_home",
                "game_date": ScheduleParser._game_date_from_href(href),
                "away_team": away,
                "home_team": home,
                "raw_lines": lines,
            },
        )


def _teams_from_lines(lines: list[str]) -> tuple[str, str] | None:
    if len(lines) < 4:
        return None
    away = ScheduleParser._normalize(lines[0], lines[1])
    home = ScheduleParser._normalize(lines[2], lines[3])
    if not ScheduleParser._valid_team_name(away):
        return None
    if not ScheduleParser._valid_team_name(home):
        return None
    return away, home


def _scores_from_lines(lines: list[str]) -> tuple[int | None, int | None]:
    scores = [
        int(match.group(1))
        for line in lines
        if (match := re.fullmatch(r"(\d{1,2})", str(line).strip()))
    ]
    if len(scores) < 2:
        return None, None
    return scores[0], scores[1]


def _winner_side(
    away_score: int,
    home_score: int,
) -> str:
    if away_score > home_score:
        return "AWAY"
    if home_score > away_score:
        return "HOME"
    return "TIE"


def _date_in_range(
    value: Any,
    start: date,
    end: date,
) -> bool:
    if not value:
        return True
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError:
        return True
    return start <= parsed <= end
