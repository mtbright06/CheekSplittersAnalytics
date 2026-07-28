# SharpStack MLB Analytics
# PROJECT_HANDOFF.md

> Operational source of truth for resuming development in a new ChatGPT or Codex session. Read this together with `ARCHITECTURE.md`, `ROADMAP.md`, `CHAT_PROTOCOL.md`, `DEVELOPMENT_ENVIRONMENT.md`, and `PARKING_LOT.md` before proposing code.

---

# 1. Project Status

**Repository:** `C:\CheekSplittersAnalytics`
**Primary branch:** `feature/recommendation-history`
**Environment:** Windows 11 / PowerShell / Python 3.13+
**Current milestone:** Epic 1 â€” Model Correctness
**Current work item:** Documentation synchronization after completed SSRP and
MLB recommendation-contract work
**Working tree:** Documentation updates pending review; do not commit or push
**Sprint 56 status:** Complete

SharpStack is stable and actively developed. The platform already has a functioning MLB recommendation pipeline, Recommendation Registry, Play of the Day, structured explanations, dashboard, Discord reporting, recommendation history, and an Azure PostgreSQL persistence foundation.

The current phase is not feature expansion. It is improving the correctness, explainability, and reliability of the underlying baseball models.

**SSRP v1:** MLB and KBO moneyline edge now use an immutable SharpStack
Reference Price when available: the first eligible real pregame quote captured
before the 60-minute MLB or 45-minute KBO cutoff. Current odds remain display
data only. SSRP is stored in a dedicated PostgreSQL table with an atomic,
create-only identity key; missing or late references produce a visible SSRP
status and no invented edge. Hammer and thresholds remain unchanged.

**Post-Sprint 56 implementation status:** SSRP v1 is implemented for MLB and
KBO moneylines. Market freshness and quote provenance now travel with the
selected quote into the completed artifact. For MLB moneylines, the
authoritative recommendation is model conviction from model probability plus
confidence; SSRP edge separately produces a market-value label. Decision
Builder, Registry, and presentation preserve both fields and their structured
explanations. Hammer remains an advisory confirmation layer and does not
replace the MLB recommendation.

**Sprint 57 — Provider Reliability, Phase 1:** implemented and awaiting
review. `build_mlb_card()` now creates one request-scoped pitcher game-log
cache shared by bullpen collection and starter profiling. The cache is not
module-global, persistent, or cross-run; it keys the MLB pitching game-log
request by endpoint, pitcher ID, season, and game type, and preserves cached
empty and failed outcomes so the existing season fallback remains unchanged.

**Sprint 57 — Provider Reliability, Phase 2:** implemented and awaiting
review. The same MLB card build now creates a request-scoped team-context cache
for doubleheaders. It reuses each team's deterministic batting and bullpen
provider results by team ID, while returning independent copies per game and
leaving probable-starter construction game-specific. The cache is not shared
across builds and does not alter serialized contracts or model inputs.

**Sprint 57 — Consciously deferred:** a shared MLB schedule snapshot across
the MLB Card, First Five, and Bomb Lab. The measured improvement is
approximately 0.52 seconds, below 1% of build time, while the required
cross-process orchestration would add disproportionate coupling and test
surface. Revisit only if build orchestration changes substantially or schedule
retrieval becomes materially more expensive.

**Sprint 58 — Bullpen Evidence Ledger, Patch 1:** implemented and awaiting
review. MLB bullpen provider output now includes an additive pitcher-level
`evidence_ledger` with existing roster, game-log, recent-usage, inclusion, and
source-status facts. It does not assign bullpen roles or availability and is
not consumed by scoring, totals, confidence, or recommendations. Failed game
logs remain explicitly unavailable rather than appearing as zero workload.
For mixed-role provenance, `observed_relief_appearances` records all non-start
outings in the raw game log, while `included_relief_appearances` records the
subset retained by the unchanged bullpen aggregation rule.

Sprint 58 Patch 2 extends that diagnostic ledger with observed relief workload
facts only. Last-3 is `as_of - 2` through `as_of`; last-5 is `as_of - 4`
through `as_of`, both inclusive and excluding future or undated outings.
Innings are derived from recorded outs; multi-inning means at least six outs.
`limited_history` is true for an empty successful log, fewer than three
observed relief outings, or no dated observed relief outings. It is `None` for
failed logs, whose workload fields remain unknown.

Sprint 58 Patch 3 adds diagnostic-only `role_evidence` to each ledger entry.
It preserves nullable game-log facts for saves, holds, games finished, recent
five-day equivalents, multi-inning relief usage, and short starts, then emits
candidate patterns only. Closer evidence is HIGH at at least 10 saves and 10
games finished, MEDIUM at 5/5, otherwise LOW with a save; setup evidence is
HIGH/MEDIUM/LOW at 10/5/1 holds. Bulk and opener candidates require observed
outs-based multi-inning or short-start-plus-relief patterns. These confidence
labels measure observed evidence strength, not a definitive role or
availability, and remain unused by all models.

**Sprint 59 — Bullpen Workload Assessment:** implemented and awaiting review.
Each bullpen evidence-ledger entry now includes an additive,
evidence-only `workload_assessment`: factual rest, consecutive-usage,
appearance-volume, innings-volume, multi-inning, and overall workload buckets
with short reasons and explicit source completeness. It uses only existing
game-log facts, preserves unknown and empty states, applies to excluded
mixed-role pitchers, and does not infer availability or affect bullpen
aggregation, scoring, totals, confidence, or recommendations.

The MLB full slate presents projected-winner ranking separately from betting
value. Its compact cards display the canonical conviction and market-value
badges; diagnostics, including Hammer and Market vs Model, remain inside
SharpStack Intelligence. Best Bets retains Registry-owned ranking.

**Roadmap sequence:** retain Epic 1 technical-debt and provider-quality work,
then Epic 2 Model Intelligence in order: Source Quality Confidence,
Lineup-Aware Offense, Rolling Form, and Park & Weather Integration. Epic 3A
then adds Recommendation Performance reporting at Sprint 63, or the earliest
approved point after sufficient persisted recommendation history is available,
followed by Historical Intelligence;
Epic 3B calibration, CLV, ROI optimization, and threshold tuning remain
evidence-gated. Epic 4 retains platform expansion and additional sports.

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

The Sprint 54, Sprint 55, and Sprint 56 execution queue is complete. Do not
select or implement new work without roadmap governance.

Do not drift into Epic 2 enhancements, Epic 3A measurement, calibration, or
future sports before Epic 1 completes. Epic 3A is planned after Epic 2 to
measure the existing recommendation record; Epic 3B calibration remains gated
on sufficient graded history.

---

# 3. Sprint 53 Status

Completed:

- S52-001 â€” Remove market leakage
- S52-002 â€” Explainable confidence / unknown starters
- S52-003 â€” Default audit
- Explicit MLB API `season` and `gameType` parameters

Sprint 53 completed:

- Sprint 53 â€” MLB Bullpen Provider
  - completes the original Real Bullpen Model work item, formerly S52-006
  - Active pitcher roster and reliever game-log ingestion
  - Normalized bullpen payload shared by totals and SharpScore
  - Source-quality metadata and neutral availability handling

---

# 4. Sprint 53 Completion Record

## 4.1 Sprint Summary

**Objective:** complete the existing MLB bullpen pipeline without replacing its
quality, fatigue, projection, adjustment, totals, or SharpScore systems.

**Completed:** added MLB active-pitcher roster and game-log ingestion, reliever
classification, raw-count aggregation, a normalized bullpen payload, game-card
integration, focused tests, and source-quality/fallback metadata.

**Outcome:** the live MLB build completed successfully with bullpen data flowing
through the existing totals and SharpScore consumers. Unavailable provider data
remains neutral and partial rather than blocking the card.

## 4.2 Architecture Decisions

- The provider owns retrieval, role classification, raw aggregation,
  normalization, and metadata because provider correctness belongs upstream of
  model scoring.
- The existing bullpen subsystem remains canonical. Adding another model or
  recalculating fatigue, quality, confidence, or run adjustments in the provider
  would duplicate ownership and make results harder to trace.
- One normalized payload is published to `game["bullpen"]` for totals and
  adapted with existing `era`/`whip` aliases for SharpScore. This preserves
  compatibility without changing `component_scores.py`.
- Availability is intentionally `UNCONFIRMED_NEUTRAL`: the current boolean
  contract receives neutral defaults while metadata exposes the uncertainty.
  A depth chart or high-precision availability model was deliberately deferred.

## 4.3 Files Changed

Added:

- `engine/mlb/bullpen/provider.py`
- `tests/test_mlb_bullpen_provider.py`

Modified:

- `engine/mlb/game_builder.py`
- `docs/PROJECT_HANDOFF.md`
- `docs/ROADMAP.md`

Unchanged by design:

- `engine/mlb/bullpen/bullpen_model.py`, `quality.py`, `fatigue.py`, and
  `game_adjustment.py`
- `engine/model/component_scores.py`
- Decision Builder and SharpScore weights

## 4.4 Validation

- Live MLB card build, Odds API integration, and totals-market integration
  passed.
- `py_compile`, `tools_test_bullpen.py`, `tools_test_mlb_totals.py`, and
  `git diff --check` passed.
- Provider tests passed.

## 4.5 Known Limitations

- Availability remains conservative; there is no closer/setup prediction model.
- Swingmen and converted starters may require role-classification refinement.
- Per-pitcher API requests could be optimized in a future sprint.

## 4.6 Parking Lot Updates

Deferred: bullpen quality enhancements, usage forecasting, advanced bullpen
metrics, velocity/Stuff+ integration, and closer availability modeling.

## 4.7 Next Execution Item

Sprint 54 is complete. Sprint 55 is Better Pitching Metrics Investigation,
formerly S52-007. It is research only: evaluate FIP, xFIP, xERA, and SIERA;
do not integrate any metric into production during this sprint.

## 4.8 Notes for Future Chats

Read the architecture, roadmap, handoff, and parking lot before proposing code.
Keep the provider upstream, retain the canonical bullpen modules, do not tune
bullpen weights yet, and do not infer precision that the available MLB data does
not support. Rebuild generated artifacts before diagnosing a presentation issue.

## 4.9 Sprint 54 Completion Record

**Objective:** reduce volatility from limited starter samples without changing
model weights, confidence, recommendation thresholds, or scoring philosophy.

**Approach:** `engine/model/pitcher_stabilization.py` centralizes the existing
empirical-Bayes formula: `IP / (IP + 50)`. At 50 innings, a metric is weighted
50% observed value and 50% league baseline; at 150 innings, it is 75% observed.
The 50-IP constant was retained to preserve established SharpScore behavior.

**Integration:** stabilized views now feed starter scoring, MLB totals, and
First Five pitcher inputs for ERA, WHIP, HR/9, K/9, and BB/9. Raw provider data
is not mutated. When innings are unavailable, raw-stat fallbacks are preserved;
unknown starters remain neutral through the existing scorer behavior.

**Validation:** focused low-, medium-, established-, and missing-innings tests;
`py_compile`; `tools_test_mlb_totals.py`; and `git diff --check` passed. The
live MLB card build could not run because this environment could not resolve
`statsapi.mlb.com` before model execution.

**Known limitations and deferrals:** baselines and the 50-IP constant are shared
across metrics; metric-specific stabilization remains deferred. Sprint 55 will
research FIP, xFIP, xERA, and SIERA only; it does not authorize production
integration.

## 4.10 Sprint 55 Research Record

**Outcome:** no production pitching metric was approved. FIP is the only
future candidate derivable from the canonical starter raw counts, but it needs
a season-specific league constant and historical incremental-value testing.
xFIP, xERA, and SIERA require unavailable batted-ball or Statcast inputs and
an approved production data contract.

**Accepted decision:** FIP is not an additive production feature. Advanced
metrics must contribute independent predictive information and pass
out-of-sample validation before production use. xERA is the preferred future
evaluation candidate only if it is licensed, validated, and operationally
supportable. No production model changes resulted from Sprint 55.

**Architecture rationale:** the current model already separately scores HR/9,
K/9, and BB/9. Adding an ERA estimator as another weighted feature would
double-count those skills and can double-regress small samples. Any later work
must use raw starter-only events, metric-specific reliability treatment,
source-quality metadata, and an out-of-sample replacement-versus-baseline test.

**Source finding:** public Baseball Savant and FanGraphs data are suitable for
research but do not establish a production redistribution or SLA contract.
Do not scrape either source for production. The full evaluation is in
`docs/SPRINT_55_PITCHING_METRICS_EVALUATION.md`.

**Next resume point:** Epic 1 review. Keep advanced pitching metrics deferred
pending licensed sourcing and historical validation; do not select a new sprint
without roadmap governance.

## 4.11 Sprint 56 Completion Record

**Objective:** make KBO confidence reflect model separation, data completeness,
starter certainty, and market availability without using mock odds as a market
signal.

**Completed:** KBO confidence now starts from an explainable baseline, adds
bounded model-separation strength and available-input completeness, and applies
unknown-starter penalties. It no longer increases from the number of generated
reasons. A missing real market receives no completeness credit, produces a
zero edge, and forces `NO PLAY`; real market edge and recommendation are
calculated only after odds enrichment.

**Architecture rationale:** the previous KBO flow used synthetic 50% mock odds
before enrichment, allowing a fabricated edge and actionable recommendation.
Finalizing after enrichment preserves the provider-to-model-to-market pipeline,
does not change Decision Builder, and keeps confidence explainable through a
serialized breakdown.

**Validation:** `py_compile`, three focused KBO confidence tests, confidence
breakdown serialization, and `git diff --check` passed. The live KBO build was
blocked before ingestion because this environment could not resolve
`mykbostats.com`.

**Known limitation:** KBO still depends on MyKBOStats for schedule and starter
data; source availability and starter identity remain visible confidence risks.
No commit was created.

---

# 5. Historical Sprint 52 Detail

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

# 6. Historical Starter Files Changed

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

# 7. Historical Starter Validation Procedure

The following was the Sprint 52 pre-commit checklist and is retained only as a
record of that completed work.

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

# 8. Historical Starter Commit Record

Sprint 52 was committed before Sprint 53; this section is retained for context
and is not an active instruction.

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

# 9. Completed Bullpen Architecture

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

Sprint 53 added a provider/normalization layer that produces a
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

These ideas may be valuable. They are not blocking the active Epic 1 objective.

---

# 11. Known Gotchas

- Patch 2.1 completed an operational UI cleanup only: the Dashboard is a
  market-deduplicated command center, Best Bets is the official betting card,
  and sport pages present intelligence inside their existing expanders. MLB's
  Decision tab reads and renders the matching canonical Decision Builder row;
  it does not calculate diagnostics. Operational pages use compact headers to
  keep current betting data above the fold. No model, confidence, ranking
  calculation, recommendation, or Decision Builder behavior changed.
- MLB moneyline recommendation authority is model conviction, not Hammer:
  `model_probability` plus `confidence` create the recommendation tier, while
  SSRP `edge` creates an independent market-value label. Keep both values
  through decision, registry, explorer, and presentation contracts.
- Market freshness is metadata from the same selected quote used for the card.
  Current odds are display context; immutable SSRP remains the moneyline edge
  reference.
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

Sprint 53 is complete in commit 139a364: the MLB bullpen provider retrieves
active pitcher roster and reliever game logs, publishes one normalized payload
for totals and SharpScore, and leaves existing bullpen models unchanged.

Sprint 54 is complete: starter ERA, WHIP, HR/9, K/9, and BB/9 now use the
shared 50-IP stabilization view in SharpScore, totals, and First Five inputs.
Sprint 55 research and Sprint 56 KBO confidence correctness are complete.
SSRP v1 is implemented, and MLB recommendation output now separates model
conviction from SSRP market value. Hammer is advisory only for MLB moneylines.

Do not select a new sprint without roadmap governance. Use small targeted
edits, preserve backward compatibility, and verify provider data before tuning
models.
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

**Complete Epic 1 model correctness before Epic 2 intelligence, Epic 3A
measurement, Epic 3B calibration, or Epic 4 platform work.**
