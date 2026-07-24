# SharpStack MLB Analytics
# PROJECT_HANDOFF.md

> Operational source of truth for resuming development in a new ChatGPT or Codex session. Read this together with `ARCHITECTURE.md`, `ROADMAP.md`, `CHAT_PROTOCOL.md`, `DEVELOPMENT_ENVIRONMENT.md`, and `PARKING_LOT.md` before proposing code.

---

# 1. Project Status

**Repository:** `C:\CheekSplittersAnalytics`
**Primary branch:** `feature/recommendation-history`
**Environment:** Windows 11 / PowerShell / Python 3.13+
**Current milestone:** Sprint 53 â€” MLB bullpen provider and integration
**Current work item:** S53-001 â€” MLB bullpen provider plumbing
**Working tree:** Intentionally modified and not yet committed
**Next approved priority after Sprint 53:** KBO confidence improvements

SharpStack is stable and actively developed. The platform already has a functioning MLB recommendation pipeline, Recommendation Registry, Play of the Day, structured explanations, dashboard, Discord reporting, recommendation history, and an Azure PostgreSQL persistence foundation.

The current phase is not feature expansion. It is improving the correctness, explainability, and reliability of the underlying baseball models.

---

# 2. Reality Check: Why the Work Shifted

The planned next priority was bullpen improvement.

Investigation showed:

- `engine/model/component_scores.py` had a simplistic bullpen score using only ERA and WHIP.
- `engine/mlb/game_builder.py` emitted a bullpen payload with all meaningful fields set to `None`.
- A more capable bullpen subsystem already existed under `engine/mlb/bullpen/`, including projection, fatigue, quality, and game-adjustment logic.
- The missing piece was not a new bullpen model. It was a provider and integration layer that could build a reliable `BullpenSnapshot` from MLB data.

Before implementing that provider, the starter data path was inspected.

That inspection revealed a more immediate structural flaw:

- `fetch_pitcher_stats()` used MLB season pitching aggregates.
- Those aggregates combined starting and relief appearances.
- Converted relievers, openers, bulk pitchers, and mixed-role pitchers could therefore be evaluated using contaminated role data.
- Kyle Hart provided a concrete example: the MLB season line contained 26 games but only 2 starts.

This was a provider/data-correctness issue, and SharpStack's architecture requires plumbing and data integrity to be fixed before model tuning.

The approved course correction became:

1. Complete Starter Model v2.
2. Return immediately to the bullpen provider and integration.
3. Improve KBO confidence handling.
4. Resume calibration only after enough historical evidence exists.

Do not drift into Starter Model v3, recency blending, metric-specific stabilization, dashboard polish, or broader scoring experimentation before the bullpen work. Those ideas are preserved in `PARKING_LOT.md`.

---

# 3. Sprint 53 Status

Completed before this session:

- S52-001 â€” Remove market leakage
- S52-002 â€” Explainable confidence / unknown starters
- S52-003 â€” Default audit
- Explicit MLB API `season` and `gameType` parameters
- S52-005 â€” Pitcher sample stabilization

Deferred:

- S52-004 â€” Calibration
  - Must wait for sufficient recommendation history and outcome evidence.

Completed:

- S52-006 â€” Starter Model v2
  - Role-aware starter-only game-log aggregation
  - Richer starter profile
  - Modernized starting-pitcher score using stabilized skill metrics

In progress:

- S53-001 â€” Bullpen provider and integration
  - Active pitcher roster and reliever game-log ingestion
  - Normalized bullpen payload shared by totals and SharpScore
  - Source-quality metadata and neutral availability handling

---

# 4. Work Completed in This Session

## 4.1 Starter-only provider path

`engine/mlb/pitchers.py` was rewritten so `fetch_pitcher_stats(person_id)`:

1. Requests MLB `gameLog` pitching data for the current season and regular season.
2. Filters appearances to `gamesStarted > 0`.
3. Aggregates raw counting statistics across starts.
4. Recomputes rate statistics from those raw totals.
5. Returns a starter-only profile.
6. Falls back safely to the prior full-season aggregate when starter game logs are unavailable or no starts exist.

The public function name and general payload contract remain backward compatible.

Existing fields retained:

- `record`
- `era`
- `whip`
- `ip`
- `so`
- `bb`
- `hr_allowed`
- `k_rate` â€” currently K/9
- `bb_rate` â€” currently BB/9
- `hr9`

New fields added:

- `starts`
- `hits`
- `hbp`
- `batters_faced`
- `h9`
- `k_bb_pct`
- `strike_pct`
- `pitches_per_inning`
- `ground_air_ratio`
- `opponent_avg`
- `data_source`

Possible `data_source` values:

- `starter_game_log`
- `season_fallback`

## 4.2 Game builder payload

`engine/mlb/game_builder.py` was updated so `pitcher_from_team()` forwards the richer starter profile into the canonical game payload.

No downstream API was removed.

## 4.3 Starting Pitcher Score v2

`engine/model/component_scores.py` was updated to use richer stabilized starter metrics.

The score still:

- Returns `50` for an unknown starter.
- Returns `50` when no usable innings exist.
- Begins at a neutral `50`.
- Regresses observed metrics toward league-average baselines.
- Clamps the final result to `0â€“100`.

Metrics now represented:

- Run prevention: ERA, WHIP
- Bat-missing and command: K/9, BB/9, K-BB%, strike%
- Contact management and efficiency: HR/9, H/9, pitches per inning, ground/air ratio

This is a structural scoring improvement built on corrected role-specific data. It is not historically calibrated.

---

# 5. Validation Performed

## Kyle Hart provider validation

Direct output included:

```text
data_source: starter_game_log
starts: 2
ip: 3.0
era: 3.0
whip: 1.0
k_rate: 9.0
bb_rate: 3.0
hr9: 0.0
strike_pct: 68.2
```

The two raw MLB start records contained:

- Start 1: 2.0 IP, 1 ER, 2 H, 1 BB, 2 K
- Start 2: 1.0 IP, 0 ER, 0 H, 0 BB, 1 K

Combined:

- 3.0 IP
- 1 ER
- 2 H
- 1 BB
- 3 K
- 0 HR
- 44 pitches
- 30 strikes

The provider aggregate matched.

Important finding:

Per-game `era` and `whip` fields in MLB game-log responses can reflect broader context and should not be averaged. Raw counts must be aggregated and rates recomputed.

## Compile and diff checks

Passed:

```powershell
python -m compileall engine\mlb\pitchers.py engine\mlb\game_builder.py
git --no-pager diff --check
```

Observed diff stat before the scoring edit:

```text
engine/mlb/game_builder.py |  25 +++
engine/mlb/pitchers.py     | 421 +++++++++++++++++++++++++++++++++++++++++++--
2 files changed, 429 insertions(+), 17 deletions(-)
```

Capture a new final diff stat before commit because `engine/model/component_scores.py` changed afterward.

## Slate-level score validation

Observed probable-starter results:

```text
Kyle Hart                 Starts=2  IP=3.0   ERA=3.00 Score=51.0
Chris Sale                Starts=19 IP=111.0 ERA=2.19 Score=65.2
Taj Bradley               Starts=20 IP=114.7 ERA=3.69 Score=53.7
Gavin Williams            Starts=21 IP=126.3 ERA=3.78 Score=59.5
Casey Legumina            Starts=3  IP=5.0   ERA=3.60 Score=50.6
Shane Bieber              Starts=6  IP=30.7  ERA=4.70 Score=46.0
Brandon Pfaadt            Starts=7  IP=37.7  ERA=3.82 Score=52.0
Michael McGreevy          Starts=20 IP=109.0 ERA=2.89 Score=53.6
Randy Dobnak              Starts=1  IP=4.3   ERA=2.08 Score=48.4
Troy Melton               Starts=9  IP=55.0  ERA=1.80 Score=59.2
```

Interpretation:

- Tiny samples remained near neutral.
- Established strong starters moved meaningfully above neutral.
- Weak current performance could move below neutral.
- No observed scores hit the 0 or 100 clamps.
- The distribution was plausible for a component score.

This is a sanity check, not calibration proof.

---

# 6. Files Expected to Be Modified

Core changes:

- `engine/mlb/pitchers.py`
- `engine/mlb/game_builder.py`
- `engine/model/component_scores.py`

Documentation to replace:

- `docs/PROJECT_HANDOFF.md`
- `docs/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/CHAT_PROTOCOL.md`
- `docs/DEVELOPMENT_ENVIRONMENT.md`
- `docs/PARKING_LOT.md`

Possible temporary file:

- `tools_validate_pitchers.py`

Before commit, either delete `tools_validate_pitchers.py` if it was only a one-time check, or intentionally retain it as a supported developer diagnostic. Do not include it accidentally.

---

# 7. Immediate Next Actions Before Commit

Run:

```powershell
python -m py_compile engine\mlb\pitchers.py
python -m py_compile engine\mlb\game_builder.py
python -m py_compile engine\model\component_scores.py
```

Search for focused tests:

```powershell
Get-ChildItem tests -Recurse -Filter *.py |
    Select-String -Pattern 'fetch_pitcher_stats|starting_pitcher_score|stabilize_pitcher_stat'
```

Then inspect the final change set:

```powershell
git --no-pager diff --check
git --no-pager diff --stat
git status --short
git --no-pager diff -- engine\mlb\pitchers.py
git --no-pager diff -- engine\mlb\game_builder.py
git --no-pager diff -- engine\model\component_scores.py
```

Rebuild recommendation artifacts because starter scores can affect MLB decisions:

```powershell
python tools_build_mlb_card.py
python tools_build_decision_card.py
python tools_build_recommendation_registry.py
python tools_build_discord_report.py
```

Inspect generated JSON for:

- starter profile presence
- no serialization failures
- plausible scores
- unknown starters remaining neutral
- no missing-key regressions
- expected recommendation count and market status

Finally:

```powershell
git status --short
git diff --check
git diff --stat
```

---

# 8. Proposed Commit Scope

One logical objective:

> Make MLB starter evaluation role-aware and skill-based.

Suggested commit message:

```text
Improve MLB starter profiles and scoring
```

Suggested body:

```text
- aggregate starter-only MLB game logs
- preserve a safe season-stat fallback
- expose richer starter skill metrics
- pass starter profile fields through game builder
- score starters using stabilized role-aware metrics
- update project documentation and next-priority handoff
```

After commit:

```powershell
git push
git log -1 --oneline
git status --short
```

Expected final state:

- Push succeeds.
- Local branch matches remote.
- Working tree is clean.

---

# 9. Current Objective: MLB Bullpen Provider and Integration

The repository already contains:

```text
engine/mlb/bullpen/
```

including components such as:

- `bullpen_model.py`
- `fatigue.py`
- `quality.py`
- `game_adjustment.py`
- `bullpen_data.py`

The totals model already expects bullpen concepts such as:

- `season_era`
- `season_whip`
- `last7_era`
- `innings_last3`
- `closer_available`
- `setup_available`

The prior game-builder placeholder was:

```python
"bullpen": {
    "era": None,
    "whip": None,
    "fip": None,
    "recent_usage": None,
}
```

The active implementation adds a provider/normalization layer that produces a
reliable `BullpenSnapshot`-shaped payload from MLB data without duplicating
quality, fatigue, projection, adjustment, or component scoring.

Approved flow:

```text
MLB API
  â†“
Bullpen provider / roster and reliever normalization
  â†“
BullpenSnapshot
  â†“
Existing bullpen projection, quality, fatigue, and adjustment modules
  â†“
Totals and SharpScore consumers
```

Why it is harder than starter work:

- team roster retrieval
- identifying active relievers
- excluding starters and handling mixed roles
- recent usage aggregation
- availability estimation
- fatigue handling
- closer/setup role handling
- season and recent performance weighting
- safe fallbacks for incomplete roster data

Guardrails:

- Do not redesign Decision Builder.
- Do not calculate bullpen logic in presentation code.
- Do not create a second bullpen subsystem.
- Do not import persistence into prediction engines.
- Do not tune bullpen weights until provider correctness is verified.
- Inspect existing contracts before writing code.

---

# 10. Explicitly Deferred to Prevent Drift

Not the next priority:

- Starter recency blend
- Last-three/last-five-start weighting
- Metric-specific stabilization innings
- Starter dashboard badges
- Pitch velocity or pitch-mix integration
- Stuff models
- Automatic model calibration
- Ranking calibration
- Hammer recalibration
- Cosmetic dashboard work

These ideas may be valuable. They are not blocking the approved bullpen objective.

---

# 11. Known Gotchas

- MLB probable pitchers may be openers or mixed-role pitchers.
- MLB game-log rate fields should not be averaged.
- `k_rate` and `bb_rate` currently mean K/9 and BB/9, not percentages.
- The starter profile uses current calendar year and regular-season game type.
- The fallback may reintroduce mixed-role season data when game logs fail; this is intentional resilience and is surfaced through `data_source`.
- Small samples are stabilized toward neutral, but weights are not historically calibrated.
- Dashboard and reports consume generated artifacts; rebuild before diagnosing UI.
- Recommendation history is immutable.
- Odds history is append-only.
- PASS is neutral, not support.
- Do not interpret one slate as calibration evidence.

---

# 12. New-Session Kickoff Prompt

```text
We are resuming SharpStack development in C:\CheekSplittersAnalytics on branch
feature/recommendation-history.

Read PROJECT_HANDOFF.md, ARCHITECTURE.md, ROADMAP.md, CHAT_PROTOCOL.md,
DEVELOPMENT_ENVIRONMENT.md, and PARKING_LOT.md before proposing code.

The current uncommitted objective is Sprint 52 Starter Model v2:
starter-only MLB game-log aggregation, richer starter payloads, and stabilized
skill-based starter scoring. Validate and commit that work first.

After the commit and push, the next approved priority is the MLB bullpen provider
and integration. The repository already contains engine/mlb/bullpen modules; do
not replace them. Investigate their contracts and build the missing MLB provider
and BullpenSnapshot plumbing.

Do not drift into starter recency blending, metric-specific stabilization,
dashboard polish, calibration, or broad refactors. Use small targeted edits,
preserve backward compatibility, and verify provider data before tuning models.
```

---

# 13. Long-Term Vision

SharpStack is evolving into an explainable, evidence-driven sports analytics platform with:

- correct provider data
- role-aware sport models
- canonical decision contracts
- immutable recommendations and odds history
- reproducible builds
- transparent scoring
- historical ROI and CLV analysis
- multi-sport expansion without architectural duplication

The immediate discipline is simple:

**Finish Starter Model v2 cleanly, then build the bullpen provider correctly.**
