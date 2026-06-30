from dataclasses import dataclass


@dataclass
class MarketQuote:
    provider: str
    sportsbook: str
    league: str
    market: str
    selection: str
    away_team: str
    home_team: str
    american_odds: int | None
    implied_probability: float | None
    event_id: str | None = None
    commence_time: str | None = None
    last_updated: str | None = None


@dataclass
class MarketEdge:
    selection: str
    market: str
    sportsbook: str | None
    american_odds: int | None
    book_probability: float | None
    model_probability: float | None
    edge: float | None
    fair_odds: int | None
    expected_roi: float | None
