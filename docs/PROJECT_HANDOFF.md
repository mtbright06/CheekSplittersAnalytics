# SharpStack MLB Analytics
# PROJECT_HANDOFF.md

> This document is the operational state of the project. It should allow a brand-new
> development chat to resume work with minimal context switching.

---

# Project Status

**Current Milestone:** Sprint 50 (Consensus Unification)

**Repository:** CheekSplittersAnalytics

**Primary Branch:** `feature/recommendation-history`

**Project State:** Stable, actively developed

---

# Executive Summary

SharpStack has evolved from a collection of independent baseball models into a
unified analytics platform.

Major accomplishments include:

- Recommendation Registry established as the primary recommendation artifact.
- Play of the Day generated from Recommendation Registry.
- Recommendation history and persistence foundation completed.
- MLB totals recommendations integrated end-to-end.
- Structured explanation framework implemented.
- Dashboard stabilized.
- Azure PostgreSQL foundation established.
- Recommendation Explorer foundation implemented.

Current work is focused on improving decision quality, not expanding features.

The highest-priority effort is ensuring every consumer receives the exact same
consensus interpretation from a single canonical source.

Deferred observation: `consensus_score` may remain modest despite unanimous agreement because it blends underlying signal quality; review during historical ranking calibration, not during consensus unification.
---

# Current Focus

## Consensus Unification

An architectural review discovered that Recommendation Registry is rebuilding
consensus independently instead of consuming the Decision Builder's canonical
agreement decisions.

Observed symptoms included:

- Recommendation reasons indicating agreement while serialized consensus showed opposition.
- Agreement percentages inconsistent with Hammer diagnostics.
- Downstream consumers displaying conflicting interpretations.

Decision:

**Decision Builder becomes the sole owner of consensus.**

Recommendation Registry, Dashboard, Explorer, Discord, and Play of the Day will
consume serialized consensus rather than reconstructing it.

---

# Important Findings

## Hammer Score

Hammer remains the primary composite recommendation score.

At this time it intentionally determines:
- recommendation eligibility
- recommendation strength

No calibration changes are approved until sufficient historical evidence exists.

## Ranking Score

Current weighting:

- Hammer: 60%
- Consensus: 18%
- Edge: 10%
- Expected Value: 7%
- Market Quality: 5%

Observation:

Hammer currently influences both eligibility and ranking.

This is documented for future review but must not be changed until consensus
serialization is complete and historical performance supports a redesign.

---

# Current Architectural Priorities

1. Canonical consensus ownership.
2. Eliminate duplicated decision logic.
3. Preserve explainability.
4. Improve analytics before expanding functionality.
5. Prefer evidence over intuition when tuning recommendations.

---

# Expected Files For Current Work

Primary:

- engine/decision/decision_builder.py
- engine/core/consensus.py
- engine/core/play_of_day.py
- tools_build_recommendation_registry.py
- dashboard consumers (read-only unless necessary)

Supporting:

- recommendation_registry.json
- play_of_day.json

---

# Validation Checklist

```powershell
python -m py_compile engine\decision\decision_builder.py
python tools_build_recommendation_registry.py
python tools_build_decision_card.py
python tools_build_discord_report.py

git diff --check
git diff --stat
git status --short
```

Confirm:
- Recommendation reasons match serialized consensus.
- Dashboard matches registry.
- Play of the Day matches registry.
- No duplicated consensus calculations remain.

---

# Known Gotchas

- Dashboard consumes generated artifacts.
- Always rebuild artifacts before debugging UI.
- Do not tune Hammer based on a single slate.
- PASS is neutral, not agreement.
- Recommendation history is immutable.

---

# Immediate Next Objective

Complete Consensus Unification by making Decision Builder the canonical source
for all agreement data and removing downstream consensus reconstruction.

After completion:

1. Validate consensus across all consumers.
2. Revisit ranking architecture using historical evidence.
3. Continue historical analytics and CLV work.

---

# Long-Term Vision

SharpStack is evolving into an explainable, evidence-driven sports analytics
platform capable of supporting multiple sports while maintaining:

- reproducible recommendations
- immutable historical records
- canonical decision contracts
- transparent scoring
- data-driven model evolution

End of handoff.
