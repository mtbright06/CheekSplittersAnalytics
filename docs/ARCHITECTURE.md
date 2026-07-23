# SharpStack Architecture

> Long-term technical constitution of SharpStack.

# 1. Vision

SharpStack is an explainable sports analytics platform built around:

- correct and traceable provider data
- role-aware sport models
- canonical decision contracts
- immutable historical records
- reproducible builds
- evidence-driven model evolution

# 2. Engineering Principles

1. Fix provider data and plumbing before tuning models.
2. Prefer one source of truth over duplicated calculations.
3. Presentation consumes data; it never computes recommendations.
4. Sport models own sport-specific projections and inputs.
5. Decision Builder owns cross-signal integration.
6. Prefer small targeted changes over broad refactors.
7. Explainability is a first-class feature.
8. Historical evidence beats intuition for calibration.
9. Every recommendation should be reproducible.
10. Missing data must degrade safely and visibly.

# 3. Layered Architecture

```text
External Providers
        â†“
Provider / Ingestion
        â†“
Normalization / Role-Aware Profiles
        â†“
Sport Models
        â†“
Decision Builder
        â†“
Recommendation Registry
        â†“
Persistence / Historical Analytics
        â†“
Presentation
```

# 4. Canonical Ownership

| Concept | Canonical Owner |
|---|---|
| Raw provider retrieval | Provider / ingestion modules |
| Role-aware profiles | Sport normalization modules |
| Sport projections | Sport-specific models |
| Starter profile | `engine/mlb/pitchers.py` |
| Bullpen snapshot | MLB bullpen provider feeding `engine/mlb/bullpen/` |
| Signal integration | Decision Builder |
| Consensus | Decision Builder |
| Hammer Score | Decision Builder |
| Recommendation Registry | Registry builder |
| Play of the Day | Play of the Day service |
| Historical grading | Analytics layer |
| Rendering | Presentation layer |

Downstream consumers must not rebuild upstream decisions.

# 5. MLB Provider and Normalization

## Starter path

```text
MLB game logs
    â†“
fetch_pitcher_stats()
    â†“
filter gamesStarted > 0
    â†“
aggregate raw counts
    â†“
recompute rates
    â†“
starter profile
    â†“
game_builder
    â†“
sport models / component scores
```

Rules:

- Do not average game-log rate fields.
- Aggregate raw counts and recompute rates.
- Preserve a safe fallback.
- Surface source through `data_source`.
- Keep unknown or unusable samples neutral.
- A mixed-role season fallback is resilience, not the preferred path.

## Bullpen path

```text
MLB roster and pitching data
    â†“
Bullpen provider / role normalization
    â†“
BullpenSnapshot
    â†“
existing quality, fatigue, projection, adjustment modules
    â†“
game_builder
    â†“
totals and SharpScore
```

The existing `engine/mlb/bullpen/` subsystem is canonical and must be extended, not replaced.

Provider responsibilities:

- active roster retrieval
- reliever identification
- starter/reliever separation
- recent usage
- season performance
- availability inputs
- source quality and fallback

Bullpen model responsibilities:

- quality
- fatigue
- projection
- game adjustment

Presentation must not infer bullpen availability or quality.

# 6. Model Scoring

Component scores should:

- start from an explainable neutral baseline
- use normalized inputs
- handle missing values explicitly
- stabilize small samples
- clamp outputs
- avoid market leakage unless explicitly market-based

Starting-pitcher scoring currently uses stabilized:

- ERA
- WHIP
- K/9
- BB/9
- HR/9
- H/9
- K-BB%
- strike%
- pitches per inning
- ground/air ratio

The structure is approved; calibration is not complete.

# 7. Decision Builder

Responsibilities:

- normalize model outputs
- match games
- integrate signals
- determine agreement and contradiction
- validate markets
- calculate Hammer
- produce canonical recommendation data
- produce canonical consensus

Do not redesign Decision Builder without concrete evidence and approval.

# 8. Consensus

Decision Builder owns:

- support and opposition direction
- agreement counts
- contradiction counts
- agreement percentage
- supporting modules
- opposing modules
- consensus score and diagnostics

Registry serializes it. Consumers display it. Consumers do not recompute it.

# 9. Recommendation Lifecycle

```text
Provider Data
    â†“
Role-Aware Normalization
    â†“
Sport Models
    â†“
Decision Builder
    â†“
Recommendation Registry
    â†“
Play of the Day
    â†“
Dashboard / Discord / Reports / API
```

# 10. Hammer and Ranking

Hammer is an explainable composite score.

Ranking orders already-qualified recommendations.

Do not recalibrate Hammer or ranking from anecdotal slate results.

# 11. Explainability

Every recommendation should answer:

- Why?
- Why not?
- What helped?
- What hurt?
- What source was used?
- What uncertainty exists?
- How confident is the platform?

# 12. Persistence

- Recommendations are immutable.
- Odds history is append-only.
- Every recommendation should trace to game, model version, run, timestamp, market snapshot, and supporting evidence.
- Prediction engines must not depend directly on persistence.

# 13. Architecture Change Gate

Before changing architecture, document:

- current rule
- problem
- evidence
- smallest viable change
- files affected
- compatibility
- testing
- rollback

# 14. What Must Never Happen

- Duplicate recommendation logic
- Duplicate consensus calculations
- Presentation-layer scoring
- Database access from prediction engines
- Historical recommendation mutation
- Odds-history rewriting
- Averaging incompatible provider rate fields
- Treating mixed-role data as starter-specific without disclosure
- Creating a second bullpen model
- Calibration from a single slate
- Broad refactors without a validated need

# 15. Current Focus

1. Finish role-aware starter profiles and scoring.
2. Connect MLB data to the existing bullpen subsystem.
3. Improve explainable uncertainty.
4. Expand historical validation and CLV.
5. Preserve shared contracts for multi-sport growth.
