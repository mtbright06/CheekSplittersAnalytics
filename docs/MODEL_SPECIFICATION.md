# SharpStack Recommendation Model Specification

SharpStack recommendations are intended to answer one product question:

> Which team or total outcome does the model believe is most likely to hit before the game starts?

Sportsbook price, edge, expected value, and odds are useful context, but they are not supposed to decide whether a recommendation qualifies, how strong it is, or where it ranks.

## End-To-End Flow

```text
Pregame game + model inputs
        |
        v
Pregame eligibility gate
        |
        v
Market-specific model
        |
        v
Recommendation label + confidence
        |
        v
Market-independent Hammer Score
        |
        v
Winner-first shared ranking
        |
        v
Recommendation Registry
        |
        v
Best Bets, Dashboard, Play of the Day, history
```

If a game is live, completed, has a live market, has no start time, or cannot be verified, SharpStack should not create or publish a new recommendation for that game.

## MLB Moneyline

Verdict: REVIEW.

The MLB moneyline model is mostly winner-first. It scores each team using offense, starting pitching, bullpen, and home field. The selected side is the team with the higher model score, and the model probability comes from the score difference. Recommendation tiers are based on model probability and model confidence.

Market edge is calculated and displayed separately as market value context.

Audit concern: MLB confidence still counts sportsbook implied probability as part of data completeness. Because confidence affects the recommendation tier, market availability can still influence MLB moneyline recommendation strength.

## MLB Totals

Verdict: PASS.

MLB totals choose OVER or UNDER by comparing the model's projected total with the pregame market line. The distance from the line is treated as model separation, not betting edge.

Totals recommendation strength uses:

- model separation from the line
- model confidence
- data quality
- bullpen confidence

Odds, price, EV, market quality, and sportsbook are preserved for display only.

## KBO Moneyline

Verdict: REVIEW.

The no-market KBO path is model-score driven. It uses KBO model score tiers and model-strength confidence when no real locked market exists.

Audit concern: the real-market KBO finalize path still recomputes edge and uses the legacy edge-based recommendation engine. Market availability also flows into the shared KBO confidence helper when that real-market path is used.

## Hammer Score

Verdict: PASS.

Hammer Score is now a model-conviction score. It excludes market edge, EV, odds, price, and sportsbook data from weighting. Missing components are skipped and the score is normalized by active weight so unavailable signals do not unfairly lower the score.

Current Hammer inputs are model score/probability, First 5 score, Bomb score, starter, offense, bullpen, park, weather, sample confidence, module agreement, and contradiction count.

## Shared Ranking, Registry, Best Bets, Dashboard, Play of the Day

Verdict: PASS with one REVIEW item.

Shared ranking now prioritizes:

1. canonical recommendation tier
2. model or outcome probability
3. model confidence
4. market-independent Hammer Score
5. final identifier tie-breaker

Registry, Best Bets, Dashboard previews, and Play of the Day inherit this winner-first order. Edge, EV, sportsbook, and odds remain display metadata.

Review item: exact ties currently fall through to `recommendation_id`, which defaults to a UUID when not supplied. That is deterministic for an already-created row, but not stable across builds unless adapters provide stable IDs.

## Current Production Recommendation

Before further model tuning, fix the remaining market-influence risks:

- remove sportsbook implied probability from MLB confidence data completeness
- remove or retire KBO real-market edge-based recommendation finalization
- replace UUID tie-break fallback with a stable deterministic event/market/selection order
- add tests proving those cases remain winner-first
