# Phase 3.3 Calibration Baseline Results

Read-only statistical analysis completed on 2026-08-06. No production code,
model logic, thresholds, weights, recommendations, or data were modified.

## Usable Sample Sizes

| Model | Total raw recommendations | Canonical episodes | Graded canonical recommendations | Completed games |
|---|---:|---:|---:|---:|
| MLB Moneyline | `121` | `6` | `2` | `206 MLB FINAL` |
| MLB Totals | `121` | `6` | `2` | `206 MLB FINAL` |
| KBO | `0` | `0` | `0` | `0 KBO FINAL` |

Usable calibration decisions:

| Model | Wins | Losses | Push/Void/Pending excluded | Hit rate | 95% Wilson interval | Verdict |
|---|---:|---:|---:|---:|---:|---|
| MLB Moneyline | `0` | `2` | `0` | `0.0%` | `0.0%-65.8%` | NOT ENOUGH DATA |
| MLB Totals | `1` | `1` | `0` | `50.0%` | `9.5%-90.5%` | NOT ENOUGH DATA |
| KBO | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |

## Confidence Calibration

| Model | Confidence bucket | Sample | Wins | Losses | Observed win rate | 95% Wilson interval | Reliability |
|---|---|---:|---:|---:|---:|---:|---|
| MLB Moneyline | 60-69 | `1` | `0` | `1` | `0.0%` | `0.0%-79.3%` | NOT ENOUGH DATA |
| MLB Moneyline | 70-79 | `1` | `0` | `1` | `0.0%` | `0.0%-79.3%` | NOT ENOUGH DATA |
| MLB Totals | 70-79 | `2` | `1` | `1` | `50.0%` | `9.5%-90.5%` | NOT ENOUGH DATA |
| KBO | all | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |

Monotonicity:

| Model | Result |
|---|---|
| MLB Moneyline | NOT ENOUGH DATA. Two losses in two adjacent buckets cannot test monotonicity. |
| MLB Totals | NOT ENOUGH DATA. Both graded rows are in the same confidence bucket. |
| KBO | INSUFFICIENT DATA. |

Overconfidence / underconfidence:

| Model | Result |
|---|---|
| MLB Moneyline | NOT ENOUGH DATA. The observed 0-2 result is too small to distinguish poor calibration from variance. |
| MLB Totals | NOT ENOUGH DATA. The observed 1-1 result has a very wide interval. |
| KBO | INSUFFICIENT DATA. |

## Recommendation Tier Calibration

Requested tier buckets:

| Model | Tier bucket | Frequency | Wins | Losses | Hit rate | 95% Wilson interval | Reliability |
|---|---|---:|---:|---:|---:|---:|---|
| MLB Moneyline | STRONG | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |
| MLB Moneyline | PLAYABLE | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |
| MLB Moneyline | LEAN | `2` | `0` | `2` | `0.0%` | `0.0%-65.8%` | NOT ENOUGH DATA |
| MLB Moneyline | PASS | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |
| MLB Totals | STRONG | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |
| MLB Totals | PLAYABLE | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |
| MLB Totals | LEAN | `1` | `1` | `0` | `100.0%` | `20.7%-100.0%` | NOT ENOUGH DATA |
| MLB Totals | PASS | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |
| KBO | all requested tiers | `0` | `0` | `0` | n/a | n/a | INSUFFICIENT DATA |

MLB Totals native tier:

| Model | Tier bucket | Frequency | Wins | Losses | Hit rate | 95% Wilson interval | Reliability |
|---|---|---:|---:|---:|---:|---:|---|
| MLB Totals | BET | `1` | `0` | `1` | `0.0%` | `0.0%-79.3%` | NOT ENOUGH DATA |

Tier-ordering verdict:

| Model | Verdict |
|---|---|
| MLB Moneyline | INSUFFICIENT DATA. Only LEAN has graded observations. |
| MLB Totals | INSUFFICIENT DATA. One LEAN win and one BET loss is not interpretable. |
| KBO | INSUFFICIENT DATA. |

## Moneyline Ordering

Sorted by model strength:

| Rank | Provider game id | Selection | Model strength | Confidence | Tier | Grade |
|---:|---|---|---:|---:|---|---|
| 1 | `824804` | Baltimore Orioles | `0.564` | `0.745` | LEAN | LOSS |
| 2 | `823754` | Pittsburgh Pirates | `0.522` | `0.682` | LEAN | LOSS |

Sorted by confidence:

| Rank | Provider game id | Selection | Confidence | Model strength | Tier | Grade |
|---:|---|---|---:|---:|---|---|
| 1 | `824804` | Baltimore Orioles | `0.745` | `0.564` | LEAN | LOSS |
| 2 | `823754` | Pittsburgh Pirates | `0.682` | `0.522` | LEAN | LOSS |

Ordering verdict: NOT ENOUGH DATA. Both moneyline canonical graded
recommendations lost, so neither model strength nor confidence ordering can be
evaluated empirically.

## Totals Ordering

Sorted by projected separation:

| Rank | Provider game id | Selection | Market line | Model separation | Hammer score | Confidence | Tier | Grade |
|---:|---|---|---:|---:|---:|---:|---|---|
| 1 | `823754` | OVER 7.5 | `7.5` | `93.1` | `89.1` | `0.780` | BET | LOSS |
| 2 | `824401` | OVER 7.5 | `7.5` | `52.3` | `72.8` | `0.780` | LEAN | WIN |

Sorted by recommendation-score proxy:

| Rank | Provider game id | Selection | Recommendation-score field | Hammer score | Model separation | Tier | Grade |
|---:|---|---|---|---:|---:|---|---|
| 1 | `823754` | OVER 7.5 | not persisted | `89.1` | `93.1` | BET | LOSS |
| 2 | `824401` | OVER 7.5 | not persisted | `72.8` | `52.3` | LEAN | WIN |

Totals ordering verdict: NOT ENOUGH DATA. The two-row sample is directionally
inverse by separation and Hammer score, but this is not reliable evidence.
Also, a first-class totals recommendation-score field was not present in the
audited canonical rows.

## Reliability Tables

The generated CSV files under `output/reports/` mirror these markdown tables:

- `calibration_confidence_baseline.csv`
- `calibration_tier_baseline.csv`

They are suitable for later reliability-diagram visualization once canonical
sample sizes increase.

## Statistical Confidence

| Study | Classification | Reason |
|---|---|---|
| MLB Moneyline confidence calibration | INSUFFICIENT DATA | `2` graded canonical decisions. |
| MLB Totals confidence calibration | INSUFFICIENT DATA | `2` graded canonical decisions, one confidence bucket. |
| KBO confidence calibration | INSUFFICIENT DATA | No persisted KBO dataset. |
| MLB Moneyline tier calibration | INSUFFICIENT DATA | Only LEAN has graded observations. |
| MLB Totals tier calibration | INSUFFICIENT DATA | Only one LEAN and one BET observation. |
| KBO tier calibration | INSUFFICIENT DATA | No persisted KBO dataset. |
| MLB Moneyline ordering | INSUFFICIENT DATA | Both graded observations are losses. |
| MLB Totals ordering | INSUFFICIENT DATA | Two observations, directionally inverse but uninterpretable. |
| Totals projection-error calibration | INSUFFICIENT DATA | Structured `projected_total` is not persisted. |

## Readiness Matrix

| Analysis | Status |
|---|---|
| Dataset inventory | PRELIMINARY |
| Confidence calibration | INSUFFICIENT DATA |
| Recommendation tier calibration | INSUFFICIENT DATA |
| Moneyline ordering | INSUFFICIENT DATA |
| Totals ordering | INSUFFICIENT DATA |
| KBO calibration | INSUFFICIENT DATA |
| Reliability-diagram table shape | READY |
| Statistical conclusions | INSUFFICIENT DATA |
