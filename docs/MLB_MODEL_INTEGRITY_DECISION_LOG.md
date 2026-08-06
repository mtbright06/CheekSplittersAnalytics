# MLB Model Integrity Decision Log

Phase 2A.2 scientific model review. Audit and analysis only; no production
logic was changed.

## Closure Recommendation

**MLB MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

The MLB moneyline model is certified as a coherent, deterministic,
winner-first heuristic. It is not certified as statistically optimal,
probability-calibrated, or empirically tuned.

## Decision Log

| Question | Current Decision | Evidence Available | Evidence Missing | Phase |
|---|---|---|---|---|
| Is the model winner-first? | Yes. Higher SharpScore selects the team before market value is considered. | `choose_side`, conviction thresholds, winner-first tests. | None for implementation integrity. | Phase 2 |
| Is market price used for the official MLB moneyline tier? | No. SSRP edge creates only market-value labels. | `mlb_moneyline_conviction_recommendation`, `market_value_classification`, winner-first tests. | None for implementation integrity. | Phase 2 |
| Are SharpScore component weights coherent? | Yes as normalized heuristic weights. | Weights sum to `1.00`; all components clamp to `0..100`. | Empirical fit, ablation, season-level validation. | Phase 3 |
| Are offense inputs independent? | Not proven. They are conceptually valid but overlapping. | RPG, OPS, HR/G, ISO, K%, BB% all represent run creation. | Correlation and ablation study on canonical data. | Phase 3 |
| Are starter inputs independent? | Not proven. Role-aware measurement is coherent; independence is not. | Starter-only aggregation and IP stabilization are implemented. | Correlation and ablation study for ERA, WHIP, K/BB, contact, efficiency fields. | Phase 3 |
| Is bullpen scoring conceptually valid? | Yes, but intentionally coarse. | Bullpen ERA/WHIP create bounded neutral scoring. | Validation of role, availability, fatigue, and leverage evidence as independent signal. | Phase 3 |
| Is home field mathematically placed correctly? | Yes as a small team-score component. | Home score `56`, away score `50`, weight `0.05`, effective edge `0.3`. | Empirical home-field magnitude validation. | Phase 3 |
| Is displayed model probability calibrated? | No. It is a model-strength transform. | Formula is `50 + diff * 0.75`, clipped to `40..70`; no calibration curve. | Calibration against locked canonical episodes. | Phase 3 |
| What does confidence mean? | Model conviction quality. | Formula combines base, score gap, data completeness, starter certainty. | Historical reliability and uncertainty calibration. | Phase 3 |
| Can confidence be used for tiering? | Yes as a coherent heuristic gate. | Thresholds require both model strength and confidence. | Validation of threshold lift and decision-rate tradeoffs. | Phase 3 |
| Is Hammer independent? | No. It is partially duplicated advisory confirmation. | Hammer consumes model strength plus starter/offense/bullpen/model confidence. | Incremental predictive value study after de-duplication. | Phase 3 |
| Is ranking winner-first? | Yes for market independence; ranking still blends tier, model strength, confidence, and Hammer. | Ranking weights exclude edge, EV, and price; tests cover market-price changes. | Empirical ranking utility validation. | Phase 3 |
| Are there conceptual defects requiring immediate code change? | No. | Audit found misleading terminology and empirical gaps, not incorrect math. | None for Phase 2 closure. | Phase 2 |

## Resolved Review Items

| Prior Item | Final Phase 2A.2 Classification |
|---|---:|
| Heuristic team-score weights | REVIEW |
| Overlapping offense inputs | REVIEW |
| Overlapping starter inputs | REVIEW |
| Coarse bullpen score | REVIEW |
| Displayed model probability | RENAME/CLARIFY |
| Confidence semantics | RENAME/CLARIFY |
| Unused confidence `odds` argument | RENAME/CLARIFY |
| Recommendation thresholds | REVIEW |
| Hammer double-counting risk | REVIEW |
| Decision-card confidence field | RENAME/CLARIFY |
| Ranking confidence fallback | RENAME/CLARIFY |

## Phase 2 Closure

Phase 2A.2 does not identify an internal mathematical contradiction, hidden
market leak, unreachable threshold, unbounded score path, or production defect
that requires immediate model-code correction. The remaining items are
terminology clarification and empirical validation work.

## Phase 3 Research Queue

1. Calibrate model win strength using locked canonical recommendation episodes.
2. Validate or refit SharpScore component weights out of sample.
3. Run feature correlation and ablation studies for offense and starter inputs.
4. Measure whether Hammer improves prediction after controlling for SharpScore.
5. Validate recommendation thresholds by tier, confidence, and decision rate.
6. Decide whether API/display fields should rename `model_probability` and
   distinguish SharpScore confidence from Hammer confidence.
