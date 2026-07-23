# SharpStack Development Environment

> Standard local environment, validation workflow, and migration notes.

# Primary Environment

**Operating system:** Windows 11
**Repository:** `C:\CheekSplittersAnalytics`
**Editor:** Visual Studio Code
**Shell:** PowerShell
**Python:** 3.13+
**Source control:** Git / GitHub
**Primary branch:** `feature/recommendation-history`

# Infrastructure

- Windows workstation
- GitHub
- Azure PostgreSQL
- Proxmox
- Ubuntu Server
- MacBook Pro

# Standard Workflow

1. Open PowerShell in the repository.
2. Confirm branch and working tree.
3. Pull only when state is understood.
4. Read all six project documents.
5. State current and next approved objectives.
6. Inspect expected files.
7. Make focused changes.
8. Run focused validation.
9. Rebuild generated artifacts.
10. Inspect outputs.
11. Review diff and temporary files.
12. Update documentation.
13. Commit one logical objective.
14. Push.
15. Confirm a clean tree.

# Session Opening Commands

```powershell
Set-Location C:\CheekSplittersAnalytics

git branch --show-current
git status --short
git log -1 --oneline
git remote -v
python --version
```

When resuming uncommitted work, do not pull or reset until changes are inspected.

# Current Validation Commands

```powershell
python -m py_compile engine\mlb\pitchers.py
python -m py_compile engine\mlb\game_builder.py
python -m py_compile engine\model\component_scores.py

git diff --check
git diff --stat
git status --short
```

Search for focused tests:

```powershell
Get-ChildItem tests -Recurse -Filter *.py |
    Select-String -Pattern 'fetch_pitcher_stats|starting_pitcher_score|stabilize_pitcher_stat'
```

# Generated Artifacts

Rebuild when MLB model or recommendation inputs change:

```powershell
python tools_build_mlb_card.py
python tools_build_decision_card.py
python tools_build_recommendation_registry.py
python tools_build_discord_report.py
```

Common outputs:

- `output/cards/mlb_card.json`
- `output/cards/decision_card.json`
- `output/cards/recommendation_registry.json`
- `output/cards/play_of_day.json`
- `output/recommendations/recommendations_today.json`
- `output/recommendations/recommendation_run_payload.json`
- Discord report outputs

Always inspect generated JSON after recommendation changes.

# MLB API Conventions

Use explicit:

```text
season=<current season>
gameType=R
```

Use timeouts and safe failure behavior.

For pitching game logs:

- filter `gamesStarted > 0`
- aggregate raw counts
- recompute rates
- do not average split ERA/WHIP
- preserve source/fallback metadata

# Temporary Starter Diagnostic

`tools_validate_pitchers.py` may exist from this session.

Before commit:

```powershell
Test-Path .\tools_validate_pitchers.py
git status --short
```

Delete if temporary:

```powershell
Remove-Item .\tools_validate_pitchers.py
```

Keep only after an explicit decision to support it.

# Git Workflow

Review exact files:

```powershell
git --no-pager diff -- engine\mlb\pitchers.py
git --no-pager diff -- engine\mlb\game_builder.py
git --no-pager diff -- engine\model\component_scores.py
git --no-pager diff -- docs
```

Suggested commit:

```powershell
git add engine\mlb\pitchers.py `
        engine\mlb\game_builder.py `
        engine\model\component_scores.py `
        docs\PROJECT_HANDOFF.md `
        docs\ROADMAP.md `
        docs\ARCHITECTURE.md `
        docs\CHAT_PROTOCOL.md `
        docs\DEVELOPMENT_ENVIRONMENT.md `
        docs\PARKING_LOT.md

git commit -m "Improve MLB starter profiles and scoring"
git push
```

Adjust document paths if they live outside `docs\`.

After push:

```powershell
git log -1 --oneline
git status --short
```

# Troubleshooting

## Dashboard unchanged

Rebuild artifacts before inspecting UI code.

## Starter metrics wrong

Inspect:

1. raw game log
2. `gamesStarted` filter
3. raw totals
4. innings-to-outs conversion
5. recomputed rates
6. fallback source

## Tiny sample looks elite

Inspect stabilization and data duplication before changing weights.

## Bullpen data empty

Expected before the next sprint. Reuse `engine/mlb/bullpen/`; build the missing provider.

## Consensus mismatch

Verify Decision Builder and registry serialization, not presentation.

# Codex Migration

1. Open `C:\CheekSplittersAnalytics` as the workspace.
2. Keep all six documents in the repository.
3. Start with the handoff prompt.
4. Ask Codex to inspect branch, status, and diffs before editing.
5. Use one objective and one commit at a time.
6. Review all generated changes.
7. Keep GitHub as the durable source of truth.

Codex can reduce browser-chat context loss, but repository documents and clean commit boundaries remain essential.

# Development Goal

Produce reliable, explainable, reproducible sports analytics through disciplined, incremental engineering.
