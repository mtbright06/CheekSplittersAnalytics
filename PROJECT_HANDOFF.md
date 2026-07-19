# SharpStack Project Handoff

**Last Updated:** 2026-07-19
**Sprint:** 38
**Status:** STABLE – Core MLB Decision Pipeline Restored
**Branch:** main

---

# Project Vision

SharpStack is evolving into a professional sports betting analytics platform capable of producing transparent, explainable recommendations across multiple sports while maintaining complete historical tracking.

Current supported sports:

* MLB
* KBO

Future roadmap:

* NFL
* NCAA Football
* NBA
* NHL
* Soccer

Primary engineering goals:

* Produce explainable recommendations
* Track every recommendation historically
* Measure model performance over time
* Support model experimentation and versioning
* Maintain immutable historical results
* Keep individual modules loosely coupled

---

# Current Architecture

Current production pipeline:

```
Schedule
    ↓
Model Generation
    ↓
MLB Card / KBO Card
    ↓
Decision Builder
    ↓
Decision Card
    ↓
Recommendation Registry
    ↓
Play of the Day
    ↓
Reports / Dashboard
```

The **Decision Builder** is now the canonical translation layer between model output and recommendation generation.

---

# Sprint 38 Summary

## Primary Objective

Restore the MLB recommendation pipeline after recommendation generation unexpectedly returned almost no actionable output.

---

# Root Cause

The issue was **not** inside the Recommendation Registry.

The issue was **not** inside Play of the Day.

The issue was **not** inside the reporting pipeline.

The actual failure occurred inside:

```
engine/decision/decision_builder.py
```

The Decision Builder had fallen behind the current MLB card schema.

Older code expected fields such as:

```python
away
home
pick
model_probability
game_pk
```

The current MLB card now provides:

```python
teams.away
teams.home
matchup
model.play
model.model_probability
model.component_scores
market_edge
totals_model
game_id
```

Because of this mismatch:

* team extraction failed
* model selection failed
* game matching failed

Every MLB game was skipped before recommendations could be generated.

---

# Major Work Completed

## Decision Builder rebuilt

The Decision Builder was updated to support both the legacy schema and the current nested MLB schema.

New compatibility includes:

* `teams.away`
* `teams.home`
* `matchup`
* `model.play`
* `model.model_probability`
* `component_scores`
* `market_edge`
* `odds`
* `totals_model`
* `game_id`

Legacy support remains intact.

---

## Market fallback restored

If First 5 market data is unavailable, the Decision Builder now falls back to MLB card market data.

This restores:

* sportsbook
* moneyline
* implied probability
* market edge
* expected ROI
* real-market classification

---

## Totals integration

Decision records now expose:

* projected total
* market total
* total edge
* total recommendation
* totals model

These values are now available for downstream reporting.

---

## Recommendation Registry validated

Registry generation now succeeds.

Current verified output:

```
Recommendations: 16
Actionable: 1
Real Market: 15
Model Only: 1
```

The Recommendation Registry is confirmed healthy.

---

## Play of the Day validated

Current output:

```
No recommendation met the Play of the Day requirements.
```

This is expected behavior.

The current threshold requires:

```
minimum_hammer_score = 74
```

Today's highest score:

```
Washington Nationals
Hammer Score = 69.3
```

No bug exists.

---

# Current Pipeline Health

Verified:

```
MLB Card
      ✓

Decision Builder
      ✓

Decision Card
      ✓

Recommendation Registry
      ✓

Play of the Day
      ✓
```

The MLB recommendation pipeline is fully operational again.

---

# Validation Results

Decision Builder produced:

```
Games Loaded: 16
Actionable: 1
Hammer Plays: 0
Bets: 0
Leans: 1
Real Market: 15
Model Only: 1
```

Recommendation Registry produced:

```
Recommendations: 16
Actionable: 1
Real Market: 15
Model Only: 1
```

Top recommendation:

```
Washington Nationals

Recommendation:
LEAN

Hammer:
69.3

Ranking:
75.5

Consensus:
4 / 6
```

---

# Current Known Limitations

## 1. First 5 integration

Decision output currently contains:

```
first5_score = None
first5_choice = ""
```

The pipeline tolerates this correctly.

Likely caused by a schema mismatch between:

```
first5_card.json
```

or

```
first5_market_card.json
```

and current game matching.

Needs investigation.

---

## 2. Bullpen quality

Bullpen module currently operates with limited confidence.

Current records indicate placeholder-quality bullpen values.

The engine currently treats bullpen as a neutral contributor.

---

## 3. Weather

Weather currently contributes no score.

Future enhancement only.

---

## 4. Totals recommendations

Totals projections now flow through the pipeline.

However, totals are still metadata rather than first-class recommendations.

Future work should allow outputs such as:

```
Moneyline:
Nationals

Total:
Under 9.5
```

---

# Engineering Principles

Do not rewrite working modules.

Work one file at a time.

Validate after every change.

Avoid broad architectural changes.

Prefer compatibility over replacement.

Never fabricate sportsbook information.

Never overwrite historical recommendation data.

---

# Current Repository State

Decision Builder:

Stable

Decision Card:

Stable

Recommendation Registry:

Stable

Play of the Day:

Stable

Dashboard:

Pending enhancement

Hammer calibration:

Next priority

---

# Recommended Next Sprint (Sprint 39)

Primary objective:

Improve recommendation quality rather than repairing infrastructure.

Priority order:

## 1. Investigate missing First 5 signals

Inspect:

```
output/cards/first5_card.json

output/cards/first5_market_card.json
```

Verify schema compatibility with Decision Builder matching logic.

---

## 2. Review Hammer Score

Inspect:

```
engine/decision/hammer_score.py
```

Document:

* score normalization
* recommendation thresholds
* agreement bonuses
* contradiction penalties
* unavailable-module behavior

Do not modify thresholds until current score distribution has been reviewed.

---

## 3. Review Play of the Day logic

Current rule:

```
minimum_hammer_score = 74
```

Determine whether:

* threshold
* consensus
* edge
* ROI
* contradiction checks

produce the desired level of selectivity.

---

## 4. Promote totals

Elevate totals into Recommendation Registry as independent recommendations rather than metadata.

---

# Start Here Next Chat

Begin with:

```
Review engine/decision/hammer_score.py.

Identify recommendation thresholds, weighting, normalization, bonuses, penalties, and unavailable-module handling.

Compare those rules against the current 16-game registry output before making any changes.
```

Do **not** rebuild the Decision Builder.

That work is complete.

---

# Suggested Commit

```
fix: restore MLB decision and recommendation pipeline
```

Commit summary:

* Updated Decision Builder for current MLB schema
* Restored market extraction
* Restored totals integration
* Restored Recommendation Registry pipeline
* Validated 16-game MLB output
* Verified Play of the Day behavior

---

# Definition of Done (Sprint 38)

✓ Decision Builder repaired

✓ MLB schema compatibility restored

✓ Decision Card populated

✓ Recommendation Registry restored

✓ Play of the Day validated

✓ End-to-end MLB recommendation pipeline operational

Sprint 38 is complete.
