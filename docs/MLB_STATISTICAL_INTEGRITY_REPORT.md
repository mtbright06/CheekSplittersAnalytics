# MLB Moneyline Statistical Integrity Report

Phase 3A audit and experimentation only. No production model weights,
thresholds, formulas, recommendation logic, labels, grading behavior, or
historical records were changed.

## Closure Recommendation

**MLB STATISTICAL INTEGRITY UNVALIDATED**

The current MLB moneyline architecture is ready to support statistical
validation, but the current canonical episode sample is empty. The model cannot
yet be called calibrated, empirically monotonic, or statistically validated.
This is a data-availability conclusion, not a production-model defect.

## Executive Summary

Phase 3A separates three forecasting properties:

- **Discrimination:** whether higher-scored selections win more often.
- **Calibration:** whether forecast values match observed win frequency.
- **Sharpness:** whether outputs meaningfully separate games rather than
  clustering.

Current production inventory has:

- `0` canonical MLB moneyline episodes.
- `0` canonical graded MLB moneyline recommendations.
- `86` raw MLB moneyline prediction snapshots from `2026-08-05`.
- `165` raw snapshot-grade rows for those snapshots, all `PENDING`.
- `15` distinct MLB moneyline provider games represented by raw graded
  snapshot rows.

Because no canonical MLB moneyline recommendation is resolved as `WIN` or
`LOSS`, no observed win-rate, Brier, log-loss, calibration-slope,
confidence-value, Hammer-value, tier, or weight-sensitivity conclusion can be
validated.

## Historical Data Inventory

| Source | Status | Classification | Notes |
|---|---:|---|---|
| Canonical graded recommendations | Available schema, empty sample | current-engine usable once populated | Correct official source; currently `0` MLB moneyline rows. |
| Recommendation episodes | Available schema, empty MLB moneyline sample | current-engine usable once populated | Prevents repeated snapshot inflation; currently no MLB moneyline episodes. |
| Canonical snapshots | Available through episode lock path | current-engine usable once populated | Required for official calibration; currently no locked canonical MLB moneyline sample. |
| Raw prediction snapshots | Present | raw-score backtest usable later | `86` MLB moneyline snapshots from `2026-08-05`; repeated snapshots can inflate results. |
| Raw snapshot grades | Present but unresolved | incomplete | `165` rows, all `PENDING`; not outcome-usable. |
| Game outcomes | Present table | incomplete for this audit | Outcomes table exists, but no resolved canonical MLB moneyline grades join to it. |
| Model component values | Present in snapshot JSON payloads where persisted | raw-score backtest usable later | Useful for future feature-overlap diagnostics only after outcomes resolve. |
| Model Win Strength | Present as `projection` / compatibility `model_probability` | raw-score backtest usable later | Raw distribution exists; no outcome validation yet. |
| Model confidence | Not populated in raw aggregate inventory | incomplete | Raw query found null min/median/max confidence. |
| Hammer | Present in components where serialized | raw-score backtest usable later | Needs outcome join and one row per game/episode. |
| Recommendation tier | Present in raw components | raw-score backtest usable later | Raw tier distribution exists but no outcomes. |
| Model versions | Present | current-engine usable | Raw snapshots use `sharpstack_registry` version `1.0.0`. |
| Legacy recommendations | No safe comparable MLB moneyline calibration set identified | legacy/non-comparable | Must remain separate from canonical winner-first records. |

## Canonical-Sample Validation

| Metric | Result |
|---|---:|
| Canonical MLB moneyline episodes | `0` |
| Canonical graded MLB moneyline recommendations | `0` |
| Date range | unavailable |
| Model versions | unavailable |
| Resolved vs pending | unavailable |
| Home/away split | unavailable |
| Favorite/underdog split | unavailable |
| Recommendation-tier counts | unavailable |
| Model Win Strength distribution | unavailable |
| Model confidence distribution | unavailable |
| Hammer distribution | unavailable |

Conclusion: **UNVALIDATED**. There is no canonical out-of-sample result set.

## Raw Snapshot Inventory

Raw snapshots are not official calibration data because repeated snapshots can
inflate games and because current raw grades are unresolved. They are useful
only as a readiness check.

| Metric | Result |
|---|---:|
| Raw MLB moneyline prediction snapshots | `86` |
| Raw distinct provider games in snapshot grades | `15` |
| Raw snapshot date range | `2026-08-05 13:32:03 UTC` to `2026-08-05 21:04:54 UTC` |
| Raw model version | `sharpstack_registry 1.0.0` |
| Raw grade rows | `165` |
| Raw grade status | `165 PENDING` |
| Raw Model Win Strength min | `50.5%` |
| Raw Model Win Strength p25 | `51.6%` |
| Raw Model Win Strength median | `52.2%` |
| Raw Model Win Strength p75 | `53.85%` |
| Raw Model Win Strength max | `58.7%` |
| Raw tier counts | `41 PASS`, `34 LEAN`, `11 PLAYABLE` |

Sharpness observation: **CONCERN**. The available raw snapshot distribution is
clustered from `50.5%` to `58.7%`; no raw snapshot reaches `60%`. This may be
normal for one slate, but it cannot yet support strong tier/calibration
claims.

## Reliability and Calibration Analysis

Requested buckets:

| Model Win Strength Bucket | Canonical Sample | Avg Strength | Observed Win Rate | Calibration Gap | Interval |
|---|---:|---:|---:|---:|---|
| 50-54 | `0` | unavailable | unavailable | unavailable | unavailable |
| 55-59 | `0` | unavailable | unavailable | unavailable | unavailable |
| 60-64 | `0` | unavailable | unavailable | unavailable | unavailable |
| 65-69 | `0` | unavailable | unavailable | unavailable | unavailable |
| 70 | `0` | unavailable | unavailable | unavailable | unavailable |

Verdict: **UNVALIDATED**.

The transform:

```text
clamp(50 + score_difference * 0.75, 40, 70)
```

cannot honestly be interpreted as a calibrated probability yet. It should
remain described as Model Win Strength or a model-implied estimate until
canonical resolved outcomes demonstrate calibration.

## Proper Scoring Rules

| Metric | Result | Status |
|---|---:|---|
| Brier score | unavailable | UNVALIDATED |
| Log loss | unavailable | UNVALIDATED |
| Calibration error | unavailable | UNVALIDATED |
| Calibration intercept | unavailable | UNVALIDATED |
| Calibration slope | unavailable | UNVALIDATED |
| Constant 50% baseline | unavailable | UNVALIDATED |
| Home-team historical win-rate baseline | unavailable | UNVALIDATED |
| Selected-team empirical base-rate baseline | unavailable | UNVALIDATED |
| Score-difference logistic baseline | unavailable | UNVALIDATED |
| Market-implied benchmark | unavailable | UNVALIDATED |

Root cause: no resolved canonical MLB moneyline outcomes exist.

## Time-Aware Validation

No chronological train/validation split can be constructed from canonical
outcomes. The current raw snapshot window covers only one date,
`2026-08-05`, and all raw snapshot grades are `PENDING`.

Required future split:

```text
earliest locked canonical MLB moneyline episodes
  -> calibration/train period
later locked canonical MLB moneyline episodes
  -> untouched validation period
```

Same-game repeated snapshots must be represented only by the locked canonical
episode to prevent leakage and sample inflation.

## Calibration-Method Comparison

| Method | Evaluation Status | Notes |
|---|---:|---|
| No calibration | UNVALIDATED | No resolved canonical outcomes. |
| Logistic/sigmoid calibration | UNVALIDATED | Needs earlier training outcomes and later validation outcomes. |
| Isotonic regression | UNVALIDATED | Not appropriate until a substantially larger sample exists. |
| Empirical bucket mapping | UNVALIDATED | Diagnostic only; current buckets have zero canonical outcomes. |

No recalibration is recommended in Phase 3A.

## Model-Confidence Validation

Requested checks:

- higher win rate
- lower Brier error
- lower absolute calibration error
- lower result variance
- incremental information after controlling for Model Win Strength

Verdict: **UNVALIDATED**.

No canonical resolved records exist. Raw aggregate inventory also showed null
confidence min/median/max, so model-confidence persistence should be checked
once canonical samples are populated.

## Hammer Validation

Requested Hammer buckets:

| Hammer Bucket | Canonical Sample | Win Rate | Error Behavior | Verdict |
|---|---:|---:|---|---|
| `<60` | `0` | unavailable | unavailable | UNVALIDATED |
| `60-69` | `0` | unavailable | unavailable | UNVALIDATED |
| `70-79` | `0` | unavailable | unavailable | UNVALIDATED |
| `80+` | `0` | unavailable | unavailable | UNVALIDATED |

Verdict: **UNVALIDATED**. Hammer remains conceptually a partially duplicated
advisory ensemble until canonical outcomes prove incremental ranking value.

## Recommendation-Tier Validation

| Tier | Canonical Sample | Observed Win Rate | Avg Strength | Avg Model Confidence | Avg Hammer | Brier |
|---|---:|---:|---:|---:|---:|---:|
| PASS | `0` | unavailable | unavailable | unavailable | unavailable | unavailable |
| LEAN | `0` | unavailable | unavailable | unavailable | unavailable | unavailable |
| PLAYABLE | `0` | unavailable | unavailable | unavailable | unavailable | unavailable |
| STRONG PLAY | `0` | unavailable | unavailable | unavailable | unavailable | unavailable |
| CHEEK RIPPER | `0` | unavailable | unavailable | unavailable | unavailable | unavailable |

Threshold classification: **UNVALIDATED**.

Raw tier inventory has `41 PASS`, `34 LEAN`, and `11 PLAYABLE`, but all are
pending and not one-row-per-canonical-episode.

## Feature-Overlap Diagnostics

Correlation matrices, rank correlations, variance-inflation diagnostics, and
ablation-style comparisons require resolved outcome rows with stored component
values. Current canonical sample size is zero.

Verdict: **UNVALIDATED**, with Phase 2A/2A.2 conceptual overlap concerns still
open:

- offense metrics overlap around run creation.
- starter metrics overlap around run prevention, command, and contact quality.
- Hammer partly reuses SharpScore-derived starter/offense/bullpen/model
  strength.

## Weight Sensitivity

Weight perturbation analysis was not run against canonical outcomes because
there are no canonical MLB moneyline outcome rows. Running selection-flip
simulations on a single unresolved raw slate would measure artifact fragility,
not statistical robustness.

Verdict: **UNVALIDATED**.

Recommended future experiment: after canonical samples exist, replay stored
component scores under `±5%` and `±10%` normalized weight perturbations and
measure selected-team flips, tier flips, ranking stability, and most sensitive
games. Do not use the result as tuning without holdout validation.

## External Best-Practice Benchmark

| Practice | SharpStack Status | Classification |
|---|---|---:|
| Reliability tables/diagrams | Architecture supports them; current sample empty | UNVALIDATED |
| Brier score | Not computable without resolved outcomes | UNVALIDATED |
| Log loss | Not computable without resolved outcomes | UNVALIDATED |
| Chronological holdout | Not yet possible | UNVALIDATED |
| Out-of-sample calibration | Not yet possible | UNVALIDATED |
| Sigmoid versus isotonic comparison | Not yet possible | UNVALIDATED |
| Baseline comparison | Not yet possible | UNVALIDATED |
| Model drift monitoring | Requires recurring canonical samples | UNVALIDATED |
| Recalibration cadence | Not established | UNVALIDATED |
| Separation of prediction quality from betting value | Implemented architecturally | PROMISING |

## Answers to Phase 3A Questions

| Question | Answer | Classification |
|---|---|---:|
| Is Model Win Strength currently calibrated? | Not proven; no canonical outcomes. | UNVALIDATED |
| Should it be called a probability? | No, not until calibration is proven. | CONCERN |
| Does higher strength produce higher observed win rates? | Unknown. | UNVALIDATED |
| Does model confidence add predictive information? | Unknown. | UNVALIDATED |
| Does Hammer improve ranking? | Unknown. | UNVALIDATED |
| Are tiers ordered correctly? | Unknown empirically; coherent by rule design only. | UNVALIDATED |
| Are current weights robust? | Unknown. | UNVALIDATED |
| Is feature overlap materially concerning? | Conceptually concerning, not outcome-quantified. | CONCERN |
| Is there enough data to fit a calibrator safely? | No. | CONCERN |
| What evidence would justify changing production behavior? | Adequate locked canonical MLB moneyline samples, chronological holdout improvement versus baselines, stable calibration/discrimination gains, and documented no-leakage replay. | UNVALIDATED |

## CONCERN Findings

| ID | Finding | Root Cause | Recommended Correction |
|---|---|---|---|
| P3A-001 | No canonical MLB moneyline calibration sample exists. | Episode lifecycle schema exists but no MLB moneyline canonical episodes/grades are present. | Accumulate locked and graded canonical episodes before calibration claims. |
| P3A-002 | Raw Model Win Strength values are clustered in one unresolved slate. | Only 86 raw snapshots from one date are available locally/remotely. | Monitor sharpness after multiple slates and canonical locks. |
| P3A-003 | Raw model confidence appears unavailable in aggregate inventory. | `recommendations.confidence` min/median/max returned null for raw MLB moneyline snapshots. | Confirm Phase 2A.3 `model_confidence` persistence on future builds. |
| P3A-004 | Feature overlap remains unquantified. | No resolved canonical component/outcome matrix exists. | Run correlation and ablation diagnostics after canonical outcomes accrue. |
| P3A-005 | Calibrator fitting is unsafe now. | Zero resolved canonical samples. | Do not fit sigmoid/isotonic/empirical calibrators until adequate chronological samples exist. |

## DEFECT Findings

None.

## Recommended Next Action

Do not tune the model. First, run enough daily builds through the canonical
episode lifecycle to produce locked and graded MLB moneyline episodes. Then
rerun Phase 3A with one row per canonical episode, chronological splits, and
baseline comparisons.

## Validation Performed

Read-only database inventory was run against the configured PostgreSQL
database. Static repository inspection verified the canonical read model and
distinguished canonical episodes from raw snapshot grades and legacy records.
