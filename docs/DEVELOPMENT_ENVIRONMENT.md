# SharpStack Development Environment

> This document describes the standard development environment and workflow for
> SharpStack.

---

# Primary Development Environment

Operating System
- Windows 11

Repository
- C:\CheekSplittersAnalytics

Primary Editor
- Visual Studio Code

Primary Shell
- PowerShell

Python
- Python 3.13+

Source Control
- Git / GitHub

---

# Infrastructure

Current infrastructure:

- Windows workstation
- Azure PostgreSQL
- GitHub
- Proxmox
- Ubuntu Server
- MacBook Pro

---

# Development Workflow

1. Pull latest code.
2. Read PROJECT_HANDOFF.md.
3. Review ROADMAP.md.
4. Make focused changes.
5. Validate.
6. Rebuild generated artifacts.
7. Verify outputs.
8. Review git status.
9. Commit.
10. Push.

---

# Generated Artifacts

Rebuild these whenever recommendation output changes:

- tools_build_mlb_card.py
- tools_build_decision_card.py
- tools_build_recommendation_registry.py
- tools_build_discord_report.py

Generated artifacts should always be regenerated before debugging dashboard behavior.

---

# Validation

Minimum validation:

```powershell
python -m py_compile <modified files>

git diff --check
git diff --stat
git status --short
```

Always inspect generated JSON after recommendation changes.

---

# Editing Philosophy

Prefer:

- Small edits
- Existing architecture
- Incremental validation
- Backward compatibility

Avoid:

- Broad refactors
- Large search-and-replace
- Multiple unrelated objectives

---

# Git Workflow

Before every commit:

```powershell
git diff --check
git diff --stat
git status --short
```

One logical objective per commit.

---

# Troubleshooting

Dashboard unchanged?

→ Regenerate artifacts.

Consensus mismatch?

→ Verify Decision Builder.

Recommendation incorrect?

→ Verify plumbing before tuning models.

Hammer issue?

→ Validate consensus before changing weights.

---

# Common Commands

```powershell
python --version
git branch --show-current
git log -1 --oneline
git status --short
git diff --check
git diff --stat
python tools_build_recommendation_registry.py
python tools_build_decision_card.py
python tools_build_discord_report.py
alembic current
```

---

# Development Goal

Produce reliable, explainable, reproducible analytics through disciplined,
incremental engineering.
