from engine.odds.implied_probability import (
    american_to_implied_probability,
    implied_probability_to_american,
)


tests = [-200, -150, -110, 100, 120, 200]

for odds in tests:
    p = american_to_implied_probability(odds)
    back = implied_probability_to_american(p)
    print(odds, "=>", p, "% =>", back)
