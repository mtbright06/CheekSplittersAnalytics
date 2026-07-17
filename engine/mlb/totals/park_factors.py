from __future__ import annotations

from dataclasses import dataclass
from typing import Any


NEUTRAL_PARK_FACTOR = 1.00

# Conservative Totals v1 run-scoring priors.
#
# 1.00 = league-average run environment
# 1.10 = approximately 10% more run-friendly
# 0.90 = approximately 10% more run-suppressing
#
# These values are intentionally compressed so the park influences the
# projection without overwhelming offense and pitching inputs.
PARK_FACTORS: dict[str, float] = {
    "ARI": 1.02,
    "ATH": 1.00,
    "ATL": 1.03,
    "BAL": 1.01,
    "BOS": 1.05,
    "CHC": 1.02,
    "CWS": 1.02,
    "CIN": 1.07,
    "CLE": 0.98,
    "COL": 1.18,
    "DET": 0.97,
    "HOU": 1.00,
    "KC": 1.01,
    "LAA": 0.99,
    "LAD": 1.01,
    "MIA": 0.96,
    "MIL": 1.01,
    "MIN": 0.99,
    "NYM": 0.98,
    "NYY": 1.04,
    "PHI": 1.04,
    "PIT": 0.97,
    "SD": 0.96,
    "SEA": 0.94,
    "SF": 0.95,
    "STL": 0.98,
    "TB": 0.97,
    "TEX": 1.02,
    "TOR": 1.01,
    "WSH": 1.00,
}


TEAM_ALIASES: dict[str, str] = {
    "OAK": "ATH",
    "ATHLETICS": "ATH",
    "AZ": "ARI",
    "ARIZONA": "ARI",
    "CHW": "CWS",
    "WHITE SOX": "CWS",
    "KCR": "KC",
    "KAN": "KC",
    "LOS ANGELES ANGELS": "LAA",
    "LOS ANGELES DODGERS": "LAD",
    "SDP": "SD",
    "SAN DIEGO": "SD",
    "SFG": "SF",
    "SAN FRANCISCO": "SF",
    "TBR": "TB",
    "TAMPA BAY": "TB",
    "WSN": "WSH",
    "WASHINGTON": "WSH",
}


@dataclass(frozen=True)
class ParkFactorResult:
    team: str
    factor: float
    source: str
    available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "factor": round(self.factor, 3),
            "source": self.source,
            "available": self.available,
        }


def normalize_team_code(value: Any) -> str:
    if value is None:
        return ""

    code = str(value).strip().upper()

    if not code:
        return ""

    return TEAM_ALIASES.get(code, code)


def extract_team_code(
    team_profile: dict[str, Any],
) -> str:
    candidates = (
        team_profile.get("abbreviation"),
        team_profile.get("abbr"),
        team_profile.get("team_abbreviation"),
        team_profile.get("team_code"),
        team_profile.get("code"),
        team_profile.get("name"),
    )

    for candidate in candidates:
        code = normalize_team_code(candidate)

        if code in PARK_FACTORS:
            return code

    return ""


def get_park_factor(
    home_team_profile: dict[str, Any],
) -> ParkFactorResult:
    """
    Return the home venue's run-scoring factor.

    Totals v1 associates each home team with its primary park.
    Neutral-site and venue-specific overrides can be added later.
    """

    team_code = extract_team_code(
        home_team_profile
    )

    if not team_code:
        return ParkFactorResult(
            team="UNKNOWN",
            factor=NEUTRAL_PARK_FACTOR,
            source="NEUTRAL_FALLBACK",
            available=False,
        )

    factor = PARK_FACTORS.get(team_code)

    if factor is None:
        return ParkFactorResult(
            team=team_code,
            factor=NEUTRAL_PARK_FACTOR,
            source="NEUTRAL_FALLBACK",
            available=False,
        )

    return ParkFactorResult(
        team=team_code,
        factor=factor,
        source="STATIC_V1",
        available=True,
    )
