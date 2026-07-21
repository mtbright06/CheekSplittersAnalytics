# SharpStack Roadmap

> This roadmap captures the strategic direction of SharpStack. It is organized
> by long-term initiatives rather than individual commits or sprint history.

---

# Guiding Principles

- Finish complete features before expanding scope.
- Improve decision quality before adding presentation.
- Validate with historical evidence.
- Preserve architectural separation.
- Prefer one canonical source of truth.
- Build reusable platform capabilities before sport-specific enhancements.

---

# Current Milestone

## Consensus Unification (Active)

Objective:

Establish Decision Builder as the canonical owner of recommendation consensus.

Deliverables:

- Single consensus contract
- Registry consumes canonical consensus
- Dashboard consumes registry
- Discord consumes registry
- Play of the Day consumes registry
- Eliminate duplicated agreement calculations

Success Criteria:

- Every consumer reports identical agreement values.
- Recommendation reasons and serialized consensus match.
- No downstream consensus reconstruction remains.

---

# Strategic Workstreams

## 1. Recommendation Intelligence

Status: Active

Completed

- Decision Builder
- Hammer Score
- Recommendation Registry
- Play of the Day
- Totals recommendations
- Structured explanations

Next

- Consensus unification
- Ranking refinement
- Recommendation semantics split
- Historical confidence validation

---

## 2. Historical Analytics

Status: Active

Goals

- Result grading
- Win/Loss/Push tracking
- ROI
- Units
- Rolling performance
- Signal attribution
- Historical replay

---

## 3. Market Intelligence

Status: Planned

Goals

- Closing Line Value
- Line movement
- Sportsbook comparison
- Market efficiency
- Opening vs closing analytics

---

## 4. Platform Services

Status: Planned

Goals

- Query services
- Stable DTO contracts
- REST API
- Authentication
- Public API

---

## 5. Dashboard Experience

Status: Active

Completed

- Recommendation Explorer foundation
- Structured explanations
- Recommendation Registry integration

Next

- Historical analytics
- CLV views
- Signal analysis
- Health dashboards
- Search and filtering

---

## 6. Automation

Status: Planned

Goals

- Automated daily builds
- Health reports
- Discord publishing
- Alerting
- Morning summaries

---

## 7. Multi-Sport Expansion

Status: Planned

Order

1. KBO
2. Soccer
3. NFL
4. NBA
5. NHL

Shared platform components will be completed before expanding models.

---

# Research Queue

These items require historical evidence before implementation.

- Hammer calibration
- Ranking calibration
- Adaptive recommendation thresholds
- Feature importance
- Automatic model tuning
- Kelly optimization
- Portfolio optimization

---

# Near-Term Priorities

1. Complete Consensus Unification.
2. Validate recommendation integrity.
3. Expand historical grading.
4. Implement CLV foundation.
5. Improve ranking with historical evidence.

---

# Deferred

- Mobile application
- OAuth
- Public API
- User accounts
- CI/CD
- Kubernetes
- Experiment tracking
- Automatic retraining

---

# Success Definition

SharpStack will be considered production-ready when it can:

- Produce explainable recommendations.
- Preserve immutable history.
- Grade historical performance.
- Measure ROI and CLV.
- Deliver identical decisions across every consumer.
- Support additional sports without architectural redesign.
