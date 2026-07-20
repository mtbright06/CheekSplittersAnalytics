## Primary Workstation

- Operating system: Windows
- Repository path: `C:\CheekSplittersAnalytics`
- Primary shell: PowerShell
- Primary editor: Visual Studio Code
- Python version: `3.13.13`
- Source control: Git and GitHub
- Current branch: maintained in `PROJECT_HANDOFF.md`

## Available Infrastructure

### Proxmox Host

A Proxmox host is available for virtual machines and containers.

Potential SharpStack uses include:

- Linux development environments
- application hosting
- database hosting
- scheduled jobs
- automated daily SharpStack runs
- API and dashboard hosting
- Discord integration services
- isolated testing environments
- persistent logs and output storage

The home environment can host services when appropriate.

Any deployment design must address:

- security,
- secrets management,
- network exposure,
- backups,
- monitoring,
- logging,
- recovery,
- and retry behavior.

### Additional Systems

- MacBook Pro
- Parallels Windows virtual machine
- Ubuntu Server environment and administration experience
- GitHub repository for source control and continuity

## Preferred Development Workflow

- Use PowerShell unless another shell is specifically required.
- Use VS Code for new files, complete-file replacements, and larger edits.
- For new files, provide the complete file for direct paste into VS Code.
- For existing files, prefer small targeted changes.
- Avoid large automated search-and-replace patches.
- Inspect current source before proposing integration changes.
- Compile after each meaningful Python change.
- Run targeted validation before full builds.
- Run `git diff --check` before committing.
- Review `git status --short` and `git diff --stat` before committing.
- Update project documentation before closing a sprint.
- Create a detailed handoff before beginning a new chat.

## Collaboration Preferences

- Do not assume function signatures, entry points, serialized paths, or field names.
- Inspect the relevant source when current code is unavailable.
- Prefer exact, copyable PowerShell commands.
- Explain what each validation checkpoint proves.
- Keep changes small enough to troubleshoot independently.
- Preserve backward compatibility unless removal is explicitly planned.
- Keep model, persistence, and presentation logic separated.
- When a full file is safer than an automated patch, provide the full file for VS Code.

## Common Commands

```powershell
python --version
git branch --show-current
git log -1 --oneline
git status --short
git diff --check
git diff --stat
python -m py_compile <files>
python .\tools_build_mlb_card.py
alembic current
