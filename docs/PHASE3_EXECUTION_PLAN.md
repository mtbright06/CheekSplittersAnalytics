# Phase 3 Execution Plan

Planning and documentation only. Do not tune models or thresholds from this
plan without a separate approved implementation sprint.

## Execution Principles

1. Validate data before validating models.
2. Use canonical episode records for official performance claims.
3. Use raw snapshots for stability and timeline diagnostics only.
4. Validate ordering before optimizing thresholds.
5. Validate feature contribution before removing or reweighting inputs.
6. Every report must include sample size, date range, model version, market,
   and exclusions.

## Proposed Execution Order

### 1. Historical Data Readiness

Goal: prove the persisted dataset can support statistical claims.

Tasks:

- Count canonical episodes by sport, league, market, model version, tier, and
  grade status.
- Count raw snapshots by same dimensions.
- Verify joins from canonical records to game results.
- Verify components JSON key availability by model/version.
- Identify missing projections, confidence, market lines, and provider ids.

Reuse:

- `CanonicalRecommendationReadModel.list_graded_records()`
- `RecommendationAnalyticsService.model_health()`
- `RecommendationHistoryService`

Output:

- data coverage table
- missing-field report
- sample-size readiness labels

Sprint 81.2 readiness resolution:

- Treat pre-Sprint 79 actionable snapshots without episode links as legacy
  stability-only records, not canonical episode history.
- Treat PASS snapshots without active episode links as intentional persisted
  evidence, not attachment failures.
- Treat ACTIVE episodes without locked canonical snapshots as transitional;
  they may appear as `UNSPECIFIED` in analytics until lock time.
- Do not use explanation-text parsing as the trusted source for totals
  projected-run error. Projection-error validation should wait for structured
  projected-total persistence or an approved extraction contract.
- Group historical comparisons by model run and git commit before relying on
  semantic Registry version labels.

Why first: no calibration or threshold report is trustworthy if canonical
sample identity, result joins, or field coverage is incomplete.

### 2. Official Baseline Performance

Goal: establish current official performance without changing anything.

Tasks:

- Produce Model Health buckets by league, market, tier.
- Separate WIN/LOSS/PUSH/VOID/PENDING/UNGRADEABLE.
- Compare canonical-only counts against legacy/raw counts.

Metrics:

- sample size
- win percentage
- decision rate
- push/void/ungegradeable rates

Output:

- official baseline report
- legacy/raw comparison appendix

Why second: creates the shared baseline every later Phase 3 report references.

### 3. Recommendation Ordering

Goal: determine whether stronger model outputs rank better.

Questions:

- Do stronger tiers outperform weaker tiers?
- Does moneyline model strength order win probability?
- Does confidence order success?
- Does totals recommendation score order Over/Under success?

Metrics:

- bucket win rate
- rank correlation
- lift versus lower buckets
- confidence intervals

Output:

- tier ordering report
- strength/confidence bucket charts

Why third: ordering can be evaluated before proving calibrated probability.

### 4. Confidence Calibration

Goal: determine whether confidence values mean what labels imply.

Questions:

- Are confidence buckets monotonic?
- Where is SharpStack falsely confident?
- Does confidence mean different things by market/model?

Metrics:

- bucket accuracy
- overconfidence rate
- expected calibration error where applicable
- Brier score only for probability-like outputs

Output:

- confidence calibration report
- false-confidence segment list

Why fourth: confidence is used across presentation, ranking, and user trust.

### 5. Projection Error

Goal: evaluate projected quantities against actual quantities.

Markets:

- MLB totals projected total versus actual total
- future NHL/NFL score projections
- any model that emits numeric projected score/total

Metrics:

- MAE
- RMSE
- signed bias
- direction accuracy versus line
- error by line-separation bucket

Output:

- projection error report
- bias by market/team/date/model version

Readiness requirement: MLB totals projected total must be available as a
structured numeric field before official projection-error conclusions are
published. Current persisted totals rows preserve market line, separation,
confidence, and explanatory projection text, but not a first-class
`projected_total` value.

Why fifth: projection error is distinct from recommendation hit rate and must
be understood before tuning totals thresholds.

### 6. Threshold Validation

Goal: test whether current thresholds create useful decision rates and lift.

Tasks:

- Offline threshold sweeps for model strength, confidence, separation, and
  recommendation score.
- Compare current thresholds against adjacent alternatives.
- Report decision-rate tradeoffs.

Metrics:

- precision/hit rate
- decision rate
- lift
- false-positive/false-negative style tables where applicable

Output:

- threshold validation report
- recommended candidates for future implementation sprint, if evidence exists

Why sixth: threshold work must follow ordering and calibration. It is the first
step that may later justify production changes, but this plan does not make
them.

### 7. Feature Contribution

Goal: determine whether each major input improves prediction.

Tasks:

- Extract feature families from components JSON by model/version.
- Run ablation or nested-model comparisons offline.
- Control for date range, market, data quality, and model version.

Metrics:

- incremental lift
- permutation importance
- ablation change in MAE/Brier/bucket accuracy
- coverage-adjusted performance

Output:

- feature contribution report by model
- keep/review/remove candidates for future sprint

Why seventh: feature studies need enough sample and stable baseline metrics.

### 8. Drift Detection

Goal: identify whether model behavior or performance changes over time.

Tasks:

- Compare distributions of strength, confidence, tier, score, and projection
  error over rolling windows.
- Segment by model version and git commit.
- Detect unexplained shifts after provider or model changes.

Metrics:

- rolling win rate
- rolling MAE/RMSE
- population stability index
- distribution shift by field

Output:

- drift report
- version-change appendix

Why eighth: drift is meaningful only after baseline metrics and field
semantics are established.

### 9. Stability And Replay

Goal: assess repeated-build recommendation stability before lock.

Tasks:

- Use raw snapshots attached to episodes.
- Exclude pre-lifecycle unlinked actionable snapshots from episode-timeline
  stability metrics; analyze them only as legacy raw snapshot distributions.
- Include PASS snapshots as withdrawal evidence only when they are attached to
  an episode.
- Measure selection flips, tier changes, confidence deltas, and PASS/actionable
  transitions.
- Compare changes by time before start and by market-line movement.

Metrics:

- flip rate
- tier-change rate
- average confidence/strength delta
- time-to-lock stability

Output:

- stability report
- replay scenario matrix

Why ninth: stability depends on raw snapshot timelines and should not be mixed
with official locked performance.

## Required Datasets By Model Family

### MLB / KBO Moneyline

Required:

- canonical records with selection side, winner side, grade
- model strength/probability
- model confidence
- tier
- Hammer or compatibility score
- model version and git commit
- provider game id and scheduled start

Primary questions:

- strength ordering
- confidence ordering
- tier lift
- false confidence
- drift

### MLB Totals

Required:

- canonical totals records or raw totals snapshots with verified lines
- projected total
- market line
- recommendation score
- confidence and data quality
- bullpen confidence
- game result total score

Primary questions:

- projection MAE/RMSE
- Over/Under direction accuracy
- separation threshold lift
- score ordering
- confidence/data-quality relationship

### NHL / NFL / Future Models

Required before certification:

- canonical episode lifecycle
- immutable snapshots with model version
- result ingestion with stable provider ids
- grade service
- model strength/confidence/tier fields
- market line/selection fields where applicable

Primary questions:

- same ordering/calibration/threshold/drift/stability sequence
- sport-specific projection error if numeric projections exist

## Minimum Sample Guidance

| Report | Minimum To Run | Preferred For Decisions |
|---|---:|---:|
| Data readiness | any sample | all available |
| Model Health | 30 per bucket | 100+ per bucket |
| Tier ordering | 50 per tier | 100+ per tier |
| Calibration | 200 per market | 500+ per market |
| Totals projection error | 100 totals | 300+ totals |
| Threshold sweeps | 300 records | 1,000+ records |
| Feature contribution | 500 records | 2,000+ records |
| Drift | 30 per window | 100+ per window |
| Stability | 50 streams | 200+ streams |

Small samples may be reported as exploratory only.

## Tooling Recommendations

Do not create new infrastructure first. Add read-only report modules only when
the existing services cannot answer the question.

Recommended sequence:

1. Extend existing services only with read-only dataset builders.
2. Create CLI scripts for Phase 3 reports after dataset shapes are stable.
3. Add dashboard presentation only after report outputs are reviewed.
4. Add production threshold/model changes only in later approved sprints.

Candidate read-only tools:

- `tools_phase3_data_readiness.py`
- `tools_phase3_model_ordering.py`
- `tools_phase3_confidence_calibration.py`
- `tools_phase3_totals_projection_error.py`
- `tools_phase3_threshold_sweep.py`
- `tools_phase3_stability.py`

These names are recommendations, not implemented deliverables.

## Completion Criteria

Phase 3.0 is complete when:

- all existing validation data sources are inventoried,
- every validation question has required data and methodology,
- execution order is documented,
- no production behavior has changed,
- future implementation work is split into read-only report sprints before any
  model-tuning sprint.
