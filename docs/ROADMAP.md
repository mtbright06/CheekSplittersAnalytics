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

# Current Status

Completed:

- S52-001 - Remove Market Leakage
- S52-002 - Explainable MLB Confidence
- S52-003 - Default Value Audit
- Explicit MLB API Parameters
- Sprint 53 - MLB Bullpen Provider
  - satisfies the original Real Bullpen Model work item, formerly S52-006
  - active roster and reliever game-log ingestion
  - canonical bullpen payload for totals and SharpScore compatibility aliases
- Sprint 54 - Pitcher Sample Stabilization
  - shared innings-based blending for starter ERA, WHIP, HR/9, K/9, and BB/9

# Epic 1: Model Correctness

**Status:** Active

Completed:

- Remove Market Leakage
- Explainable MLB Confidence
- Default Value Audit
- Explicit MLB API Parameters
- Sprint 53 - MLB Bullpen Provider
- Sprint 54 - Pitcher Sample Stabilization

## Sprint 54: Pitcher Sample Stabilization

Formerly S52-005. Completed.

Delivered:

- Centralized the existing 50-inning empirical-Bayes blend for ERA, WHIP,
  HR/9, K/9, and BB/9.
- Applied stabilized views to SharpScore, MLB totals, and First Five starter
  inputs without changing weights, confidence, or recommendation thresholds.
- Preserved raw-stat fallbacks when innings are absent; unknown starters remain
  a separate neutral-scoring state.

## Sprint 55: Better Pitching Metrics Investigation

Formerly S52-007. Research only; no production integration during this sprint.

Evaluate:

- FIP
- xFIP
- xERA
- SIERA

## Sprint 56: KBO Confidence Correctness

Formerly S52-008.

Correct confidence behavior for missing starters and missing market information.

# Epic 2: Model Intelligence

**Status:** Not started

These enhancements intentionally occur after Epic 1 completes:

- Source Quality Confidence
- Lineup-Aware Offense
- Rolling Form
- Park & Weather Integration

# Epic 3: Calibration & Persistence

**Status:** Deferred

No implementation begins until sufficient graded recommendation history exists.

Includes:

- S52-004 - calibration and persistence work remains deferred
- Azure persistence verification
- Recommendation grading
- Weight optimization
- Probability calibration
- Hammer Score calibration
- CLV analysis
- ROI analysis

# Epic 4: Platform

**Status:** Future

- Explainability Dashboard
- Analytics Dashboard
- NFL
- NHL

# Technical Debt and Research Queue

Preserve existing technical debt and research items until completed or separately
approved. Current items include:

- provider caching or batched MLB retrieval
- pitcher stabilization requires innings pitched; when innings are unavailable,
  observed statistics are preserved. Revisit this behavior as part of future
  source-quality work.
- explicit closer/setup availability inference
- reliever role-transition handling
- Hammer and ranking calibration research
- adaptive thresholds, feature importance, and automated tuning
- portfolio and Kelly optimization
- starter recency blending and metric-specific stabilization
- pitch quality, arsenal intelligence, and expected pitching metrics
- Stuff+, Location+, Pitching+, or comparable proprietary models

# Validation Queue

Preserve validation work until sufficient historical evidence exists:

- starter score validation
- bullpen component validation
- confidence-band performance
- Hammer and ranking review
- threshold calibration
- model-version comparison
- historical grading, ROI, and CLV analysis

# Design Decision Register

Architecture decisions remain governed by `ARCHITECTURE.md`: provider data and
normalization precede model tuning; sport models own projections; Decision
Builder owns integration; presentation consumes canonical outputs.

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

Epic 1 owns the active pitching-correctness queue. Pitching enhancements remain
deferred until that queue completes.

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

Epic 4 future work, after MLB reaches production quality:

- NFL
- NHL

# Explicit Anti-Drift Rule

Do not promote Epic 2, Epic 3, or Epic 4 work while Epic 1 remains active.
Do not redesign scoring or confidence during Sprint 54, and do not integrate
research metrics from Sprint 55 into production.

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
