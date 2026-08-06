# MLB Totals Model Technical Audit Reference

Phase 2C.2 review. Audit and documentation first; no production behavior was
changed. The earlier Phase 2C "certified" wording was preliminary and is
superseded by this deeper resolution pass.

## Closure Recommendation

**TOTALS MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

Certification here means every conceptual issue from Phase 2C has been
resolved as either coherent implementation, terminology cleanup, or explicit
Phase 3 statistical validation. It does not mean the model is calibrated or
performance-certified.

## Files Audited

- `engine/mlb/game_builder.py`
- `engine/mlb/totals/totals_model.py`
- `engine/mlb/totals/expected_runs.py`
- `engine/mlb/totals/market.py`
- `engine/mlb/totals/recommendation.py`
- `engine/mlb/totals/park_factors.py`
- `engine/mlb/totals/helpers.py`
- `engine/mlb/totals/explanation.py`
- `engine/mlb/bullpen/bullpen_model.py`
- `engine/mlb/bullpen/quality.py`
- `engine/mlb/bullpen/fatigue.py`
- `engine/mlb/bullpen/game_adjustment.py`
- `engine/adapters/mlb_totals_adapter.py`
- `engine/core/recommendation.py`
- `engine/core/ranking.py`
- `dashboard/pages/dashboard_page.py`
- `tests/test_mlb_totals_winner_first.py`
- `tests/test_mlb_totals_adapter.py`
- shared winner-first, ranking, recommendation, and pregame tests

## Resolved REVIEW Matrix

| ID | Final | Evidence | Remaining Uncertainty | Phase Owner | Production Action |
|---|---:|---|---|---|---|
| TOTALS-005 confidence semantics | RENAME/CLARIFY | `confidence_from_data_points` is `40 + data_points * 4`, capped `40..78`. | It is not uncertainty or reliability. | Phase 3 docs/calibration | No formula change now. |
| TOTALS-006 projected total semantics | RENAME/CLARIFY | `projected_total = away_expected_runs + home_expected_runs + bullpen_adjustment`. | Not proven mean or median by outcomes. | Phase 3 statistical validation | Keep label; describe as deterministic expected-runs estimate. |
| TOTALS-007 offense overlap | REVIEW | RPG, OPS, and wRC+ all measure run creation but from run rate, base/power production, and context-adjusted offense. | Incremental value unproven. | Phase 3 feature study | No removal without evidence. |
| TOTALS-008 starter overlap | REVIEW | ERA, WHIP, and HR/9 are an intentional starter-quality ensemble. | Correlation and incremental value unproven. | Phase 3 feature study | No removal without evidence. |
| TOTALS-009 park/data points | PASS | Park affects both teams directly and contributes one unique data point after duplicate removal. | Static park table needs empirical validation. | Phase 3 park validation | No correction now. |
| TOTALS-010 separation double-use | PASS | Separation is both direction evidence and magnitude score; score gate prevents separation alone from causing action in low-quality cases. | Threshold lift needs outcome validation. | Phase 3 threshold validation | No correction now. |
| TOTALS-011 score weights | REVIEW | Score weights are explicit and bounded: separation `.40`, confidence `.30`, data quality `.20`, bullpen `.10`. | Empirical support absent. | Phase 3 weighting validation | No tuning now. |
| TOTALS-013 bullpen fatigue default | REVIEW | Missing `innings_last3` becomes `0.0` rested through adapter default. | Missing workload may understate uncertainty. | Provider/data quality sprint | No correction unless provider contract changes. |
| TOTALS-014 closer/setup default | REVIEW | Missing availability defaults true, preserving prior neutral behavior. | Availability is not proven. | Provider/data quality sprint | No correction unless availability source exists. |
| TOTALS-016 Hammer compatibility | RENAME/CLARIFY | Adapter maps totals recommendation score into generic `Recommendation.hammer_score` for Registry ranking. | Could be misread as true MLB Hammer. | Contract/UI cleanup | No broad contract redesign now. |

No item is classified DEFECT in Phase 2C.2.

## Offense Inputs

| Input | Raw Source | Normalization | Range | Weight | Meaning | Overlap Verdict |
|---|---|---|---:|---:|---|---:|
| Runs/game | team profile offense fields | `RPG - 4.45`, clamped `-1.25..1.25` | `-1.25..1.25` | one member of average | observed run output | REVIEW |
| wRC+ | team profile offense fields | `(wRC+ - 100) / 100 * 1.35`, clamped `-0.80..0.80` | `-0.80..0.80` | one member of average | context-adjusted offensive quality | REVIEW |
| OPS | team profile offense fields | `(OPS - .720) * 4.5`, clamped `-0.65..0.65` | `-0.65..0.65` | one member of average | on-base plus power production | REVIEW |

The combination is **REVIEW - plausible but empirically unverified**. It is
not a construction defect because each available input is averaged rather than
summed, which limits mechanical double counting. It remains correlated and
requires Phase 3 incremental-value testing.

## Starter Inputs

| Input | Normalization | Max Per-Team Influence | Max Game Influence | Typical Role | Verdict |
|---|---|---:|---:|---|---:|
| ERA | stabilized, `(ERA - 4.20) * .42`, clamp `-1.15..1.15` | one third of starter average | up to `2.30` before averaging effects | run prevention | REVIEW |
| WHIP | stabilized, `(WHIP - 1.30) * 1.35`, clamp `-0.75..0.75` | one third | up to `1.50` before averaging effects | baserunner prevention | REVIEW |
| HR/9 | stabilized, `(HR9 - 1.15) * .45`, clamp `-0.50..0.50` | one third | up to `1.00` before averaging effects | contact damage | REVIEW |

Starter metrics are an intentional ensemble, not accidental duplicate
arithmetic. ERA is outcome-level, WHIP is traffic, and HR/9 is damage shape.
They are correlated and need Phase 3 validation.

## Bullpen Semantics

Bullpen quality affects the projected total through run adjustment:

```text
quality = ERA*.50 + WHIP*.25 + last7 ERA*.25 transformed around league average
quality_run_adjustment = clamp(-weighted_quality * .60, -0.35, 0.35)
fatigue_adjustment = 0.00 / 0.10 / 0.25 / 0.45
availability_adjustment = closer_missing*.08 + setup_missing*.05
team_adjustment = clamp(sum, -0.50, 0.75)
game_adjustment = clamp(away + home, -1.25, 2.50)
```

Bullpen confidence affects recommendation conviction:

```text
team_bullpen_confidence starts 45
+18 season ERA, +15 season WHIP, +12 last7 ERA, +5 available quality
-2 closer unavailable, -2 setup unavailable
game_bullpen_confidence = average teams
recommendation contribution = game_bullpen_confidence * .10
```

Verdict: **PASS with REVIEW assumptions**. This is conceptually an
independent estimate plus uncertainty: bullpen quality changes the projection,
while bullpen confidence changes trust in the projection. It is not a defect.
Provider defaults for workload and availability remain REVIEW.

## Confidence Semantics

Totals confidence measures input completeness only:

```text
data_points = away_projection_points + home_projection_points - duplicated_park_point
confidence = clamp(40 + data_points * 4, 40, 78)
```

It does not measure projection certainty, disagreement, bullpen certainty,
historical reliability, or prediction uncertainty. Bullpen certainty is
separate and enters recommendation score at 10%.

Answer: a totals confidence of `75` means high available offense/starter/park
input coverage under the current completeness scale. Authoritative
terminology should be **projection_input_confidence** or **input_completeness
confidence** when contracts allow.

## Separation Double-Use

Representative complete-data examples with confidence `78`, data quality
`EXCELLENT`, and bullpen confidence `95`:

| Separation | Separation Score | Recommendation Score | Tier |
|---:|---:|---:|---|
| `0.39` | `51.7` | `72.6` | PASS |
| `0.40` | `52.0` | `72.7` | LEAN |
| `0.75` | `62.5` | `76.9` | BET |
| `1.25` | `77.5` | `82.9` | STRONG BET |
| `2.00` | `100.0` | `91.9` | STRONG BET |

Low-quality example with confidence `40`, data quality `LIMITED`, bullpen
confidence `45`:

| Separation | Score | Tier |
|---:|---:|---|
| `0.40` | `47.3` | PASS |
| `0.75` | `51.5` | PASS |
| `1.25` | `57.5` | PASS |
| `2.00` | `66.5` | LEAN |

Verdict: **PASS**. Separation can change tiers at gates, but score gates
prevent separation alone from automatically producing high-conviction plays.
This is reasonable monotonic confirmation, not excessive double emphasis.

## Recommendation Score Weights

| Component | Weight | Effective Range | Min Contribution | Max Contribution | Missing Behavior |
|---|---:|---:|---:|---:|---|
| Separation score | `.40` | `0..100` | `0` | `40` | `0` without verified line |
| Model confidence | `.30` | `40..78` normally, clamped `0..100` | `12` normal | `23.4` normal | computed from data points |
| Data quality | `.20` | `50..95` | `10` | `19` | unknown maps LIMITED `50` |
| Bullpen confidence | `.10` | `0..100` | `0` | `10` | neutral/partial confidence |

Verdict: **coherent heuristic**. Nominal weights broadly match effective
influence. Separation has the largest influence by design and does not dominate
solely because of scale.

## Thresholds

Totals thresholds:

```text
STRONG BET: separation >= 1.25 and score >= 82
BET:        separation >= 0.75 and score >= 72
LEAN:       separation >= 0.40 and score >= 64
PASS:       otherwise
```

Verdict: **PASS with Phase 3 validation**. Gates are monotonic, reachable,
non-overlapping, and have no dead branches. A small separation change at
`0.40`, `0.75`, or `1.25` can change labels only when score is already high
enough. Near-line handling is PASS below `0.40`.

## Park And Data Points

Park affects the projection directly for both teams:

```text
park_adjustment = clamp((park_factor - 1.00) * 4.0, -0.80, 0.80)
```

Park availability affects data points once, not twice. Each team projection
contains the same park input, then `calculate_game_data_points` subtracts one
duplicated park point. Missing park data uses neutral factor `1.00`, no
projection adjustment, and no park data point.

Verdict: **PASS** for internal accounting. Static park factors remain Phase 3
validation.

## Projected Total Terminology

Verdict: **RENAME/CLARIFY**. The best authoritative description is
**deterministic central expected-runs estimate**. The label
`projected_total` is acceptable. Avoid claiming calibrated mean, median, or
probability until Phase 3 validates distribution behavior. Per-team clamp
`2.25..7.25` and game floor `0.0` make it a bounded heuristic composite.

## Hammer Compatibility

Active consumers:

- `engine/adapters/mlb_totals_adapter.py` maps totals recommendation score to
  `Recommendation.hammer_score`.
- `engine/core/ranking.py` consumes `hammer_score` as a generic ranking input.
- Registry/Best Bets display may show the shared score field depending on
  presentation path.

Verdict: **RENAME/CLARIFY**. This is a safe compatibility alias for ranking,
not a true Hammer calculation. No broad contract redesign is required now, but
docs/UI should avoid presenting totals `hammer_score` as independent Hammer
conviction.

## Walkthroughs

Current artifacts have totals projections but no verified totals lines, so the
real current rows are PASS. The actionable examples below are synthetic
boundary examples using production formulas, clearly labeled as such.

| Case | Starter Total | Bullpen Adj | Projected | Line | Separation | Confidence | Bullpen Conf | Score | Tier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Synthetic strong OVER | `8.69` | `+0.57` | `9.26` | `8.00` | `+1.26` | `78` | `93` | `82.6` | STRONG BET OVER |
| Synthetic strong UNDER | `8.30` | `-0.11` | `8.19` | `9.50` | `-1.31` | `78` | `95` | `83.6` | STRONG BET UNDER |
| Current close/no-line PASS | `9.57` | `-0.47` | `9.10` | none | none | `78` | `95` | `0.0` | PASS |

## Comparison With MLB Moneyline

| Area | MLB Moneyline | MLB Totals | Classification |
|---|---|---|---:|
| Official authority | model win strength + model confidence | projected total vs verified line + confidence/data quality | intentional |
| Market role | SSRP edge display only | total line is the Over/Under comparison target; odds price display only | intentional |
| Probability semantics | bounded score, not calibrated probability | projected expected runs, not probability | aligned |
| Confidence semantics | separation/completeness/starter certainty | input completeness, bullpen confidence separate | RENAME/CLARIFY |
| Hammer | explicit advisory layer | no true Hammer; recommendation score compatibility alias | RENAME/CLARIFY |
| Ranking | tier, model strength, confidence, Hammer | tier plus recommendation score through shared contract | compatible |
| Explainability | structured model/Hammer reasons | projection, bullpen, market-line explanation | PASS |

## DEFECT Findings

No objective mathematical DEFECT was found. No production correction is
required now.
