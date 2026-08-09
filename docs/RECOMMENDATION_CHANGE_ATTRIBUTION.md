# Recommendation Change Attribution

Sprint 84.0 reviewed the major changes that could explain reduced MLB
moneyline actionability. This was documentation and read-only investigation
only; no code, thresholds, weights, recommendation logic, UI, data, or
migrations were changed.

## Authority Timeline

| Area | Current owner | Current behavior | Expected effect on actionability |
| --- | --- | --- | --- |
| Winner-first MLB selection | SharpScore moneyline model | Selects the side with the better model score. | Prevents row order, market price, or edge from selecting a team. |
| MLB moneyline conviction tier | `engine/model/recommendations.py::mlb_moneyline_conviction_recommendation` | Uses model win strength plus model confidence. | Reduces plays unless both gates clear. |
| Market value | `engine/model/recommendations.py::market_value_classification` | Labels SSRP edge separately. | Positive edge no longer promotes weak conviction. |
| MLB confidence | `engine/model/confidence.py::calculate_confidence` | Uses score separation, data completeness, and starter certainty; ignores odds. | Lowers confidence when market data previously contributed or when separation is modest. |
| Hammer | `engine/decision/hammer_score.py` | Advisory confirmation using MLB model score plus overlapping model and module components. | Does not alter official MLB tier, but affects ranking context and user perception. |
| Recommendation episodes | `app/services/recommendation_episode_service.py` and lock/grade services | Official analytics count canonical episodes instead of repeated snapshots. | Reduces inflated official counts without changing per-game model tier. |

## Code-Level Findings

MLB moneyline recommendation authority is currently:

```python
mlb_moneyline_conviction_recommendation(model_probability, confidence)
```

with thresholds:

```text
CHEEK RIPPER: model_probability >= 63.0 and confidence >= 85.0
STRONG PLAY:  model_probability >= 59.0 and confidence >= 78.0
PLAYABLE:     model_probability >= 56.5 and confidence >= 74.0
LEAN:         model_probability >= 52.0 and confidence >= 65.0
PASS:         otherwise
```

Legacy edge-based helper functions still exist for non-MLB compatibility, but
the MLB model specification, Decision Builder, and focused tests confirm that
edge/EV/odds do not own MLB moneyline recommendation authority.

## Observed Alignment

The current behavior aligns with the expected impact of recent authority work:

- Positive market edge can coexist with LEAN or PASS model recommendations.
- Hammer WATCH can coexist with model LEAN or PLAYABLE.
- PLAYABLE requires model strength and confidence, not market value.
- Official analytics count canonical recommendations rather than repeated
  snapshots.

The concerning product outcome is not a hidden alternate authority path. It is
that the current official authority may be stricter than the model's practical
score distribution supports.

## Most Likely Contributors

1. Two-dimensional tier gate: model strength and model confidence both must
   clear thresholds.
2. High correlation between model strength and model confidence because both
   include SharpScore separation.
3. Removal of market edge/EV/odds from authority, which intentionally prevents
   price value from rescuing modest model conviction.
4. Canonical episode architecture reducing inflated historical counts, which
   can make official recommendation volume look lower even when per-game tiers
   are unchanged.

## Not Proven

The investigation could not prove:

- whether recommendation quality improved after authority tightening;
- whether prior authority outperformed current authority;
- whether current thresholds are empirically optimal;
- whether Hammer improves outcome ordering after controlling for duplicated MLB
  model components.

The available canonical graded sample is too small for those conclusions.

## Attribution Conclusion

The current LEAN-heavy distribution is best explained by threshold/filter
stacking after the winner-first and market-independent authority work. This is
not an implementation defect. It is an empirically unvalidated authority design
that deserves Phase 3 validation before further tuning or redesign.
