from __future__ import annotations

from typing import Any

from engine.nfl.models import NFLTeam


CURRENT_TEAM_ROWS = (
    ("ARI", "Arizona Cardinals", "NFC", "West"),
    ("ATL", "Atlanta Falcons", "NFC", "South"),
    ("BAL", "Baltimore Ravens", "AFC", "North"),
    ("BUF", "Buffalo Bills", "AFC", "East"),
    ("CAR", "Carolina Panthers", "NFC", "South"),
    ("CHI", "Chicago Bears", "NFC", "North"),
    ("CIN", "Cincinnati Bengals", "AFC", "North"),
    ("CLE", "Cleveland Browns", "AFC", "North"),
    ("DAL", "Dallas Cowboys", "NFC", "East"),
    ("DEN", "Denver Broncos", "AFC", "West"),
    ("DET", "Detroit Lions", "NFC", "North"),
    ("GB", "Green Bay Packers", "NFC", "North"),
    ("HOU", "Houston Texans", "AFC", "South"),
    ("IND", "Indianapolis Colts", "AFC", "South"),
    ("JAX", "Jacksonville Jaguars", "AFC", "South"),
    ("KC", "Kansas City Chiefs", "AFC", "West"),
    ("LV", "Las Vegas Raiders", "AFC", "West"),
    ("LAC", "Los Angeles Chargers", "AFC", "West"),
    ("LAR", "Los Angeles Rams", "NFC", "West"),
    ("MIA", "Miami Dolphins", "AFC", "East"),
    ("MIN", "Minnesota Vikings", "NFC", "North"),
    ("NE", "New England Patriots", "AFC", "East"),
    ("NO", "New Orleans Saints", "NFC", "South"),
    ("NYG", "New York Giants", "NFC", "East"),
    ("NYJ", "New York Jets", "AFC", "East"),
    ("PHI", "Philadelphia Eagles", "NFC", "East"),
    ("PIT", "Pittsburgh Steelers", "AFC", "North"),
    ("SEA", "Seattle Seahawks", "NFC", "West"),
    ("SF", "San Francisco 49ers", "NFC", "West"),
    ("TB", "Tampa Bay Buccaneers", "NFC", "South"),
    ("TEN", "Tennessee Titans", "AFC", "South"),
    ("WAS", "Washington Commanders", "NFC", "East"),
)

PROVIDER_ALIASES = {
    "JAC": "JAX",
    "WSH": "WAS",
}


def normalize_nfl_abbreviation(
    value: Any,
    *,
    current_franchise: bool = True,
) -> str:
    abbreviation = str(value or "").strip().upper()
    if not current_franchise:
        return abbreviation
    return PROVIDER_ALIASES.get(abbreviation, abbreviation)


def nfl_logo_key(team: NFLTeam | str) -> str:
    abbreviation = (
        team.abbreviation
        if isinstance(team, NFLTeam)
        else str(team or "")
    )
    return normalize_nfl_abbreviation(abbreviation).lower()


def load_nfl_teams() -> list[NFLTeam]:
    return [
        NFLTeam(
            abbreviation=abbreviation,
            full_name=full_name,
            conference=conference,
            division=division,
            logo_key=nfl_logo_key(abbreviation),
        )
        for abbreviation, full_name, conference, division in CURRENT_TEAM_ROWS
    ]


def nfl_team_registry() -> dict[str, NFLTeam]:
    return {
        team.abbreviation: team
        for team in load_nfl_teams()
    }


def nfl_team_from_abbreviation(value: Any) -> NFLTeam:
    abbreviation = normalize_nfl_abbreviation(value)
    registry = nfl_team_registry()
    return registry.get(
        abbreviation,
        NFLTeam(
            abbreviation=abbreviation,
            full_name=abbreviation or "Unknown",
            logo_key=nfl_logo_key(abbreviation),
        ),
    )
