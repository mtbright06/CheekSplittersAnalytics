from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol

import requests

from engine.nhl.goalies import (
    CONFIRMED,
    PROJECTED,
    UNKNOWN,
    UNAVAILABLE,
)
from engine.nhl.models import NHLGame, NHLGoalieAssignment, NHLPlayer
from engine.nhl.teams import normalize_nhl_abbreviation


DAILY_FACEOFF_BASE_URL = "https://www.dailyfaceoff.com"
SOURCE_DAILY_FACEOFF = "daily_faceoff_next_data"


@dataclass(frozen=True)
class NHLAvailabilityLine:
    label: str
    players: tuple[NHLPlayer, ...]
    unresolved_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class NHLTeamAvailability:
    team_abbreviation: str
    goalie_assignment: NHLGoalieAssignment
    forward_lines: tuple[NHLAvailabilityLine, ...] = ()
    defense_pairs: tuple[NHLAvailabilityLine, ...] = ()
    power_play_units: tuple[NHLAvailabilityLine, ...] = ()
    scratches: tuple[NHLPlayer, ...] = ()
    injury_notes: tuple[str, ...] = ()
    source: str = SOURCE_DAILY_FACEOFF
    retrieved_at: datetime | None = None
    source_timestamp: datetime | None = None
    game_start_time: datetime | None = None
    state: str = "UNKNOWN"
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True)
class NHLGameAvailability:
    source_game_id: int
    away: NHLTeamAvailability
    home: NHLTeamAvailability
    source: str = SOURCE_DAILY_FACEOFF
    retrieved_at: datetime | None = None
    concerns: tuple[str, ...] = ()


class NHLGameAvailabilityProvider(Protocol):
    def load_game_availability(
        self,
        game: NHLGame,
    ) -> NHLGameAvailability:
        ...


class DailyFaceoffAvailabilityProvider:
    def __init__(
        self,
        *,
        fetcher=requests.get,
    ) -> None:
        self._fetcher = fetcher
        self._lineup_cache: dict[str, dict[str, Any]] = {}
        self._goalie_cache: dict[str, list[dict[str, Any]]] = {}

    def load_game_availability(
        self,
        game: NHLGame,
    ) -> NHLGameAvailability:
        retrieved_at = datetime.now(UTC)
        if game.game_date.date() < date.today():
            away = _unknown_team_availability(
                game.away_team.abbreviation,
                game,
                retrieved_at,
                concern="current_availability_not_attached_to_historical_game",
            )
            home = _unknown_team_availability(
                game.home_team.abbreviation,
                game,
                retrieved_at,
                concern="current_availability_not_attached_to_historical_game",
            )
            return NHLGameAvailability(
                source_game_id=game.source_game_id,
                away=away,
                home=home,
                retrieved_at=retrieved_at,
                concerns=("historical_availability_omitted",),
            )

        try:
            goalies = self._load_goalies_for_date(
                game.game_date.date()
            )
            away_goalie, home_goalie = _goalies_for_game(
                goalies,
                away_team=game.away_team.full_name,
                home_team=game.home_team.full_name,
                game_start_time=game.game_date,
                away_roster=game.away_roster,
                home_roster=game.home_roster,
                retrieved_at=retrieved_at,
            )
        except Exception:
            away_goalie = _unavailable_goalie_assignment(
                game.game_date,
                retrieved_at,
                "goalie_source_unavailable",
            )
            home_goalie = _unavailable_goalie_assignment(
                game.game_date,
                retrieved_at,
                "goalie_source_unavailable",
            )
        away = self._load_team_availability(
            game.away_team.full_name,
            game.away_team.abbreviation,
            game.away_roster,
            away_goalie,
            game,
            retrieved_at,
        )
        home = self._load_team_availability(
            game.home_team.full_name,
            game.home_team.abbreviation,
            game.home_roster,
            home_goalie,
            game,
            retrieved_at,
        )
        return NHLGameAvailability(
            source_game_id=game.source_game_id,
            away=away,
            home=home,
            retrieved_at=retrieved_at,
            concerns=tuple(
                concern
                for concern in away.concerns + home.concerns
                if concern
            ),
        )

    def _load_team_availability(
        self,
        team_name: str,
        team_abbreviation: str,
        roster: tuple[NHLPlayer, ...],
        goalie_assignment: NHLGoalieAssignment,
        game: NHLGame,
        retrieved_at: datetime,
    ) -> NHLTeamAvailability:
        try:
            payload = self._load_line_combinations(
                team_name
            )
        except Exception:
            return NHLTeamAvailability(
                team_abbreviation=normalize_nhl_abbreviation(team_abbreviation),
                goalie_assignment=goalie_assignment,
                retrieved_at=retrieved_at,
                game_start_time=game.game_date,
                state="PARTIAL",
                concerns=("line_combinations_unavailable",),
            )

        combinations = payload.get("combinations") or {}
        source_timestamp = _parse_timestamp(
            combinations.get("updatedAt")
        )
        lines, concerns = _line_groups_from_combinations(
            combinations,
            roster=roster,
        )
        state = (
            "COMPLETE"
            if lines["forward_lines"]
            and lines["defense_pairs"]
            and lines["power_play_units"]
            else "PARTIAL"
        )
        return NHLTeamAvailability(
            team_abbreviation=normalize_nhl_abbreviation(team_abbreviation),
            goalie_assignment=goalie_assignment,
            forward_lines=tuple(lines["forward_lines"]),
            defense_pairs=tuple(lines["defense_pairs"]),
            power_play_units=tuple(lines["power_play_units"]),
            injury_notes=tuple(lines["injury_notes"]),
            retrieved_at=retrieved_at,
            source_timestamp=source_timestamp,
            game_start_time=game.game_date,
            state=state,
            concerns=tuple(concerns),
        )

    def _load_line_combinations(
        self,
        team_name: str,
    ) -> dict[str, Any]:
        slug = _daily_faceoff_team_slug(team_name)
        if slug not in self._lineup_cache:
            url = f"{DAILY_FACEOFF_BASE_URL}/teams/{slug}/line-combinations"
            self._lineup_cache[slug] = _next_data_from_url(
                url,
                self._fetcher,
            )
        return self._lineup_cache[slug]

    def _load_goalies_for_date(
        self,
        target_date: date,
    ) -> list[dict[str, Any]]:
        key = target_date.isoformat()
        if key not in self._goalie_cache:
            url = f"{DAILY_FACEOFF_BASE_URL}/starting-goalies/{key}"
            payload = _next_data_from_url(
                url,
                self._fetcher,
            )
            self._goalie_cache[key] = (
                payload.get("data")
                if isinstance(payload.get("data"), list)
                else []
            )
        return self._goalie_cache[key]


def _line_groups_from_combinations(
    combinations: dict[str, Any],
    *,
    roster: tuple[NHLPlayer, ...],
) -> tuple[dict[str, list], list[str]]:
    groups = {
        "forward_lines": [],
        "defense_pairs": [],
        "power_play_units": [],
        "injury_notes": [],
    }
    concerns: list[str] = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for raw_player in combinations.get("players") or []:
        if not isinstance(raw_player, dict):
            continue
        category = str(raw_player.get("categoryIdentifier") or "")
        identifier = str(raw_player.get("groupIdentifier") or "")
        label = str(raw_player.get("groupName") or identifier)
        grouped.setdefault(
            (category, identifier, label),
            [],
        ).append(raw_player)
        injury = raw_player.get("injuryStatus")
        if injury:
            groups["injury_notes"].append(
                f"{raw_player.get('name')}: {injury}"
            )

    for (category, identifier, label), players in sorted(grouped.items()):
        line = _availability_line_from_players(
            label,
            players,
            roster=roster,
        )
        if line.unresolved_names:
            concerns.append("line_identity_resolution_incomplete")
        if category == "ev" and identifier.startswith("f"):
            groups["forward_lines"].append(line)
        elif category == "ev" and identifier.startswith("d"):
            groups["defense_pairs"].append(line)
        elif category == "pp":
            groups["power_play_units"].append(line)

    return groups, concerns


def _availability_line_from_players(
    label: str,
    players: list[dict[str, Any]],
    *,
    roster: tuple[NHLPlayer, ...],
) -> NHLAvailabilityLine:
    resolved = []
    unresolved = []
    for raw_player in players:
        player, concern = resolve_player_identity(
            raw_player.get("name"),
            roster,
        )
        if player is None:
            unresolved.append(str(raw_player.get("name") or "Unknown"))
        else:
            resolved.append(player)
        if concern == "ambiguous":
            unresolved.append(str(raw_player.get("name") or "Unknown"))

    return NHLAvailabilityLine(
        label=label,
        players=tuple(resolved),
        unresolved_names=tuple(dict.fromkeys(unresolved)),
    )


def resolve_player_identity(
    name: Any,
    roster: tuple[NHLPlayer, ...],
) -> tuple[NHLPlayer | None, str | None]:
    cleaned = _clean_name(name)
    matches = [
        player
        for player in roster
        if _clean_name(player.name) == cleaned
    ]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, "ambiguous"
    return None, "unmatched"


def _goalies_for_game(
    games: list[dict[str, Any]],
    *,
    away_team: str,
    home_team: str,
    game_start_time: datetime,
    away_roster: tuple[NHLPlayer, ...],
    home_roster: tuple[NHLPlayer, ...],
    retrieved_at: datetime,
) -> tuple[NHLGoalieAssignment, NHLGoalieAssignment]:
    for raw_game in games:
        if not isinstance(raw_game, dict):
            continue
        if (
            _clean_name(raw_game.get("awayTeamName")) == _clean_name(away_team)
            and _clean_name(raw_game.get("homeTeamName")) == _clean_name(home_team)
        ):
            return (
                _goalie_assignment_from_daily_faceoff(
                    raw_game,
                    side="away",
                    roster=away_roster,
                    game_start_time=game_start_time,
                    retrieved_at=retrieved_at,
                ),
                _goalie_assignment_from_daily_faceoff(
                    raw_game,
                    side="home",
                    roster=home_roster,
                    game_start_time=game_start_time,
                    retrieved_at=retrieved_at,
                ),
            )

    return (
        _unknown_goalie_assignment(
            game_start_time,
            retrieved_at,
            "goalie_game_not_found",
        ),
        _unknown_goalie_assignment(
            game_start_time,
            retrieved_at,
            "goalie_game_not_found",
        ),
    )


def _goalie_assignment_from_daily_faceoff(
    raw_game: dict[str, Any],
    *,
    side: str,
    roster: tuple[NHLPlayer, ...],
    game_start_time: datetime,
    retrieved_at: datetime,
) -> NHLGoalieAssignment:
    prefix = "away" if side == "away" else "home"
    goalie_name = raw_game.get(f"{prefix}GoalieName")
    strength = str(raw_game.get(f"{prefix}NewsStrengthName") or "")
    source_timestamp = _parse_timestamp(
        raw_game.get(f"{prefix}NewsCreatedAt")
    )
    if not goalie_name:
        return _unknown_goalie_assignment(
            game_start_time,
            retrieved_at,
            "goalie_name_missing",
            source_timestamp=source_timestamp,
        )
    player, concern = resolve_player_identity(
        goalie_name,
        roster,
    )
    concerns = []
    if concern:
        concerns.append(f"goalie_identity_{concern}")
    status = (
        CONFIRMED
        if strength.strip().lower() == "confirmed"
        else PROJECTED
        if strength
        else UNKNOWN
    )
    return NHLGoalieAssignment(
        status=status,
        player=player,
        source=SOURCE_DAILY_FACEOFF,
        retrieved_at=retrieved_at,
        source_timestamp=source_timestamp,
        game_start_time=game_start_time,
        concerns=tuple(concerns),
    )


def _unknown_goalie_assignment(
    game_start_time: datetime,
    retrieved_at: datetime,
    concern: str,
    *,
    source_timestamp: datetime | None = None,
) -> NHLGoalieAssignment:
    return NHLGoalieAssignment(
        status=UNKNOWN,
        source=SOURCE_DAILY_FACEOFF,
        retrieved_at=retrieved_at,
        source_timestamp=source_timestamp,
        game_start_time=game_start_time,
        concerns=(concern,),
    )


def _unavailable_goalie_assignment(
    game_start_time: datetime,
    retrieved_at: datetime,
    concern: str,
) -> NHLGoalieAssignment:
    return NHLGoalieAssignment(
        status=UNAVAILABLE,
        source=SOURCE_DAILY_FACEOFF,
        retrieved_at=retrieved_at,
        game_start_time=game_start_time,
        concerns=(concern,),
    )


def _unknown_team_availability(
    team_abbreviation: str,
    game: NHLGame,
    retrieved_at: datetime,
    *,
    concern: str,
) -> NHLTeamAvailability:
    return NHLTeamAvailability(
        team_abbreviation=normalize_nhl_abbreviation(team_abbreviation),
        goalie_assignment=_unknown_goalie_assignment(
            game.game_date,
            retrieved_at,
            concern,
        ),
        retrieved_at=retrieved_at,
        game_start_time=game.game_date,
        state="UNKNOWN",
        concerns=(concern,),
    )


def _next_data_from_url(
    url: str,
    fetcher,
) -> dict[str, Any]:
    response = fetcher(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
    )
    if not match:
        raise ValueError("Daily Faceoff Next.js payload not found")
    payload = json.loads(match.group(1))
    page_props = payload.get("props", {}).get("pageProps")
    if not isinstance(page_props, dict):
        raise ValueError("Daily Faceoff pageProps payload not found")
    return page_props


def _daily_faceoff_team_slug(team_name: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        str(team_name or "").strip().lower(),
    ).strip("-")


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_name(value: Any) -> str:
    return " ".join(
        str(value or "")
        .replace(".", "")
        .replace("'", "")
        .strip()
        .lower()
        .split()
    )
