# MLB Totals Model Specification

Phase 2C audit. Audit only; no totals formulas, weights, thresholds, or
production behavior were changed.

## Closure Recommendation

**TOTALS MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

The MLB Totals model is coherent as a deterministic projection-first totals
heuristic. Official Over/Under direction is derived from projected total versus
verified pregame total line. Odds, sportsbook, price quality, EV, and market
staleness do not affect conviction scoring. Phase 3 validation remains needed
for empirical weights, calibration, confidence semantics, tier reachability,
and outcome performance.

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
  -> exporters / output/cards/mlb_card.json
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

`projected_total` is a deterministic expected-runs estimate, best described as
a model-implied mean run total. It is not a simulated median, a calibrated
probability, or a market-derived fair line.

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

## Inputs

| Input | Phenomenon | Normalization | Missing Data | Influence | Audit |
|---|---|---|---|---:|---:|
| Team RPG | run-scoring baseline | `RPG - 4.45`, clamped `-1.25..1.25` | omitted from average | per-team offense average | PASS |
| Team wRC+ | quality of offense | `(wRC+ - 100) / 100 * 1.35`, clamped `-0.80..0.80` | omitted | per-team offense average | REVIEW |
| Team OPS | offensive production | `(OPS - .720) * 4.5`, clamped `-0.65..0.65` | omitted | per-team offense average | REVIEW |
| Starter ERA | opposing starter run prevention | stabilized toward baseline, `(ERA - 4.20) * .42`, clamped `-1.15..1.15` | omitted | per-team starter average | REVIEW |
| Starter WHIP | opposing starter baserunners | stabilized, `(WHIP - 1.30) * 1.35`, clamped `-0.75..0.75` | omitted | per-team starter average | REVIEW |
| Starter HR/9 | opposing starter HR damage | stabilized, `(HR9 - 1.15) * .45`, clamped `-0.50..0.50` | omitted | per-team starter average | REVIEW |
| Park factor | run environment | `(factor - 1.00) * 4.0`, clamped `-0.80..0.80` | neutral `1.00` | added to both teams | PASS |
| Home field | home run context | constant `+0.12` | always available | home team only | REVIEW |
| Bullpen ERA/WHIP/last7 ERA | relief quality | weighted quality `0.50/0.25/0.25`; run adj clamped `-0.35..0.35` | neutral quality | bullpen total | PASS |
| Bullpen innings last 3 | relief fatigue | buckets `0.00/.10/.25/.45` | default `0.0` | bullpen total | REVIEW |
| Closer/setup availability | late-inning availability | `+0.08/+0.05` if unavailable | defaults available | bullpen total | REVIEW |
| Market total line | comparison line | positive numeric line only | no recommendation | direction and separation | PASS |

## Confidence

Totals model confidence is input-completeness confidence:

```text
confidence = clamp(40 + data_points * 4, 40, 78)
```

Data points count offense, starter, and park inputs across both teams with one
duplicated park point removed. Bullpen confidence is tracked separately and
then contributes 10% of the recommendation score.

A totals confidence of `75` means the projection had enough modeled input
coverage to land near the top of the current completeness scale. It does not
mean 75% probability, historical reliability, or quantified run-total
uncertainty.

## Recommendation Tiers

| Tier | Required Separation | Required Score |
|---|---:|---:|
| STRONG BET OVER/UNDER | `>= 1.25` runs | `>= 82` |
| BET OVER/UNDER | `>= 0.75` runs | `>= 72` |
| LEAN OVER/UNDER | `>= 0.40` runs | `>= 64` |
| PASS | otherwise | otherwise |

The gates are monotonic and reachable with complete data. Separation appears
both in direction/tier gates and in 40% of recommendation score; this is
intentional enough to be coherent, but should be validated for double-counting
impact in Phase 3.

## Walkthroughs

Current `output/cards/mlb_card.json` contains 15 totals projections but no
verified totals lines, so there are no current real actionable Over/Under
recommendations to trace. The current card therefore produces `PASS` totals
recommendations with `recommendation_score = 0.0`.

Representative current no-line example:

| Game | Starter Total | Bullpen Adj | Projected Total | Line | Separation | Confidence | Score | Tier |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Washington Nationals @ Philadelphia Phillies | `9.94` | `-0.02` | `9.92` | none | none | `78.0` | `0.0` | PASS |
| New York Mets @ Cleveland Guardians | `8.30` | `-0.11` | `8.19` | none | none | `78.0` | `0.0` | PASS |
| Chicago White Sox @ Boston Red Sox | `9.57` | `-0.47` | `9.10` | none | none | `78.0` | `0.0` | PASS |

Formula-level Over/Under authority is deterministic: a verified line below the
projection produces OVER, a verified line above the projection produces UNDER,
and a missing or ineligible line produces PASS. Odds prices do not change this.
