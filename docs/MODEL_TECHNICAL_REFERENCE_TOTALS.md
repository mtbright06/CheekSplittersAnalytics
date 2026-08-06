# MLB Totals Model Technical Audit Reference

Phase 2C audit. No production behavior was changed.

## Closure Recommendation

**TOTALS MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

The model is projection-first and market-price independent. It requires a
verified pregame total line, derives OVER/UNDER direction from projected total
minus line, and scores recommendations from model separation, input
completeness confidence, data quality, and bullpen confidence. No objective
mathematical defect requiring code change was found.

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
- `tests/test_mlb_totals_bullpen.py`
- shared winner-first, ranking, recommendation, and pregame tests

## PASS / REVIEW / DEFECT Matrix

| ID | Classification | Finding |
|---|---:|---|
| TOTALS-001 | PASS | Direction authority is `projected_total - market_total`: positive OVER, negative UNDER, zero/no line PASS. |
| TOTALS-002 | PASS | Recommendation score excludes odds price, sportsbook, EV, market quality, and staleness. |
| TOTALS-003 | PASS | Verified pregame line is required before any actionable totals recommendation. |
| TOTALS-004 | PASS | `projected_total` is explainable from starter/team projections plus bullpen adjustment. |
| TOTALS-005 | RENAME/CLARIFY | `confidence` measures input completeness, not prediction probability or historical reliability. |
| TOTALS-006 | REVIEW | `projected_total` is best described as expected runs/mean estimate, but no calibration evidence proves mean or median behavior. |
| TOTALS-007 | REVIEW | Offense RPG, OPS, and wRC+ are partially overlapping run-production signals. |
| TOTALS-008 | REVIEW | Starter ERA, WHIP, and HR/9 overlap run prevention and contact-quality effects. |
| TOTALS-009 | REVIEW | Park factor is added to both teams, so one duplicated park data point is removed from confidence; projection influence remains intentionally doubled at game level. |
| TOTALS-010 | REVIEW | Separation is used both as a score component and as tier gate; monotonic but potentially double-counted. |
| TOTALS-011 | REVIEW | Recommendation score uses fixed `0.40/0.30/0.20/0.10` weights without empirical support in code/docs. |
| TOTALS-012 | PASS | Score components are active; no dead or inactive weights were found. |
| TOTALS-013 | REVIEW | Bullpen fatigue defaults missing `innings_last3` to rested `0.0`, which may understate uncertainty if provider data is absent. |
| TOTALS-014 | REVIEW | Closer/setup availability defaults to available, a conservative compatibility choice but not proof of availability. |
| TOTALS-015 | PASS | Shared Registry adapter carries totals recommendation score for ranking and leaves edge/EV null. |
| TOTALS-016 | REVIEW | Adapter maps totals recommendation score into generic `hammer_score`; this is compatibility naming, not MLB Hammer. |
| TOTALS-017 | PASS | Current artifact with no totals lines correctly produces PASS despite model projections. |

## Weight Findings

Projection weighting:

| Stage | Weight / Scale | Effective Influence | Audit |
|---|---:|---:|---:|
| Offense RPG | average member; clamp `-1.25..1.25` | up to one third of offense adjustment | REVIEW |
| Offense wRC+ | average member; clamp `-0.80..0.80` | up to one third of offense adjustment | REVIEW |
| Offense OPS | average member; clamp `-0.65..0.65` | up to one third of offense adjustment | REVIEW |
| Starter ERA | average member; clamp `-1.15..1.15` | up to one third of starter adjustment | REVIEW |
| Starter WHIP | average member; clamp `-0.75..0.75` | up to one third of starter adjustment | REVIEW |
| Starter HR/9 | average member; clamp `-0.50..0.50` | up to one third of starter adjustment | REVIEW |
| Park | `(factor - 1.0) * 4.0`, clamp `-0.80..0.80` | added to both teams | PASS/REVIEW |
| Home field | `+0.12` | home team only | REVIEW |
| Bullpen quality | ERA `.50`, WHIP `.25`, last7 `.25` | run adjustment clamp `-0.35..0.35` per team | PASS/REVIEW |
| Bullpen fatigue | bucketed `0..0.45` | per team | REVIEW |
| Availability | closer `+0.08`, setup `+0.05` | per team | REVIEW |

Recommendation weighting:

| Component | Weight | Notes | Audit |
|---|---:|---|---:|
| Model separation | `0.40` | `40 + runs * 30`, clamped | PASS/REVIEW |
| Model confidence | `0.30` | input-completeness confidence `40..78` | RENAME/CLARIFY |
| Data quality | `0.20` | categorical score `50..95` | REVIEW |
| Bullpen confidence | `0.10` | game average bullpen confidence | PASS/REVIEW |

No inactive recommendation-score weights were found. Missing components are
generally omitted from averages or use neutral fallbacks rather than adding
zero-weight dead branches.

## Feature-Overlap Findings

| Relationship | Classification | Finding |
|---|---:|---|
| RPG vs OPS/wRC+ | PARTIAL OVERLAP | All measure offense run creation from different views. |
| Starter ERA vs WHIP/HR9 | PARTIAL OVERLAP | ERA reflects run prevention partly explained by baserunners and home runs. |
| Starter projection vs projected total | LIKELY DOUBLE COUNT IF TREATED SEPARATELY | Projected total includes starter projection by construction. |
| Bullpen adjustment vs bullpen confidence | PARTIAL OVERLAP | Bullpen inputs affect run total and separately influence recommendation quality. |
| Projected total vs model separation | DERIVED | Separation is projected total minus line. |
| Model separation vs recommendation score/tier | PARTIAL OVERLAP | Separation is both a weighted score component and mandatory tier gate. |
| Data points vs data quality | DERIVED | Data quality label is derived from data point count. |
| Model confidence vs data quality | PARTIAL OVERLAP | Confidence and data quality both reflect input completeness. |
| Market total vs sportsbook odds | INDEPENDENT IN AUTHORITY | Line is required for direction; price is display only. |

## Projection Semantics

`projected_total` means a deterministic expected-runs estimate:

```text
away_expected_runs + home_expected_runs + combined_bullpen_adjustment
```

It is built from league-average team runs, offense quality, opposing starter
quality, park environment, home field, and bullpen run adjustment. It does not
include weather, confirmed lineups, umpire, defensive alignment, extra-inning
distribution, or simulated run variance.

Verdict: **RENAME/CLARIFY** only if UI/docs call it probability. Otherwise
coherent as projected/expected total.

## Confidence Verdict

Totals confidence is not prediction certainty. It is input completeness:

```text
40 + data_points * 4, clamped to 40..78
```

`75 confidence` means high source/input coverage within the current totals
projection pipeline. It does not mean 75% chance, 75% historical reliability,
or calibrated uncertainty.

Verdict: **RENAME/CLARIFY**.

## Recommendation-Scoring Verdict

The score is monotonic and bounded. Separation, model confidence, data quality,
and bullpen confidence all increase or preserve recommendation score. No
market-price fields affect it. The only review item is duplication: separation
controls both the score and the tier gate, while data quality and confidence
are closely related completeness measures.

Verdict: **PASS with REVIEW items**.

## Threshold Verdict

Thresholds are reachable under complete data:

```text
0.40+ runs and score 64+ -> LEAN
0.75+ runs and score 72+ -> BET
1.25+ runs and score 82+ -> STRONG BET
```

The gates are monotonic and non-overlapping. Phase 3 should validate whether
the score thresholds and run-separation thresholds produce useful decision
rates and outcome calibration.

Verdict: **PASS with Phase 3 validation items**.

## Comparison With MLB Moneyline

| Area | MLB Moneyline | MLB Totals | Classification |
|---|---|---|---:|
| Official authority | model win strength + model confidence | projected total vs line + confidence/data quality | intentional |
| Market role | SSRP edge display only | total line defines Over/Under separation; price display only | intentional |
| Probability semantics | bounded score, not calibrated probability | projected expected runs, not probability | aligned |
| Confidence semantics | separation/completeness/starter certainty | input completeness, bullpen confidence separate | different but coherent |
| Hammer | explicit advisory layer | no true Hammer; recommendation score mapped to `hammer_score` for Registry | REVIEW |
| Ranking | tier, model strength, confidence, Hammer | tier, neutral model probability, confidence label, recommendation score as Hammer | compatible but semantically overloaded |
| Explainability | structured model/Hammer reasons | projection, bullpen, market-line explanation | PASS |

## DEFECT Findings

No objective mathematical DEFECT was found in this audit. Review items remain
for Phase 3 statistical validation and semantic cleanup.
