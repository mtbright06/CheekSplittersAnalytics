# SharpStack Parking Lot

Completed MLB totals recommendations and the initial structured explanation framework have been removed from this document because they are now implemented.

## Purpose

This document captures ideas that have been discussed but are intentionally
deferred.

These items should NOT interrupt the current sprint unless explicitly promoted
into the roadmap.

Nothing in this document is considered committed work.

---
# Upcoming Promotions

These ideas are expected to graduate into the roadmap soon.

---

## Recommendation Explorer

Unified game dashboard exposing every SharpStack model from a single screen.

Planned capabilities

- Moneyline
- Totals
- Hammer
- Bomb Lab
- First 5
- Market comparison
- Structured explanations
- Historical performance

---

## API Platform

REST API exposing:

- Recommendation history
- Today's slate
- Model runs
- ROI
- CLV
- Health reports

Consumes shared DTOs.

---

## Multi-Sport Foundation

Before expanding into additional sports, complete the shared contracts for:

- Recommendation
- Odds history
- Grading
- Analytics
- Dashboard consumers

Initial expansion order

1. KBO
2. Soccer
3. WNBA
4. NFL
5. NBA
# Model Intelligence

## Automatic Hammer Calibration

Instead of manually tuning Hammer weights, use historical graded recommendations
to optimize:

- agreement bonus
- contradiction penalty
- market penalties
- recommendation thresholds

Goal:
Allow Hammer to improve itself over time while remaining explainable.

Status:
Deferred until sufficient recommendation history exists.

---

## Signal Attribution

Determine which signal combinations consistently outperform.

Examples:

Bomb + First5

Bomb only

Market only

Bomb + Market

Hammer > 70

Hammer 60-70

Real Market Loaded vs Missing Market

Goal:
Identify which combinations actually generate long-term ROI.

---

## Recommendation Confidence Bands

Evaluate performance grouped by:

70-75

75-80

80-85

85+

Determine optimal recommendation tiers.

---

## Adaptive Recommendation Thresholds

Allow recommendation thresholds to change by:

sport

market

season

sample size

Only after historical validation.

---

# Market Analytics

## Closing Line Value

Track:

Opening Line

Recommendation Line

Closing Line

CLV

Historical CLV

Average CLV by model

---

## Sportsbook Performance

Compare:

DraftKings

FanDuel

BetMGM

Caesars

Fanatics

Goal:

Determine which sportsbook consistently provides the best value.

---

## Line Movement Alerts

Notify when:

Market moves toward SharpStack projection

Market moves away

Edge disappears

Edge increases

---

# Model Quality

## Recommendation Replay

Replay any historical slate using:

old model version

old odds

old weather

old lineup

Purpose:

Compare historical versions of SharpStack.

---

## Model Version Comparison

Compare:

v0.4

v0.5

v0.6

using identical historical slates.

---

## Feature Importance

Estimate contribution of:

weather

bullpen

park factor

market

Bomb

First5

Goal:

Understand which variables actually drive winning picks.

---

# Operations

## Automatic Morning Health Report

Email / Discord summary including:

Games

Coverage

Warnings

Pipeline health

Recommendation distribution

---

## Pipeline Alerts

Notify when:

provider fails

market coverage low

weather unavailable

probable pitchers missing

Bomb missing

First5 missing

---

# User Experience


## Recommendation Cards

Generate polished cards for:

Discord

Twitter/X

Website

---

## Daily Slate Report

Automatically produce:

Top Plays

Biggest Edges

Model Health

Watch List

Fade Candidates

---

# Dashboard Ideas

Recommendation history

ROI

Rolling ROI

Win %

Units

CLV

Signal attribution

Model comparison

Line movement

Market coverage

Provider health

---

# AI Features

## Daily AI Recap

Generate narrative summary explaining:

Today's best plays

Model confidence

Major disagreements

Pipeline issues

---

## AI Chat Assistant

Allow questions like:

Why is Atlanta a LEAN?

Show today's biggest market edge.

Compare today's slate to yesterday.

Show Bomb-only recommendations.

---

# Multi-Sport Expansion

Future sports:

KBO

Soccer

WNBA

NFL

NBA

NHL

College Baseball

College Football

---

# Research Ideas

Expected Value optimization

Bankroll optimization

Kelly Criterion

Portfolio optimization

Risk-adjusted recommendation ranking

Monte Carlo simulations

Weather sensitivity studies

Bullpen fatigue modeling

Travel fatigue

Umpire impact

Rest advantage

Live betting models

Player prop framework

Arbitrage detection

Steam move detection

Consensus fade analysis

Market efficiency scoring

Bookmaker sharpness ranking

---

# Nice-to-Have

Plugin architecture

Mobile app

API authentication

Public API

OAuth

Cloud deployment

Docker

Kubernetes

CI/CD

Automatic retraining

Feature store

Experiment tracking

A/B testing

User accounts

Saved filters

Recommendation subscriptions

Historical exports

CSV/PDF reporting

## Recommendation semantics

Separate the two bettor-facing concepts currently represented by the recommendation score:

- **Model confidence:** How trustworthy is today's projection?
- **Recommendation score:** How attractive is this wager?

These should eventually become separate fields throughout the model, serialized output, reports, dashboard, and Discord presentation.

## Automated hosting and delivery

Host SharpStack on the Proxmox environment so the application can:

- Run automatically on a daily schedule.
- Refresh required data and market inputs.
- Build the daily cards and recommendations.
- Preserve logs and surface failures.
- Eventually publish recommendations through a Discord application or bot.

Future hosting design should consider containers or a lightweight virtual machine, scheduled execution, secrets management, persistent output storage, health monitoring, and retry behavior.
