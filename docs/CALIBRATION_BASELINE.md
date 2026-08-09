# Phase 3.3 Calibration Baseline

Read-only statistical analysis completed against the configured Azure
PostgreSQL database on 2026-08-06. No production code, model logic, thresholds,
weights, recommendations, or data were modified.

## Purpose

This document defines the first empirical calibration baseline for
SharpStack's canonical recommendation architecture. The goal is descriptive:
measure how the current persisted recommendations behave against observed
outcomes and expose uncertainty.

Current sample sizes are too small for model-quality conclusions. This
baseline establishes methodology and output shapes for later Phase 3 analysis.

## Dataset Rules

Official performance metrics use canonical recommendation episodes only:

- `recommendation_streams`
- `recommendation_episodes`
- `recommendations` through `canonical_snapshot_id`
- `canonical_recommendation_grades`
- `game_results`

Raw prediction snapshots are excluded from official calibration. They remain
useful for stability and replay studies, but not official hit-rate claims.

Included grade statuses:

- `WIN`
- `LOSS`

Excluded from hit-rate denominators:

- `PUSH`
- `VOID`
- `PENDING`
- `UNGRADEABLE`
- active or locked episodes without a grade

## Metrics

Hit rate:

```text
wins / (wins + losses)
```

Uncertainty:

```text
95% Wilson score interval
```

Interpretation labels:

| Label | Rule |
|---|---|
| READY | Enough graded canonical observations for directional interpretation. |
| PRELIMINARY | Some graded canonical observations exist, but sample size is too small for reliable conclusions. |
| INSUFFICIENT DATA | No usable graded canonical observations, or the required field is absent. |

For Sprint 81.3, any bucket with fewer than `30` decisions is treated as
statistically unreliable. Every observed bucket in the current dataset is
therefore preliminary or insufficient.

## Bucket Definitions

Confidence buckets:

| Bucket | Stored confidence range |
|---|---|
| 40-49 | `0.40 <= confidence < 0.50` |
| 50-59 | `0.50 <= confidence < 0.60` |
| 60-69 | `0.60 <= confidence < 0.70` |
| 70-79 | `0.70 <= confidence < 0.80` |
| 80+ | `confidence >= 0.80` |

Tier buckets:

| Canonical bucket | Included labels |
|---|---|
| STRONG | `CHEEK RIPPER`, `STRONG PLAY`, `STRONG BET`, `HAMMER` |
| PLAYABLE | `PLAYABLE` |
| LEAN | `LEAN` |
| PASS | `PASS`, `NO PLAY`, `NO_PLAY`, `NONE` |
| BET | MLB Totals native `BET` tier, reported separately from moneyline `PLAYABLE`. |

Ordering studies:

- MLB Moneyline strength uses canonical snapshot `projection`, currently the
  persisted moneyline model probability/model strength compatibility value.
- Moneyline confidence uses canonical snapshot `confidence`.
- MLB Totals ordering uses structured `components.model_separation` and
  persisted `hammer_score` compatibility value. A separate first-class totals
  recommendation-score field was not present in the audited rows.

## Reliability Limits

The current canonical sample is not large enough to support:

- calibrated probability claims;
- confidence monotonicity claims;
- tier superiority claims;
- threshold conclusions;
- meaningful KBO conclusions;
- totals projection-error conclusions.

The current result should be read as a baseline wiring and methodology check,
not a model verdict.
