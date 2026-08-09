# SharpStack Model Validation Report

Sprint 78.2 audit date: 2026-08-05.

This report is an empirical evidence audit only. It does not tune weights,
thresholds, recommendation logic, grading, or persistence.

## Executive Verdict

The current Winner-First implementation is conceptually aligned with the
product rule, but it is not yet empirically validated. The post-reset
recommendation database contains current-engine snapshots, but every
post-reset grade is still `PENDING`. That means current outcomes cannot yet
support accuracy, calibration, monotonicity, or tier-performance claims.

Major conclusion classification:

| Area | Classification | Reason |
|---|---:|---|
| MLB moneyline current-engine performance | UNVALIDATED | 45 post-reset snapshots, 0 resolved grades |
| MLB totals current-engine performance | UNVALIDATED | 45 post-reset snapshots, 0 resolved grades |
| KBO current-engine performance | UNVALIDATED | 0 post-reset KBO snapshots found |
| Hammer monotonicity | UNVALIDATED | Hammer values exist, but no resolved outcomes |
| Recommendation tiers | UNVALIDATED | Tiers exist, but no resolved outcomes |
| Current weights/thresholds | UNVALIDATED | No resolved current-engine sample |
| Historical raw game results | PROMISING | 202 MLB results exist, but need safe joins to current projections |
| Legacy recommendation history | LEGACY/NON-COMPARABLE | Reset after Winner-First transition |

## Data Sources Found

| Source | Date range observed | Sample size | Classification | Notes |
|---|---:|---:|---|---|
| Azure `recommendations` prediction snapshots | 2026-08-05 13:32:03 UTC to 2026-08-05 13:52:19 UTC | 90 | usable for current-engine validation after games resolve | 45 MLB moneyline, 45 MLB totals |
| Azure `prediction_snapshot_grades` | current | 90 | incomplete | All 90 are `PENDING` |
| Azure `game_results` | current table contents | 202 | usable for raw outcome joins | 187 `FINAL`, 15 `SCHEDULED`; MLB only |
| Azure `recommendation_grades` legacy settlements | current | 0 | unavailable | No legacy settlement rows |
| Azure `model_runs` | 2026-08-05 13:32:03 UTC to 2026-08-05 13:52:28 UTC | 3 | usable for provenance | All completed |
| Azure active slots | current | 30 | incomplete for performance | Lifecycle state, not outcome evidence |
| Azure activation events | current | 150 | incomplete for performance | Lifecycle state, not outcome evidence |
| `output/cards/recommendation_registry.json` | 2026-08-04 23:53:49 | 0 | incomplete | Current local Registry is empty |
| `output/cards/decision_card.json` | 2026-08-05 03:53:49 UTC | 15 decisions | usable only for raw current-card inspection | No outcomes attached |
| `output/cards/mlb_card.json` | 2026-08-05 02:49:50 UTC | 15 games | usable only for raw current-card inspection | No resolved grading attached |
| `output/cards/kbo_card.json` | 2026-08-04 22:48:59 | 5 games | usable only for raw current-card inspection | No outcome/grade join found |
| `output/cards/first5_card.json` | 2026-08-04 22:49:55 | 15 games | out of Sprint 78.2 market scope except Hammer context | No outcome/grade join found |
| `output/cards/first5_market_card.json` | 2026-08-04 22:49:55 | 15 games | out of scope for this validation | Market-edge sprint deferred |
| odds caches | current local cache | MLB ML 302, MLB totals 314, KBO ML 80 | market provenance only | Not outcome evidence |
| `output/audit/component_distribution.json` | current local audit | component summary | usable for component distribution only | Does not include outcomes |
| local `data/` directory | not present | 0 | unavailable | No local historical data tree |
| local SQLite/CSV/JSONL history files | none found | 0 | unavailable | No local database/history export found |

## Current Post-Reset Snapshot Sample

Azure current-engine snapshots:

| Market | Snapshots | Grade status |
|---|---:|---|
| MLB moneyline | 45 | 45 pending |
| MLB totals | 45 | 45 pending |
| KBO moneyline | 0 | none |

MLB moneyline tiers in current snapshots:

| Tier | Count | Outcome sample |
|---|---:|---:|
| PASS | 21 | 0 resolved |
| LEAN | 18 | 0 resolved |
| PLAYABLE | 6 | 0 resolved |

MLB totals tiers in current snapshots:

| Tier | Count | Outcome sample |
|---|---:|---:|
| PASS | 15 | 0 resolved |
| LEAN | 7 | 0 resolved |
| BET | 23 | 0 resolved |

## MLB Moneyline Findings

Required measurements:

| Measurement | Result | Classification |
|---|---|---|
| Overall winner accuracy | unavailable, 0 resolved current-engine grades | UNVALIDATED |
| Accuracy by model-probability bucket | unavailable | UNVALIDATED |
| Accuracy by recommendation tier | unavailable | UNVALIDATED |
| Accuracy by Hammer bucket | unavailable | UNVALIDATED |
| Favorite vs underdog | unavailable; current snapshots do not expose a resolved odds/result sample | UNVALIDATED |
| Home vs away | unavailable without resolved side/result joins | UNVALIDATED |
| Probability calibration | unavailable | UNVALIDATED |
| Higher probability monotonicity | unavailable | UNVALIDATED |
| Higher Hammer monotonicity | unavailable | UNVALIDATED |

Conceptual status:

- The current code is winner-first after Sprint 78.1.
- The current weights and thresholds are not empirically supported yet.
- Existing raw MLB game results are promising for future retrospective testing,
  but a safe projection-to-result join must be built before using them.

Component review:

| Component | Evidence status | Comment |
|---|---|---|
| Starting pitching | UNVALIDATED | Important conceptually; no resolved component/outcome table yet |
| Offense | UNVALIDATED | No resolved component/outcome table yet |
| Bullpen | UNVALIDATED | No resolved component/outcome table yet |
| Home field | UNVALIDATED | No resolved home/away outcome split yet |
| Confidence/data completeness | UNVALIDATED | Current implementation is market-independent, but not outcome-calibrated |

No inverted or double-counted signal is empirically confirmed from the
available data.

## KBO Moneyline Findings

Required measurements:

| Measurement | Result | Classification |
|---|---|---|
| Overall winner accuracy | no post-reset KBO snapshots | UNVALIDATED |
| Accuracy by model-score band | unavailable | UNVALIDATED |
| Accuracy by recommendation tier | unavailable | UNVALIDATED |
| Accuracy by confidence band | unavailable | UNVALIDATED |
| Favorite vs underdog | unavailable | UNVALIDATED |
| Home vs away | unavailable | UNVALIDATED |
| Before/after KBO logic changes | unavailable from current post-reset data | UNVALIDATED |

Recent-decline question:

The recent KBO decline cannot be linked to edge contamination from available
evidence. Sprint 78.1 removed the verified real-market finalization leak, but
there are no resolved post-fix KBO snapshots and no comparable post-reset KBO
history in the current database.

Classification: UNVALIDATED, with no confirmed causal link.

## MLB Totals Findings

Required measurements:

| Measurement | Result | Classification |
|---|---|---|
| OVER/UNDER accuracy | unavailable, 0 resolved current-engine grades | UNVALIDATED |
| Accuracy by projection separation | unavailable | UNVALIDATED |
| Accuracy by recommendation tier | unavailable | UNVALIDATED |
| Accuracy by model confidence | unavailable | UNVALIDATED |
| Accuracy by data-quality label | unavailable | UNVALIDATED |
| Accuracy by bullpen confidence | unavailable | UNVALIDATED |
| Projected total error | unavailable | UNVALIDATED |
| Mean absolute error | unavailable | UNVALIDATED |
| OVER/UNDER bias | unavailable | UNVALIDATED |
| Larger separation monotonicity | unavailable | UNVALIDATED |

True side-probability calibration is not currently possible from the available
resolved current-engine data. The totals model stores projection, line, and
selection fields, but all current grades are pending.

## Hammer Score Findings

Hammer bucket validation requires resolved outcomes. Current snapshots include
Hammer values, but none have a win/loss/push result.

| Requirement | Result | Classification |
|---|---|---|
| 80+ outperform 70-79 | unavailable | UNVALIDATED |
| 70-79 outperform 60-69 | unavailable | UNVALIDATED |
| lower bands do not outperform higher bands | unavailable | UNVALIDATED |
| sport/market mix by Hammer band | partially inspectable | PROMISING |
| compression/generosity | cannot judge without outcomes | UNVALIDATED |
| cross-market comparability | cannot judge without outcomes | UNVALIDATED |

Conceptually, Hammer is now market-independent and bounded. Empirically, it is
not yet proven well ordered.

## Recommendation Tier Findings

Current post-reset tier counts exist, but there are no resolved outcomes.

| Market | Tier | Count | Outcome evidence | Classification |
|---|---|---:|---:|---|
| MLB moneyline | PASS | 21 | 0 resolved | UNVALIDATED |
| MLB moneyline | LEAN | 18 | 0 resolved | UNVALIDATED |
| MLB moneyline | PLAYABLE | 6 | 0 resolved | UNVALIDATED |
| MLB totals | PASS | 15 | 0 resolved | UNVALIDATED |
| MLB totals | LEAN | 7 | 0 resolved | UNVALIDATED |
| MLB totals | BET | 23 | 0 resolved | UNVALIDATED |

No tier can be called validated. No tier can be called defective from outcome
evidence yet.

## Calibration Tables

Calibration tables are intentionally not populated because there are no
resolved current-engine grades.

Minimum future tables:

| Table | Required fields |
|---|---|
| Moneyline probability calibration | predicted probability bucket, wins, losses, win rate, average probability |
| Moneyline tier performance | tier, wins, losses, pushes, win rate |
| Totals separation calibration | separation bucket, over/under side, wins, losses, pushes, win rate |
| Totals projection error | projected total, actual total, error, absolute error |
| Hammer monotonicity | Hammer bucket, market mix, wins, losses, win rate |
| KBO ordinal calibration | model-score band, wins, losses, win rate |

## Concerns

| Finding | Classification | Detail |
|---|---:|---|
| No resolved current-engine grades | CONCERN | The system cannot yet support tuning or validation claims |
| No post-reset KBO snapshots | CONCERN | KBO decline cannot be evaluated with current comparable data |
| Local Registry is empty | CONCERN | Local artifacts alone cannot validate current recommendations |
| Current sample is one day / three runs | CONCERN | Even after resolution, 90 snapshots is too small for stable calibration |
| Legacy history reset | expected limitation | Correct product decision, but it removes comparable historical recommendation performance |

## Defects

No new implementation or data defect was confirmed by this audit.

The absence of resolved grades is a validation blocker, not a model defect.

## Are Current Weights Defensible?

Conceptually defensible: yes, with caution.

Empirically defensible: not yet.

The winner-first structure now matches the product philosophy, but the actual
weights, thresholds, confidence buckets, and Hammer tiers need resolved
post-reset outcomes before they can be defended statistically.

## Immediate Production Fix Required?

No immediate production logic fix is required from this audit.

The next production work should be evidence plumbing, not tuning:

1. Ensure daily post-game grading converts pending snapshots to resolved grades.
2. Add a read-only backtest report that joins current-engine snapshots to final
   results and produces the tables listed above.
3. Accumulate enough post-reset samples before tuning thresholds.

## Recommended Tuning Sequence

Do not tune yet. Recommended sequence:

1. Build a read-only validation query/report over resolved current-engine
   snapshots.
2. Confirm MLB moneyline probability calibration by bucket.
3. Confirm MLB totals projection error and separation monotonicity.
4. Confirm Hammer monotonicity within each market before comparing across
   markets.
5. Evaluate KBO only after post-78.1 KBO snapshots are generated and graded.
6. Tune market-specific thresholds first; tune Hammer weights last.

## Existing Tests Relevant To This Audit

Existing focused tests cover grading, persistence, analytics, and the
winner-first invariants, but they use synthetic fixtures rather than resolved
production history:

- `tests/test_prediction_snapshot_grading_service.py`
- `tests/test_game_result_ingestion_service.py`
- `tests/test_daily_persistence_service.py`
- `tests/test_recommendation_analytics_service.py`
- `tests/test_recommendation_analytics.py`
- `tests/test_recommendation_history_service.py`
- `tests/test_winner_first_shared_integrity.py`
- `tests/test_kbo_confidence.py`
- `tests/test_mlb_recommendation_authority.py`
- `tests/test_mlb_totals_winner_first.py`

## Canonical Analytics Note

As of Sprint 79.4, official validation tables should be built from canonical
recommendation episodes and canonical grades, not raw snapshot grades.
Prediction snapshots remain timeline/audit evidence, but repeated model builds
must not inflate win/loss, calibration, Hammer, tier, league, or market
summaries.

Canonical-empty behavior is intentional: if no `GRADED` canonical episodes are
available, validation reports should show no official sample rather than
falling back to legacy `prediction_snapshot_grades`.
