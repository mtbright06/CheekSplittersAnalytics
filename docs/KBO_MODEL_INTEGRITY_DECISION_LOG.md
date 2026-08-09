# KBO Model Integrity Decision Log

Phase 2B audit, updated by Sprint 80.1 correctness repair and Sprint 80.2
normalization resolution.

## Closure Recommendation

**KBO MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

## Decision Log

| Question | Current Decision | Evidence | Missing / Risk | Classification |
|---|---|---|---|---:|
| Is KBO winner-first? | Yes. | `KBOModel.score` selects away on positive weighted score, home on negative weighted score, and no side on zero. | Phase 3 should validate the score contract statistically. | PASS |
| Does market data affect recommendation tier? | No. | `finalize` computes edge separately and tiers from model score. | Continue regression tests. | PASS |
| Does market data affect confidence? | No in final output. | `finalize` replaces confidence with normalized model score. | Initial `ConfidenceEngine.calculate` path is overwritten and mostly diagnostic. | PASS |
| Is displayed probability calibrated? | No. | Formula is ordinal score `50 + weighted_score * 8`. | Needs rename/clarification and Phase 3 calibration. | RENAME/CLARIFY |
| What does 75 confidence mean? | Relative model-score strength. | `_model_strength_confidence` maps `42.4..59.6` to `0..100`. | Does not represent historical reliability. | RENAME/CLARIFY |
| Are weights coherent? | Configured weights are applied exactly. | Sprint 80.2 active normalization was reverted as unsafe against fixed confidence bounds and tier thresholds. Neutral bullpen/recent-form components retain reserved configured weights. | Compressed practical range and tier reachability remain Phase 3 validation items. | REVIEW |
| Is bullpen measured correctly? | Intentionally neutral. | `BullpenCalculator` returns `0.0` rather than a fabricated heuristic. | Future activation requires genuine KBO bullpen ERA, WHIP, or equivalent relief-quality data. | PASS |
| Is recent form measured correctly? | Intentionally neutral. | `RecentFormCalculator` returns `0.0` rather than a fabricated heuristic. | Future activation requires genuine KBO recent-results or rolling-performance data. | PASS |
| Does KBO use Hammer? | No true Hammer calculation. | Adapter maps confidence into `hammer_score`. | Ranking/Best Bets compatibility can mislead. | REVIEW |
| Are recommendation thresholds internally coherent? | Yes. | Thresholds are monotonic and reachable. | Need Phase 3 outcome validation. | PASS |

## Sprint 80.1 Correctness Repair

Sprint 80.1 resolved the objective defects without tuning:

1. Selection authority now derives from final weighted model-score direction,
   independent of row order, dataframe index, game position, or iteration
   order.
2. Bullpen is neutral `0.0` because no already-wired genuine KBO bullpen
   statistic exists in the current scoring pipeline.
3. Recent form is neutral `0.0` because no already-wired genuine KBO recent
   form input exists in the current scoring pipeline.
4. KBO now emits `model_strength` and `model_confidence` compatibility aliases
   while preserving numeric values and existing downstream contracts.

## Future Activation Requirements

Bullpen may be reactivated only after a real KBO bullpen data source is present
in the pipeline, such as team bullpen ERA, team bullpen WHIP, or a documented
relief-quality equivalent with provenance and missing-data tests.

Recent form may be reactivated only after genuine recent KBO team-performance
data is present in the pipeline, with a documented lookback window,
normalization rule, and duplicate-signal review.

KBO Hammer ownership remains a future architecture decision: either implement a
true KBO Hammer layer or keep the current model-strength compatibility mapping
explicitly labeled.

## Sprint 80.2 Normalization Resolution

**ACTIVE WEIGHT NORMALIZATION REVERTED**

Sprint 80.2 verification found that active-weight normalization widened the KBO
ordinal score range from the established confidence/tier scale. The
normalization was therefore not safe as a narrow correctness correction and was
reverted.

```text
starter_score * 0.35
+ offense_score * 0.25
+ 0.0 * 0.15
+ 0.0 * 0.10
```

Bullpen and recent-form contributions are intentionally neutral while their
configured weights remain reserved. The active model therefore currently has a
narrower practical score range. Threshold and confidence calibration will be
evaluated during KBO statistical integrity work rather than altered without
evidence.
