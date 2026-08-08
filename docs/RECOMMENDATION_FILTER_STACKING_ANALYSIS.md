# Recommendation Filter Stacking Analysis

Sprint 84.2 evaluated whether the MLB moneyline recommendation path repeatedly
filters the same underlying signal. No production behavior was changed.

## Today's Live Slate

The live build generated `11` MLB games at `2026-08-07T01:16:24+00:00`.
Decision Builder generated at `2026-08-07T01:16:28+00:00`.

| Metric | Minimum | Maximum | Average |
| --- | ---: | ---: | ---: |
| SharpScore gap | 0.3 | 8.3 | 3.11 |
| Model Win Strength | 50.2 | 56.2 | 52.32 |
| Model Confidence | 65.3 | 74.1 | 68.42 |
| Hammer | 52.0 | 59.8 | 55.31 |

Recommendation distribution:

| Tier | Games |
| --- | ---: |
| PASS | 5 |
| LEAN | 6 |
| PLAYABLE | 0 |
| STRONG PLAY | 0 |
| CHEEK RIPPER | 0 |

Hammer distribution:

| Hammer tier | Games |
| --- | ---: |
| PASS | 6 |
| WATCH | 5 |
| LEAN | 0 |
| BET | 0 |
| HAMMER | 0 |

## Correlation

| Pair | Correlation |
| --- | ---: |
| SharpScore gap vs Model Win Strength | 0.9999 |
| SharpScore gap vs Model Confidence | 0.9999 |
| Model Win Strength vs Model Confidence | 0.9999 |
| Model Win Strength vs Hammer | 0.7743 |
| Model Confidence vs Hammer | 0.7760 |
| SharpScore gap vs Hammer | 0.7762 |

The first three correlations are effectively perfect because model strength is a
direct transform of the score gap, and confidence includes the same score gap as
its matchup-strength component.

## Independence Matrix

| Component | Independent | Mostly Derived | Fully Derived | Notes |
| --- | --- | --- | --- | --- |
| SharpScore | yes | no | no | First aggregation point for offense, starter, bullpen, and home field. |
| Model Win Strength | no | no | yes | Direct linear transform of SharpScore gap. |
| Model Confidence | no | yes | no | Reuses SharpScore gap, then adds data completeness and starter certainty. |
| Hammer | partial | yes | no | Adds First 5/Bomb/agreement/context but also reuses model strength and component scores. |
| Recommendation Tier | no | no | yes | Threshold lookup from strength and confidence. |
| Recommendation Authority | no | no | yes | Final MLB moneyline recommendation equals model tier; Hammer remains advisory. |

## Reuse Counts

| Underlying signal | SharpScore | Model strength | Model confidence | Hammer | Tier/authority | Total evaluations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Starter quality | 1 | indirectly | directly via starter certainty/data completeness | directly | indirectly | 5 |
| Offense | 1 | indirectly | directly via data completeness | directly | indirectly | 5 |
| Bullpen | 1 | indirectly | no | directly | indirectly | 4 |
| Home/context | 1 | indirectly | no | park/context direct if available | indirectly | 4 |
| SharpScore separation | 1 | directly | directly | indirectly through model strength | directly | 5 |
| Market/odds | no authority | no | no | no authority | no | 0 |

## Gate Analysis

Promotion path:

```text
SharpScore
  -> Model Win Strength
     No new information; direct transform of score gap.

  -> Model Confidence
     Some new information from data completeness and starter certainty, but the
     largest variable component is the same score gap.

  -> Recommendation Tier
     No new information; threshold lookup.

  -> Hammer
     Some new information from First 5, Bomb, agreement, park/weather, and
     sample confidence, but it reuses model strength and component scores.

  -> Displayed Recommendation
     No new information; MLB tier remains authority.
```

## Primary Bottleneck

Today's PLAYABLE threshold failed because the upstream SharpScore gap is
compressed.

Evidence:

- Highest SharpScore gap: `8.3`.
- That becomes model win strength `56.2`.
- PLAYABLE requires model win strength `56.5`.
- The same gap produces model confidence `74.1`, barely above the PLAYABLE
  confidence threshold.
- No game reached PLAYABLE because no score gap reached the strength threshold.

This is not mainly Hammer rejecting good plays. Hammer also stays low, but
official MLB moneyline authority has already stopped at the model tier gate.

## Filter Stacking Finding

SIGNIFICANT FILTER STACKING is present. The official gate requires both model
strength and model confidence, but both are mostly expressions of SharpScore
separation. Hammer then reuses model strength and components as advisory
confirmation, creating an additional product-visible confirmation layer even
though it is not the official authority gate.
