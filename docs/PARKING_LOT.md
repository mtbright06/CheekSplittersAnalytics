# SharpStack Parking Lot

> Valuable ideas intentionally deferred. Nothing here is approved or scheduled unless moved to `ROADMAP.md`.

# Purpose

Use this file to preserve ideas without interrupting the active objective.

# Starter Model Research

## Starter Recency Blend

Potential future blend:

- season starter profile for stability
- last five starts for current form
- last three starts for rapid change detection

Questions:

- What improves out-of-sample performance?
- How should injury return, opener usage, or role changes be handled?
- Should recency be separate rather than blended?

Do not implement before bullpen provider work and historical validation.

## Metric-Specific Stabilization

Current state:

- Starter Model v2 uses one global stabilization constant.
- That is acceptable for the current model because the priority was
  role-aware starter data correctness, not fine-grained calibration.

Future research may replace the global factor with metric-specific
stabilization constants backed by sabermetric research.

Different baseball statistics stabilize at different sample sizes. For
example:

- Strike%
- K%
- BB%

These tend to become meaningful relatively quickly.

Other metrics need larger samples:

- ERA
- WHIP
- H/9

HR/9 usually requires an even larger sample because home runs are sparse
events.

Potential future work:

- research stabilization points by metric
- replace the single constant with metric-specific constants
- document the source and rationale for each constant
- validate whether the added complexity improves historical performance

Do not tune from one slate.

## Future Pitching Intelligence

Potential additions after the current provider and validation work:

- velocity trends
- pitch mix evolution
- Swinging Strike%
- CSW%
- Chase%
- Stuff+
- Location+
- Pitching+
- xERA
- xwOBA allowed
- Barrel%
- HardHit%
- contact quality suppression
- platoon-specific pitch quality and arsenal fit

These are intentionally deferred until:

1. starter data correctness is complete
2. bullpen provider integration is complete
3. historical validation exists

Requires reliable providers, licensing/source review, and evidence that the
metrics improve out-of-sample decisions.

## Starter Source Transparency

Potential display:

- starter-only game-log source
- season fallback source
- starts
- starter innings
- sample/confidence label

Useful, not blocking bullpen work.

# Bullpen Research Beyond the Provider

After the base provider is correct:

- leverage index
- inherited-runner skill
- closer/setup confidence
- multi-day fatigue curves
- travel and extra-inning burden
- handedness availability
- bullpen depth
- opener/bulk interaction
- postseason usage patterns

# Recommendation Intelligence

## Recommendation Semantics

Separate:

- Model Confidence
- Recommendation Attractiveness

## Ranking Calibration

Hammer influences both qualification and ranking. Revisit only after sufficient historical data.

## Consensus Score Calibration

Future questions:

- Should low-quality supportive modules reduce consensus strength?
- Should support require a minimum signal score?
- Should consensus represent agreement, signal quality, or a documented blend?

## Automatic Hammer Calibration

Potentially optimize:

- agreement bonus
- contradiction penalty
- thresholds
- weights

Must remain explainable.

# Historical Analytics

- signal attribution
- confidence bands
- feature importance
- recommendation replay
- model-version comparison
- component-level outcome analysis
- starter and bullpen validation

# Market Intelligence

- Closing Line Value
- sportsbook performance
- line movement alerts
- market efficiency
- opening vs closing comparison
- steam detection

# Dashboard and Presentation

Deferred:

- starter source badge
- bullpen availability summary
- bullpen fatigue explanation
- model-health diagnostics
- palette refinement
- stronger Explorer affordance
- richer historical views

Presentation must consume canonical data.

# Platform

- REST API
- OAuth
- public API
- mobile application
- user accounts
- saved filters
- stable external DTOs

# Infrastructure

- Docker
- CI/CD
- automated deployments
- scheduled runs
- health monitoring
- alerting
- experiment tracking

Kubernetes is not a near-term need.

# AI

- daily AI recap
- interactive recommendation assistant
- natural-language querying
- automated narrative generation

# Multi-Sport

After MLB maturity:

- KBO
- Soccer
- NFL
- NBA
- NHL
- College Baseball
- College Football

# Research Ideas

- Kelly Criterion
- portfolio optimization
- Monte Carlo simulation
- live betting
- umpire impact
- travel fatigue
- weather sensitivity
- arbitrage detection

# Parking Lot Rule

This file must remain selective. If it becomes the active backlog, it has failed its purpose.
