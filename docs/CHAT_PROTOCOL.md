# SharpStack Chat Protocol

> This document defines how future development chats should contribute to the
> SharpStack project. It serves as the contributor guide for both human
> developers and AI assistants.

---

# Required Documents

Every new development chat should begin with these documents:

1. PROJECT_HANDOFF.md
2. ARCHITECTURE.md
3. ROADMAP.md
4. CHAT_PROTOCOL.md
5. DEVELOPMENT_ENVIRONMENT.md

Together they define:

- Current state
- Architecture
- Strategic direction
- Development workflow
- Local environment

---

# Opening Workflow

Before writing code:

1. Read all project documents.
2. Summarize the current objective.
3. Confirm architectural constraints.
4. Identify expected files.
5. Identify unknowns before making assumptions.

Never begin implementation before understanding the current state.

---

# Investigation Order

When something appears incorrect, investigate in this order:

1. Provider data
2. Data normalization
3. Game matching
4. Decision Builder
5. Consensus
6. Hammer
7. Recommendation Registry
8. Presentation

Do not recalibrate scores until plumbing has been verified.

---

# Development Philosophy

Prefer:

- Small targeted edits
- Existing patterns
- Reusable contracts
- Canonical ownership
- Backward compatibility

Avoid:

- Broad refactors
- Duplicate calculations
- Multiple sources of truth
- Premature optimization

---

# Architectural Guardrails

Never:

- Calculate recommendations inside presentation code.
- Duplicate consensus calculations.
- Duplicate Hammer calculations.
- Import persistence into prediction engines.
- Rewrite recommendation history.
- Rewrite odds history.

Presentation consumes data.

It never creates it.

---

# Validation Expectations

After meaningful changes:

```powershell
python -m py_compile <modified files>

git diff --check
git diff --stat
git status --short
```

Run focused validation before full builds.

Verify generated artifacts whenever dashboard behavior changes.

---

# Documentation Expectations

Every completed development session should update:

- PROJECT_HANDOFF.md
- ROADMAP.md (when priorities change)

Architecture documentation should only change after an approved architectural
decision.

---

# Git Expectations

Each commit should:

- Have one primary objective.
- Be independently understandable.
- Exclude unrelated modified files.
- Pass validation.

---

# Architecture Review Gate

Before proposing architecture changes, document:

- Current design
- Problem
- Evidence
- Smallest change
- Files affected
- Compatibility
- Testing
- Rollback

Wait for approval.

---

# End-of-Chat Deliverables

Every development chat should finish with:

1. Summary
2. Files changed
3. Validation results
4. Commit message
5. Push confirmation
6. Known issues
7. Updated documentation
8. Next-chat prompt

---

# Contributor Mindset

SharpStack favors:

- Evidence over opinion.
- Simplicity over cleverness.
- Explainability over mystery.
- Consistency over convenience.
- Long-term maintainability over short-term speed.

Whenever multiple solutions exist, choose the one that produces the clearest,
most reproducible system.
