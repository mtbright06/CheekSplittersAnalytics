from dataclasses import dataclass


@dataclass
class BullpenSnapshot:
    team: str

    season_era: float | None
    season_whip: float | None

    last7_era: float | None
    innings_last7: float

    innings_last3: float

    appearances_last3: int

    closer_available: bool

    setup_available: bool

    fatigue_score: float

    quality_score: float

    confidence: float
