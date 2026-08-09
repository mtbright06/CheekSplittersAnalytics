# MLB Totals Model Specification

Phase 2C.2 audit. Audit and documentation first; no totals formulas, weights,
thresholds, or production behavior were changed. The earlier Phase 2C
certification wording was preliminary and is superseded by this deeper review.

## Closure Recommendation

**TOTALS MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

The MLB Totals model is coherent as a deterministic projection-first
Over/Under heuristic. Official direction is derived from projected total
versus verified pregame total line. Odds, sportsbook, price quality, EV, and
market staleness do not affect conviction scoring. Remaining issues are
assigned to Phase 3 statistical validation or terminology cleanup.

## Recommendation Path

```text
engine/mlb/game_builder.py
  -> team profiles, probable starters, bullpen payload, totals quote
  -> engine/mlb/totals/totals_model.py::build_totals_projection
  -> engine/mlb/totals/expected_runs.py::project_team_runs
  -> engine/mlb/bullpen/bullpen_model.py::build_bullpen_projection
  -> engine/mlb/bullpen/game_adjustment.py::build_game_bullpen_adjustment
  -> engine/mlb/totals/market.py::evaluate_market_edge
  -> engine/mlb/totals/recommendation.py::build_totals_recommendation
  -> engine/mlb/totals/explanation.py
  -> output/cards/mlb_card.json
  -> engine/adapters/mlb_totals_adapter.py
  -> engine/core/recommendation.py
  -> engine/core/ranking.py
  -> Recommendation Registry / Best Bets
```

## Projection Formula

Per-team expected runs:

```text
expected_runs =
  4.45
  + offense_adjustment
  + opposing_starter_adjustment
  + park_adjustment
  + home_field_adjustment

expected_runs is clamped to 2.25..7.25
```

Game total:

```text
starter_based_total = away_expected_runs + home_expected_runs
projected_total = max(0, starter_based_total + combined_bullpen_adjustment)
```

`projected_total` means a deterministic central expected-runs estimate. It is
not a calibrated probability, not a proven median, and not a market-derived
fair line.

## Inputs

| Input | Baseball Meaning | Normalization | Missing Behavior | Verdict |
|---|---|---|---|---:|
| Runs/game | observed scoring output | `RPG - 4.45`, clamp `-1.25..1.25` | omitted from average | REVIEW |
| wRC+ | context-adjusted offense | `(wRC+ - 100) / 100 * 1.35`, clamp `-0.80..0.80` | omitted | REVIEW |
| OPS | on-base plus power production | `(OPS - .720) * 4.5`, clamp `-0.65..0.65` | omitted | REVIEW |
| Starter ERA | opposing starter run prevention | stabilized, `(ERA - 4.20) * .42`, clamp `-1.15..1.15` | omitted | REVIEW |
| Starter WHIP | opposing starter traffic | stabilized, `(WHIP - 1.30) * 1.35`, clamp `-0.75..0.75` | omitted | REVIEW |
| Starter HR/9 | opposing starter damage | stabilized, `(HR9 - 1.15) * .45`, clamp `-0.50..0.50` | omitted | REVIEW |
| Park factor | run environment | `(factor - 1.00) * 4.0`, clamp `-0.80..0.80` | neutral `1.00`, no data point | PASS |
| Home field | home run context | constant `+0.12` | always applied to home | REVIEW |
| Bullpen quality | relief run suppression/inflation | ERA `.50`, WHIP `.25`, last7 ERA `.25` | neutral quality | PASS/REVIEW |
| Bullpen fatigue | recent relief workload | `0.00/.10/.25/.45` buckets | defaults rested `0.0` | REVIEW |
| Closer/setup availability | late-inning availability | `+0.08/+0.05` if unavailable | defaults available | REVIEW |
| Market total line | Over/Under comparison target | positive numeric line | no actionable recommendation | PASS |

Offense and starter inputs are correlated but averaged as ensembles, not summed
as independent run additions. That makes the design plausible and bounded, but
empirically unverified.

## Recommendation Authority

```text
edge_runs = projected_total - market_total
direction = OVER if edge_runs > 0
direction = UNDER if edge_runs < 0
direction = NONE if edge_runs == 0 or no verified line
model_separation = abs(edge_runs)
```

Recommendation score:

```text
separation_score = clamp(40 + model_separation * 30, 0, 100)
model_confidence_score = clamp(model_confidence, 0, 100)
data_quality_score = EXCELLENT 95, GOOD 82, FAIR 68, LIMITED 50
bullpen_confidence_score = clamp(bullpen_confidence, 0, 100)

recommendation_score =
  separation_score * 0.40
  + model_confidence_score * 0.30
  + data_quality_score * 0.20
  + bullpen_confidence_score * 0.10
```

Pregame verification is mandatory. Without an eligible pregame line,
recommendation score is `0.0` and recommendation is `PASS`.

## Confidence

Totals confidence is input-completeness confidence:

```text
data_points = away_projection_points + home_projection_points - duplicated_park_point
confidence = clamp(40 + data_points * 4, 40, 78)
```

A totals confidence of `75` means high offense/starter/park input coverage
under the current completeness scale. It does not mean 75% probability,
historical reliability, disagreement resolution, bullpen certainty, or
quantified prediction uncertainty. Preferred terminology when contracts allow:
`projection_input_confidence`.

## Recommendation Tiers

| Tier | Required Separation | Required Score |
|---|---:|---:|
| STRONG BET OVER/UNDER | `>= 1.25` runs | `>= 82` |
| BET OVER/UNDER | `>= 0.75` runs | `>= 72` |
| LEAN OVER/UNDER | `>= 0.40` runs | `>= 64` |
| PASS | otherwise | otherwise |

The gates are monotonic, reachable, and non-overlapping. Separation is used in
both the score and the tier gate. Phase 2C.2 classifies this as reasonable
monotonic confirmation because low-quality projections still remain PASS even
with large separation.

## Walkthroughs

Current `output/cards/mlb_card.json` contains totals projections but no
verified totals lines, so current real rows are PASS. Actionable examples
below are synthetic boundary examples using production formulas.

| Case | Starter Total | Bullpen Adj | Projected | Line | Separation | Confidence | Bullpen Conf | Score | Tier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Synthetic strong OVER | `8.69` | `+0.57` | `9.26` | `8.00` | `+1.26` | `78` | `93` | `82.6` | STRONG BET OVER |
| Synthetic strong UNDER | `8.30` | `-0.11` | `8.19` | `9.50` | `-1.31` | `78` | `95` | `83.6` | STRONG BET UNDER |
| Current close/no-line PASS | `9.57` | `-0.47` | `9.10` | none | none | `78` | `95` | `0.0` | PASS |

## Certification Boundary

The model is certified as an internally coherent projection-first heuristic.
It is not certified as statistically calibrated. Phase 3 owns empirical
validation of feature overlap, weights, threshold decision rates, confidence
calibration, and projected-total error distribution.
