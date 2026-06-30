from dataclasses import dataclass


@dataclass
class OddsQuote:
    sport: str
    league: str
    away_team: str
    home_team: str
    market: str
    selection: str
    american_odds: int | None
    implied_probability: float | None
    sportsbook: str = "MockBook"
    opening_odds: int | None = None
    current_odds: int | None = None
    line_movement: int | None = None
    last_updated: str | None = None
