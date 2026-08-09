# Totals Confidence Investigation

Sprint 83.1 investigated why MLB Totals cards frequently display `78.0 / 100`
confidence across the slate. This was an investigation only. No formulas,
thresholds, model behavior, UI code, or persistence code were changed.

## Recommendation

WORKING BUT LOW INFORMATION VALUE

The repeated `78.0` is mathematically consistent with the current implementation
and is not a UI-only defect. It is a saturation effect caused by the totals model
confidence formula: complete data reaches the hard cap. The value currently
measures input completeness, not calibrated prediction certainty, historical hit
rate, wager strength, or actionability.

## Calculation Trace

Displayed totals confidence originates in the totals model and is later rendered
by MLB card surfaces:

1. `engine/mlb/game_builder.py` attaches `totals_model` to each MLB game.
2. `engine/mlb/totals/totals_model.py::build_totals_projection` builds the
   starter-based total, bullpen adjustment, projected total, market edge, data
   points, numeric model confidence, data quality, and betting recommendation.
3. `engine/mlb/totals/totals_model.py::calculate_game_data_points` counts
   unique offense, starter, and park inputs.
4. `engine/mlb/totals/totals_model.py::confidence_from_data_points` converts
   data points into the displayed numeric confidence.
5. `engine/mlb/totals/recommendation.py::build_totals_recommendation` uses the
   numeric model confidence as one component of the actionable recommendation
   score when a verified pregame totals line exists.
6. `engine/mlb/totals/totals_model.py::TotalsProjection.to_dict` emits
   `confidence`, `recommendation_score`, `betting_confidence`, and score
   components into the card payload.
7. `engine/adapters/mlb_totals_adapter.py::adapt_mlb_totals_game` maps the
   betting recommendation label and score into the shared recommendation object
   for registry and persistence consumers.
8. `app/services/prediction_snapshot_service.py` and
   `app/services/prediction_snapshot_persistence_service.py` persist normalized
   confidence values when the registry row provides them.
9. `dashboard/components/mlb/mlb_card.py`,
   `dashboard/components/mlb/workstation.py`, and
   `dashboard/components/explorer/recommendation_explorer.py` render the numeric
   totals model confidence from `totals_model["confidence"]`.

Important distinction: the `78.0 / 100` value shown on totals cards is numeric
model input-completeness confidence. The actionable betting confidence label
(`PASS`, `LOW`, `MODERATE`, `HIGH`, `VERY HIGH`) comes from the separate totals
recommendation score.

## Formula Walkthrough

Numeric totals model confidence:

```text
data_points =
    away_projection.data_points
  + home_projection.data_points
  - duplicated_park_points

duplicated_park_points = 1 when the park factor is available, else 0

confidence = clamp(
    40.0 + (data_points * 4.0),
    min=40.0,
    max=78.0
)
```

`confidence_from_data_points` explicitly documents that totals confidence
measures input completeness, not wager strength. The `78.0` cap was retained so
bullpen integration would not unexpectedly change the established confidence
scale.

Current data quality labels:

```text
data_points >= 11 -> EXCELLENT
data_points >= 8  -> GOOD
data_points >= 5  -> FAIR
otherwise         -> LIMITED
```

Actionable totals recommendation score, when a verified pregame line exists:

```text
separation_component = clamp(40.0 + model_separation * 30.0, 0.0, 100.0)
model_component      = clamp(model_confidence, 0.0, 100.0)
data_component       = EXCELLENT 95, GOOD 82, FAIR 68, LIMITED 50
bullpen_component    = clamp(bullpen_confidence, 0.0, 100.0)

recommendation_score =
    separation_component * 0.40
  + model_component      * 0.30
  + data_component       * 0.20
  + bullpen_component    * 0.10
```

If no verified pregame totals line exists, `recommendation_score` is forced to
`0.0` and the betting recommendation is `PASS`, regardless of the displayed
numeric model confidence.

## Saturation Analysis

The numeric model confidence reaches the hard cap at `10` or more data points:

| Data points | Raw confidence | Displayed confidence |
| --- | ---: | ---: |
| 0 | 40.0 | 40.0 |
| 1 | 44.0 | 44.0 |
| 2 | 48.0 | 48.0 |
| 3 | 52.0 | 52.0 |
| 4 | 56.0 | 56.0 |
| 5 | 60.0 | 60.0 |
| 6 | 64.0 | 64.0 |
| 7 | 68.0 | 68.0 |
| 8 | 72.0 | 72.0 |
| 9 | 76.0 | 76.0 |
| 10 | 80.0 | 78.0 |
| 11 | 84.0 | 78.0 |
| 12 | 88.0 | 78.0 |

Therefore `78.0` is a hard maximum for the displayed numeric totals model
confidence, not a naturally occurring midpoint.

## Slate Distribution

The available local MLB card artifact is `output/cards/mlb_card.json`, generated
at `2026-08-05T02:49:50+00:00`. The builder artifact did not refresh during this
investigation, so this distribution reflects the repository's available local
slate artifact.

| Matchup | Raw confidence | Displayed confidence | Capped | Projected total | Market total | Recommendation score |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Los Angeles Angels @ Baltimore Orioles | 84.0 | 78.0 | yes | 9.41 | n/a | 0.0 |
| New York Mets @ Cleveland Guardians | 84.0 | 78.0 | yes | 8.19 | n/a | 0.0 |
| Athletics @ Cincinnati Reds | 84.0 | 78.0 | yes | 9.23 | n/a | 0.0 |
| Washington Nationals @ Philadelphia Phillies | 84.0 | 78.0 | yes | 9.92 | n/a | 0.0 |
| St. Louis Cardinals @ New York Yankees | 84.0 | 78.0 | yes | 9.38 | n/a | 0.0 |
| Chicago White Sox @ Boston Red Sox | 84.0 | 78.0 | yes | 9.10 | n/a | 0.0 |
| Miami Marlins @ Atlanta Braves | 84.0 | 78.0 | yes | 9.52 | n/a | 0.0 |
| Minnesota Twins @ Kansas City Royals | 84.0 | 78.0 | yes | 8.95 | n/a | 0.0 |
| Pittsburgh Pirates @ Milwaukee Brewers | 84.0 | 78.0 | yes | 9.56 | n/a | 0.0 |
| Los Angeles Dodgers @ Chicago Cubs | 84.0 | 78.0 | yes | 9.59 | n/a | 0.0 |
| San Francisco Giants @ Texas Rangers | 84.0 | 78.0 | yes | 9.05 | n/a | 0.0 |
| Toronto Blue Jays @ Houston Astros | 84.0 | 78.0 | yes | 8.66 | n/a | 0.0 |
| Tampa Bay Rays @ Colorado Rockies | 84.0 | 78.0 | yes | 10.77 | n/a | 0.0 |
| San Diego Padres @ Arizona Diamondbacks | 84.0 | 78.0 | yes | 8.49 | n/a | 0.0 |
| Detroit Tigers @ Seattle Mariners | 84.0 | 78.0 | yes | 7.94 | n/a | 0.0 |

Distribution:

| Metric | Value |
| --- | ---: |
| Games | 15 |
| Minimum | 78.0 |
| Maximum | 78.0 |
| Average | 78.0 |
| Median | 78.0 |
| Standard deviation | 0.0 |
| Unique displayed values | 1 |

Every available totals game had `EXCELLENT` data quality and enough data points
to exceed the cap. All were displayed at `78.0`; all lacked market totals in the
local artifact, so all actionable recommendation scores were `0.0`.

## Sensitivity Findings

Numeric model confidence only responds to counted data points:

| Scenario | Numeric confidence impact |
| --- | ---: |
| Add one data point below the cap | +4.0 |
| Remove one data point below the cap | -4.0 |
| Move from 9 to 10 data points | +2.0 displayed, then capped |
| Move from 10 to 11 data points | 0.0 displayed, still capped |
| Missing weather | 0.0, weather is not part of this formula |
| Weak bullpen confidence | 0.0, bullpen affects recommendation score instead |
| Missing totals line | 0.0 numeric confidence, recommendation score forced to 0.0 |

Recommendation-score sensitivity with a representative verified-line baseline
(`model_separation=1.0`, `model_confidence=78.0`, `data_quality=EXCELLENT`,
`bullpen_confidence=95.0`) produced a baseline score of `79.9` and confidence
label `HIGH`.

| Scenario | Recommendation score | Label | Recommendation impact |
| --- | ---: | --- | --- |
| Missing totals line | 0.0 | PASS | forced PASS |
| Not pregame verified | 0.0 | PASS | forced PASS |
| Weak bullpen confidence, 50 | 75.4 | MODERATE | still BET |
| FAIR data quality | 74.5 | MODERATE | still BET |
| LIMITED data quality | 70.9 | MODERATE | drops to LEAN |
| Model confidence 66 | 76.3 | MODERATE | still BET |
| Separation 0.40 | 72.7 | MODERATE | LEAN |
| Separation 0.75 | 76.9 | MODERATE | BET |
| Separation 1.25 | 82.9 | HIGH | STRONG BET |

This confirms that the displayed numeric confidence has low slate-to-slate
differentiation once input completeness is high, while the betting
recommendation score can still vary through separation, data quality, bullpen
confidence, and line availability.

## Product Assessment

If every game displays approximately `78.0 / 100`, the metric has low user
information value. It truthfully communicates that the model has complete
expected inputs under the current formula, but the label `Confidence` can
reasonably be misunderstood as prediction certainty, historical reliability, or
probability of the totals recommendation being correct.

The current display does not prove an implementation defect, but it does risk
false precision. A user could infer meaningful per-game confidence differences
where the system is mostly reporting that the same input-completeness threshold
was reached.

## Calibration Assessment

The current numeric totals confidence is not suitable as a standalone future
calibration target for prediction certainty. It is dominated by data
availability and capped at `78.0`, leaving little variance among complete games.

It can be studied as an input-completeness feature, but calibration work should
not treat `78.0` as a calibrated expected hit rate or a direct probability of a
correct Over/Under recommendation.

## Final Finding

The repeated `78.0 / 100` display is a documented saturation effect and is
working as coded. The metric's product meaning is narrow: input completeness.
Because it is shown as generic confidence and frequently collapses to a single
value, the final Sprint 83.1 recommendation is:

WORKING BUT LOW INFORMATION VALUE
