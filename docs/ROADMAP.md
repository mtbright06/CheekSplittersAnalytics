# SharpStack Roadmap

> Strategic priority order. This document defines what comes next and what does not.

# Guiding Principles

- Correct provider data before tuning models.
- Finish approved work before expanding scope.
- Reuse existing architecture.
- Prefer one canonical source of truth.
- Preserve backward compatibility.
- Validate with historical evidence.
- Keep presentation separate from prediction logic.
- Prefer small targeted changes over broad refactors.

# Current Milestone

## Sprint 52 â€” MLB Model Integrity and Data Quality

Completed:

- S52-001 â€” Remove market leakage
- S52-002 â€” Explainable confidence / unknown starters
- S52-003 â€” Default audit
- Explicit MLB API season and regular-season parameters
- S52-005 â€” Pitcher sample stabilization

In progress:

- S52-006 â€” Starter Model v2
  - starter-only game-log aggregation
  - safe season fallback
  - richer starter profile
  - stabilized skill-based starter score
  - end-to-end artifact validation

Deferred:

- S52-004 â€” Calibration
  - requires sufficient historical recommendations, outcomes, and market context

# Approved Near-Term Priority Order

## 1. Finish Starter Model v2

Success criteria:

- Starter and relief appearances are separated whenever game logs are available.
- Raw counts are aggregated and rates are recomputed.
- Tiny samples remain near neutral.
- Established strong and weak starters separate plausibly.
- Unknown starters remain neutral.
- Generated artifacts build successfully.
- Documentation, commit, and push are complete.

## 2. MLB Bullpen Provider and Integration

This is the next priority after the starter commit.

Deliverables:

- Inspect existing `engine/mlb/bullpen/` contracts.
- Build MLB roster and reliever ingestion.
- Normalize season and recent-use data.
- Produce `BullpenSnapshot`.
- Feed existing quality, fatigue, projection, and game-adjustment modules.
- Populate game-builder bullpen data.
- Share one normalized bullpen contract across totals and SharpScore.
- Add safe fallbacks and source-quality indicators.
- Validate provider data before tuning weights.

Success criteria:

- Bullpen payloads are populated for normal MLB games.
- Reliever identification is role-aware.
- Recent usage and availability are plausible.
- Existing bullpen modules remain canonical.
- Missing data degrades safely to neutral behavior.

## 3. KBO Confidence Improvements

Expected themes:

- unknown starter handling
- source quality
- confidence degradation
- role and sample awareness
- clear separation among playable, lean, recommendation, and pass

## 4. Historical Validation and Calibration

Only after the data and plumbing work above:

- starter score validation
- bullpen component validation
- confidence-band performance
- Hammer and ranking review
- threshold calibration
- model-version comparison

No calibration should be justified by a single slate.

# Strategic Workstreams

## Recommendation Intelligence

Completed:

- Decision Builder
- Hammer Score
- Recommendation Registry
- Play of the Day
- totals recommendations
- structured explanations
- canonical consensus direction

Current:

- improve MLB input quality
- improve uncertainty handling
- preserve explainability

Later:

- confidence vs attractiveness split
- ranking calibration
- threshold calibration
- historical signal attribution

## Historical Analytics

Goals:

- grading
- W/L/P tracking
- ROI and units
- rolling performance
- signal attribution
- recommendation replay
- model-version comparison

## Pitching Intelligence

Foundation:

- Starter Model v2
- MLB bullpen provider
- Bullpen quality model

Future:

- Starter Model v3 / recency
- metric-specific stabilization
- pitch quality
- expected metrics
- pitch arsenal intelligence
- historical calibration

This initiative should not expand until starter data correctness, bullpen
provider integration, and historical validation foundations are in place.

## Market Intelligence

Planned:

- Closing Line Value
- line movement
- sportsbook comparison
- market efficiency
- steam detection

## Dashboard Experience

Stable, not immediate priority.

Later:

- historical analytics
- CLV views
- model-health views
- bullpen transparency
- search and filtering
- palette refinements

## Automation

Planned:

- scheduled builds
- health reports
- Discord publishing
- alerting
- morning summaries

## Multi-Sport Expansion

After MLB and shared platform maturity:

1. KBO
2. Soccer
3. NFL
4. NBA
5. NHL

# Research Queue

Requires evidence or a separately approved investigation:

- Hammer calibration
- ranking calibration
- adaptive thresholds
- feature importance
- automated tuning
- Kelly optimization
- portfolio optimization
- starter recency blending
- metric-specific stabilization
- pitch quality and arsenal intelligence
- expected pitching metrics
- Stuff+, Location+, Pitching+, or comparable proprietary models

# Explicit Anti-Drift Rule

Until the bullpen provider and integration are complete, do not promote these into the active sprint without explicit approval:

- Starter Model v3
- last-three/last-five-start weighting
- metric-specific stabilization
- starter dashboard enhancements
- cosmetic dashboard changes
- calibration
- broad refactors
- new sports
- new public platform features

Approved sequence:

```text
Finish Starter Model v2
    â†“
Commit and push
    â†“
Bullpen provider and integration
    â†“
KBO confidence
    â†“
Historical calibration
```

# Production Readiness

SharpStack is production-ready when it can:

- ingest correct and role-aware provider data
- produce explainable recommendations
- preserve immutable history
- grade performance
- measure ROI and CLV
- deliver identical decisions across every consumer
- degrade safely when data is missing
- support additional sports without duplicating platform logic
