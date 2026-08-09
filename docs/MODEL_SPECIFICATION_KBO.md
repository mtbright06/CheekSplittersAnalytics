# KBO Moneyline Model Specification

Phase 2B audit snapshot, updated by Sprint 80.1 correctness repair and Sprint
80.2 normalization resolution. This document describes current behavior; it
does not approve tuning, weights, thresholds, or future behavior.

## Closure Recommendation

**KBO MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

Sprint 80.1 repaired the objective winner-first correctness defects identified
in Phase 2B. Sprint 80.2 verification found active-weight normalization unsafe
against the established KBO ordinal scale, so the model retains configured
component weights while bullpen and recent form remain neutral reserved
components. KBO selected team authority comes from the final weighted
model-score direction, not row order, dataframe index, game position, or
iteration order. Market edge remains display/provenance only.

## Recommendation Path

```text
providers/kbo.py
  -> providers/kbo_data_provider.py / parsers
  -> models/game.py
  -> loaders/pitcher_loader.py
  -> calculators/*
  -> models/kbo_model.py::score
  -> engine/enrichers/odds_enricher.py
  -> models/kbo_model.py::finalize
  -> exporters/json_exporter.py
  -> output/cards/kbo_card.json
  -> engine/adapters/kbo_card_adapter.py
  -> engine/core/recommendation.py
  -> engine/core/ranking.py
  -> tools_build_recommendation_registry.py
  -> Best Bets / registry presentation
```

## Model Score

File: `models/kbo_model.py`

The model loops over these calculators:

| Component | File | Raw Score Range | Weight | Contribution Range |
|---|---|---:|---:|---:|
| Starting Pitching | `calculators/starting_pitching.py` | `-2..2` | `0.35` | `-0.70..0.70` |
| Offense | `calculators/offense.py` | `-1..1` | `0.25` | `-0.25..0.25` |
| Bullpen | `calculators/bullpen.py` | `0` | `0.15` | `0` |
| Recent Form | `calculators/recent_form.py` | `0` | `0.10` | `0` |

The displayed ordinal score is:

```text
contribution = round(raw_score * configured_weight, 2)
weighted_score = sum(contributions)
model_probability/model_strength = round(50 + weighted_score * 8, 1)
```

With Sprint 80.1 neutral bullpen and recent form:

```text
weighted_score =
  round(starter_score * 0.35, 2)
  + round(offense_score * 0.25, 2)
  + 0.0
  + 0.0

practical model_strength/model_probability range = 42.4..57.6
```

Audit classification: **RENAME/CLARIFY**. This is an ordinal model score, not
a calibrated probability.

## Selection

Current production behavior:

```text
weighted_score > 0: select away team
weighted_score < 0: select home team
weighted_score == 0: no selected team / neutral NO PLAY behavior
```

This follows the current KBO calculator contract: positive component scores
favor the away side and negative component scores favor the home side.

Audit classification: **PASS**. Selection is deterministic and derived from
model-score direction.

## Inputs

| Feature | Why It Exists | Measurement | Missing Data | Effective Influence | Consumers | Audit |
|---|---|---|---|---:|---|---:|
| Starter ERA | run prevention | lower-is-better threshold score | neutral `0` if missing | high through starter score | KBO score, reasons, adapter consensus | REVIEW |
| Starter WHIP | baserunner prevention | lower-is-better threshold score | neutral `0` if missing | high through starter score | KBO score, reasons, adapter consensus | REVIEW |
| Starter K/9 | bat-missing skill | higher-is-better threshold score | neutral `0` if missing | moderate | KBO score, reasons | REVIEW |
| Starter BB/9 | command | lower-is-better threshold score | neutral `0` if missing | moderate | KBO score, reasons | REVIEW |
| Starter HR/9 | contact damage | lower-is-better threshold score | neutral `0` if missing | moderate | KBO score, reasons | REVIEW |
| Runs/game | offense | higher team RPG wins offense point | neutral `0` if either side missing | moderate | KBO score, reasons, confidence data quality | PASS |
| Bullpen | bullpen strength | intentionally neutral `0.0` | neutral `0` | none | KBO score, reasons, adapter consensus | PASS |
| Recent form | recent team quality | intentionally neutral `0.0` | neutral `0` | none | KBO score, reasons, adapter consensus | PASS |
| Home field | venue/team context | not modeled | unavailable | none | none | REVIEW |
| Park/weather | environment | present in card display fields only | not scored | none | presentation only | PASS |

## Confidence

There are two KBO confidence paths:

1. `engine/confidence.py::ConfidenceEngine.calculate` initially combines
   score separation, starter data completeness, offense data completeness, and
   starter certainty. It accepts `market_available` but does not use it.
2. `models/kbo_model.py::finalize` replaces confidence with ordinal model
   strength:

```text
confidence = (model_score - 42.4) / (59.6 - 42.4) * 100
```

The final exported confidence therefore means relative position within the
active KBO ordinal score range. A value of `75` means the score is about 75% of
the way from `42.4` to `59.6`; it does not mean 75% win probability,
historical reliability, or calibrated prediction certainty.

Audit classification: **RENAME/CLARIFY**.

## Recommendation Thresholds

File: `models/kbo_model.py::_model_score_recommendation`

| Tier | Ordinal Score |
|---|---:|
| STRONG PLAY | `>= 58.0` |
| PLAYABLE | `>= 55.0` |
| LEAN | `>= 52.0` |
| NO PLAY | otherwise |

Thresholds are monotonic. With bullpen and recent form neutral, `LEAN` and
`PLAYABLE` are currently reachable; `STRONG PLAY` is compressed out of the
practical starter/offense-only range and remains a Phase 3 validation item.

Audit classification: **COHERENT**, with Phase 3 validation still required.

## Market Handling

`finalize` computes SSRP/reference edge when a locked reference is available,
otherwise leaves edge unavailable. Recommendation tier and final confidence use
only the ordinal model score.

Audit classification: **PASS** for market independence.

## Hammer / Ranking / Best Bets

The KBO adapter does not run `engine/decision/hammer_score.py`. It maps KBO
model confidence into `Recommendation.hammer_score`, then shared ranking uses
that score along with tier, model probability/score, confidence fallback, and
stable identity. Best Bets inherits Registry ordering.

Audit classification: **REVIEW**. This is coherent as legacy compatibility,
but KBO does not have an explicit Hammer layer comparable to MLB. The field
name overstates what is actually present.

## Neutral Components

Bullpen is intentionally neutral because no already-available KBO bullpen ERA,
KBO bullpen WHIP, or equivalent team relief metric was found wired into the
current scoring pipeline. Activating this component later requires a real KBO
team bullpen input with source provenance, missing-data behavior, and tests
showing it measures relief-pitching quality rather than schedule position.

Recent form is intentionally neutral because no genuine recent KBO team-results
or rolling-performance input was found wired into the current scoring pipeline.
Activating this component later requires a real recent-form data source, a
defined lookback window, neutral incomplete-data behavior, and tests showing it
does not duplicate offense/starter signals without disclosure.

## Current Behavior Walkthrough

For a game with neutral starters, away runs/game above home runs/game, and
neutral bullpen/recent form:

```text
offense_score = +1
weighted_score = +0.25
model_strength/model_probability = 52.0
selected team = away
recommendation = LEAN
```

For the mirrored home offensive advantage:

```text
offense_score = -1
weighted_score = -0.25
model_strength/model_probability = 48.0
selected team = home
recommendation = NO PLAY
```

For a zero weighted score:

```text
model_strength/model_probability = 50.0
selected team = none
recommendation = NO PLAY
```
