# SharpStack Roadmap

## Roadmap Principles

- Finish one usable feature at a time.
- Prefer analytics quality over adding new surfaces.
- Do not build presentation before stable backend contracts.
- Do not recalibrate scores before historical evidence exists.
- Preserve immutable recommendation and append-only market history.
- Use structured explanation contracts instead of surface-specific reasoning.
- Keep renderers presentation-only.

# Strategic Feature Tracks

These tracks span multiple sprints.

A sprint may advance one or more tracks, but unfinished work remains associated
with its feature track until completed.

This prevents long-term initiatives from disappearing as sprint priorities
change.

---

## Track 1 — MLB Recommendation Engine
Status: Active

Completed

- Recommendation framework
- Hammer integration
- Totals recommendations
- Structured explanations
- Dashboard totals integration

Remaining

- Recommendation Explorer
- Recommendation replay
- Model comparison
- Recommendation semantics split

---

## Track 2 — Historical Analytics
Status: Active

Completed

- Recommendation history foundation

Remaining

- Historical grading
- ROI
- Rolling performance
- Signal attribution
- Recommendation confidence studies

---

## Track 3 — Market Intelligence
Status: Planned

Remaining

- Odds history
- Line movement
- Closing Line Value
- Sportsbook comparisons
- Steam movement
- Market efficiency analytics

---

## Track 4 — Platform Services
Status: Planned

Remaining

- Query services
- API layer
- DTO contracts
- Authentication
- Public API

---

## Track 5 — Dashboard Experience
Status: Active

Completed

- Dashboard totals explanations

Remaining

- Recommendation Explorer
- Historical analytics views
- CLV views
- Market comparison
- Explorer filters
- Search
- Favorites

---

## Track 6 — Discord Automation
Status: Planned

Remaining

- Daily recommendations
- Health warnings
- Live alerts
- Daily recap
- Recommendation cards

---

## Track 7 — Multi-Sport Expansion
Status: Planned

Target Sports

- KBO
- Soccer
- NFL
- NBA
- NHL
- College Baseball
- College Football

Shared Contracts

- Game identity
- Recommendation
- Odds history
- Grading
- Analytics
- Dashboard consumers

## Current Position

### Sprint 39 — Signal Plumbing Repair

Completed:

- First5 game matching repaired
- First5 recommendation extraction repaired
- `decision_score` prioritized
- empty-market fallback repaired
- Hammer diagnostics persisted
- Hammer weights intentionally unchanged

### Sprint 40 — Recommendation History Foundation

Completed as the persistence and continuity foundation for recommendation history and future analytics.

Historical grading, ROI, and performance analytics remain active priorities.

### Sprint 41 — MLB Totals Recommendations

Completed and committed:
f289bf9 feat: add bettor-facing MLB totals recommendations
829d0ea feat: add structured totals explanation contract and renderer
## Current Position

SharpStack has completed the core signal-integration repair for MLB Decision Builder.

Verified state:

- First5 availability: 16 / 16 games
- Real sportsbook markets: 16 / 16 games
- First5 game matching repaired
- First5 recommendation extraction repaired
- First5 `decision_score` prioritized
- Empty-market fallback repaired
- Hammer diagnostics persisted
- Recommendation distribution appears healthy
- Hammer weights intentionally unchanged

The project is now moving from infrastructure and signal plumbing into historical analytics and model quality.

## Sprint 40 — Recommendation History Analytics

### Primary Objective

Turn stored recommendations into trustworthy performance analytics.

### Scope

1. Query stored recommendations and model runs.
2. Add or complete result grading.
3. Calculate win percentage, losses, pushes, units, ROI, average odds, and rolling 7-day/30-day summaries.
4. Break down performance by recommendation tier, market, model version, Hammer range, signal combination, and real-market status.
5. Produce CLI/report output before dashboard work.

### Constraints

- No architecture redesign.
- No React work.
- No Hammer-weight changes.
- No unrelated odds-provider changes.
- Do not mix intentionally uncommitted provider/game-builder files into this sprint unless explicitly required.

### Definition of Done

- Historical recommendations can be queried.
- Grading produces correct win/loss/push results.
- Units and ROI are verified with tests.
- Rolling summaries are reproducible.
- Output includes model and signal context.
- Changes are committed and pushed.
- Handoff and roadmap are updated.

## Sprint 41 — Play of the Day Audit

Document the current selection algorithm, determine whether it duplicates or bypasses Hammer, compare selected plays with top Hammer recommendations, evaluate agreement and market context, and test historical candidate rules.

Guardrail: do not introduce a second unexplained composite score.

## Sprint 42 — Model Health Report

Create a morning system-health report with games loaded, market/Bomb/First5 coverage, real-market count, unmatched games, Hammer distribution, recommendation distribution, agreement/contradiction counts, missing data, stale data, and pipeline warnings.

Deliver CLI/report first.

## Sprint 43 — Odds History and Line Movement

Persist append-only odds observations and expose line movement, including provider, sportsbook, observed timestamp, line, price, normalized market, and opening/current/closing identification.

Dependency: recommendation history and grading should be stable first.

---

# Sprint 44 — Dashboard Totals Explanation Integration

Status: COMPLETE

Commit

0e430e7

Delivered

- Dashboard totals model card
- Structured explanation integration
- Renderer-only implementation
- Existing explanation contract reused
- UI formatting improvements
- End-to-end dashboard validation

Validation

- py_compile passed
- tools_test_mlb_totals.py passed
- Dashboard verified
---
# Sprint 45 — Recommendation Explorer (Phase 1)

Objective

Begin the Recommendation Explorer.

The Explorer becomes the primary dashboard experience for viewing every
SharpStack model for a single matchup.

Scope

- Explorer shell
- Moneyline section
- Totals section
- Existing explanation integration
- Navigation framework for future model tabs

Future phases will integrate:

- Hammer
- Bomb Lab
- First 5
- Market comparison
- Historical analytics
- Recommendation replay

Constraints

Presentation only.

Reuse existing DTOs.

Reuse existing explanation contracts.

Do not duplicate model logic.

## Sprint 46

Priority 1
- Recommendation scoring improvements
- Recommendation confidence tuning
- Market edge refinements

Priority 2
- MLB engine enhancements
- First 5 model improvements
- Recommendation analytics

Priority 3
- Dashboard refresh helper
- Additional historical analytics

## Deferred

Renderer wording polish.

Discord integration.

Recommendation Explorer integration.


#
## Objective

Create a unified game explorer capable of displaying every SharpStack model for an individual matchup.

## ScopeSprint 45 — Recommendation Explorer

Present existing outputs for:

- Moneyline
- Totals
- Hammer
- Bomb Lab
- First 5
- Market Comparison
- Structured Explanations

## Constraints

Do not duplicate recommendation logic.

Do not duplicate explanation logic.

Do not redesign backend services.

Explorer consumes existing DTOs and serialized outputs.

## Success Criteria

A single dashboard view presents all model outputs for one game while remaining presentation-only.

## Sprint 46 — Dashboard

Build daily slate, model health, history, trends, model comparison, signal analytics, line movement, and CLV views after APIs stabilize.

## Sprint 47 — Discord Integration

Publish finalized recommendations and health warnings through a stable integration layer. Discord must consume existing outputs and must not calculate model logic independently.

## Multi-Sport Expansion

After MLB history, grading, and analytics stabilize, apply shared contracts to KBO, soccer, WNBA, and future sports.

Shared contracts:

- Game identity
- ModelVersion
- ModelRun
- Recommendation
- Odds history
- Grading
- Analytics

## Deferred Ideas

- automated model calibration
- bankroll management
- portfolio optimization
- recommendation deduplication
- alerting
- anomaly detection
- retraining pipelines
- feature store
- experiment tracking
- user accounts and permissions

## Priority Order

1. Historical grading and ROI
2. Play of the Day audit
3. Model health
4. Odds history
5. CLV
6. API
7. Dashboard
8. Discord
9. Multi-sport expansion
