import csv
from model import evaluate_game

with open("data/sample_games.csv", newline="") as f:
    games = list(csv.DictReader(f))

for game in games:
    result = evaluate_game(game)

    print("=" * 50)
    print(f"{result['team']} vs {result['opponent']}")
    print(f"Odds: {result['odds']}")
    print(f"Model: {result['model_pct']}%")
    print(f"Book: {result['book_pct']}%")
    print(f"Edge: {result['edge_pct']}%")
    print(f"Recommendation: {result['recommendation']}")