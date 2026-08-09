# Recommendation Quality Investigation

Sprint 84.0 investigated why MLB moneyline recommendations have become less
actionable. This was an investigation only. No production code, thresholds,
model weights, recommendation logic, UI code, data, or migrations were changed.

## Root Cause Assessment

FILTER STACKING DETECTED

The current MLB moneyline authority is internally coherent and winner-first, but
the active recommendation tier requires two highly related values to clear at
the same time:

```text
model_win_strength = bounded transform of SharpScore separation
model_confidence   = base + SharpScore separation component + data completeness
                     + starter certainty

tier = threshold(model_win_strength, model_confidence)
```

On the available current MLB slate artifact, `model_win_strength` and
`model_confidence` had a correlation of `0.9997`. Both values are largely driven
by the same SharpScore separation. Requiring both to clear tier thresholds means
the model must effectively prove the same matchup separation twice before
promoting from LEAN to PLAYABLE or higher.

This is not an implementation defect: the code behaves as documented. It is also
not proven to be better than prior authority because the available canonical
graded sample is far too small.

## Historical Recommendation Distribution

Read-only database inspection found:

- `242` raw recommendation snapshots.
- `12` recommendation episodes.
- `4` canonical grades.
- MLB moneyline snapshot persistence begins in the inspected dataset on
  `2026-08-05`, which is already after the recommendation architecture changes.

Because the available persisted history does not include a reliable pre-change
period, the requested before/after comparison cannot be proven from current
data. The table below reports the available post-architecture MLB moneyline
snapshot distribution.

| Date | Build commit | Snapshots | Distinct games | PASS | LEAN | PLAYABLE | STRONG PLAY | CHEEK RIPPER | Avg Hammer | Avg model strength | Avg model confidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-08-05 | `43935b8` | 30 | 15 | 14 | 12 | 4 | 0 | 0 | 56.59 | 53.17 | unavailable |
| 2026-08-05 | `064bfee` | 15 | 15 | 7 | 6 | 2 | 0 | 0 | 56.59 | 53.17 | unavailable |
| 2026-08-05 | `4d2502c` | 30 | 15 | 14 | 12 | 4 | 0 | 0 | 56.58 | 53.17 | unavailable |
| 2026-08-05 | `cd2fa32` | 11 | 11 | 6 | 4 | 1 | 0 | 0 | 55.84 | 52.68 | unavailable |
| 2026-08-06 | `ab10d38` | 35 | 11 | 14 | 21 | 0 | 0 | 0 | 56.22 | 52.26 | 68.32 |

Historical notes:

- No STRONG PLAY or CHEEK RIPPER snapshots were present in the inspected MLB
  moneyline history.
- The only persisted day with `confidence_score` populated in registry snapshot
  components was `2026-08-06`.
- `confidence` on the top-level `recommendations` table is null for these raw
  registry snapshots; model confidence is embedded in components only when the
  adapter emitted it.
- Earlier pre-architecture recommendation distribution is not available in the
  inspected persistence layer, so material frequency change cannot be quantified
  with statistical confidence.

## Current Slate Summary

The available local MLB card artifact is `output/cards/mlb_card.json`, generated
at `2026-08-05T02:49:50+00:00`. The matching Decision Builder artifact is
`output/cards/decision_card.json`, generated at `2026-08-05T03:53:49+00:00`.

Current MLB moneyline distribution:

| Tier | Games |
| --- | ---: |
| PASS | 4 |
| LEAN | 11 |
| PLAYABLE | 0 |
| STRONG PLAY | 0 |
| CHEEK RIPPER | 0 |

Current slate averages:

| Metric | Average | Minimum | Maximum |
| --- | ---: | ---: | ---: |
| SharpScore separation | 4.28 | 0.2 | 8.0 |
| Model win strength | 53.22 | 50.2 | 56.0 |
| Model confidence | 66.86 | 62.4 | 70.9 |
| Hammer score | 56.00 | 47.8 | 62.8 |

No current game reached the PLAYABLE gates:

```text
PLAYABLE requires model win strength >= 56.5 and model confidence >= 74.0
Current maximum model win strength = 56.0
Current maximum model confidence = 70.9
```

## Threshold Pressure

Current slate threshold pass counts:

| Tier gate | Model strength pass | Confidence pass | Both pass |
| --- | ---: | ---: | ---: |
| LEAN | 11 / 15 | 11 / 15 | 11 / 15 |
| PLAYABLE | 0 / 15 | 0 / 15 | 0 / 15 |
| STRONG PLAY | 0 / 15 | 0 / 15 | 0 / 15 |
| CHEEK RIPPER | 0 / 15 | 0 / 15 | 0 / 15 |

Restrictiveness ranking on the current slate:

1. PLAYABLE-or-higher model strength threshold: rejects `15 / 15`.
2. PLAYABLE-or-higher model confidence threshold: rejects `15 / 15`.
3. Hammer advisory promotion threshold: `0 / 15` reached LEAN/BET/HAMMER,
   but Hammer is advisory and does not own MLB moneyline authority.
4. LEAN thresholds: reject `4 / 15`.

## Filter Stacking

Correlation on the current slate:

| Pair | Correlation |
| --- | ---: |
| Model win strength vs model confidence | 0.9997 |
| Model win strength vs Hammer score | 0.6218 |
| Model confidence vs Hammer score | 0.6135 |

Finding:

- Model win strength and model confidence are nearly perfectly correlated for
  this slate because both are driven by SharpScore separation.
- Hammer is moderately correlated with both because it consumes MLB model score
  plus overlapping model components, First 5, Bomb, starter, offense, bullpen,
  park, weather, sample confidence, agreement, and contradiction inputs.
- Official MLB moneyline tiering does not require Hammer, but product surfaces
  can still make Hammer feel like an additional validation layer because it is
  displayed and used in ranking context.

Conclusion: filter stacking exists. The strongest stack is not an explicit
Hammer gate; it is the two-dimensional model tier gate itself.

## Historical Change Attribution

Major authority changes identified in documentation and code:

| Change | Expected impact on frequency | Observed alignment |
| --- | --- | --- |
| Winner-first recommendation overhaul | Removes market/price as authority; recommendations depend on model side and conviction. Should reduce plays that previously existed mainly because price edge was favorable. | Aligns: current authority ignores edge and uses model strength/confidence only. |
| Removal of edge/EV/odds from authority | Prevents market value from promoting weak model conviction. Should reduce actionability when model strength is modest even if price looks attractive. | Aligns: persisted snapshots include ELITE/STRONG/POSITIVE market-value labels that do not promote beyond model tier. |
| MLB moneyline tier thresholds | Requires both model strength and confidence cutoffs. Should reduce PLAYABLE/PLAY frequency if score separation is compressed. | Aligns strongly: current max strength/confidence do not reach PLAYABLE. |
| Hammer as advisory confirmation | Should not change official MLB model tier; may still affect ranking and user perception. | Aligns: Decision Builder counts actionable plays by `model_recommendation`, while Hammer tiers are reported separately. |
| Canonical recommendation architecture | Changes official counting from repeated snapshots to episodes, reducing inflated official counts. Should not change per-game model tier. | Aligns: official analytics are less inflated, but this does not explain why daily card tiers are LEAN-heavy. |
| Confidence correction removing market probability | Should lower confidence for games that previously received market-completeness or market-agreement credit. | Likely contributor, but before/after samples are insufficient to isolate magnitude. |

Most likely explanation: the combination of market-authority removal plus the
current two-dimensional strength/confidence thresholds is producing fewer
PLAYABLE-or-better model recommendations. This is expected from the current
contract, but not yet empirically validated as better.

## Quality Versus Quantity

The available canonical graded dataset is too small to determine whether the
stricter recommendation authority improved historical performance:

- Canonical grades: `4` total across markets.
- MLB moneyline graded canonical episodes observed in the read-only episode
  sample: `2`, both LEAN.
- No meaningful PLAYABLE/STRONG/old-authority comparison is available.

Conclusion: reduced recommendation volume is not currently supported by
statistical evidence. It may be mathematically consistent, but it has not been
proven better.

## Current Authority Evaluation

If SharpStack were rebuilt today using the current models, this investigation
would not recreate the authority exactly without further empirical validation.
The implementation is coherent and market-independent, but these areas deserve
future investigation before treating the current authority as certified:

- Whether model win strength and confidence should both gate tier promotion
  when they are highly correlated.
- Whether model confidence should separate data completeness/starter certainty
  from model separation more explicitly.
- Whether PLAYABLE/STRONG thresholds match the actual observed distribution of
  SharpScore separations.
- Whether Hammer adds incremental predictive information once overlapping MLB
  model components are controlled for.
- Whether actionability should be validated by canonical outcome history rather
  than heuristic threshold strictness.

No redesign is recommended in this sprint. These are Phase 3 validation and
future product-authority questions.

## Final Assessment

Current recommendation authority is not proven defective, but it is also not
proven better. The immediate reason recommendations disappear is that the
PLAYABLE and higher gates are unreachable on the current slate, and the two
primary gates are nearly identical in practice because both reflect SharpScore
separation.

Root cause: FILTER STACKING DETECTED.
