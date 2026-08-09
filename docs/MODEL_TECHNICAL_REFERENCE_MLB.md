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

## Phase 2A.3 Semantic Contract

Authoritative MLB moneyline terminology:

| Concept | Authoritative Field | Compatibility Alias | Retirement Status |
|---|---|---|---|
| Bounded model-strength value | `model_win_strength` | `model_probability` | Retain until downstream consumers finish migration. |
| MLB model conviction quality | `model_confidence` | model-payload `confidence` | Retain until downstream consumers finish migration. |
| Hammer-derived confidence label | `hammer_confidence` | Decision Builder row `confidence` | Retain until downstream consumers finish migration. |

`model_win_strength` and `model_probability` are the same numeric value. The
compatibility alias must not be recalculated separately.

Ranking confidence fallback order is:

1. explicit `Recommendation.model_confidence`
2. explicit `components["model_confidence"]`
3. explicit `source_signals["model_confidence"]`
4. generic numeric `components["confidence"]` retained by older model
   contracts
5. non-Hammer compatibility label in `Recommendation.confidence`
6. neutral fallback

Ranking does not use `hammer_confidence`, edge, EV, odds, price, or market
quality as model confidence.

The `odds` parameter on `calculate_confidence` is a deprecated compatibility
argument. The authoritative MLB moneyline confidence formula intentionally
ignores it.

## Phase 3A Statistical Integrity Status

See `docs/MLB_STATISTICAL_INTEGRITY_REPORT.md`.

Classification: **UNVALIDATED**.

The canonical recommendation architecture is the correct source for
calibration, but the current database inventory contains no canonical MLB
moneyline episodes or canonical graded MLB moneyline recommendations. Raw
snapshot data exists, but all matching raw snapshot-grade rows are `PENDING`
and repeated snapshots would inflate one-game-per-decision statistics.

Current inventory:

| Source | Count / Status |
|---|---:|
| Canonical MLB moneyline episodes | `0` |
| Canonical graded MLB moneyline recommendations | `0` |
| Raw MLB moneyline prediction snapshots | `86` |
| Raw distinct provider games in snapshot grades | `15` |
| Raw snapshot-grade rows | `165 PENDING` |
| Raw snapshot date range | `2026-08-05 13:32:03 UTC` to `2026-08-05 21:04:54 UTC` |

No Brier score, log loss, reliability slope, Hammer incremental value, tier
ordering, or weight-sensitivity conclusion is validated yet. Model Win
Strength must remain described as a score until adequate chronological
canonical outcomes prove calibration.

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
| MLB-010 | RENAME/CLARIFY | Displayed `model_win_strength` is a bounded score transform, not proven calibrated probability; `model_probability` is a compatibility alias |
| MLB-011 | RENAME/CLARIFY | `model_confidence` mixes separation, completeness, and starter certainty; it is not pure uncertainty |
| MLB-012 | RENAME/CLARIFY | `calculate_confidence` accepts deprecated compatibility `odds` but intentionally does not use it |
| MLB-013 | REVIEW | Recommendation thresholds are coherent but empirically unvalidated |
| MLB-014 | REVIEW | Hammer may double-count MLB model information through model score plus component scores |
| MLB-015 | RENAME/CLARIFY | Decision-card exports `model_confidence` and `hammer_confidence`; generic `confidence` remains a Hammer compatibility alias |
| MLB-016 | RENAME/CLARIFY | Ranking fallback is model-first and treats explicit Hammer confidence as neutral for model-confidence scoring |

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

---

# Phase 2A.2 Scientific Model Review Addendum

Audit and analysis only. No production code, weights, thresholds, or model
logic were changed.

## Closure Recommendation

**MLB MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

Certification here means the current MLB moneyline implementation is coherent,
traceable, and free of known conceptual defects. It does not mean the model is
statistically optimal or probability-calibrated.

## Resolved REVIEW Matrix

| Prior ID | Phase 2A.2 Result | Resolution |
|---|---:|---|
| MLB-006 | REVIEW | Team-score weights are internally coherent because they sum to 1.0 and apply to 0..100 component scores, but remain empirically unvalidated. |
| MLB-007 | REVIEW | Offense inputs are baseball-reasonable but partially overlapping; no internal defect, but independence is not established. |
| MLB-008 | REVIEW | Starter inputs are role-aware and stabilized, but several measure the same run-prevention skill path; independence is not established. |
| MLB-009 | REVIEW | Bullpen ERA/WHIP scoring is coherent but intentionally coarse relative to available bullpen evidence. |
| MLB-010 | RENAME/CLARIFY | Displayed `model_probability` is a bounded model-strength transform, not a calibrated probability. |
| MLB-011 | RENAME/CLARIFY | Confidence measures a conviction heuristic: matchup separation plus limited data completeness plus starter certainty. |
| MLB-012 | RENAME/CLARIFY | The unused `odds` argument is harmless for market independence but misleading API surface. |
| MLB-013 | REVIEW | Tier thresholds are monotonic and reachable, but require Phase 3 empirical validation. |
| MLB-014 | REVIEW | Hammer is a partially duplicated ensemble, acceptable as advisory confirmation, not independent evidence. |
| MLB-015 | RENAME/CLARIFY | Decision-card `confidence` is Hammer confidence label; MLB model confidence is distinct. |
| MLB-016 | RENAME/CLARIFY | Ranking may consume the Hammer confidence label fallback if numeric model confidence is absent downstream. |

No prior REVIEW item was upgraded to DEFECT.

## Complete Feature Map

```text
MLB provider data
  -> offense profile
       raw: runs, games, OPS, HR, SLG, AVG, K, BB, PA
       normalized: RPG, OPS, HR/G, ISO, K%, BB%
       consumed by: offense_score
       reappears: Hammer offense_score; First 5/Bomb may share offensive context
  -> probable starter profile
       raw: starter-only outs, ER, H, BB, SO, HR, BF, strikes, pitches, GO, AO
       normalized: ERA, WHIP, K/9, BB/9, HR/9, H/9, K-BB%, strike%, P/IP, G/A
       consumed by: starting_pitcher_score after IP stabilization
       reappears: Hammer starter_score; First 5 and Bomb can share starter context
  -> bullpen profile
       raw: bullpen ERA, WHIP from bullpen provider profile
       normalized: bullpen_score
       consumed by: SharpScore team score
       reappears: Hammer bullpen_score
  -> home/away identity
       normalized: home_field_score 56 home, 50 away
       consumed by: SharpScore team score
       reappears: nowhere material in MLB moneyline path
  -> park/weather context
       normalized: park_score/weather_score if present in card payloads
       consumed by: Hammer only
       reappears: Bomb/totals contexts may use related environment data
```

End-to-end dependency:

```text
raw MLB data
  -> normalized offense/starter/bullpen/home features
  -> away/home SharpScore component scores
  -> weighted team scores
  -> higher score selects side
  -> score differential becomes displayed model strength/probability
  -> model strength + confidence become MLB recommendation tier
  -> Decision Builder preserves MLB tier as authority
  -> Hammer consumes model strength plus supporting module/component signals
  -> ranking uses tier, model strength, confidence, and Hammer
```

## Feature-Overlap Findings

| Relationship | Classification | Finding |
|---|---:|---|
| Runs per game vs OPS/ISO/HR/BB/K | PARTIAL OVERLAP | RPG is the outcome of the same offensive events measured by rate statistics. |
| OPS vs ISO/HR/G/BB% | LIKELY DOUBLE COUNT | OPS already includes on-base and slugging components, while ISO, HR/G, and BB% repeat parts of the same skill set. |
| Starter ERA vs WHIP/H9/HR9/K9/BB9 | PARTIAL OVERLAP | ERA captures run prevention caused partly by the component skill metrics. |
| WHIP vs H9 and BB9 | LIKELY DOUBLE COUNT | WHIP is directly composed from hits and walks per inning. |
| K9 and BB9 vs K-BB% | LIKELY DOUBLE COUNT | K-BB% recombines strikeout and walk information already used separately. |
| BB9 vs strike% vs pitches/IP | PARTIAL OVERLAP | Each represents command/efficiency from related pitch-count behavior. |
| Team recent form vs season offense | UNKNOWN WITHOUT DATA | No current SharpScore moneyline recent-form term was found; future cards may expose it elsewhere. |
| Bullpen performance vs team run prevention | UNKNOWN WITHOUT DATA | SharpScore uses bullpen ERA/WHIP directly; broader team run prevention is not a separate moneyline input here. |
| Starter in SharpScore vs starter in Hammer | LIKELY DOUBLE COUNT | Hammer consumes starter score after starter already helped create model score/probability. |
| Offense in SharpScore vs offense in Hammer | LIKELY DOUBLE COUNT | Hammer consumes offense score after offense already helped create model score/probability. |
| Bullpen in SharpScore vs bullpen in Hammer | PARTIAL OVERLAP | Same component reappears, but with lower Hammer weight. |
| Model probability in Hammer vs components | LIKELY DOUBLE COUNT | Model probability is derived from the same offense/starter/bullpen/home scores Hammer can also consume. |
| First 5 vs starter signal | PARTIAL OVERLAP | First 5 naturally emphasizes starters and early offense, overlapping full-game starter inputs. |
| Home field vs home/away splits | INDEPENDENT IN CURRENT PATH | No additional home/away split input was found in current SharpScore. |

## Effective-Weight Findings

SharpScore weights normalize: offense `0.40`, starting pitching `0.45`,
bullpen `0.10`, and home field `0.05` sum to `1.00`. Because each component is
clamped to `0..100`, configured and effective team-score scales are comparable.

Maximum team-score contribution:

| Component | Weight | Max Contribution |
|---|---:|---:|
| Offense | 0.40 | 40.0 |
| Starting pitching | 0.45 | 45.0 |
| Bullpen | 0.10 | 10.0 |
| Home field | 0.05 | 5.0 |

Effective matchup differential can be dominated by starter/offense because
their weights and practical ranges are larger. Home field is mathematically
consistent as a team-score component; its fixed score difference of `6` creates
a `0.3` team-score advantage, which is small relative to offense/starter
movement.

Missing SharpScore components return neutral `50`, so missing data does not
renormalize the team-score weights. Hammer behaves differently: unavailable
Hammer components are removed from `used_weight`, which preserves a bounded
average but changes relative influence among available signals.

Hammer default weights sum to `1.05`, then normalize by used weight. With all
inputs available, its effective shares are approximately:

| Hammer Input | Nominal Weight | Effective Share |
|---|---:|---:|
| MLB model | 0.27 | 25.7% |
| First 5 | 0.17 | 16.2% |
| Starter | 0.15 | 14.3% |
| Bomb | 0.12 | 11.4% |
| Offense | 0.12 | 11.4% |
| Bullpen | 0.08 | 7.6% |
| Park | 0.05 | 4.8% |
| Weather | 0.05 | 4.8% |
| Sample confidence | 0.04 | 3.8% |

This is coherent as a bounded advisory score, but the nominal weights should
not be read as independent evidence shares because several inputs are derived
from or correlated with SharpScore.

## Probability Verdict

`probability_from_scores(selected_score, opponent_score)` computes:

```text
model_probability = clamp(50 + (selected_score - opponent_score) * 0.75, 40, 70)
```

Input range is the selected score differential after the higher-scoring side is
chosen, so practical input is `>= 0` except exact ties. Output is clipped to
`40..70`, but selected-side outputs are practically `50..70`. Opposing team
values are not calculated as a paired distribution and therefore are not shown
to sum to 1. The value is used for tiering, display, Hammer, and ranking.

Verdict: **RENAME/CLARIFY**. The value is best described as **Model Win
Strength** or **model-implied win probability**, not calibrated model
probability.

## Confidence Verdict

Current confidence decomposes into:

| Contributor | Concept | Effect |
|---|---|---|
| Base 45 | default floor | fixed starting point |
| `min(score_diff * 1.1, 30)` | matchup separation / conviction | monotonic with team-score gap |
| completeness of ERA/WHIP/OPS fields times 20 | data completeness | more complete selected inputs raise score |
| unknown starter penalty | starter certainty | unknown starters lower score |

A confidence value of `70` means the model has baseline trust plus some mix of
score separation and available core fields, after starter penalties. It does
not mean 70% win probability, 70% calibration reliability, or 70% historical
accuracy.

Answers:

- Bounded: yes, `35..95`.
- Monotonic in score differential: yes, until the 30-point matchup cap.
- Better data can lower confidence: no for this formula; added completeness
  raises or preserves confidence, while confirmed bad stats affect team score
  and therefore separation.
- Missing data can accidentally increase confidence: not directly, but neutral
  missing scores can preserve a favorable separation created elsewhere.
- Identical team scores can produce high confidence: with full data and known
  starters, identical scores produce `65`, which can reach LEAN confidence
  threshold but cannot create a LEAN because model strength is only `50`.
- Duplicates probability/margin: partially; matchup strength is the same score
  differential that creates displayed model strength.

Verdict: **RENAME/CLARIFY**. The number currently represents **model conviction
quality**, not Data Quality alone, Prediction Uncertainty, or Historical
Reliability.

## Hammer Verdict

Hammer is a **partially duplicated ensemble**. It adds useful cross-module
context from First 5, Bomb Lab, park, weather, sample confidence, agreement,
and contradictions, but it also repeats MLB model information through model
strength plus starter/offense/bullpen component scores.

Representative duplication example:

```text
Selected score 63.0 vs opponent 53.0
Model strength: 57.5
Model confidence: 81.0
MLB tier: PLAYABLE
Hammer inputs: model 57.5, First 5 68, Bomb 61, starter 72,
offense 65, bullpen 59, park 52, weather 50, sample confidence 81
Hammer base: 62.9
Hammer final: 65.4 WATCH / MODERATE after one agreement bonus
```

The repeated MLB-derived block is model strength plus starter/offense/bullpen
and sample confidence: nominal `0.66` of `1.05`, or about `62.9%` of the
all-input Hammer average. Because First 5 and Bomb can also share starter and
offense context, true duplication risk can be higher without data.

Verdict: **REVIEW**. Coherent as advisory confirmation; not independent enough
to be described as separate proof.

## Threshold Verdict

MLB moneyline tiers are monotonic and non-overlapping:

| Tier | Model Strength | Confidence |
|---|---:|---:|
| CHEEK RIPPER | `>= 63.0` | `>= 85.0` |
| STRONG PLAY | `>= 59.0` | `>= 78.0` |
| PLAYABLE | `>= 56.5` | `>= 74.0` |
| LEAN | `>= 52.0` | `>= 65.0` |
| PASS | otherwise | otherwise |

A higher model strength can receive a lower tier if confidence is lower; this
is intentional and monotonic in the two-dimensional rule set. No unreachable or
overlapping condition was found.

Verdict: **COHERENT HEURISTIC; REQUIRES EMPIRICAL VALIDATION**.

## Representative Walkthroughs

No current generated MLB card JSON was found in the repository audit. The
following are representative code-level traces using production formulas.

| Case | Component Pattern | Team Scores | Strength | Confidence | MLB Tier | Hammer | Ranking Drivers |
|---|---|---:|---:|---:|---|---|---|
| Strong favorite | stronger starter/offense, moderate bullpen, neutral environment | 63.0 vs 53.0 | 57.5 | 81.0 | PLAYABLE | 65.4 WATCH | tier, 57.5 strength, 81 confidence, 65.4 Hammer |
| Close matchup | near-even components, incomplete Bomb/park | 55.0 vs 54.0 | 50.8 | 66.1 | PASS | 52.6 PASS | PASS tier dominates despite fair data |
| Model-selected underdog | away side wins model score despite no home edge | 58.0 vs 52.0 | 54.5 | 77.0 | LEAN | 64.7 WATCH | LEAN tier, 54.5 strength, 77 confidence |

The explanation path is deterministic: component scores produce team scores;
team-score gap produces model strength; score gap plus data/starter fields
produce confidence; strength and confidence produce tier; Hammer and ranking
then consume the serialized model output.
