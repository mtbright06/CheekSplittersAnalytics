# SharpStack Chat Protocol

> Contributor guide for ChatGPT, Codex, and human developers.

# Required Documents

Every new development session must begin with:

1. `PROJECT_HANDOFF.md`
2. `ARCHITECTURE.md`
3. `ROADMAP.md`
4. `CHAT_PROTOCOL.md`
5. `DEVELOPMENT_ENVIRONMENT.md`
6. `PARKING_LOT.md`

# Opening Workflow

Before proposing code:

1. Read all six documents.
2. State the current objective.
3. State the next approved objective.
4. Identify architectural guardrails.
5. Identify expected files.
6. Inspect branch and git status.
7. Identify unknowns before assumptions.
8. Confirm whether work is uncommitted.

Never begin implementation from memory alone.

# Priority Discipline

Current authoritative sequence:

```text
Finish Starter Model v2
    â†“
Commit and push
    â†“
MLB bullpen provider and integration
    â†“
KBO confidence
    â†“
Historical calibration
```

Do not promote a side idea into the active sprint without explicit approval.

When a new idea appears:

- finish the current objective if possible
- place the idea in `PARKING_LOT.md`
- explain whether it blocks current work
- return to the approved priority

# Investigation Order

When something looks wrong:

1. Provider response
2. Role classification
3. Normalization and aggregation
4. Game matching
5. Sport model
6. Decision Builder
7. Consensus
8. Hammer
9. Recommendation Registry
10. Presentation

Do not recalibrate scores until provider data and plumbing are verified.

# Development Philosophy

Prefer:

- small targeted edits
- existing patterns
- reusable contracts
- canonical ownership
- backward compatibility
- observable fallbacks
- focused validation

Avoid:

- broad refactors
- duplicate calculations
- multiple sources of truth
- premature optimization
- tuning from one slate
- speculative feature expansion

# Architectural Guardrails

Never:

- calculate recommendations in presentation code
- duplicate consensus calculations
- duplicate Hammer calculations
- import persistence into prediction engines
- rewrite recommendation history
- rewrite odds history
- create a competing bullpen subsystem
- hide fallback data sources
- average provider rate fields when raw counts exist
- redesign Decision Builder without evidence and approval

# Provider and Model Validation

For provider changes:

- inspect at least one raw response
- compare raw counts with normalized output
- verify missing-data behavior
- verify fallback behavior
- test mixed-role or edge-case players

For score changes:

- test unknown input
- test no-sample input
- test tiny sample
- test established strong sample
- test established weak sample
- check for 0/100 saturation
- do not call sanity checks calibration

# Validation Expectations

```powershell
python -m py_compile <modified files>
git diff --check
git diff --stat
git status --short
```

When recommendation inputs change:

```powershell
python tools_build_mlb_card.py
python tools_build_decision_card.py
python tools_build_recommendation_registry.py
python tools_build_discord_report.py
```

Inspect generated JSON before debugging dashboard behavior.

# Documentation Expectations

Update:

- `PROJECT_HANDOFF.md` every completed session
- `ROADMAP.md` when priorities or milestone state change
- `PARKING_LOT.md` when valuable ideas are deferred
- `ARCHITECTURE.md` only after an approved architecture change
- `DEVELOPMENT_ENVIRONMENT.md` when environment/workflow changes
- `CHAT_PROTOCOL.md` when collaboration rules change

Do not let documentation remain multiple sprints behind the code.

# Git Expectations

Before commit:

```powershell
git diff --check
git diff --stat
git status --short
```

Each commit should:

- have one primary objective
- be independently understandable
- exclude temporary/unrelated files
- pass validation
- include intended documentation
- follow generated-artifact policy

After commit and push:

```powershell
git log -1 --oneline
git status --short
```

Record commit hash and clean-tree confirmation.

# Temporary Diagnostics

Temporary scripts are allowed.

Before commit, explicitly:

- delete them, or
- retain them as supported developer tools

Never include temporary validation files accidentally.

# Architecture Review Gate

Before changing architecture, document:

- current design
- problem
- evidence
- smallest change
- files affected
- compatibility
- testing
- rollback

Wait for approval.

# End-of-Session Deliverables

1. Objective completed or exact stopping point
2. Files changed
3. Validation results
4. Generated artifacts rebuilt
5. Known issues
6. Deferred ideas
7. Updated documentation
8. Commit message
9. Push confirmation
10. Clean-tree confirmation
11. Next-session prompt

# Codex Migration Guidance

When moving to Codex:

- open the repository root
- provide the six project documents
- instruct Codex to inspect git status before editing
- make it summarize objective and constraints first
- use one task/commit objective at a time
- review diffs before broad edits
- preserve these documents in the repository

Codex may improve repository persistence, but it does not replace disciplined handoffs or state validation.

# Contributor Mindset

SharpStack favors:

- evidence over opinion
- simplicity over cleverness
- explainability over mystery
- consistency over convenience
- long-term maintainability over short-term speed
- completion over drift
