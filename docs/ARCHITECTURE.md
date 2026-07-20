# SharpStack Architecture

## 1. Purpose

This document is the authoritative design reference for SharpStack.

Every new development chat must read it before proposing code. The handoff explains **where the project is now**; this document explains **how the system is designed, which boundaries are intentional, and which changes are prohibited unless explicitly approved**.

When a proposed implementation conflicts with this document, this document wins unless the user explicitly approves an architecture change.

## 2. Product Vision

SharpStack is a production-grade sports analytics platform that:

1. Ingests game, model, and market data.
2. Generates explainable betting recommendations.
3. Persists every recommendation and model run.
4. Tracks historical outcomes and performance.
5. Evaluates signal quality, model health, ROI, and closing-line value.
6. Supports multiple sports without coupling each sport's model logic to storage or presentation.
7. Produces human-readable output for console, reports, APIs, dashboards, and Discord.

SharpStack is not a single script. It is a modular analytics platform with separation between data ingestion, model computation, decision logic, persistence, analytics, reporting, and presentation.

## 3. Non-Negotiable Architecture Rules

### 3.1 Prediction Engines Stay Independent

Sports models and prediction engines must not depend on SQLAlchemy, Alembic, PostgreSQL, FastAPI, React, or presentation code.

The engine may produce Python objects, dictionaries, data classes, JSON, CSV, or report-ready structures.

The engine must not:

- open database sessions,
- issue SQL,
- import ORM models,
- know table names,
- know API routes,
- know dashboard components,
- or write directly to Discord.

### 3.2 Persistence Happens Through Services

Database writes occur through dedicated application/persistence services.

Preferred flow:

```text
Sports Engine
    ↓
Normalized Result / Recommendation DTO
    ↓
Application or Persistence Service
    ↓
SQLAlchemy ORM
    ↓
Azure PostgreSQL
```

### 3.3 Recommendation History Is Immutable

A saved recommendation represents what SharpStack knew and recommended at that point in time.

Do not overwrite historical recommendations after odds, lineups, models, projections, or outcomes change. A rerun creates a new ModelRun and new recommendation rows.

Corrections, grading, and outcomes must be added separately rather than rewriting the original recommendation.

### 3.4 Odds History Is Append-Only

Each odds observation is a new time-series record. Do not update one row to represent the latest odds.

Each observation should preserve provider, sportsbook, market, line, price, observed timestamp, game identity, and source metadata.

### 3.5 Every Recommendation Must Be Traceable

Every persisted recommendation must trace to:

- one Game,
- one ModelVersion,
- one ModelRun,
- its market/model context,
- its timestamp,
- and explainability components.

### 3.6 Backend First

Do not build the React dashboard before stable backend query and analytics services exist. Presentation consumes stable contracts and should not query ORM entities directly.

### 3.7 No Architecture Redesign Without a Feature Need

Do not revisit completed architecture because another pattern seems cleaner.

A redesign is justified only when a concrete feature is blocked, a verified defect requires it, data integrity is at risk, or the user explicitly approves it.

Any proposal must identify:

1. the feature blocked,
2. why the current design cannot support it,
3. the smallest required change,
4. migration and rollback impact,
5. and compatibility effects.

## 4. Current System Context

SharpStack currently includes working baseball analytics pipelines and supporting platform infrastructure:

- MLB game-level modeling,
- Bomb Lab,
- First5,
- First5 market integration,
- sportsbook market extraction,
- Decision Builder,
- Hammer diagnostics,
- recommendation output,
- recommendation persistence,
- Azure PostgreSQL,
- SQLAlchemy ORM,
- Alembic migrations,
- and end-to-end persistence/read-back verification.

The project is moving from infrastructure and signal plumbing into analytics refinement and historical performance analysis.

## 5. High-Level Architecture

```text
External Data Sources
    ├── schedules / probable pitchers
    ├── Statcast / model inputs
    ├── sportsbook markets
    ├── weather / park context
    └── future sport-specific providers
              ↓
Provider and Ingestion Layer
              ↓
Sport-Specific Models
    ├── MLB Model
    ├── Bomb Lab
    ├── First5 Model
    ├── First5 Market Model
    └── future sports
              ↓
Decision Builder
    ├── normalizes signals
    ├── applies agreement/contradiction logic
    ├── validates markets
    ├── computes Hammer diagnostics
    └── emits recommendation-ready output
              ↓
Application Integration Layer
    ├── converts output to persistence DTOs
    ├── starts ModelRun
    ├── saves recommendations
    └── preserves run metadata
              ↓
Azure PostgreSQL
              ↓
Analytics and Query Services
    ├── recommendation history
    ├── grading
    ├── ROI
    ├── model health
    ├── rolling summaries
    └── signal-combination performance
              ↓
Presentation
    ├── CLI
    ├── reports
    ├── REST API
    ├── dashboard
    └── Discord
```

## 6. Layer Responsibilities

### 6.1 Provider and Ingestion Layer

Responsibilities:

- retrieve source data,
- validate responses,
- normalize external identifiers,
- preserve source timestamps,
- detect missing or stale data,
- expose provider failures,
- and avoid model scoring logic.

Missing data must not be replaced with fabricated values. Fallbacks must be explicit and auditable.

### 6.2 Sport-Specific Model Layer

Responsibilities:

- calculate sport/model-specific projections,
- calculate model confidence or decision scores,
- expose component metrics,
- produce directional or neutral outputs,
- and remain independent of storage and UI.

Current First5 rules:

- prioritize `decision_score` over legacy confidence fields,
- recognize `f5_ml.lean`,
- and treat PASS as neutral rather than agreement.

### 6.3 Decision Builder

Decision Builder is the central signal-integration layer.

Responsibilities:

- match outputs to games,
- normalize recommendations,
- evaluate agreement and contradictions,
- validate whether a real market exists,
- calculate market edge and expected value where possible,
- produce Hammer score and tier,
- emit internal diagnostics,
- and preserve explainability.

Current Hammer diagnostics include:

- `agreement_bonus`
- `contradiction_penalty`
- `market_status_penalty`
- `real_market_loaded`

#### Matching Rule

Exact game IDs are preferred. When IDs differ but the matchup is the same, normalized matchup fallback is allowed. Ambiguous games must not be joined.

#### Market Fallback Rule

A non-empty dictionary does not prove a usable market exists. A real market requires actual sportsbook data such as provider identity, usable odds, line/implied probability, and required market fields.

`NO MARKET` or empty placeholder objects must not block fallback to another valid source.

#### Scoring Stability Rule

When output appears wrong, investigate in this order:

1. game matching,
2. field extraction,
3. missing data,
4. market validation,
5. score source selection,
6. agreement/contradiction direction,
7. only then score calibration.

## 7. Hammer Philosophy

Hammer is a composite decision score, not a raw probability.

It may incorporate base model strength, Bomb agreement, First5 agreement, market edge, contradiction penalties, missing-market penalties, and approved risk adjustments.

Hammer must remain explainable, with material adjustments visible in diagnostics.

Current tiers include LEAN, WATCH, and PASS. Do not change thresholds from one slate; calibration must use historical graded results.

PASS from a contributing model is a valid neutral outcome and should generally contribute neither agreement nor contradiction.

## 8. Persistence Architecture

### 8.1 Platform

- Azure PostgreSQL
- SQLAlchemy ORM
- Alembic migrations

Schema changes must be versioned through Alembic. Do not use metadata creation as a deployment substitute.

### 8.2 Core Entities

- **League** — competition such as MLB or KBO.
- **Team** — team within a league.
- **Game** — scheduled event with external identity and home/away teams.
- **ModelVersion** — model name, version, Git commit, and description.
- **ModelRun** — one model execution, including timing, status, source, label, notes, and metadata.
- **Recommendation** — immutable recommendation for one game, model version, and model run.

### 8.3 Transaction Boundary

Saving a run and recommendations should be atomic:

```text
Create/reuse League
Create/reuse Teams
Create/reuse Game
Create/reuse ModelVersion
Create ModelRun
Insert Recommendations
Mark ModelRun completed
Commit
```

No partial batch should remain after failure.

## 9. Data Contracts and Integration Boundary

Prediction engines do not pass ORM objects.

Recommended internal contract:

```text
GameIdentity
ModelIdentity
RunMetadata
RecommendationInput[]
```

The persistence service owns normalization required for storage, transaction management, entity lookup/reuse, run creation, recommendation insertion, and durable IDs. It must not recalculate model scores.

## 10. Recommendation History and Analytics

Recommended progression:

### Phase 1 — History Querying
- list model runs,
- view recommendations by run,
- filter by date, league/sport, market, tier, confidence, and model version.

### Phase 2 — Grading
- attach actual result,
- calculate win/loss/push,
- preserve grading timestamp,
- support market-specific grading,
- and never rewrite original recommendation fields.

### Phase 3 — Performance Analytics
- win percentage,
- units,
- ROI,
- average odds,
- performance by tier, market, version, signal combination, and Hammer range,
- rolling 7-day and 30-day summaries.

### Phase 4 — Market Analytics
- opening line,
- recommendation-time line,
- closing line,
- closing-line value,
- line movement,
- sportsbook/provider comparison.

## 11. Model Health Architecture

The health report should validate whether a slate is trustworthy before recommendations are used.

Minimum metrics:

- games loaded,
- model coverage,
- market coverage,
- Bomb coverage,
- First5 coverage,
- real sportsbook market count,
- average/median/high/low Hammer,
- recommendation distribution,
- agreement and contradiction counts,
- unmatched games,
- stale data,
- missing probable pitchers,
- provider and pipeline warnings.

The health report diagnoses condition; it should not silently repair or reinterpret output.

## 12. Play of the Day Architecture

Play of the Day must be selected from recommendation output, not an unrelated scoring path.

It may eventually consider Hammer, recommendation tier, Bomb/First5 agreement, real-market status, market edge, expected value, historical signal performance, odds range, data completeness, and risk adjustments.

Do not introduce a second unexplained composite score.

## Structured Explanation Architecture

Structured explanations are the reusable reasoning contract for presentation consumers.

The contract may contain:

- summary,
- strengths,
- risks,
- market evidence,
- contextual evidence,
- stable explanation ID,
- category,
- title,
- detail,
- impact,
- direction,
- metric,
- value,
- unit,
- confidence,
- evidence score,
- and priority.

Rules:

- Explanations describe existing model and recommendation output.
- Explanations must not recalculate projections, Hammer, market edge, confidence, or recommendation thresholds.
- Stable explanation IDs are downstream contracts and should not be renamed casually.
- Renderers may sort, limit, and format explanation items but must not change their meaning.
- Legacy `reasons: list[str]` may remain during migration.
- CLI, Discord, API, dashboard, and AI consumers should use the shared explanation contract rather than create independent reasoning logic.

## 13. Reporting and Presentation

Presentation layers must not own business logic.

- CLI/reports call query or analytics services.
- REST API returns stable schemas/DTOs, not raw ORM entities.
- Dashboard consumes API/query contracts.
- Discord consumes finalized outputs.

No presentation layer recalculates Hammer or projections.

## 14. Testing Strategy

### Unit Tests

Use for scoring, extraction, market validation, game matching, grading, and analytics math.

### Integration Tests

Use for persistence, transaction boundaries, provider adapters, history queries, and API/database integration.

### Slate Regression Tests

Use known slates to prevent regressions in game coverage, market coverage, recommendation distribution, First5 matching, and Hammer diagnostics.

Tests should assert behavior, not merely execution.

## 15. Database Change Policy

Before changing schema, answer:

1. What feature needs the change?
2. Why can the current schema not support it?
3. Is the change additive?
4. Is a backfill required?
5. What is the downgrade path?
6. How will it be tested?

Prefer additive changes, nullable transitions, separate backfills, and later tightening of constraints. Do not casually rename or delete historical columns.

## 16. Git and Sprint Workflow

Each sprint should have one primary goal, focused commits, validation before commit, push confirmation, an updated handoff, and an updated roadmap when priorities change.

Unrelated modified files must remain outside the sprint commit.


## 17. Prohibited Patterns

New chats must not:

- calculate recommendation logic inside a renderer,
- create separate explanation logic for each presentation surface,
- import SQLAlchemy into prediction engines,
- rewrite historical recommendations,
- overwrite odds history,
- build dashboard logic before backend contracts,
- recalibrate Hammer before validating plumbing,
- create duplicate scoring paths without justification,
- bypass Alembic,
- combine unrelated modified files into one commit,
- redesign completed services because another pattern is fashionable,
- or treat a non-empty market object as proof of real odds.

## 18. Architecture Change Gate

Before any architecture change, present:

```text
Current rule:
Feature blocked:
Evidence:
Smallest required change:
Files affected:
Schema impact:
Migration impact:
Backward compatibility:
Testing plan:
Rollback plan:
```

Wait for user approval before implementation.

## 19. New Chat Startup Protocol

Every new SharpStack chat should receive:

1. `PROJECT_HANDOFF.md`
2. `ARCHITECTURE.md`
3. `ROADMAP.md`
4. `CHAT_PROTOCOL.md`
5. `DEVELOPMENT_ENVIRONMENT.md`

The opening prompt should require the new chat to summarize the sprint, preserved constraints, expected files, and ambiguities before writing code.

## 20. End-of-Chat Protocol

Before ending a sprint chat, update:

- current sprint,
- completed work,
- validation,
- branch,
- latest commit,
- Alembic revision,
- intentionally uncommitted files,
- blockers,
- immediate next sprint,
- and exact next-chat prompt.

Update `ARCHITECTURE.md` only after an approved architecture change.

## 21. Approved Design Summary

The approved design is:

- independent sports engines,
- Decision Builder as signal-integration layer,
- Hammer as explainable composite decision score,
- persistence through services,
- immutable recommendations,
- append-only odds,
- ModelVersion and ModelRun traceability,
- Azure PostgreSQL with Alembic,
- analytics before presentation,
- and no redesign without a concrete approved need.
