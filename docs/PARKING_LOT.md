# SharpStack Parking Lot

> This document captures valuable ideas that are intentionally deferred.
> Nothing in this file represents approved or scheduled work.

---

# Purpose

The Parking Lot exists to preserve good ideas without interrupting the current
development objective.

If an item belongs on the active roadmap, move it there and remove it from this
document.

---

# Recommendation Intelligence

## Recommendation Semantics

Separate:

- Model Confidence
- Recommendation Attractiveness

These are currently represented by overlapping concepts and should eventually
be independent throughout the platform.

---

## Ranking Calibration

Current observation:

Hammer influences both qualification and ranking.

This should be revisited only after sufficient historical recommendation data
exists.

---

### Consensus score calibration

Current behavior:

- `agreement_pct` measures directional module agreement.
- `consensus_score` blends participating signal scores, sample bonus, and contradiction penalty.
- A play can therefore be `UNANIMOUS` while still having a modest `consensus_score`.

Example observed:

- Cincinnati Reds
- Agreement: 100%
- Consensus score: 55.3

Decision:

Do not change during Sprint 50. Sprint 50 is limited to canonical consensus ownership and serialization.

Revisit when:

- consensus is flowing correctly through Registry, Dashboard, Explorer, Discord, and Play of Day
- sufficient recommendation history exists to compare consensus score against outcomes
- ranking calibration work begins

Questions to answer later:

- Should low-scoring supportive modules reduce consensus strength this heavily?
- Should Bomb Lab support require a minimum score?
- Should consensus score represent agreement only, signal quality only, or a clearly documented blend?

## Automatic Hammer Calibration

Use historical performance to optimize:

- agreement bonus
- contradiction penalty
- thresholds
- weighting

Must remain explainable.

---

# Historical Analytics

Future work:

- Signal attribution
- Confidence bands
- Feature importance
- Recommendation replay
- Model version comparison

---

# Market Intelligence

Future ideas:

- Closing Line Value
- Sportsbook performance
- Line movement alerts
- Market efficiency scoring
- Steam move detection

---

# Platform

Potential future work:

- REST API
- OAuth
- Public API
- Mobile application
- User accounts
- Saved filters

---

# Infrastructure

Potential future improvements:

- Docker
- CI/CD
- Kubernetes
- Automated deployments
- Scheduled daily runs
- Health monitoring
- Alerting

---

# AI

Potential future capabilities:

- Daily AI recap
- Interactive recommendation assistant
- Natural-language querying
- Automated narrative generation

---

# Multi-Sport

Planned expansion after MLB analytics mature:

- KBO
- Soccer
- NFL
- NBA
- NHL
- College Baseball
- College Football

---

# Research Ideas

Long-term investigations:

- Kelly Criterion
- Portfolio optimization
- Monte Carlo simulation
- Live betting
- Umpire impact
- Travel fatigue
- Weather sensitivity
- Arbitrage detection

---

# Parking Lot Rules

An item belongs here when:

- It is valuable.
- It is not blocking current work.
- It requires future evidence.
- It deserves preservation.

This document should remain intentionally short.

If it becomes a backlog, it has failed its purpose.
