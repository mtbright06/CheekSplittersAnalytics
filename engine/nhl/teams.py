from __future__ import annotations

from typing import Any

from engine.nhl.models import NHLTeam


def normalize_nhl_abbreviation(value: Any) -> str:
    return str(value or "").strip().upper()


def nhl_logo_key(team: NHLTeam | str) -> str:
    abbreviation = (
        team.abbreviation
        if isinstance(team, NHLTeam)
        else str(team or "")
    )
    return normalize_nhl_abbreviation(abbreviation).lower()


def nhl_team_from_provider(team: dict[str, Any]) -> NHLTeam:
    abbreviation = normalize_nhl_abbreviation(
        team.get("abbrev")
        or team.get("triCode")
    )
    return NHLTeam(
        source_team_id=int(team.get("id") or 0),
        full_name=_team_full_name(team, abbreviation),
        abbreviation=abbreviation,
    )


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
