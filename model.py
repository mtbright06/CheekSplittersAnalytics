import math
from config import WEIGHTS
from odds import american_to_implied

def score_to_probability(score):
    return 1 / (1 + math.exp(-score / 4.5))

def grade_edge(edge):
    if edge >= 0.05:
        return "BET"
    if edge >= 0.02:
        return "LEAN"
    if edge <= -0.02:
        return "AVOID"
    return "PASS"

def evaluate_game(row):
    score = sum(float(row[col]) * weight for col, weight in WEIGHTS.items())
    model_prob = score_to_probability(score)
    book_prob = american_to_implied(row["odds"])
    edge = model_prob - book_prob

    return {
        **row,
        "model_pct": round(model_prob * 100, 1),
        "book_pct": round(book_prob * 100, 1),
        "edge_pct": round(edge * 100, 1),
        "recommendation": grade_edge(edge),
    }