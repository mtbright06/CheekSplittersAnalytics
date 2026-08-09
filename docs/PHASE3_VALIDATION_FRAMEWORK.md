# Phase 3 Statistical Validation Framework

Planning and documentation only. No production model, weight, or threshold
changes are authorized by this document.

## Purpose

Phase 3 answers one question:

```text
How do we know SharpStack is actually improving?
```

The answer must come from persisted prediction-time records, official
outcomes, and repeatable statistical methods. Intuition, anecdotal slates, and
post-hoc screenshots are not sufficient.

## Data Inventory

### Official Recommendation Layer

Use this layer for official model-performance claims.

| Data | Source | Available Fields | Validation Use |
|---|---|---|---|
| Canonical recommendations | `recommendation_episodes` + canonical snapshot | episode id, stream id, status, selection, side, market line, opened/locked/closed timestamps, canonical snapshot id | official sample identity, lifecycle, lock timing |
| Streams | `recommendation_streams` | sport, league, provider, provider game id, market, model version, scheduled start | joins and grouping |
| Canonical grades | `canonical_recommendation_grades` | grade status, graded time, grading version, game result id/revision, canonical snapshot id | official outcomes |
| Canonical read model | `CanonicalRecommendationReadModel.list_graded_records()` | joined official record with grade, game result, model version, components | primary Phase 3 read surface |

### Raw Snapshot Layer

Use this layer for stability, drift, and timeline questions. Do not use raw
snapshots as official performance counts unless explicitly labeled legacy/raw.

| Data | Source | Available Fields | Validation Use |
|---|---|---|---|
| Prediction snapshots | `recommendations` | recommendation time, market, selection, market line, projection, edge, confidence, components, explanation, source | repeated-build behavior, feature values, timeline |
| Snapshot identity | `recommendations` | idempotency key, provider game id, league, sport, scheduled start at prediction, model run id | deduplication, stream reconstruction |
| Episode attachment | `recommendations.recommendation_episode_id` | nullable episode link | attach raw snapshots to official lifecycle |
| Snapshot grades | `prediction_snapshot_grades` | WIN/LOSS/PUSH/VOID/PENDING/UNGRADEABLE, game result revision, grading version | raw snapshot diagnostics only |

### Truth Layer

| Data | Source | Available Fields | Validation Use |
|---|---|---|---|
| Game results | `game_results` | provider, league, provider game id, status, away/home/final total, winner side, completed time, extra innings, revision, source metadata | moneyline result, totals actual score, revision control |
| Provider identifiers | `provider`, `league_code`, `provider_game_id` | stable provider game identity | joins |

### Model Metadata

| Data | Source | Available Fields | Validation Use |
|---|---|---|---|
| Model version | `model_versions` | model name, version, git commit, description | version comparisons and drift |
| Model run | `model_runs` | started/completed times, status, source, label, logical run key, metadata | run stability and retry analysis |

### Prediction Fields In Components

Persisted `Recommendation.components` is the extensible feature store. Current
known fields include or can contain:

- `prediction.conviction_tier`, `model_recommendation`, `recommendation`
- `prediction.hammer_score`, `hammer_score`, `hammer`, `hammer_rating`
- model strength / probability values
- model confidence and confidence labels
- market context and real-market flags
- totals projected total, market total, recommendation score, separation,
  bullpen confidence, data quality where emitted by adapters
- KBO model strength/model confidence aliases

Phase 3 queries must inspect actual JSON keys by model/version before assuming
field presence.

## Existing Analytics Inventory

| Existing Capability | Location | Computes | Reuse |
|---|---|---|---|
| Canonical read model | `app/services/canonical_recommendation_read_model.py` | official graded recommendation records and timelines | primary official query layer |
| Model Health | `app/services/recommendation_analytics_service.py` | sample size, grade counts, win percentage, decision rate by league/market/tier | reuse for baseline bucket reports |
| Recommendation History | `app/services/recommendation_history_service.py` | canonical history filtering and episode timelines | reuse for history pages and timeline extraction |
| Canonical grading | `app/services/canonical_recommendation_grading_service.py` | one official grade per locked episode | source of official outcomes |
| Snapshot grading | `app/services/prediction_snapshot_grading_service.py` | raw snapshot grades | raw/stability diagnostics only |
| Game result ingestion | `app/services/game_result_ingestion_service.py` | authoritative result persistence and revisions | truth source |
| Legacy settlement summary | `RecommendationAnalyticsService.summarize_performance` | legacy ROI/win summaries | legacy-only comparisons |
| Totals console | `engine/reports/totals_console.py` and `tools_test_mlb_totals.py` | projection explanation, not historical validation | example/report formatting only |
| Recommendation tracker | `engine/results/recommendation_tracker.py` | legacy tracking output | legacy reference only |
| Dashboard Model Health | `dashboard/pages/model_health_page.py` | read-only Model Health presentation | presentation reuse |

Current gaps: calibration curves, Brier score, log loss, totals MAE/RMSE,
feature ablation, threshold sweeps, drift detection, and stability metrics are
not implemented yet.

## Canonical Validation Questions

### Calibration

Question: Does higher model strength/confidence correspond to higher empirical
success?

Required data: canonical records, grade status, model probability/strength,
confidence, league, market, model version.

Metrics: bucket accuracy, calibration curve, expected calibration error,
Brier score when the prediction is probability-like, log loss only when valid
probabilities exist.

Interpretation:

- Acceptable: monotonic buckets and low calibration error for sufficient sample.
- Warning: non-monotonic adjacent buckets or overconfidence in one segment.
- Failure: inverted confidence/strength ordering across broad buckets.

### Recommendation Tiers

Question: Do stronger tiers outperform weaker tiers?

Required data: canonical records grouped by tier, market, league, model
version, grade.

Metrics: win/loss/push rate, decision rate, confidence intervals, lift versus
lower tier and versus all actionable recommendations.

Interpretation:

- Acceptable: stronger tiers show non-negative lift with adequate sample.
- Warning: indistinguishable tiers after sample threshold.
- Failure: stronger tiers underperform lower tiers with statistical support.

### Moneyline Ordering

Question: Does higher model strength correspond to higher win probability?

Required data: canonical moneyline records, model strength/probability,
selection side, winner side, grade.

Metrics: bucket win rate, rank correlation, Brier score if probability scale
is valid, calibration plot.

Exclusions: PASS, VOID, UNGRADEABLE, missing model strength.

### Confidence Ordering

Question: Is model confidence monotonic with realized success?

Required data: canonical records with confidence and grade.

Metrics: bucket accuracy, Spearman rank correlation by market, overconfidence
rate by bucket.

### False Confidence

Question: Where does SharpStack consistently overestimate itself?

Required data: canonical records with confidence, tier, model version,
components, grade.

Metrics: high-confidence loss clusters, bucket error, feature/tier breakdowns.

### Projection Error

Question: How far are projected totals from actual totals?

Required data: canonical or raw totals snapshots, `projection` or
`components.projected_total`, `market_line`, `game_results.total_score`.

Metrics: MAE, RMSE, signed bias, line-separation bucket error, over/under
direction accuracy.

### Threshold Validation

Question: Are current thresholds producing useful decision rates and lift?

Required data: canonical records with pre-threshold fields where available,
tier, confidence, model strength, recommendation score, grade.

Metrics: threshold sweep tables, precision/recall for actionability,
decision-rate curves, lift by threshold.

Rule: threshold studies may recommend changes but may not directly tune
production thresholds without a separate approved implementation sprint.

### Feature Contribution

Question: Does each feature add predictive value?

Required data: raw components JSON by model version, canonical outcomes,
feature availability flags.

Metrics: ablation studies, nested model comparison, permutation importance,
coverage-adjusted lift.

Minimum standard: do not compare feature-present rows to feature-missing rows
without controlling for data quality and date range.

### Drift

Question: Has model behavior changed over time?

Required data: model runs, versions, timestamps, canonical records, raw
snapshot distributions.

Metrics: distribution shift of strength/confidence/tier, performance by
month/version, population stability index, sample-size adjusted trend lines.

### Stability

Question: Are recommendations stable between repeated builds?

Required data: raw snapshots attached to episodes, model runs, timelines.

Metrics: selection flip rate, tier change rate, confidence/strength deltas,
time-to-lock stability, PASS/actionable transitions.

### Market Comparison

Question: Does SharpStack add value beyond the market line/price?

Required data: market line, sportsbook line/odds where persisted, canonical
grades, result totals/sides.

Metrics: closing-line comparison when available, line-separation outcomes,
market-only baseline versus model-selected sample.

Current limitation: closing line is not a fully established canonical field for
all markets; use only where persisted and clearly label coverage.

## Dataset Requirements

| Question | Tables / Services | Min Sample | Date Range | Exclusions | Output |
|---|---|---:|---|---|---|
| Model Health baseline | canonical read model | 30 per bucket warning, 100 preferred | all available, then rolling | VOID/UNGRADEABLE for win rate | bucket table |
| Tier validation | canonical records | 100 per tier preferred | by model version | PASS unless evaluating pass rate | lift table |
| Calibration | canonical records | 200+ per market preferred | stable model-version window | non-probability fields for log loss | calibration curve |
| Moneyline ordering | canonical moneyline | 200+ | stable version | PUSH/VOID/UNGRADEABLE/PASS | strength buckets |
| Confidence ordering | canonical records | 100 per confidence band | stable version | missing confidence | confidence buckets |
| Totals projection error | totals snapshots + game results | 100+ totals with actual totals | stable totals version | missing projection/result | MAE/RMSE table |
| Threshold validation | canonical + raw pre-threshold fields | 300+ preferred | stable version | missing score inputs | sweep table |
| Feature contribution | components JSON + outcomes | 500+ preferred | stable version | missing key features unless testing coverage | ablation report |
| Drift | model runs + canonical/raw snapshots | 30 per time bucket minimum | rolling weekly/monthly | incomplete runs | drift dashboard |
| Stability | raw snapshots + episodes | 50+ streams | pregame windows | ineligible snapshots separate | transition matrix |

## Methodology Standards

- Always separate official canonical episodes from raw snapshots.
- Always group by sport, league, market, model name, model version, and date
  window before making performance claims.
- Report sample size with every metric.
- Treat PUSH, VOID, PENDING, and UNGRADEABLE explicitly.
- Use confidence intervals for win rates and tier comparisons.
- Use rolling windows for drift; do not compare unlike model versions without
  labeling the version change.
- Do not use log loss unless the field is a calibrated probability candidate.
- For totals, report projection error separately from recommendation hit rate.
- For KBO and MLB heuristic strength fields, start with ordering/calibration
  diagnostics before claiming probability quality.

## Metric Bands

These are framework defaults, not production pass/fail gates.

| Metric | Acceptable | Warning | Failure |
|---|---|---|---|
| Tier ordering | stronger tiers non-decreasing with sample | adjacent tiers tied/inconclusive | stronger tiers materially worse |
| Confidence monotonicity | mostly non-decreasing buckets | one adjacent inversion | broad inversion |
| Calibration error | low and stable for field type | persistent over/underconfidence | unusable probability interpretation |
| Totals MAE/RMSE | improves over baseline | equals baseline | worse than baseline |
| Drift | explainable by version/date | unexplained distribution shift | shift plus performance drop |
| Stability | late changes explainable by data/line movement | frequent unexplained tier changes | repeated selection churn near lock |

## Tooling Recommendations

Reuse first:

1. `CanonicalRecommendationReadModel` for official graded records.
2. `RecommendationAnalyticsService` for baseline Model Health buckets.
3. `RecommendationHistoryService` for history filters and episode timelines.
4. Existing `game_results` and grade services for truth and outcome status.

New tooling should be limited to read-only Phase 3 report scripts/services:

- `ValidationDatasetBuilder` around canonical/raw joins.
- `CalibrationReport` for bucketed confidence/strength analyses.
- `ProjectionErrorReport` for totals and future score projections.
- `ThresholdSweepReport` for offline what-if tables.
- `StabilityReport` for snapshot timeline churn.

No new infrastructure is required before these read-only reports.
