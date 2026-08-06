# SharpStack MLB Analytics
# PROJECT_HANDOFF.md

> Operational source of truth for resuming development in a new ChatGPT or Codex session. Read this together with `ARCHITECTURE.md`, `ROADMAP.md`, `CHAT_PROTOCOL.md`, `DEVELOPMENT_ENVIRONMENT.md`, and `PARKING_LOT.md` before proposing code.

---

# 1. Project Status

**Repository:** `C:\CheekSplittersAnalytics`
**Primary branch:** `feature/recommendation-history`
**Environment:** Windows 11 / PowerShell / Python 3.13+
**Current milestone:** Epic 1 â€” Model Correctness
**Current work item:** Sprint 68.1 Application Shell - awaiting review
**Working tree:** Application-shell implementation pending review; do not commit or push
**Sprint 62 status:** Complete

SharpStack is stable and actively developed. The platform already has a functioning MLB recommendation pipeline, Recommendation Registry, Play of the Day, structured explanations, dashboard, Discord reporting, recommendation history, and an Azure PostgreSQL persistence foundation.

**Current baseline:** Dashboard routing is stable and the Model Health page is
reachable through the SharpStack shell. No work has been lost. The experimental
UI redesign is preserved only on `backup/model-health-ui-wip` at `45f380a` and
must be treated as a recovery/reference branch, not an implementation source.

**Current database status:** Azure PostgreSQL is operational for
`recommendations`, `game_results`, and `prediction_snapshot_grades`.
`RecommendationAnalyticsService` remains the single, read-only source for
historical reporting; no analytics tables are maintained.

**Model Health routing:** the clean dashboard shell owns Model Health routing.
Launch with `streamlit run dashboard/app.py`; the horizontal SharpStack
navigation includes Model Health, while `.streamlit/config.toml` disables
Streamlit's automatic file-based page explorer. The dashboard-only runtime
bootstrap must run before importing `app.services` so `dashboard/app.py` cannot
shadow the repository `app` package.

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

**Sprint 59 — Conservative Availability Evidence:** implemented and awaiting
review. The ledger now adds `availability_evidence`, derived only from
provenance, `workload_assessment`, and role evidence. Its only statuses are
`UNKNOWN`, `NO_OBSERVED_CONCERN`, and `OBSERVED_WORKLOAD_CONCERN`; none
predict a pitcher will appear. Incomplete, empty, failed, or limited-history
evidence remains `UNKNOWN`. Role candidates add explanatory context only, and
the new object remains unused by aggregation, scoring, totals, confidence, and
recommendations.

**Sprint 61 — Prediction Snapshot Architecture:** complete. A typed immutable
`PredictionSnapshot` now converts canonical Registry rows into prediction-time
identity, run, model, market, evidence-summary, component, and explanation
data. Its prediction-time schedule field is explicitly
`scheduled_start_at_prediction`; later schedule changes are external mutable
observations. `PredictionSnapshotLifecycle` owns one in-memory slate run with explicit
begin, persist, complete, and fail transitions; it has no Azure write hook or
build integration yet. A retry-stable `logical_run_key` is derived from the
durable logical build ID, canonical artifact fingerprint, model identity, and
schema version; database `ModelRun` UUIDs remain relational identities only.
The legacy per-game `RecommendationService.save_batch()`
still creates `ModelRun` records and must be replaced by a future transactional
Azure adapter after an idempotency-key schema migration is approved.

**Sprint 62 — Azure Prediction Persistence and Active Recommendation
Lifecycle:** complete. Immutable snapshots now persist
through `Recommendation` with deterministic idempotency and direct
prediction-time identity fields. Append-only activation events record
activation, supersession, withdrawal, and reinstatement; a unique mutable
active-slot projection exposes only one current snapshot for each provider
game, league, and market. The transaction creates the run, inserts snapshots,
locks active slots, records events, updates slots, and completes the run as one
unit. Only an already completed logical run is idempotent; any persisted
incomplete run fails loudly, while a fully rolled-back attempt has no run row
and can retry cleanly. Registry JSON, dashboard, Discord, Play of the Day, and grading behavior
remain unchanged until a later approved consumer-integration patch.

**Sprint 63 — Ground Truth (Game Results):** complete. `GameResult` is a
standalone mutable provider-outcome record keyed by provider, league, and
provider game ID. It stores canonical game status, final scores, winner side,
derived total score, completion/extra-innings context where supplied, source
update metadata, local ingestion time, and an incrementing revision for
provider corrections. The ingestion service derives totals from away/home
scores and rejects an inconsistent supplied total. It performs idempotent
identity lookup and correction-safe updates in one transaction. It does not read or write PredictionSnapshots,
recommendations, grades, odds, ROI, CLV, Hammer, Market Value, or model logic.

**Sprint 64 — Recommendation Grading:** complete. A new immutable
`RecommendationGrade` evaluates one persisted PredictionSnapshot against one
specific `GameResult` revision using a grading-rule version. It records only
`PENDING`, `WIN`, `LOSS`, `PUSH`, `VOID`, or `UNGRADEABLE`; prediction tiers,
odds, stake, profit, ROI, CLV, analytics, reporting, and active-slot behavior
remain outside this sprint. The pre-existing wager-settlement record remains
isolated as legacy compatibility data and is not used by this grading service.
New moneyline snapshots retain their display selection and also serialize an
immutable `selection_side` (`HOME` or `AWAY`) derived from the matchup so
grading can compare it to provider-independent `GameResult.winner_side`.
`grading_version` records the canonical algorithm version but is not a second
grade identity: each snapshot/result revision has exactly one grade. A future
grading-rule upgrade must migrate or recompute that canonical record rather
than create parallel versioned grades.

**Sprint 65 — Operational Persistence Wiring:** complete. The standard
`build.py` workflow now invokes `tools_persist_daily_history.py` after the
canonical Registry is built and before downstream Explorer and Discord output.
The command persists immutable Registry snapshots via the existing lifecycle
service, normalizes recent MLB Stats API schedule results through
`GameResultIngestionService`, then grades matching snapshots using stable MLB
provider game IDs. It does not write directly to `game_results`, change model
outputs, or alter Registry JSON. Azure is currently at Alembic revision
`c0f6e12d9a41`; the reviewed immutable persistence lifecycle is operational in
Azure. Recommendations now flow from engine output through immutable snapshot
persistence, authoritative result ingestion, grading, and historical
analytics without manual intervention. Registry `event_time` remains
presentation-only; immutable snapshots populate `scheduled_start_at_prediction`
only from canonical scheduled time, otherwise leaving it null.

**Sprint 66 — Model Health Analytics Service:** complete and stable. The read-only
`RecommendationAnalyticsService` derives on-demand model-health buckets from
persisted prediction snapshots and their latest immutable grade revision. It
groups by league, market, and canonical recommendation tier and reports sample
size, grade counts, win percentage, decision rate, and first/last prediction
timestamps. It writes no analytics records and is independent of dashboard/UI,
persistence, and grading behavior.
Model Health excludes legacy rows by default: an immutable snapshot requires
both `idempotency_key` and `model_run_id`. Display `NO PLAY` variants normalize
to `PASS`; `BET` remains the established MLB totals tier and is not relabeled
as a moneyline tier. Historical totals stored with opaque odds-provider event
IDs cannot safely match authoritative MLB game results and remain pending;
the service does not infer a matchup-based link or alter grading rules.

**Sprint 67 — Model Health:** complete. Model Health provides league, market,
and recommendation-tier grouping with `ModelHealthReport` and
`ModelHealthBucket`; it uses latest immutable grades and excludes legacy rows
by default. The dashboard page is restored and reachable through the clean
SharpStack shell.

The MLB full slate presents projected-winner ranking separately from betting
value. Its compact cards display the canonical conviction and market-value
badges; diagnostics, including Hammer and Market vs Model, remain inside
SharpStack Intelligence. Best Bets retains Registry-owned ranking.

Sprint 76.1 replaced the live KBO per-game presentation renderer only. The
`KBO` route, card loading, generated JSON, odds enrichment, registry adapter,
persistence, history, grading, and KBO recommendation logic remain unchanged.
KBO games now render through a compact workstation-style card that consumes the
existing `kbo_card.json` payload directly and presents matchup, selected side,
recommendation tier, model strength, market status, model snapshot, pitching
snapshot, and existing reasons without the legacy stacked summary/progress/
intelligence-expander presentation.

Sprint 76.3 updated the multi-sport Dashboard presentation only. The Dashboard
now opens as a SharpStack Command Center with system metrics and compact
workstation previews for MLB, totals, KBO, and Bomb Lab using existing page
routes, badges, status pills, logos, and generated card/registry data.

Sprint 76.4 polished Bomb Lab research presentation only. Pitcher Explorer now
uses compact workstation rows with logos and vulnerability score styling,
Metrics Lab groups existing fields into research sections, and Game Explorer
reuses the Bomb Lab workstation card language. No Bomb Lab payloads, rankings,
scores, models, or recommendation logic changed.

Sprint 76.4 cleanup retired the standalone Park research section from Bomb Lab
presentation while preserving park inputs inside existing Bomb Score display
surfaces. Pitcher Explorer now includes an explicit Side column after Attack
Team and keeps presentation-only risk coloring from existing payload values.

Sprint 76.4b reshaped Pitcher Explorer into two-column workstation cards:
attack identity on the left, vertical research metrics on the right, and
existing Bomb Lab reasons as compact bullets beneath each card. The previous
table-style header row and oversized reason banners were removed; rankings,
scores, target selection, payloads, routing, filtering, and sorting remain
unchanged.

Pitcher Explorer final cleanup added the pitching-team logo beside the pitcher
identity, compressed the Side and metric rows, renamed Tier to Attack Tier, and
moved existing Bomb Lab reasons into a left-column Quick Intel section.

**Sprint 68.1 — Application Shell:** implemented and awaiting review. The
dashboard now has a dedicated `dashboard/shell/` boundary that owns one route
configuration, compact sidebar navigation, slim top bar, and shell session
initialization. `dashboard/app.py` continues to own only page dispatch; all
existing renderers, route names, analytics, persistence, grading, and model
behavior are unchanged. Shell CSS is scoped to the sidebar and top bar, and
the failed `backup/model-health-ui-wip` experiment was not merged.

**Sprint 68.2 — Design Tokens:** implemented and awaiting review. Shared
frontend colors, spacing, typography, radius, and sizing now live in
`dashboard/design/tokens.py` as CSS custom properties. Only shell chrome
consumes the new tokens in this sprint; existing page-specific CSS remains
unchanged by design. `docs/DESIGN_SYSTEM.md` defines the approved token roles
and guardrails for future shared components.

**Sprint 68.3 — Sidebar Component:** implemented and awaiting review. The
shell sidebar now renders canonical grouped navigation through compact,
token-based navigation rows rather than Streamlit buttons. It preserves the
existing `st.session_state.page` route contract, keeps every group expanded by
default, and exposes the active route with a clear accent indicator. No page
renderer, route name, backend service, or URL-routing behavior changed.

**Sprint 68.3.1 — Sidebar Density:** implemented, then superseded by the
wrapper-cascade correction in Sprint 68.3.2. The compact-control token is 32px
and shell-only padding/group spacing are reduced, but that change alone did not
address Streamlit-generated layout gaps. No overflow is hidden and no route or
page behavior changed.

**Sprint 68.3.2 — Sidebar Viewport Layout:** implemented and awaiting visual
review. The correction targets Streamlit's actual sidebar wrappers: the
sidebar-content vertical block, element containers, and inline radio-group
layout. The active rail now targets the checked radio root rather than its
sibling label, and Engine Online is placed by the shell flex column. No hidden
overflow, route, or page behavior changes were introduced.

**Sprint 68.3.3 — Streamlit API Cleanup:** implemented and awaiting review.
The deprecated Streamlit container-width dataframe keyword was removed from
the Model Health table and replaced with Streamlit's modern
`width="stretch"` API. No layout, styling, routing, shell, analytics,
persistence, model, recommendation, or scoring behavior changed.

**Sprint 68.5 — SharpStack Status Pills:** implemented and awaiting manual
screenshot review. A reusable compact `StatusPill` component now provides
escaped, inline semantic status HTML using existing design-token colors. The
first migration is intentionally limited to the Best Bets registry card market
status field (`REAL MARKET` / `MODEL ONLY`). No status calculations,
recommendation logic, routing, card structure, database code, metrics, shell,
or page headings changed.

**Sprint 68.6 — Standard Page Header and Toolbar:** implemented and awaiting
manual screenshot review. A reusable `render_page_header()` pattern now
renders compact escaped page-title HTML with optional eyebrow, status, and
native metric columns. The first migration is intentionally limited to the
Best Bets page header. Best Bets title/subtitle text, metric labels and
values, tabs, cards, data loading, empty states, StatusPill behavior,
routing, shell, and recommendation logic remain unchanged.

**Sprint 68.7 — Recommendation Card Refinement:** implemented and awaiting
manual screenshot review. Best Bets registry cards now use registry-scoped
presentation classes to make the selection, matchup, recommendation row, and
Hammer Score read with less boxed-in visual weight. The renderer remains
data-compatible, StatusPill mappings are unchanged, and Play of the Day logic
was not touched. No recommendation calculations, registry data, sorting,
filtering, tabs, routing, page header, metrics, database code, sidebar, or
shell behavior changed.

**Sprint 68.8 — Table Styling and Density:** implemented and awaiting manual
screenshot review. A reusable `render_data_table()` wrapper now centralizes
native Streamlit dataframe defaults and a scoped SharpStack table style hook.
The first migration is intentionally limited to First 5 Lab's Market Edge tab
Full Market Board. The table rows, column order, column labels, numeric
values, native toolbar behavior, scrolling, tabs, calculations, routing, and
all other tables remain unchanged.

**Sprint 68.9 — Matchup Hero Refinement:** implemented and awaiting manual
screenshot review. The existing Matchup Hero now presents away/home teams,
the projected winner, recommendation, model win probability, and confidence
with restrained analytical hierarchy using only existing game/model fields.
No calculations, model output, routing, sidebar, headers, tables,
recommendation cards, page layout, or Play Summary logic changed.

**Immediate roadmap:** Sprint 69 Recommendation Explorer 2.0; Sprint 70 ROI
analytics; Sprint 71 closing-line value; Sprint 72 calibration; Sprint 73
recommendation attribution; Sprint 74 historical charts; Sprint 75 model
version comparison. These build on the immutable prediction, result, and
grading foundation rather than altering it.

Future reporting must keep separate: all historical snapshot performance,
final active recommendation performance, published recommendation performance,
wagers actually placed, model accuracy, and betting profit/ROI. They are not
one record or one headline metric.

**UI retrospective:** UI work is intentionally paused. The experimental branch
mixed feature work, navigation redesign, CSS refactoring, typography, and
spacing changes into one evolving implementation. Future UI work begins with
shell architecture and design approval, not incremental CSS adjustment.

**Next-chat objective:** do not code immediately. Design the permanent
SharpStack application shell: navigation architecture, typography and spacing
systems, reusable component hierarchy, design tokens, page template, and
implementation strategy. Freeze that shell before Explorer, CLV, ROI, or
future-sport UI work plugs into it.

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

Sprints 61-67 are complete. Sprint 68.1 is awaiting review; after approval,
follow the Sprint 68-75 sequence before returning to
deferred provider, Epic 2, calibration, or future-sport work.

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
- Critical live-line guard added: pregame recommendation eligibility is now a
  shared domain object consumed by MLB market comparison, totals
  recommendation construction, registry adapters, and daily persistence.
  Missing/unverified game state or start time fails closed for new pregame
  recommendation snapshots while preserving existing historical records for
  grading and Model Health.
- Sprint 69.1 hotfix: canonical `scheduled_start_at` must be a complete
  timezone-aware ISO datetime or `None`. KBO display-only `start_time` values
  such as `6:30pm` remain display fields only and now fail closed as
  `UNVERIFIED`; daily persistence logs and skips malformed rows
  instead of crashing the slate.
- Sprint 77.0 Pregame Recommendation Integrity makes
  `PregameEligibility(GAME_NOT_STARTED/GAME_STARTED/LIVE_MARKET/COMPLETED/
  UNVERIFIED/NO_START_TIME)` the canonical pre-recommendation gate. Registry
  adapters, Recommendation Registry publication, Best Bets top-play display,
  and daily persistence now require explicit `pregame_eligible=True` with
  `pregame_eligibility_reason=GAME_NOT_STARTED`; unverified or live rows are
  skipped without mutating historical recommendations.
- Sprint 77.2A removes market value from shared conviction and ordering.
  Hammer Score is now model-conviction only, with structural zero influence
  from edge, expected value, odds, price, implied probability, or market
  availability. Recommendation Registry, Best Bets, Dashboard previews, and
  Play of Day inherit winner-first ranking by canonical tier, model/outcome
  probability, model confidence, market-independent Hammer Score, and stable
  recommendation identity. Market edge, EV, sportsbook, and price remain
  display/provenance metadata only.
- Sprint 77.2B redesigns MLB totals recommendation conviction to be
  winner-first. Totals still choose OVER/UNDER from the model projection
  relative to the pregame line, but scoring and tier qualification now use
  model separation from the line, model confidence, data quality, and bullpen
  confidence only. Market edge, EV, price, sportsbook, stale status, and
  market quality remain display/provenance metadata and do not affect totals
  conviction.
- Sprint 77.3 intentionally reset recommendation history following
  implementation of the Winner-First recommendation engine. Historical
  recommendation metrics before this point are not comparable and were
  intentionally discarded; new recommendation-performance tracking begins
  from the first post-reset build.
- Sprint 78 completed a recommendation model audit and added durable model
  documentation in `docs/MODEL_SPECIFICATION.md` and
  `docs/MODEL_TECHNICAL_REFERENCE.md`. No production model tuning was made;
  follow-up review items remain around MLB confidence market completeness,
  KBO real-market edge finalization, Decision Builder edge fallback, and
  deterministic ranking tie-breaks.
- Sprint 78.1 closed the verified winner-first gaps: KBO real-market
  finalization now keeps edge as display metadata while using KBO model-score
  recommendation/confidence, MLB confidence no longer counts market
  probability, Decision Builder no longer substitutes edge for missing model
  conviction, and shared/registry ranking now ties by deterministic schedule,
  league, market, event, and selection fields.
- Sprint 78.2 completed the historical backtest and calibration audit in
  `docs/MODEL_VALIDATION_REPORT.md`. The current Winner-First implementation
  is conceptually aligned but empirically unvalidated: Azure contains 90
  post-reset prediction snapshots, all still `PENDING`, with no post-reset KBO
  snapshots. Do not tune weights or thresholds until resolved post-reset grades
  populate the validation tables.
- Sprint 79.0 completed the recommendation episode architecture audit in
  `docs/RECOMMENDATION_EPISODE_ARCHITECTURE.md`. The design preserves every
  immutable snapshot while introducing streams/episodes so primary analytics
  count one canonical locked recommendation per game/market instead of every
  model-run snapshot.
- Sprint 79.1 added the recommendation episode schema foundation only:
  `recommendation_streams`, `recommendation_episodes`, and
  `canonical_recommendation_grades` ORM/migration definitions plus focused
  schema tests. No consumers, grading behavior, Model Health, History,
  Explorer, Dashboard, Best Bets, or persisted data were migrated.
- Sprint 79.1 correction removed market line from episode identity. Market
  line remains stored for audit/grading context, but episodes are identified by
  stream, selection, selection side, and opened timestamp.
- Sprint 79.2 added the recommendation episode lifecycle foundation. Immutable
  snapshot persistence now resolves streams, attaches snapshots to episodes,
  supersedes selection flips, withdraws PASS/no-play transitions, and leaves
  ineligible snapshots unattached. Analytics and grading remain unmigrated.
- Sprint 79.2 correction preserves the committed Sprint 79.1 migration
  `a7c9e2f4b681_add_recommendation_episode_schema.py` unchanged. Snapshot-to-
  episode attachment is isolated in follow-on revision `c3d9a4f7e2b1`, which
  adds nullable `recommendations.recommendation_episode_id`, its foreign key to
  `recommendation_episodes.id`, and the lookup index. Focused lifecycle tests
  cover stable same-selection attachment, non-splitting metadata changes,
  supersession, withdrawal evidence, ineligible unattached snapshots, PASS-to-
  actionable creation, and rollback of snapshot persistence plus episode
  attachment in one transaction.
- Sprint 79.3 added canonical episode locking and grading services. The
  canonical recommendation is the final active actionable episode in a stream,
  locked to the latest attached eligible pregame snapshot before
  `scheduled_start_at`. Canonical grading reuses the existing snapshot grading
  rules, writes at most one `canonical_recommendation_grades` row per episode,
  and transitions `LOCKED` episodes to `GRADED`. `CANCELED` marks the episode
  `VOID`; `SUSPENDED` remains pending after lock. The daily result flow now
  uses canonical episode grading and does not create new snapshot-level
  `PENDING` rows for episode-enabled snapshots. Existing snapshot grades remain
  legacy/audit-readable and are not rewritten.
- Sprint 79.4 migrated official analytics reads to canonical episodes and
  canonical grades through `CanonicalRecommendationReadModel`.
  `RecommendationAnalyticsService`, Model Health, and
  `RecommendationHistoryService` now count one official recommendation per
  `GRADED` canonical episode and use the canonical snapshot for tier,
  confidence, Hammer, projection, market line, and timestamps. Snapshot
  timelines remain available through explicit episode timeline reads only.
  Legacy `prediction_snapshot_grades` are not deleted or rewritten and are not
  a silent fallback; canonical-empty analytics return empty samples. Read-only
  Azure verification reached revision `f2c8a1e6d4b7`, where episode tables are
  not yet deployed; immutable snapshot count was 172 at verification time.
- Sprint 77.0 replaced the live Bomb Lab tabbed presentation with a
  presentation-only workstation renderer. The Bomb model, HR calculations,
  generated JSON contract, registry, persistence, odds, routing, and build
  pipeline remain unchanged; the page now consumes the existing
  `bomb_lab_card.json` payload directly for matchup, Bomb recommendation,
  batter snapshot, supporting factors, and supporting metrics.
- Sprint 77.0 polish restored the multi-hitter Bomb Squad workflow inside
  each Bomb Lab workstation card: the existing top hitter remains featured,
  alternate hitters are immediately selectable from compact cards, and the
  supporting reasons are presented as `Why We Like Him`.

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

Sprint 62 prediction persistence is awaiting review. Sprint 63 is limited to
objective outcome truth, and Sprint 64 now evaluates those results against
immutable snapshots. Sprint 65 wires those services into the daily build;
Sprint 67 Model Health is complete. Sprint 68 Application Shell Redesign is
design-only, followed by Sprint 69 Recommendation Explorer 2.0 through Sprint
75 Model Version Comparison. Keep all-snapshot, final-active-call, published,
placed-wager, model-accuracy, and profit/ROI reporting distinct.

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

**Complete the approved outcomes-and-learning sequence before returning to
deferred provider/model intelligence, calibration, or platform work.**
