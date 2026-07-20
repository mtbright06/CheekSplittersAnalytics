# SharpStack Chat Protocol

## Files to Attach to Every New Chat

## Files to Attach to Every New Chat

1. `PROJECT_HANDOFF.md`
2. `ARCHITECTURE.md`
3. `ROADMAP.md`
4. `CHAT_PROTOCOL.md`
5. `DEVELOPMENT_ENVIRONMENT.md`

## Opening Prompt

> We are continuing the SharpStack project.
> Read all four attached project documents before proposing code.
> ARCHITECTURE.md is authoritative for system design.
> PROJECT_HANDOFF.md is authoritative for current state.
> ROADMAP.md defines priority and sequencing.
> Do not redesign completed architecture unless you first identify a concrete blocker, explain the smallest necessary change, and receive approval.
> Before writing code, summarize:
> 1. the current sprint goal,
> 2. the architecture rules you will preserve,
> 3. the exact files you expect to change,
> 4. any ambiguity or conflict you found.
> End the chat by updating PROJECT_HANDOFF.md and ROADMAP.md.

## Required First Response

The new chat should not immediately produce code. It should confirm:

- current sprint,
- current branch,
- latest commit if known,
- Alembic revision if known,
- feature objective,
- intentionally uncommitted files,
- prohibited changes,
- expected implementation files.

## Rules During the Chat

- Inspect actual source before assuming signatures, object paths, fields, or entry points.
- Prefer small targeted changes to existing files.
- For a new file or deliberate full-file replacement, provide the complete file for VS Code.
- Avoid large automated search-and-replace scripts unless no safer option exists.
- Use PowerShell commands by default.
- Compile after each meaningful code change.
- Separate unrelated changes.
- Do not change schema without explaining why.
- Do not alter Hammer weights before validating signal plumbing.
- Do not import SQLAlchemy into prediction engines.
- Do not overwrite recommendation history.
- Do not overwrite odds history.
- Do not add presentation logic to model code.
- Do not include unrelated modified files in commits.
- Do not put model or recommendation calculations in renderers.
## Architecture Change Gate

Before any architecture change, show:

```text
Current architecture rule:
Feature blocked:
Evidence of blocker:
Smallest required change:
Files affected:
Database impact:
Backward compatibility:
Tests:
Rollback:
```

Wait for approval.

## End-of-Chat Deliverables

1. Sprint summary
2. Files changed
3. Validation commands and results
4. Commit command and message
5. Push verification
6. Current Alembic revision
7. Remaining modified/uncommitted files
8. Known issues or gotchas
9. Updated `PROJECT_HANDOFF.md`
10. Updated `ROADMAP.md`
11. Exact opening prompt for the next chat

## Handoff Quality Standard

A handoff is incomplete unless the next chat can answer:

- What was just completed?
- What is next?
- What must not change?
- What files are modified?
- What tests pass?
- What database revision is active?
- What is the latest commit?
- What is the first command to run?
- Which environment and editing workflow should be used?
