# MLB Totals Model Integrity Decision Log

Phase 2C.2 audit only. No production behavior was changed. The earlier Phase
2C closure was preliminary and is superseded by this deeper review.

## Closure Recommendation

**TOTALS MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

## Decision Log

| Question | Current Decision | Evidence | Missing / Risk | Classification |
|---|---|---|---|---:|
| Is Totals Over/Under-first? | Yes. | Direction comes from `projected_total - market_total`. | Requires verified line; no current line means PASS. | PASS |
| Do odds, EV, sportsbook, or market quality affect authority? | No. | `build_totals_recommendation` ignores price, EV, sportsbook, staleness, and market quality. | Continue regression tests. | PASS |
| Is offense overlap a defect? | No. | RPG, OPS, and wRC+ are averaged, not summed; they represent output, production shape, and context-adjusted offense. | Incremental value unproven. | REVIEW |
| Is starter overlap a defect? | No. | ERA, WHIP, and HR/9 form a bounded ensemble of run prevention, traffic, and damage. | Incremental value unproven. | REVIEW |
| Is bullpen rewarded twice? | No defect. | Bullpen adjustment changes projection; bullpen confidence changes trust in projection. | Fatigue/availability defaults need provider validation. | REVIEW |
| What does confidence mean? | Input completeness. | `confidence_from_data_points` maps offense/starter/park input count to `40..78`. | Not reliability or uncertainty. | RENAME/CLARIFY |
| Is separation double-use excessive? | No. | Separation affects score and gates, but low-quality cases with large separation remain PASS/LEAN only. | Outcome validation of gates required. | PASS |
| Are recommendation weights coherent? | Yes as heuristic. | Components are bounded and active; separation has largest intended share. | Empirical support absent. | REVIEW |
| Are thresholds coherent? | Yes. | Gates are monotonic, reachable, non-overlapping; near-line below `0.40` is PASS. | Decision-rate validation deferred. | PASS |
| Is park counted correctly? | Yes. | Park adjustment affects both teams; confidence subtracts one duplicated park data point. | Static park table needs validation. | PASS |
| Is `projected_total` terminology accurate? | Mostly. | It is a deterministic expected-runs estimate with clamps. | Do not claim calibrated mean/median yet. | RENAME/CLARIFY |
| Is totals `hammer_score` safe? | Safe compatibility alias with naming risk. | Adapter maps recommendation score for shared ranking; no true Hammer calculation runs. | UI/docs must avoid true-Hammer wording. | RENAME/CLARIFY |
| Are current actionable walkthroughs available? | No. | Current card has totals projections but no verified total lines; Registry has no totals rows. | Re-run with actionable artifacts later. | REVIEW |

## Resolved Findings

- Offense overlap: **REVIEW**, not DEFECT. Bounded average prevents mechanical
  double counting, but Phase 3 must test incremental value.
- Starter overlap: **REVIEW**, not DEFECT. Bounded ensemble is conceptually
  defensible, but Phase 3 must test correlation and incremental value.
- Bullpen semantics: **REVIEW/PASS**. Projection adjustment and confidence are
  conceptually separate estimate/trust channels; defaults remain provider
  validation items.
- Confidence semantics: **RENAME/CLARIFY**. Formula should be described as
  input-completeness confidence.
- Separation double-use: **PASS**. It is monotonic confirmation, not an
  internally inconsistent double count.
- Recommendation-score weights: **REVIEW**. Coherent heuristic, empirically
  unvalidated.
- Thresholds: **PASS with Phase 3 validation**. No dead branches or overlap.
- Park/data points: **PASS**. Projection and confidence accounting are
  internally consistent.
- Projected-total terminology: **RENAME/CLARIFY**. Use deterministic central
  expected-runs estimate.
- Hammer compatibility: **RENAME/CLARIFY**. Safe alias, not true Hammer.

## Production Corrections

None. No objectively incorrect math, duplicated contribution by construction,
misleading authoritative field contract requiring immediate code change,
unreachable behavior, or inconsistent missing-data treatment was found.

## Phase 3 Ownership

1. Validate projected-total error distribution and whether it behaves like a
   calibrated mean.
2. Validate offense and starter feature incremental value.
3. Validate recommendation-score weights and tier thresholds by decision rate
   and outcomes.
4. Split or rename confidence contracts when consumer compatibility allows.
5. Clarify totals recommendation score versus true Hammer in shared UI/API
   language.
6. Re-run real walkthroughs when verified totals lines exist in current
   artifacts or canonical snapshots.
