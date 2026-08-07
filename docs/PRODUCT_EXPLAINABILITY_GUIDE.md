# Product Explainability Guide

This guide defines how SharpStack should explain user-facing recommendation
values without overstating statistical certainty.

## Core Explanation Path

Every official recommendation should be explainable as:

```text
Inputs
  -> model calculation
  -> recommendation / tier
  -> Registry row
  -> persisted snapshot
  -> canonical episode
  -> canonical grade
  -> dashboard/history presentation
```

Raw snapshots explain how recommendations evolved. Canonical episodes explain
official performance. Legacy snapshot grades are audit data, not official
performance fallback.

## User-Facing Explanations

### Recommendation

What it means:

SharpStack's current play label for the selected team or side.

What it does not mean:

It is not a guarantee and is not necessarily a market-value label.

Trace:

Model/adapters assign it, Registry serializes it, persistence snapshots it, and
canonical history grades it after the game.

### Recommendation Tier

What it means:

The rule-based strength label produced by the current model contract.

What it does not mean:

It is not yet a statistically validated performance band.

### Model Win Strength

What it means:

A bounded model-implied strength value used for ranking and tiering.

What it does not mean:

It is not currently proven to be calibrated win probability.

Preferred wording:

Use "Model Win Strength" or "Model-Implied Win Strength" instead of plain
"Probability" unless calibration has been validated.

### Confidence

What it means:

A model-specific trust heuristic. Depending on market, it may combine matchup
separation, data quality, starter certainty, bullpen certainty, or ordinal
model-score position.

What it does not mean:

It is not historical hit rate and not a guarantee.

Preferred wording:

Use "Model Confidence" for model trust and "Hammer Confidence" for Hammer
confirmation. Avoid generic "Confidence" when both exist.

### Hammer Score

What it means:

For MLB moneyline, Hammer is an advisory confirmation score from Decision
Builder. It can support ranking and presentation context.

What it does not mean:

It is not the official recommendation authority for MLB moneyline. It is not
always true Hammer for KBO or Totals, where compatibility scores may be mapped
into the same field.

Preferred wording:

Use "Hammer Score" only for true Hammer. Use "Ranking Score" or "Model Strength"
where an adapter maps a compatibility value.

### Recommendation Score

What it means:

A weighted score used by a model, especially totals, to combine separation,
confidence, data quality, and related inputs.

What it does not mean:

It is not probability.

### Projected Total

What it means:

SharpStack's deterministic projected runs total from the totals model or First
5 model.

What it does not mean:

It is not yet proven calibrated as a mean or median total.

### Edge

What it means:

For moneyline, market-vs-model price/value. For totals, it may mean run
separation from the market line.

What it does not mean:

It is not the authoritative recommendation selector unless a specific model
contract says so. For current MLB moneyline, edge is value context, not
conviction authority.

Preferred wording:

Use "Market Edge" for price/value and "Run Separation" for totals.

### Model Health

What it means:

Read-only performance over canonical recommendation episodes and canonical
grades.

What it does not mean:

It does not silently include legacy snapshot grades or uncanonical raw
snapshots.

## Page-Specific Notes

| Page | User explanation to preserve |
|---|---|
| Dashboard | Preview only; detailed metric context lives in model/Registry pages. |
| Best Bets | Official Registry card. Ranking is Registry-owned. |
| Registry | Best place to show reasons and component trace. |
| Model Health | Canonical-only performance. |
| History | Canonical recommendation and grade trail. |
| Bomb Lab | Research diagnostics, not HR probability. |
| First 5 | First-five-inning model projections and leans. |
| KBO | Model-only status must be clear when no real market is loaded. |

## Minimum Context Needed

Before broad user release, add concise help text or hover/context blocks for:

- Model Win Strength
- Model Confidence
- Hammer Score
- Recommendation Tier
- Projected Total
- Recommendation Score
- Edge
