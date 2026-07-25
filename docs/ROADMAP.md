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
- Sprint 55 - Better Pitching Metrics Investigation
  - research completed; no production advanced metric approved
- Sprint 56 - KBO Confidence Correctness
  - confidence and real-market finalization corrected without market leakage
- SSRP v1 - Immutable MLB/KBO moneyline reference price
  - first eligible pregame quote persists as the edge reference; current odds
    remain display data
- MLB market freshness and quote provenance
  - selected quote freshness metadata and completed artifact timestamps are
    traceable and timezone-safe
- MLB conviction and market-value separation
  - model probability plus confidence determine the MLB moneyline conviction
    tier; SSRP edge independently determines market-value classification

# Epic 1: Model Correctness

**Status:** Active

Completed:

- Remove Market Leakage
- Explainable MLB Confidence
- Default Value Audit
- Explicit MLB API Parameters
- Sprint 53 - MLB Bullpen Provider
- Sprint 54 - Pitcher Sample Stabilization
- Sprint 55 - Better Pitching Metrics Investigation
- Sprint 56 - KBO Confidence Correctness
- SSRP v1, market freshness/provenance, and MLB conviction/market-value
  separation

All defined Sprints 52-56 are complete. Epic 1 remains active for validation
and approved technical-debt work; selecting a new sprint requires governance.

## Sprint 57: Provider Reliability

**Status:** In review — Phases 1 and 2 implemented.

Phase 1 adds a request-scoped pitcher game-log cache for one MLB card build.
It removes duplicate starter/bullpen game-log requests without persistent
caching, contract changes, or model behavior changes. Later phases remain
limited to approved provider efficiency and source-quality work.

Phase 2 adds a request-scoped MLB team-context cache for doubleheaders. It
reuses deterministic batting and bullpen retrieval by team ID within one card
build, while retaining separate game-specific starter construction and no
persistent cache.

Consciously deferred: a shared MLB schedule snapshot across the MLB Card,
First Five, and Bomb Lab. Measured savings are approximately 0.52 seconds per
build, below 1% of total build time. Do not implement this unless build
orchestration changes substantially or schedule retrieval becomes materially
more expensive.

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

Formerly S52-007. Completed research; no production integration approved.

Findings:

- FIP is not an additive production feature; it overlaps current HR/9, K/9,
  and BB/9 inputs.
- Advanced metrics must contribute independent predictive information and pass
  out-of-sample validation before production use.
- xERA is the preferred future evaluation candidate only if licensed, validated,
  and operationally supportable.
- No production model changes resulted from Sprint 55. See
  `SPRINT_55_PITCHING_METRICS_EVALUATION.md`.

## Sprint 56: KBO Confidence Correctness

Formerly S52-008. Completed.

Delivered:

- Replaced mock-edge/reason-count confidence with explainable model separation,
  data quality, and starter-certainty inputs.
- Unknown starters reduce confidence; missing market data receives no market
  completeness credit and cannot create an edge or actionable recommendation.
- Real market edge and recommendation are finalized only after odds enrichment.

# Epic 2: Model Intelligence

**Status:** Not started

These enhancements intentionally occur after Epic 1 completes:

- Source Quality Confidence
- Lineup-Aware Offense
- Rolling Form
- Park & Weather Integration

# Epic 3A: Recommendation Measurement & Historical Intelligence

**Status:** Planned for Sprint 63, or the earliest approved point after
sufficient persisted recommendation history is available

Measurement reports what has already happened. It does not alter model
weights, probabilities, Hammer, thresholds, or recommendations.

Priority deliverables:

- Recommendation Performance Dashboard (Sprint 63 target; highest-priority
  Epic 3A deliverable once persisted recommendation history is sufficient)
  - recommendation count and historical record
  - win/loss and win rate by recommendation tier
  - win/loss and win rate by market-value tier
  - recommendation distribution, average odds, and ROI where outcomes exist
  - CLV display when closing-line data exists
- Historical Intelligence (next Epic 3A deliverable)
  - matchup-level recent history by recommendation tier and conviction/value
    combination
  - aggregate record, ROI, and closing-line context where available
- Azure persistence verification and Recommendation History reporting

These are validation capabilities, not model features. They make the existing
conviction-versus-market-value contract observable before any recalibration.

# Epic 3B: Calibration & Persistence

**Status:** Deferred

No calibration implementation begins until sufficient graded recommendation
history exists.

Includes:

- Recommendation grading
- Weight optimization
- Probability calibration
- Hammer Score calibration
- CLV analysis
- ROI analysis

# Epic 4: Platform

**Status:** Future

- Explainability Dashboard
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
- MLB conviction and SSRP market-value explanations

Current:

- improve MLB input quality
- improve uncertainty handling
- preserve explainability

Later:

- ranking calibration
- threshold calibration
- historical signal attribution

## Historical Analytics

Epic 3A measurement goals:

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

Do not promote Epic 2, Epic 3A, Epic 3B, or Epic 4 work while Epic 1 remains
active. Epic 3A measures existing recommendations; Epic 3B calibrates only
after sufficient graded history exists.
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
