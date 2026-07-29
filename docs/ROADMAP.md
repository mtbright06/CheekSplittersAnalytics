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

All defined Sprints 52-56 are complete. Sprints 62-64 established the local
prediction-persistence, results, and grading architecture. Sprint 65 is the
operational wiring step: apply the reviewed schema through the normal Azure
release process, persist the daily Registry, ingest authoritative results, and
grade eligible historical snapshots before beginning model-health reporting.

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

## Sprint 62: Azure Prediction Persistence and Active Recommendation Lifecycle

**Status:** Complete.

Immutable PredictionSnapshots, deterministic idempotency, append-only
activation events, and one active recommendation slot per game/league/market
are operational in Azure. Immutable snapshots, results, and grades now provide
the durable historical foundation for reporting and future analytics.

# Completed Outcomes and Learning Foundation

**Rationale:** persistence gives SharpStack durable prediction memory. Results
ingestion provides objective outcome truth. Grading connects predictions to
outcomes. Model Health turns graded outcomes into evidence. The next priority
is a permanent application shell so historical intelligence can plug into a
stable interface.

## Sprint 63: Results Ingestion

**Status:** Complete.

Store objective provider game truth only: provider game identity, final status,
away/home scores, derived final total, winner, completion timestamp,
regulation/extra-inning context where available, postponed/canceled/suspended/
incomplete states, and source metadata. Ingestion must be correction-safe and
refresh-safe.

Do not grade recommendations or calculate ROI, profit, CLV, or model-health
metrics in this sprint.

## Sprint 64: Recommendation Grading

**Status:** Complete.

Grade immutable PredictionSnapshots against authoritative results as `WIN`,
`LOSS`, `PUSH`, `VOID`, `UNGRADEABLE`, or `PENDING` where appropriate. Preserve the
exact recommendation UUID, keep superseded snapshots historically gradable,
and distinguish final active-call performance from all historical snapshots.

Prepare for later odds-based profit and ROI, but do not require either in the
first grading implementation.

Sprint 64 uses an immutable `RecommendationGrade` record linked to the
persisted prediction snapshot and a specific `GameResult` revision. It stores
only derived evaluation status, grading version, and timestamps. The legacy
wager-settlement table remains separate and is not a Sprint 64 input or output.

## Sprint 65: Operational Persistence Wiring

**Status:** Complete.

Wire the existing immutable PredictionSnapshot, GameResult, and
RecommendationGrade services into the standard daily build. Persist the
completed Registry idempotently, ingest authoritative provider results through
the ingestion service, and grade matching snapshots by stable provider game
identity. This sprint does not add analytics, ROI, CLV, or model-health
reporting.

## Sprint 66: Model Health

**Status:** Complete.

Observe existing behavior through overall accuracy, recommendation-tier and
confidence performance, probability calibration, Hammer and Market Value
effectiveness, league/market/model-version breakdowns, time-series views, and
final-active-call versus all-snapshot performance.

Do not alter recommendation logic from early samples. Model changes require
adequate sample size and documented evidence.

## Sprint 67: Model Health

**Status:** Complete.

Expose the read-only Model Health report through the SharpStack dashboard.
The page groups latest immutable grades by league, market, and recommendation
tier while excluding legacy rows by default.

## Sprint 68: Application Shell Redesign

**Status:** Sprint 68.1 implemented; awaiting review.

Sprint 68.1 establishes the permanent shell only: a compact left sidebar, a
slim top bar, and a single route configuration for all existing pages,
including Model Health. Existing page renderers, styling, analytics, and model
behavior remain unchanged. Component-library and page-redesign work remain out
of scope.

## Sprint 69: Recommendation Explorer 2.0

Build the historical recommendation browser with filters for date, league,
market, tier, grade, matchup, and selection. Each record should expose its
immutable snapshot, market context, explanation, latest grade, revision, and
model version.

## Sprint 70: ROI Analytics

## Sprint 71: Closing Line Value

## Sprint 72: Calibration

## Sprint 73: Recommendation Attribution

## Sprint 74: Historical Charts

## Sprint 75: Model Version Comparison

# Deferred Priorities After Sprint 75

## Sprint 57: Provider Reliability

**Status:** In review — Phases 1 and 2 implemented; deferred behind the
approved outcomes-and-learning sequence.

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

# Epic 2: Model Intelligence

**Status:** Not started

These enhancements remain planned after the approved Sprint 68-75 sequence:

- Source Quality Confidence
- Lineup-Aware Offense
- Rolling Form
- Park & Weather Integration

# Deferred Measurement Follow-On

**Status:** Deferred behind Sprint 68-75.

Measurement reports what has already happened. It does not alter model
weights, probabilities, Hammer, thresholds, or recommendations.

Priority deliverables:

- Recommendation Performance Dashboard, after Sprint 66 establishes model
  health and sufficient persisted recommendation history exists
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

# Deferred Calibration and Optimization

**Status:** Deferred

No calibration implementation begins until sufficient graded recommendation
history exists.

Includes:

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

Deferred follow-on dashboards consume the outcome, grading, health, and market
records created by Sprints 63-66. They do not replace those foundational
systems.

- historical performance views
- ROI and units
- rolling performance
- signal attribution
- recommendation replay
- model-version comparison

## Pitching Intelligence

Epic 1 owns the active pitching-correctness queue. Pitching enhancements remain
deferred until that queue completes.

## Market Intelligence

Post-Sprint 75 research and later follow-ons:

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

Do not promote deferred provider work, Epic 2, calibration, or Epic 4 work
ahead of the approved Sprint 68-75 sequence. Deferred measurement and
calibration work remain evidence-gated.
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
