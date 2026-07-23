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

Future research may test different stabilization rates for:

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

Do not tune from one slate.

## Pitch Quality and Arsenal Features

Potential additions:

- velocity changes
- pitch-mix changes
- swinging-strike rate
- called-strike plus whiff rate
- Stuff+ or comparable metrics
- platoon-specific pitch quality

Requires reliable provider and licensing/source review.

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
