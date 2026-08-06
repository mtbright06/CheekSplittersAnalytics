# MLB Moneyline Model Specification

Phase 2A audit snapshot. This document describes the current model; it does
not approve tuning, weights, or future behavior.

## Executive Summary

The current MLB moneyline implementation is winner-first and market-independent
for the betting recommendation tier. It selects the team with the higher
SharpScore, converts that score separation into a bounded displayed model
probability, applies confidence thresholds, and classifies market value
separately from conviction.

The model is mathematically coherent as a deterministic scoring system, but it
is not empirically validated as a calibrated win-probability model. Most
weights, scaling constants, and thresholds are heuristic. Several inputs are
baseball-reasonable but statistically overlapping, especially offense metrics,
starter metrics, and Hammer's reuse of MLB component information.

No narrow objectively incorrect mathematical defect was found that warrants a
code change in this audit.

## Winner-First Philosophy

The authoritative MLB moneyline recommendation is intended to answer:

```text
Which team does SharpStack project as the better side before considering price?
```

Market price then answers a separate question:

```text
Is the available or reference price favorable relative to the model projection?
```

Implementation:

- `engine/model/sharpscore.py::choose_side` selects the higher team score.
- `engine/model/recommendations.py::mlb_moneyline_conviction_recommendation`
  uses only model probability and model confidence.
- `engine/model/recommendations.py::market_value_classification` separately
  labels SSRP edge.
- `engine/decision/decision_builder.py::build_decision_card` preserves the MLB
  model recommendation as authority and retains Hammer as advisory context.

## Data Flow

```text
MLB provider data
  |
  +-- engine/mlb/offense.py
  |     season team hitting metrics
  |
  +-- engine/mlb/pitchers.py
  |     starter-only pitching game-log aggregates
  |
  +-- engine/mlb/bullpen/provider.py
        bullpen season/recent profile

team_profile + probable starters + SSRP quote
  |
  v
engine/model/sharpscore.py
  |
  +-- offense_score
  +-- starting_pitcher_score
  +-- bullpen_score
  +-- home_field_score
  +-- weighted team score
  +-- selected side
  +-- displayed model probability
  +-- confidence
  +-- recommendation tier
  +-- separate market-value label
```

## Team Score

File: `engine/model/sharpscore.py`

Weights:

| Component | Weight | Purpose |
|---|---:|---|
| Offense | 0.40 | Team run-creation ability |
| Starting pitching | 0.45 | Probable starter run prevention and skills |
| Bullpen | 0.10 | Late-game run prevention |
| Home field | 0.05 | Home advantage |

Formula:

```text
team_score =
  offense_score * 0.40
  + starting_pitcher_score * 0.45
  + bullpen_score * 0.10
  + home_field_score * 0.05
```

The selected side is the higher team score. Exact ties select home.

## Offense Score

File: `engine/model/component_scores.py::offense_score`

Baseline: `50`

Inputs:

| Input | Phenomenon | Current Measurement | Scoring Effect |
|---|---|---|---|
| `runs_per_game` | Actual run production | team season runs / games | `(rpg - 4.4) * 7` |
| `ops` | Overall on-base + slugging quality | MLB Stats API season OPS | `(ops - .710) * 120` |
| `hr_per_game` | Power production | home runs / games | `(hrpg - 1.1) * 8` |
| `iso` | Extra-base-hit power | SLG - AVG | `(iso - .160) * 90` |
| `k_rate` | Contact ability | strikeouts / PA percentage | `-(k_rate - 22.0) * .6` |
| `bb_rate` | Plate discipline | walks / PA percentage | `(bb_rate - 8.0) * .8` |

The final offense score is clamped to `0..100`.

Audit classification: **REVIEW**. Inputs are baseball-reasonable, but not
independent. OPS overlaps with ISO, walks, and power; runs per game is an
outcome of the same offensive events. The score is coherent but likely
double-counts offensive quality.

## Starting Pitcher Score

File: `engine/model/component_scores.py::starting_pitcher_score`

Baseline: `50`

Unknown starter or missing innings returns neutral `50`.

Each metric is stabilized toward the league baseline using:

```text
reliability = IP / (IP + 50)
stabilized = league_average + reliability * (observed - league_average)
```

Inputs:

| Input | Phenomenon | Current Measurement | Scoring Effect |
|---|---|---|---|
| ERA | Run prevention | starter-only earned runs per 9 | `(4.50 - era) * 3.0` |
| WHIP | Baserunner prevention | starter-only walks + hits / IP | `(1.35 - whip) * 10.0` |
| K/9 | Bat-missing skill | starter-only strikeouts per 9 | `(k9 - 8.50) * 1.25` |
| BB/9 | Command | starter-only walks per 9 | `(3.20 - bb9) * 1.5` |
| K-BB% | Net dominance | `(K - BB) / BF` | `(k_bb_pct - 14.0) * .30` |
| Strike% | Zone/control proxy | strikes / pitches | `(strike_pct - 64.0) * .35` |
| HR/9 | Contact damage | home runs per 9 | `(1.20 - hr9) * 4.0` |
| H/9 | Hit prevention | hits per 9 | `(8.50 - h9) * .75` |
| Pitches/IP | Efficiency | pitches / IP | `(16.5 - pitches_per_inning) * .40` |
| Ground/Air | Batted-ball tendency | ground outs / air outs, clamped .50..2.00 | `(ratio - 1.00) * 1.5` |

The final starter score is clamped to `0..100`.

Audit classification: **REVIEW**. Starter-only aggregation and stabilization
are coherent. The metric set is not independent: ERA, WHIP, H/9, HR/9, K/9,
BB/9, K-BB%, strike%, and pitches/IP overlap. This may double-count starter
quality, especially command/contact effects.

## Bullpen Score

File: `engine/model/component_scores.py::bullpen_score`

Baseline: `50`

Inputs:

| Input | Phenomenon | Current Measurement | Scoring Effect |
|---|---|---|---|
| ERA | Bullpen run prevention | season bullpen ERA | `(4.25 - era) * 5` |
| WHIP | Bullpen baserunner prevention | season bullpen WHIP | `(1.35 - whip) * 15` |

Audit classification: **REVIEW**. The score is coherent but coarse. It ignores
availability evidence, leverage role, fatigue, handedness, and recent quality
except where upstream profile values already encode them.

## Home Field Score

File: `engine/model/component_scores.py::home_field_score`

The home team receives `56`; away receives `50`. With a 0.05 team-score
weight, this contributes a 0.3 team-score edge to the home side.

Audit classification: **REVIEW**. Coherent and bounded, but the constant is
heuristic and not empirically justified in the repository.

## Probability

File: `engine/model/sharpscore.py::probability_from_scores`

Formula:

```text
model_probability = clamp(50 + (selected_score - opponent_score) * 0.75, 40, 70)
```

The value is displayed as a probability percentage.

Audit classification: **REVIEW**. This is a normalized score-to-percentage
mapping, not a proven calibrated probability. The 0.75 multiplier and 40..70
clamp are heuristic. Downstream consumers should treat it as model-implied win
probability until calibration is established.

## Confidence

File: `engine/model/confidence.py::calculate_confidence`

Confidence currently measures a blend of:

| Contributor | Formula | Concept |
|---|---|---|
| Base | `45` | default model confidence floor |
| Matchup strength | `min(score_diff * 1.1, 30)` | model separation |
| Data quality | present count of pitcher ERA/WHIP and offense OPS times `20` | minimal data completeness |
| Starter certainty | `0`, `-10`, or `-20` | unknown probable starter penalty |

Final confidence is clamped to `35..95`.

Audit classification: **REVIEW**. Confidence is not a pure statistical
uncertainty estimate. It mixes model separation, feature completeness, and
starter certainty. It intentionally ignores market probability. The `odds`
argument is unused, which is harmless for market independence but misleading
as an API signal.

## Recommendation Thresholds

File: `engine/model/recommendations.py::mlb_moneyline_conviction_recommendation`

| Tier | Probability | Confidence |
|---|---:|---:|
| CHEEK RIPPER | `>= 63.0` | `>= 85.0` |
| STRONG PLAY | `>= 59.0` | `>= 78.0` |
| PLAYABLE | `>= 56.5` | `>= 74.0` |
| LEAN | `>= 52.0` | `>= 65.0` |
| PASS | otherwise | otherwise |

Audit classification: **REVIEW**. The thresholds are internally consistent and
winner-first, but no empirical validation evidence was found for these values.

## Market Value

File: `engine/model/recommendations.py::market_value_classification`

SSRP edge is display/diagnostic market-value information only. It does not
alter the MLB moneyline recommendation tier.

Audit classification: **PASS**.

## Hammer Contribution

Files:

- `engine/decision/hammer_score.py`
- `engine/decision/decision_builder.py`

Hammer inputs include MLB model score/probability, First 5 score, Bomb score,
starter score, offense score, bullpen score, park, weather, sample confidence,
module agreement, and contradiction penalty. Market value, edge, EV, price,
and availability are absent from the Hammer formula.

Audit classification: **REVIEW**. Hammer is market-independent and bounded,
but it partially double-counts MLB moneyline information by using both the MLB
model score and its underlying starter/offense/bullpen component scores. It
also includes First 5 and Bomb Lab signals that share some baseball inputs.
This is acceptable as advisory confirmation, but not proven independent.

## End-To-End Recommendation Trace

For one game:

1. `engine/mlb/game_builder.py` builds team profiles from MLB provider data.
2. `engine/mlb/offense.py` computes season offense inputs.
3. `engine/mlb/pitchers.py` aggregates probable-starter-only game logs.
4. `engine/mlb/bullpen/provider.py` supplies bullpen ERA/WHIP profile fields.
5. `build_sharpscore_decision` computes away and home team scores.
6. `choose_side` selects the higher score; exact tie goes home.
7. `probability_from_scores` maps score separation to a displayed
   model-implied probability.
8. `calculate_confidence` combines score separation, data completeness, and
   starter certainty.
9. `mlb_moneyline_conviction_recommendation` assigns the recommendation tier.
10. SSRP market edge is computed separately and converted to a market-value
    label.
11. `Decision Builder` retains the MLB model recommendation as authority.
12. Hammer is calculated as advisory confirmation.
13. Registry, dashboard, and persistence consume the serialized recommendation.

## Audit Recommendation

The MLB moneyline model can be treated as a coherent winner-first heuristic
model. It should not be described as calibrated or empirically validated until
resolved canonical samples prove calibration, threshold performance, and input
independence.

---

# Phase 2A.2 Scientific Review Closure

Audit and analysis only. No production code, model weights, recommendation
thresholds, or Hammer behavior were changed.

## Closure Recommendation

**MLB MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

The implementation is conceptually and mathematically defensible as a
deterministic winner-first heuristic model. It is not certified as a calibrated
probability model or an empirically optimized betting model.

## Canonical Terminology

| Current Field | Phase 2A.2 Interpretation | Notes |
|---|---|---|
| `model_probability` | Model Win Strength / model-implied win probability | Bounded score transform; not calibrated. |
| `confidence` in SharpScore model payload | Model conviction quality | Mixes separation, core data completeness, and starter certainty. |
| `confidence` in Decision Builder row | Hammer confidence label | Label derived from Hammer score, distinct from SharpScore numeric confidence. |
| Hammer Score | Advisory confirmation score | Partially duplicates SharpScore components; not independent proof. |
| Market Value | SSRP price-value label | Separate from recommendation conviction. |

## End-To-End Dependency Map

```text
raw MLB provider fields
  -> normalized offense / starter / bullpen / home features
  -> component scores clamped to 0..100
  -> weighted away/home team scores
  -> higher score selects side
  -> score gap maps to bounded model win strength
  -> score gap + data completeness + starter certainty maps to confidence
  -> model win strength + confidence maps to MLB moneyline tier
  -> Decision Builder preserves MLB tier as authority
  -> Hammer consumes model win strength plus First 5, Bomb, component,
     park, weather, sample-confidence, agreement, and contradiction inputs
  -> ranking sorts by tier, model strength, confidence, Hammer, and stable identity
```

## Scientific Review Verdicts

| Area | Verdict |
|---|---:|
| Winner-first selection | PASS |
| Market independence for conviction tier | PASS |
| Component score normalization | PASS |
| SharpScore weight normalization | PASS |
| Missing-data safety | PASS |
| Probability semantics | RENAME/CLARIFY |
| Confidence semantics | RENAME/CLARIFY |
| Offense input independence | REVIEW |
| Starter input independence | REVIEW |
| Bullpen completeness | REVIEW |
| Hammer independence | REVIEW |
| Tier thresholds | REVIEW |
| Objective conceptual defect | None found |

## Probability Specification

The displayed MLB moneyline value currently named `model_probability` is:

```text
clamp(50 + (selected_score - opponent_score) * 0.75, 40, 70)
```

Because the selected team is chosen before this calculation, normal selected
outputs are `50..70`. The model does not compute a paired home/away probability
distribution, does not prove that opposing probabilities sum to 1, and does
not include a calibration curve. The correct current meaning is model win
strength on a probability-like display scale.

## Confidence Specification

MLB confidence is:

```text
45
+ min(score_diff * 1.1, 30)
+ core data completeness * 20
+ starter certainty penalty
clamped to 35..95
```

It represents model conviction quality. It does not represent historical
reliability, empirical uncertainty, price confidence, or calibrated win
probability.

## Hammer Specification

Hammer is advisory. It is market-independent, bounded, and useful for showing
cross-module support, but it is not independent from the MLB moneyline model.
It can reuse the model score, starter score, offense score, bullpen score, and
model confidence that already influenced the official recommendation.

## Phase 3 Validation Items

Future empirical validation should:

1. Calibrate model win strength against canonical locked episodes.
2. Validate or refit team-score weights with out-of-sample evidence.
3. Run offense and starter ablation tests to measure duplicated information.
4. Evaluate whether Hammer improves predictive discrimination after removing
   duplicated SharpScore inputs.
5. Validate tier thresholds by outcome, calibration, decision rate, and sample
   stability.
6. Clarify display/API labels for model win strength and the two confidence
   concepts.
