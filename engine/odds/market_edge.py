from engine.odds.implied_probability import implied_probability_to_american
from engine.odds.models import MarketEdge


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def expected_roi(model_probability, american_odds):
    p = safe_float(model_probability)

    if p is None or american_odds is None:
        return None

    p = p / 100

    if american_odds > 0:
        profit = american_odds / 100
    else:
        profit = 100 / abs(american_odds)

    roi = (p * profit) - (1 - p)

    return round(roi * 100, 2)


def calculate_market_edge(model_probability, quote):
    model_probability = safe_float(model_probability)
    book_probability = safe_float(quote.implied_probability)

    if model_probability is None or book_probability is None:
        edge = None
    else:
        edge = round(model_probability - book_probability, 2)

    fair_odds = implied_probability_to_american(model_probability)

    return MarketEdge(
        selection=quote.selection,
        market=quote.market,
        sportsbook=quote.sportsbook,
        american_odds=quote.american_odds,
        book_probability=book_probability,
        model_probability=model_probability,
        edge=edge,
        fair_odds=fair_odds,
        expected_roi=expected_roi(model_probability, quote.american_odds),
    )


def market_edge_to_dict(edge):
    return {
        "selection": edge.selection,
        "market": edge.market,
        "sportsbook": edge.sportsbook,
        "moneyline": edge.american_odds,
        "american_odds": edge.american_odds,
        "book_probability": edge.book_probability,
        "model_probability": edge.model_probability,
        "edge": edge.edge,
        "fair_odds": edge.fair_odds,
        "expected_roi": edge.expected_roi,
    }
