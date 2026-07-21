# SharpStack Architecture

> The architecture document is the long-term technical constitution of SharpStack.
> It describes **how the platform is intentionally designed**, not what a single
> sprint happens to be implementing.

---

# 1. Vision

SharpStack is an explainable sports analytics platform built around reproducible
models, canonical decision contracts, immutable historical records, and
evidence-driven evolution.

Every architectural decision should improve one or more of:

- Accuracy
- Explainability
- Reproducibility
- Maintainability
- Historical analysis

---

# 2. Engineering Principles

These principles guide every design decision.

1. Fix plumbing before tuning models.
2. One source of truth is always preferred over duplicated calculations.
3. Presentation consumes data; it never computes recommendations.
4. Small targeted changes are preferred over broad refactors.
5. Explainability is a feature—not an afterthought.
6. Historical evidence beats intuition when calibrating models.
7. Every recommendation should be reproducible.

---

# 3. Layered Architecture

External Providers
        │
        ▼
Provider / Ingestion Layer
        │
        ▼
Sport Models
        │
        ▼
Decision Builder
        │
        ▼
Recommendation Registry
        │
        ▼
Persistence / Analytics
        │
        ▼
Presentation
(Dashboard, Discord, Reports, API)

Each layer has a single responsibility.

---

# 4. Canonical Ownership

To prevent duplicated logic, every major concept has a single owner.

| Concept | Canonical Owner |
|---------|-----------------|
| Model projections | Sport-specific models |
| Signal integration | Decision Builder |
| Consensus | Decision Builder |
| Hammer Score | Decision Builder |
| Recommendation Registry | Recommendation Registry builder |
| Play of the Day | Play of the Day service |
| Historical grading | Analytics layer |
| Rendering | Presentation layer |

Downstream consumers must never rebuild upstream decisions.

---

# 5. Decision Builder

Decision Builder is the heart of SharpStack.

Responsibilities:

- Normalize model outputs.
- Match games.
- Integrate model signals.
- Determine agreement and contradiction.
- Validate markets.
- Calculate Hammer.
- Produce canonical recommendation data.
- Produce canonical consensus.

No downstream component should reinterpret these decisions.

---

# 6. Consensus Architecture

Consensus is a first-class architectural contract.

Decision Builder owns:

- support / oppose direction
- agreement counts
- contradiction counts
- agreement percentage
- supporting modules
- opposing modules

Recommendation Registry serializes this information.

Consumers display it.

Consumers do not recompute it.

---

# 7. Recommendation Lifecycle

Provider Data

↓

Model Outputs

↓

Decision Builder

↓

Recommendation Registry

↓

Play of the Day

↓

Dashboard / Discord / Reports

Every consumer should observe identical recommendation semantics.

---

# 8. Hammer Philosophy

Hammer is an explainable composite recommendation score.

It incorporates approved model inputs such as:

- model strength
- agreement
- contradiction penalties
- market quality
- edge
- approved adjustments

Hammer must always remain explainable.

---

# 9. Ranking Philosophy

Ranking determines ordering among already-qualified recommendations.

Current weighting:

- Hammer 60%
- Consensus 18%
- Edge 10%
- EV 7%
- Market Quality 5%

Observation:

Hammer currently influences both qualification and ranking.

This is intentional for now.

Future changes require historical evidence—not individual slate results.

---

# 10. Recommendation Philosophy

Recommendation quality is determined by:

1. Correct data.
2. Correct plumbing.
3. Correct integration.
4. Correct scoring.
5. Historical validation.

Never reverse this order.

---

# 11. Explainability

Every recommendation should answer:

- Why?
- Why not?
- What helped?
- What hurt?
- How confident is the platform?

Explainability is shared across all presentation layers through common
contracts.

---

# 12. Persistence Principles

Recommendations are immutable.

Odds history is append-only.

Every recommendation traces back to:

- Game
- Model Version
- Model Run
- Timestamp
- Supporting evidence

---

# 13. Architecture Change Gate

Before changing architecture, document:

- Current rule
- Feature blocked
- Evidence
- Smallest change
- Files affected
- Compatibility
- Testing
- Rollback

Architecture changes require explicit approval.

---

# 14. Current Focus

Current development is improving decision quality rather than adding new
features.

Primary objectives:

- Canonical consensus ownership
- Analytics refinement
- Historical performance
- Closing Line Value
- Multi-sport readiness

---

# 15. What Must Never Happen

- Duplicate recommendation logic.
- Duplicate consensus calculations.
- Presentation-layer scoring.
- Database access from prediction engines.
- Historical recommendation mutation.
- Hammer recalibration from anecdotal results.
- Broad refactors without a feature need.

---

# 16. Long-Term Direction

SharpStack should evolve through measurable improvements supported by historical
results.

Every major enhancement should preserve:

- explainability
- reproducibility
- architectural separation
- canonical ownership
- long-term maintainability

When in doubt, prefer the simpler design that produces one trustworthy answer.
