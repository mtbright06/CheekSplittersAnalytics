# MLB Totals Model Integrity Decision Log

Phase 2C audit only. No production behavior was changed.

## Closure Recommendation

**TOTALS MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

## Decision Log

| Question | Current Decision | Evidence | Missing / Risk | Classification |
|---|---|---|---|---:|
| Is Totals Over/Under-first? | Yes. | Direction comes from `projected_total - market_total`. | Requires verified line; no current line means PASS. | PASS |
| Do odds or EV affect authority? | No. | `build_totals_recommendation` ignores price, EV, sportsbook, and staleness. | Continue regression tests. | PASS |
| Is `projected_total` coherent? | Yes as a deterministic expected-runs estimate. | Sum of team run projections plus bullpen adjustment. | Not proven calibrated mean/median. | REVIEW |
| What does confidence mean? | Input completeness. | `confidence_from_data_points` maps data points to `40..78`. | Historical reliability and uncertainty are not measured. | RENAME/CLARIFY |
| Are weights coherent? | Deterministic and bounded. | Projection and recommendation weights are explicit. | Empirical support absent. | REVIEW |
| Are thresholds coherent? | Yes. | Separation and score gates are monotonic and reachable. | Decision-rate and calibration validation deferred. | PASS |
| Is market total a leakage risk? | No for price; line is required model comparison target. | Direction needs the line, but not odds price or EV. | Explain line versus price clearly. | PASS |
| Is bullpen integrated safely? | Yes with review items. | Missing quality is neutral; confidence tracked separately. | Fatigue/availability default assumptions need validation. | REVIEW |
| Does Registry ranking preserve authority? | Compatible. | Adapter maps recommendation score to `hammer_score`, edge/EV null. | `hammer_score` label is semantically overloaded. | REVIEW |
| Are there current real actionable examples? | No. | Current card has projections but no verified total lines; Registry has no totals rows. | Need future artifact with lines for walkthrough validation. | REVIEW |

## Phase 3 Validation Items

1. Validate whether `projected_total` behaves like a calibrated mean run total.
2. Validate recommendation-score weights and separation thresholds by outcome
   and decision rate.
3. Quantify overlap among offense RPG, OPS, and wRC+.
4. Quantify overlap among starter ERA, WHIP, and HR/9.
5. Decide whether totals confidence should remain input completeness or split
   into completeness and prediction uncertainty.
6. Rename or isolate Registry `hammer_score` usage for totals if a true totals
   Hammer layer is not intended.
7. Re-run walkthrough audit when verified totals lines are present in current
   artifacts.

## Recommendation

The MLB Totals model can proceed as a coherent projection-first heuristic, but
should not be described as calibrated or statistically certified until Phase 3
validation is complete.
