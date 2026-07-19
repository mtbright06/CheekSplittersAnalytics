# SharpStack Project Handoff
Last Updated: 2026-07-19
Sprint: 39
Status: STABLE
Branch: main

---

# Project Vision

SharpStack is intended to become a professional sports betting analytics platform capable of producing explainable recommendations across multiple sports while tracking historical performance over time.

Current sports:

- MLB
- KBO

Future:

- NFL
- NCAA Football
- NBA
- NHL
- Soccer

Primary goals:

- Produce explainable recommendations
- Persist every recommendation historically
- Measure model performance over time
- Support experimentation through model versioning
- Never overwrite historical recommendations

---

# Current Architecture

Current pipeline:

Schedule
↓

Models

↓

Cards

↓

Recommendation Explorer

↓

Recommendation Payload

↓

RecommendationService (next sprint)

↓

Azure PostgreSQL

↓

Dashboard / Analytics

The Recommendation Explorer is now considered the canonical staging layer between model generation and persistence.

---

# Current Sprint (Sprint 39)

## Completed

Added recommendation generation for:

- MLB Moneylines
- MLB Totals
- KBO Moneylines

Recommendation Explorer now produces:

recommendations_today.json

recommendations_today.csv

recommendation_run_payload.json

Immutable historical snapshots

output/recommendations/history/

Every execution generates a unique run timestamp.

Historical recommendations are never overwritten.

---

# What Was Verified

Verified successfully:

✓ Recommendation snapshots

✓ Immutable history

✓ Moneyline recommendations

✓ MLB totals recommendations

✓ Pitcher context

✓ Confidence values

✓ Recommendation payload

✓ Timestamped run keys

Verified manually from console.

No git commit has been made yet.

---

# Important Design Decision

Recommendation Explorer DOES NOT currently write directly into PostgreSQL.

Instead it generates:

recommendation_run_payload.json

This payload is intentionally shaped so it can be handed to RecommendationService without additional transformation.

Reason:

The existing database service layer was not available during development.

Rather than invent interfaces or risk breaking persistence, the explorer stops at a validated payload.

This was an intentional engineering decision.

---

# Azure PostgreSQL Status

Azure PostgreSQL database remains the system of record.

Nothing in Sprint 39 replaces the database.

Current status:

Cards
↓

Recommendation Explorer

↓

Payload

STOPS HERE

Next sprint resumes here:

Payload

↓

RecommendationService

↓

ModelRun

↓

Recommendation

↓

Azure PostgreSQL

---

# Totals Recommendation Behavior

Current behavior is intentional.

If sportsbook totals are unavailable:

market_line = None

selection = NONE

recommendation = PASS

sportsbook = Unavailable

No recommendation is fabricated.

Once sportsbook totals become available, Recommendation Explorer should automatically produce:

OVER

UNDER

PASS

based on model edge.

---

# Bug Fixed During Sprint

Original issue:

Totals inherited:

sportsbook = FanDuel

from the moneyline market.

This incorrectly implied totals odds existed.

Fixed.

Current behavior:

sportsbook = Unavailable

when totals markets are unavailable.

Verified.

---

# Known Limitations

1.

MLB totals currently lack sportsbook totals.

The model projects totals correctly.

Sportsbook totals are simply unavailable from current data.

No action required until odds provider is expanded.

---

2.

Recommendation Explorer is file-backed only.

Database persistence is the next milestone.

---

3.

Recommendation history exists as immutable JSON snapshots.

Database history is not yet connected.

---

# Next Sprint (Sprint 40)

Highest priority:

Wire Recommendation Explorer into existing persistence layer.

Tasks:

Read recommendation_run_payload.json

Create ModelRun

Create Recommendation rows

Persist to Azure PostgreSQL

Verify:

ModelRun count

Recommendation count

Foreign keys

Indexes

Historical runs

No duplicate recommendations within a run

Do NOT rewrite Recommendation Explorer.

The explorer has been validated.

Only connect it.

---

# Engineering Principles

Never overwrite history.

Every execution is immutable.

Every recommendation belongs to exactly one ModelRun.

Recommendation Explorer should remain independent from database implementation.

Avoid coupling model generation to persistence.

Always validate outputs before git commit.

---

# Important Gotchas

1.

Do not fabricate sportsbook data.

If totals are unavailable:

PASS

is correct.

---

2.

Recommendation Explorer is now effectively an API.

Downstream systems should consume its payload rather than rebuilding recommendation logic.

---

3.

Do not store generated JSON/CSV/history outputs in Git.

Only commit source.

---

4.

Historical snapshots are expected to grow quickly.

Eventually move history storage into PostgreSQL while keeping immutable semantics.

---

# Current Repository State

Recommendation generation:

Stable

Moneylines:

Stable

Totals:

Stable (waiting on sportsbook totals)

Recommendation payload:

Stable

Database persistence:

Next sprint

Dashboard:

Future sprint

---

# Suggested Commit

feat: add totals recommendations and immutable recommendation snapshots
