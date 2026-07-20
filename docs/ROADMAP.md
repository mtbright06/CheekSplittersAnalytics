# SharpStack Roadmap

## Roadmap Principles

- Finish one usable feature at a time.
- Prefer analytics quality over adding new surfaces.
- Do not build presentation before stable backend contracts.
- Do not recalibrate scores before historical evidence exists.
- Preserve immutable recommendation and append-only market history.
- Use structured explanation contracts instead of surface-specific reasoning.
- Keep renderers presentation-only.

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

## Objective

Expose the existing structured Totals Explanation contract through the dashboard UI.

The dashboard becomes the primary presentation layer for MLB Totals recommendations.

No backend redesign is expected.

---

## Goals

- Integrate structured explanations into dashboard cards.
- Reuse existing explanation contract.
- Preserve renderer-only presentation responsibilities.
- Keep backend recommendation engine unchanged.

---

## Investigation

Review:

- dashboard/components/mlb/mlb_card.py
- dashboard/card_loader.py
- output/cards/mlb_card.json

Determine how explanation payloads currently flow.

---

## Success Criteria

Dashboard displays:

- Recommendation
- Selection
- Projected Total
- Market Total
- Edge
- Confidence
- Compact Explanation

No duplicate explanation logic exists.

All existing validation continues passing.

closing line value
Measure CLV by recommendation, market, tier, model version, signal combination, and rolling period.
---

## Deferred

Renderer wording polish.

Discord integration.

Recommendation Explorer integration.


## Sprint 45 — API Layer

Expose stable endpoints for model runs, recommendations, history summaries, model health, ROI, CLV, and Play of the Day audit.

Guardrail: return DTOs/schemas, not raw ORM entities.

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
