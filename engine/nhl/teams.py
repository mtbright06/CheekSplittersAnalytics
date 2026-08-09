from __future__ import annotations

from typing import Any

import requests

from engine.nhl.models import NHLTeam


STATS_TEAM_URL = "https://api.nhle.com/stats/rest/en/team"
STANDINGS_URL = "https://api-web.nhle.com/v1/standings/now"


def normalize_nhl_abbreviation(value: Any) -> str:
    return str(value or "").strip().upper()


def nhl_logo_key(team: NHLTeam | str) -> str:
    abbreviation = (
        team.abbreviation
        if isinstance(team, NHLTeam)
        else str(team or "")
    )
    return normalize_nhl_abbreviation(abbreviation).lower()


def fetch_nhl_team_registry() -> list[NHLTeam]:
    standings = requests.get(
        STANDINGS_URL,
        timeout=30,
    )
    standings.raise_for_status()

    stats = requests.get(
        STATS_TEAM_URL,
        timeout=30,
    )
    stats.raise_for_status()

    return normalize_nhl_team_registry(
        standings.json(),
        stats.json(),
    )


def load_nhl_teams(
    *,
    raw_standings: dict[str, Any] | None = None,
    raw_stats_teams: dict[str, Any] | None = None,
) -> list[NHLTeam]:
    if raw_standings is None or raw_stats_teams is None:
        return fetch_nhl_team_registry()
    return normalize_nhl_team_registry(
        raw_standings,
        raw_stats_teams,
    )


def normalize_nhl_team_registry(
    raw_standings: dict[str, Any] | None,
    raw_stats_teams: dict[str, Any] | None,
) -> list[NHLTeam]:
    if not isinstance(raw_standings, dict):
        return []

    ids_by_abbreviation = _team_ids_by_abbreviation(raw_stats_teams)
    teams: list[NHLTeam] = []
    seen = set()

    for row in raw_standings.get("standings") or []:
        if not isinstance(row, dict):
            continue
        team = nhl_team_from_standings(
            row,
            source_team_id=ids_by_abbreviation.get(
                normalize_nhl_abbreviation(
                    _localized_value(row.get("teamAbbrev"))
                )
            ),
        )
        if not team.abbreviation or team.abbreviation in seen:
            continue
        seen.add(team.abbreviation)
        teams.append(team)

    return sorted(
        teams,
        key=lambda team: team.abbreviation,
    )


def nhl_team_from_standings(
    row: dict[str, Any],
    *,
    source_team_id: int | None = None,
) -> NHLTeam:
    abbreviation = normalize_nhl_abbreviation(
        _localized_value(row.get("teamAbbrev"))
    )
    full_name = (
        _localized_value(row.get("teamName"))
        or abbreviation
    )
    return NHLTeam(
        source_team_id=source_team_id,
        full_name=full_name,
        abbreviation=abbreviation,
        logo_key=nhl_logo_key(abbreviation),
        conference=(
            str(row.get("conferenceName") or "").strip()
            or None
        ),
        division=(
            str(row.get("divisionName") or "").strip()
            or None
        ),
    )


def nhl_team_from_provider(team: dict[str, Any]) -> NHLTeam:
    abbreviation = normalize_nhl_abbreviation(
        team.get("abbrev")
        or team.get("triCode")
    )
    return NHLTeam(
        source_team_id=_optional_int(team.get("id")),
        full_name=_team_full_name(team, abbreviation),
        abbreviation=abbreviation,
        logo_key=nhl_logo_key(abbreviation),
    )


def _team_ids_by_abbreviation(
    raw_stats_teams: dict[str, Any] | None,
) -> dict[str, int]:
    if not isinstance(raw_stats_teams, dict):
        return {}

    ids: dict[str, int] = {}
    for team in raw_stats_teams.get("data") or []:
        if not isinstance(team, dict):
            continue
        abbreviation = normalize_nhl_abbreviation(
            team.get("triCode")
            or team.get("rawTricode")
        )
        team_id = _optional_int(team.get("id"))
        if abbreviation and team_id is not None:
            ids[abbreviation] = team_id
    return ids


def _team_full_name(
    team: dict[str, Any],
    abbreviation: str,
) -> str:
    place = _localized_value(
        team.get("placeName")
        or team.get("placeNameWithPreposition")
    )
    common = _localized_value(
        team.get("commonName")
        or team.get("teamName")
        or team.get("name")
    )
    if place and common:
        return f"{place} {common}".strip()
    return common or place or abbreviation


def _localized_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(
            value.get("default")
            or value.get("en")
            or ""
        ).strip()
    return str(value or "").strip()


def _optional_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
