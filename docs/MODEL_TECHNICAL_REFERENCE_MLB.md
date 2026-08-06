# MLB Moneyline Technical Audit Reference

Phase 2A audit. No model changes were made.

## Executive Summary

The MLB moneyline path faithfully implements the documented winner-first
philosophy: model-side selection and conviction are separated from market
price/value, and Hammer remains advisory.

Certification is **PASS WITH REVIEWS**:

- PASS: deterministic winner-first selection, market-independent conviction,
  bounded scores, neutral missing-data fallbacks, pregame gates, and market
  value separation.
- REVIEW: heuristic weights/thresholds, uncalibrated displayed probabilities,
  overlapping offensive and starter inputs, Hammer double-counting risk, and
  confidence semantics.
- DEFECT: none found during this audit.

## Files Audited

- `engine/model/sharpscore.py`
- `engine/model/component_scores.py`
- `engine/model/confidence.py`
- `engine/model/recommendations.py`
- `engine/model/pitcher_stabilization.py`
- `engine/mlb/offense.py`
- `engine/mlb/pitchers.py`
- `engine/mlb/game_builder.py`
- `engine/decision/decision_builder.py`
- `engine/decision/hammer_score.py`
- `engine/adapters/mlb_decision_adapter.py`
- `engine/core/recommendation.py`
- `engine/core/ranking.py`
- `engine/odds/market_edge.py`
- focused MLB/winner-first tests

## Findings

| ID | Classification | Finding |
|---|---:|---|
| MLB-001 | PASS | MLB moneyline recommendation is selected winner-first from model score, not market edge |
| MLB-002 | PASS | Market value classification is separated from conviction tier |
| MLB-003 | PASS | Market probability/edge/EV do not affect Hammer score |
| MLB-004 | PASS | Unknown or missing offense/starter/bullpen data falls back to neutral scoring |
| MLB-005 | PASS | Starter stats are aggregated from raw starter-only game logs and then stabilized |
| MLB-006 | REVIEW | Team-score weights are heuristic and lack empirical justification in repo docs/code |
| MLB-007 | REVIEW | Offense score uses overlapping metrics and may double-count run creation |
| MLB-008 | REVIEW | Starter score uses overlapping metrics and may double-count pitcher quality |
| MLB-009 | REVIEW | Bullpen score is coarse and does not use full bullpen availability/role evidence |
| MLB-010 | REVIEW | Displayed model probability is a bounded score transform, not proven calibrated probability |
| MLB-011 | REVIEW | Confidence mixes separation, completeness, and starter certainty; it is not pure uncertainty |
| MLB-012 | REVIEW | `calculate_confidence` accepts `odds` but intentionally does not use it; signature may mislead readers |
| MLB-013 | REVIEW | Recommendation thresholds are coherent but empirically unvalidated |
| MLB-014 | REVIEW | Hammer may double-count MLB model information through model score plus component scores |
| MLB-015 | REVIEW | Decision-card `confidence` field is Hammer confidence label, while MLB model numeric confidence remains inside the model payload before adaptation |
| MLB-016 | REVIEW | Ranking uses `recommendation.confidence` label fallback when model confidence is not in components, which may rank by Hammer label for adapted MLB moneylines |

No DEFECT was found that requires a code change under the user's audit-only
instruction.

## Input Audit

### Offense

File: `engine/model/component_scores.py::offense_score`

| Input | Why it exists | Phenomenon | Measured correctly? | Independence / double-count risk |
|---|---|---|---:|---|
| `runs_per_game` | Direct team scoring output | run production | REVIEW: computed correctly as runs/games, but context-neutral | overlaps with all batting quality inputs |
| `ops` | Broad hitting quality | OBP + SLG | PASS as raw measure | overlaps with ISO, BB rate, HR rate |
| `hr_per_game` | Power scoring | home-run frequency | PASS as raw measure | overlaps with SLG/ISO/runs |
| `iso` | Extra-base power | SLG - AVG | PASS | overlaps with OPS and HR rate |
| `k_rate` | Contact weakness | strikeout percentage | PASS | related to OPS/run production |
| `bb_rate` | Plate discipline | walk percentage | PASS | overlaps with OBP/OPS |

Root review cause: offensive events are intentionally combined, but the model
does not orthogonalize them. This is coherent for a heuristic score, not
statistically independent.

### Starting Pitcher

Files:

- `engine/mlb/pitchers.py::aggregate_starter_splits`
- `engine/model/pitcher_stabilization.py::stabilize_pitcher_stat`
- `engine/model/component_scores.py::starting_pitcher_score`

| Input | Why it exists | Phenomenon | Measured correctly? | Independence / double-count risk |
|---|---|---|---:|---|
| ERA | Run prevention | earned runs per nine | PASS from aggregate starter-only raw counts | overlaps with WHIP, HR9, H9, K/BB |
| WHIP | Baserunner prevention | hits + walks per IP | PASS | overlaps with H9 and BB9 |
| K/9 | Bat-missing skill | strikeouts per nine | PASS | overlaps with K-BB% and pitches/IP |
| BB/9 | Command | walks per nine | PASS | overlaps with WHIP, K-BB%, strike% |
| HR/9 | Contact damage | home runs per nine | PASS | overlaps with ERA and H9 |
| H/9 | Hit prevention | hits per nine | PASS | overlaps with WHIP |
| K-BB% | Net dominance | strikeout-minus-walk percentage by BF | PASS | duplicates K9/BB9 direction |
| Strike% | command proxy | strikes / pitches | PASS | overlaps with BB9 |
| Pitches/IP | efficiency | pitches per inning | PASS | overlaps with WHIP, K/BB, strike% |
| Ground/Air | batted-ball tendency | ground outs / air outs | REVIEW: only outs, not all batted balls | correlated with contact management |

Stabilization at 50 IP is coherent and documented. It is not validated here as
optimal.

### Bullpen

File: `engine/model/component_scores.py::bullpen_score`

| Input | Why it exists | Phenomenon | Measured correctly? | Independence / double-count risk |
|---|---|---|---:|---|
| ERA | relief run prevention | bullpen season ERA | PASS as raw profile field | overlaps with WHIP |
| WHIP | relief baserunners | bullpen season WHIP | PASS as raw profile field | overlaps with ERA |

Review: this score underuses the richer bullpen provider evidence now present
elsewhere. That is a future-model issue, not an implementation defect.

### Home Field

File: `engine/model/component_scores.py::home_field_score`

Home receives 56, away 50. The value is coherent and bounded, but the constant
is heuristic.

## Weight Audit

### Team Score Weights

File: `engine/model/sharpscore.py::WEIGHTS`

| Component | Weight | Audit |
|---|---:|---|
| Offense | 0.40 | REVIEW: plausible large signal, but not empirically justified |
| Starting pitching | 0.45 | REVIEW: plausible given probable-starter importance, but not validated |
| Bullpen | 0.10 | REVIEW: plausible but low relative to full-game impact; no evidence cited |
| Home field | 0.05 | REVIEW: bounded and modest; no evidence cited |

The weights sum to 1.0 and operate on 0..100 component scores. Scale is
internally consistent.

### Component Scaling Constants

All component scaling constants are heuristic. Examples:

- offense OPS multiplier `120`
- starter WHIP multiplier `10`
- starter HR/9 multiplier `4`
- bullpen WHIP multiplier `15`
- probability separation multiplier `0.75`

Audit result: **REVIEW**. They are deterministic and bounded, but not supported
by documented regression, backtest, calibration, or ablation evidence.

## Confidence Audit

File: `engine/model/confidence.py::calculate_confidence`

Confidence measures:

1. default trust floor (`base = 45`)
2. team-score separation (`matchup_strength`)
3. narrow data completeness (`away/home pitcher ERA/WHIP`, `away/home OPS`)
4. probable-starter known/unknown penalty

It does not measure:

- historical calibration
- betting edge
- market agreement
- injury/news uncertainty
- lineup certainty
- weather or umpire uncertainty
- model version reliability

Audit result: **REVIEW**. The value is useful as a model-certainty heuristic,
but it should not be described as calibrated statistical confidence.

## Probability Audit

File: `engine/model/sharpscore.py::probability_from_scores`

Displayed MLB moneyline probability is:

```text
50 + score_diff * 0.75, clamped to 40..70
```

Audit result: **REVIEW**. This is a normalized model score expressed on a
probability-looking scale. It is not proven calibrated. Any documentation or
presentation should describe it as model-implied probability until canonical
graded samples validate calibration.

## Recommendation Threshold Audit

File: `engine/model/recommendations.py::mlb_moneyline_conviction_recommendation`

Thresholds are monotonic and internally coherent. They use probability and
confidence only.

Audit result: **REVIEW**. No empirical support was found for 52.0, 56.5, 59.0,
63.0 probability cutoffs or 65.0, 74.0, 78.0, 85.0 confidence cutoffs.

## Hammer Audit

Files:

- `engine/decision/hammer_score.py::calculate_hammer_score`
- `engine/decision/decision_builder.py::build_decision_card`

PASS:

- market edge, EV, price, and real-market availability do not affect Hammer
  score.
- weights are normalized by used weight, so missing components do not collapse
  scores solely because a component is absent.
- agreement bonus and contradiction penalty are bounded.

REVIEW:

- Hammer includes MLB model score/probability plus starter/offense/bullpen
  component scores that already contributed to MLB model score.
- First 5 and Bomb Lab can share underlying starter/offense information with
  the full-game model.
- Default weights sum to 1.05 before used-weight normalization. The output is
  bounded, but the weight set is not directly interpretable as simple
  percentages.

## Interaction Audit

| Interaction | Status | Detail |
|---|---:|---|
| MLB model vs market edge | PASS | market edge does not alter conviction tier |
| MLB model vs market value label | PASS | value label is separate display metadata |
| MLB model vs Hammer | PASS | Decision Builder preserves model recommendation as authority |
| MLB model vs Registry ranking | PASS | ranking prioritizes recommendation tier/probability/confidence/Hammer, not market edge |
| Confidence vs market | PASS | test confirms market probability does not affect confidence |
| Confidence vs Hammer | REVIEW | exported adapted `confidence` may mean Hammer confidence label rather than MLB numeric confidence |
| Component scores vs Hammer | REVIEW | component scores are reused after contributing to MLB model score |

## Explainability Trace

Given an MLB game:

1. Provider data identifies away/home teams and probable starters.
2. Offense metrics are season batting aggregates from MLB Stats API.
3. Starter metrics are raw-count starter-game-log aggregates recomputed into
   rates.
4. Bullpen metrics are provider profile season ERA/WHIP fields.
5. Component scores map these metrics to 0..100 heuristic scores.
6. Team score weights combine offense, starter, bullpen, and home field.
7. Higher score selects the team.
8. Score differential maps to displayed model-implied probability.
9. Confidence blends separation, data completeness, and starter certainty.
10. Recommendation thresholding maps probability + confidence to tier.
11. SSRP edge separately maps to market-value label.
12. Decision Builder calculates Hammer and consensus context.
13. Recommendation artifact can explain:
    - selected team
    - selected/opponent component scores
    - model-implied probability
    - confidence breakdown
    - recommendation tier
    - market-value classification
    - Hammer advisory confirmation

Explainability status: **PASS WITH REVIEW**. The path is deterministic and
traceable, but confidence/probability labels should be explicit about their
heuristic nature.

## Recommended Future Research

No implementation in this sprint.

1. Calibrate `probability_from_scores` against canonical graded MLB moneyline
   episodes.
2. Run ablation tests for offense inputs to measure redundant contribution of
   RPG, OPS, HR/G, ISO, K%, and BB%.
3. Run ablation tests for starter inputs to measure redundancy of ERA, WHIP,
   H/9, HR/9, K/9, BB/9, K-BB%, strike%, and pitches/IP.
4. Validate SharpScore component weights with out-of-sample canonical
   episodes.
5. Validate recommendation thresholds by tier for win rate, calibration, and
   decision rate.
6. Test Hammer monotonicity after separating MLB model score from reused
   component inputs.
7. Clarify field naming for model confidence versus Hammer confidence in
   Decision Builder and downstream adapters.
8. Consider richer bullpen availability/role evidence only after proving it
   adds independent signal.

## Validation Performed

Static audit:

- traced MLB moneyline model data flow from provider normalization through
  SharpScore, Decision Builder, Registry adapter, Hammer, and ranking.
- searched for market leakage and duplicated scoring/ranking paths relevant to
  MLB moneyline.
- reviewed existing focused winner-first tests.

Commands run:

- `python3 -m compileall app engine dashboard tests alembic`
- `git diff --check`
- direct focused test runner for MLB recommendation authority, MLB moneyline
  classification, winner-first shared integrity, pregame boundaries, and
  dashboard presentation zero-argument tests.

No code changes were made.
