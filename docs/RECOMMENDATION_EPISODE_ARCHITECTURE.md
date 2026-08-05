# Recommendation Episode Architecture

Sprint 79.0 audit date: 2026-08-05.

This document is audit and design only. It does not change production code,
database schema, or persisted data.

Sprint 79.1 implementation note: the schema foundation now exists in ORM
models and an Alembic migration. No consumers, grading services, analytics,
history, Explorer, Dashboard, Best Bets, or persisted data were migrated.

## Purpose

SharpStack must preserve every prediction snapshot for auditability while
counting only one statistically meaningful recommendation per game and market
in primary performance analytics.

The current persistence layer stores immutable model-run snapshots correctly,
but Model Health and historical analytics currently operate at snapshot level.
Repeated builds can therefore inflate performance sample size unless a
canonical recommendation layer is added.

## Definitions

### Prediction Snapshot

An immutable record produced by one model run. It represents the exact model
state at prediction time.

Current table: `recommendations`.

Key fields:

- `id`
- `model_run_id`
- `model_version_id`
- `idempotency_key`
- `provider_game_id`
- `league_code`
- `sport`
- `market_type`
- `selection`
- `market_line`
- `projection`
- `confidence`
- `components`
- `recommendation_time`
- `scheduled_start_at_prediction`

Snapshots are never edited or deleted.

### Recommendation Stream

The long-lived stream of pregame recommendations for one model family, game,
league, and market.

Recommended stream identity:

```text
sport + league_code + provider + provider_game_id + market_type + model_version_id
```

Selection does not belong in the stream identity. A stream can contain Yankees,
Red Sox, PASS, OVER, UNDER, or changing total lines over time.

### Recommendation Episode

A continuous pregame period in one stream during which the same actionable
selection remains active.

Tier, Hammer, confidence, price, edge, or metadata changes with the same
selection do not create a new episode.

Selection changes do create a new episode:

- `Yankees -> Yankees -> Yankees`: one episode
- `Yankees -> Red Sox`: close Yankees episode, open Red Sox episode
- `OVER 8.5 -> UNDER 8.5`: close OVER episode, open UNDER episode
- `PASS -> Yankees`: open an actionable Yankees episode
- `Yankees -> PASS`: close Yankees episode; no actionable episode is active
- `Yankees -> PASS -> Yankees`: two Yankees episodes

### Canonical Recommendation

The final active, eligible pregame actionable episode before lock/first pitch.

Only the canonical recommendation counts in primary:

- win/loss record
- Model Health
- calibration
- Hammer performance
- recommendation-tier performance
- published historical record

Earlier snapshots and superseded episodes remain available for timeline,
flip, and audit analysis.

## Current-State Findings

### Tables

| Table | Current role |
|---|---|
| `model_runs` | one persisted Registry/model run; keyed by `logical_run_key` for retry-stable run persistence |
| `recommendations` | immutable prediction snapshots; also still used as generic recommendation rows |
| `active_recommendation_slots` | mutable current pointer per `provider_game_id + league_code + market_type` |
| `recommendation_activation_events` | append-only activation/supersession/withdrawal event log |
| `game_results` | mutable authoritative provider result keyed by `provider + league_code + provider_game_id`, with revision counter |
| `prediction_snapshot_grades` | immutable grade of one snapshot against one game-result revision |
| `recommendation_grades` | legacy wager-settlement table; not Sprint 64 prediction grading |

### Current Constraints

| Table | Constraint |
|---|---|
| `recommendations` | unique nullable `idempotency_key` |
| `active_recommendation_slots` | unique `provider_game_id + league_code + market_type` |
| `prediction_snapshot_grades` | unique `prediction_snapshot_id + game_result_id + game_result_revision` |
| `game_results` | provider identity and revision managed by ingestion service |

### Services And Functions

| File | Current responsibility |
|---|---|
| `app/services/prediction_snapshot_service.py` | defines immutable snapshot identity, payload, idempotency, run lifecycle |
| `app/services/prediction_snapshot_persistence_service.py` | persists runs, inserts snapshots, updates active slots, appends activation events |
| `app/services/daily_persistence_service.py` | persists Registry, ingests recent results, grades all matching snapshots |
| `app/services/game_result_ingestion_service.py` | creates/updates provider result rows and increments revisions on changes |
| `app/services/prediction_snapshot_grading_service.py` | grades one snapshot against one game-result revision |
| `app/services/recommendation_analytics_service.py` | derives Model Health from snapshots and latest grade revision |
| `app/services/recommendation_history_service.py` | legacy history reader tied to legacy `Game`, `League`, and settlement grade tables |
| `tools_persist_daily_history.py` | CLI entry point for daily snapshot/result/grade persistence |
| `tools_build_recommendation_registry.py` | builds current Registry and Play of Day artifacts |
| `dashboard/pages/model_health_page.py` | reads `RecommendationAnalyticsService` |
| `dashboard/pages/best_bets_page.py` | reads current Registry JSON and Play of Day JSON |
| `dashboard/components/explorer/recommendation_explorer.py` | renders snapshot-style recommendation detail from current card artifacts |

### Current Behavior

Current Azure evidence before this design:

- 15 unique MLB games
- 30 game/market pairs
- 4 model runs
- 120 distinct pending snapshots
- 126 pending grade rows
- no final games currently failing to grade

The 120 snapshots are correct historical evidence. They are not 120 primary
recommendations.

## Duplicate-Grade Root Cause

Game `824646` has extra pending grade rows because its `game_results` row has
revision `3` while still `SCHEDULED`.

Current grade constraint is:

```text
prediction_snapshot_id + game_result_id + game_result_revision
```

That means a snapshot can receive one PENDING grade for revision 1, another
PENDING grade for revision 2, and another PENDING grade for revision 3. This is
not a same-revision duplicate; it is expected under the current immutable
grade identity.

Root cause:

1. `GameResultIngestionService` increments `GameResult.revision` whenever any
   normalized result field changes.
2. `DailyPersistenceService._grade_matching_snapshots` grades every snapshot
   for the game after each ingestion.
3. `PredictionSnapshotGradingService` treats each game-result revision as a
   unique immutable evaluation.
4. Scheduled/pre-final result revisions therefore create multiple immutable
   `PENDING` grades for the same snapshot.

Would duplicates all grade after completion?

No. Existing `PENDING` grade rows are immutable and will remain pending for
their historical pre-final revisions. A final result revision would create a
new grade row for each snapshot, likely `WIN`, `LOSS`, `PUSH`, `VOID`, or
`UNGRADEABLE`. Analytics that select the latest result revision avoid counting
older pending rows, but raw grade-row counts are inflated.

Minimal corrective approach:

- Do not create immutable grade rows for non-terminal `SCHEDULED` or `LIVE`
  result revisions, or
- separate snapshot/result matching status from immutable final grading.

For canonical episode grading, grade only canonical locked recommendations
against terminal result revisions. Pending display can be derived, not stored
as repeated immutable facts.

## Proposed Schema

Minimum new structure:

### `recommendation_streams`

One row per long-lived model/game/market stream.

Fields:

- `id`
- `sport`
- `league_code`
- `provider`
- `provider_game_id`
- `market_type`
- `model_version_id`
- `created_at`
- `updated_at`

Unique constraint:

```text
sport + league_code + provider + provider_game_id + market_type + model_version_id
```

Implemented Sprint 79.1 uniqueness key:

```text
sport + league_code + provider + provider_game_id + market + model_version
```

`model_version_id` is stored as an optional FK for relational linkage, but the
deterministic stream identity uses the approved model-version string.

### `recommendation_episodes`

One row per continuous actionable selection episode.

Fields:

- `id`
- `stream_id`
- `selection`
- `selection_side`
- `market_line`
- `status`
- `opened_at`
- `closed_at`
- `lock_timestamp`
- `closure_reason`
- `opened_by_snapshot_id`
- `latest_snapshot_id`
- `canonical_snapshot_id`
- `superseded_by_episode_id`
- `created_at`
- `updated_at`

Recommended statuses:

- `ACTIVE`
- `WITHDRAWN`
- `SUPERSEDED`
- `LOCKED`
- `GRADED`
- `VOID`

Implemented Sprint 79.1 fields:

- `recommendation_stream_id`
- `selection`
- `selection_side`
- `market_line`
- `status`
- `opened_at`
- `closed_at`
- `locked_at`
- `closure_reason`
- `canonical_snapshot_id`
- `superseded_by_episode_id`
- timestamps

Unique constraints:

- only one `ACTIVE` episode per stream
- only one canonical episode per stream
- no duplicate open actionable episode for the same stream, selection, side, and opened timestamp

### `canonical_recommendation_grades`

Preferred if a separate grade entity is needed instead of extending
`prediction_snapshot_grades`.

Fields:

- `id`
- `episode_id`
- `canonical_snapshot_id`
- `game_result_id`
- `game_result_revision`
- `grade_status`
- `graded_at`
- `grading_version`

Unique constraints:

```text
episode_id + game_result_id + game_result_revision
canonical_snapshot_id + game_result_id + game_result_revision
```

Implemented Sprint 79.1 rule:

```text
recommendation_episode_id
```

This guarantees one canonical grade per episode. Snapshot-level
`prediction_snapshot_grades` remains in place as legacy/audit-only during the
transition.

Alternative minimal path:

- Add `recommendation_episode_id` to `recommendations`.
- Add `is_canonical` or `canonical_snapshot_id` through the episode table.
- Keep `prediction_snapshot_grades` for snapshot audit only.
- Point Model Health to canonical episode grades.

## Identity Rules

### Stream Identity

```text
sport + league_code + provider + provider_game_id + market_type + model_version_id
```

Selection is not included.

### Episode Identity

```text
stream_id + normalized actionable selection + selection_side + opened_at
```

Market line remains an episode/snapshot field for audit and canonical grading
context, but it does not define episode identity. `OVER 8.5 -> OVER 9.0`
stays inside the same episode; `OVER -> UNDER` opens a new episode.

### Snapshot Identity

Current snapshot idempotency remains:

```text
logical_run_key + provider_game_id + league + market + selection + selection_side
```

This is appropriate for immutable build snapshots and should remain separate
from episode identity.

## Episode Begin And Close Rules

An episode begins when:

- a verified pregame snapshot is actionable, and
- no active episode exists for the stream, or
- the active episode has a different selection or side.

An episode closes when:

- a different actionable selection appears: `SUPERSEDED`
- the stream becomes PASS/no-play: `WITHDRAWN`
- the game locks/starts: `LOCKED`
- game is postponed/canceled: `VOID`
- manual administrative withdrawal occurs: `WITHDRAWN`

Tier/Hammer/confidence/market changes with same selection:

- update `latest_snapshot_id`
- append timeline evidence
- keep the same episode open

## Canonical Selection Rule

Canonical recommendation:

> Last eligible pregame snapshot in the final active actionable episode before
> lock/first pitch.

If no build occurs immediately before first pitch:

- lock using the latest eligible pregame snapshot known before scheduled start.
- `lock_timestamp` should be the scheduled start if no more authoritative
  start/lock timestamp is available.

If the final snapshot is model-only:

- it can still be canonical if it is verified pregame and actionable.
- market metadata remains display/provenance only.

If KBO game-state verification is unavailable:

- do not lock as canonical unless pregame eligibility is verified.
- otherwise keep the stream unverified and exclude it from primary analytics.

If the game is postponed:

- keep snapshots and episodes for audit.
- do not grade as win/loss.
- close active episode as `VOID` or keep `ACTIVE` only if the provider supplies
  a reliable rescheduled start and the recommendation is still pregame-valid.

If the game is canceled:

- close active episode as `VOID`.

If suspended/incomplete:

- leave canonical grade pending until final or void status is authoritative.

## State Machine

Use only these episode states:

```text
ACTIVE -> SUPERSEDED
ACTIVE -> WITHDRAWN
ACTIVE -> LOCKED
ACTIVE -> VOID
LOCKED -> GRADED
LOCKED -> VOID
```

State meanings:

- `ACTIVE`: current actionable episode before lock.
- `SUPERSEDED`: selection changed to a different actionable selection.
- `WITHDRAWN`: active actionable selection became PASS/no-play or was manually withdrawn before lock.
- `LOCKED`: final canonical episode selected at game lock/first pitch.
- `GRADED`: locked canonical episode received terminal grade.
- `VOID`: game or recommendation cannot produce a valid performance result.

No `OBSERVED` state is required. PASS snapshots are observations on the stream
timeline, not episodes.

## Analytics Contract

| Surface | Authoritative entity |
|---|---|
| Recommendation Timeline | snapshots + activation events |
| Recommendation Explorer detail | snapshots + episode context |
| Best Bets current slate | active episode/current snapshot from Registry or active slots |
| Dashboard current slate | active episode/current snapshot from Registry or active slots |
| Recommendation History | canonical recommendations, with timeline access |
| Model Health | canonical graded recommendations |
| Calibration | canonical graded recommendations |
| Hammer performance | canonical graded recommendations |
| Flip analysis | episodes + snapshots |
| Play of Day current slate | current selected snapshot |
| Play of Day history | canonical Play of Day episode/selection record |

## Play Of Day

Play of Day should be represented as a separate daily selection event that
references the underlying recommendation episode and snapshot.

Recommended identity:

```text
sport + league_code + market_date + play_of_day_scope
```

It should record:

- selected snapshot ID
- selected episode ID
- selected at
- replaced/superseded by if changed
- final canonical Play of Day at lock

Primary Play of Day performance should count one canonical daily selection,
not every Dashboard/Registry rebuild.

## Grading Contract

Snapshots:

- may keep snapshot-level grades for audit if desired.
- should not feed primary Model Health by default.

Episodes:

- receive primary grade only when locked/canonical.
- grade relationship should point to the canonical snapshot and result
  revision used for evaluation.

Game results:

- scheduled/live result revisions should not create persistent pending grades
  for every snapshot.
- terminal revisions should create or reuse one canonical grade per episode.

## Migration And Reset Recommendation

Do not delete snapshots.

Recommended migration path:

1. Create streams from distinct snapshot stream keys.
2. Replay snapshots and activation events in recommendation time order.
3. Build episodes according to the selection/line rules.
4. Mark active final pregame episode per stream.
5. Lock episodes where game start has passed and eligibility is verified.
6. Create canonical grades only for locked episodes with terminal result rows.
7. Leave existing snapshot grades as audit rows or mark them legacy in analytics.

For the current tiny post-reset sample, no reset is necessary. A one-time
backfill is enough.

## Implementation Sequence

1. Add ORM models for `RecommendationStream` and `RecommendationEpisode`.
2. Add read-only episode builder tests from synthetic snapshot timelines.
3. Extend persistence service to resolve stream and episode while inserting
   snapshots.
4. Update active-slot handling to point at the latest snapshot but episode
   handling to preserve continuous selection identity.
5. Add canonical lock service using scheduled start/game status.
6. Add canonical grading service for locked episodes and terminal results.
7. Stop creating persisted `PENDING` snapshot grades for non-terminal result
   revisions, or isolate them from primary analytics.
8. Point Model Health and calibration to canonical episode grades.
9. Add timeline views that preserve all snapshots and episode transitions.
10. Backfill streams/episodes from existing post-reset snapshots.

## Acceptance Criteria

- Repeated builds with the same selection create one episode.
- Selection flips create separate episodes.
- PASS withdraws the active episode.
- PASS followed by same selection opens a new episode.
- Totals line changes stay inside the same episode when the selected side does
  not change.
- Exactly one canonical recommendation per stream can be counted in primary
  analytics.
- Model Health sample size equals canonical graded recommendations, not raw
  snapshots.
- Snapshot timeline still shows every model run.
- Scheduled/live result revisions do not create repeated pending performance
  facts.
- Terminal result grading is idempotent.
- Duplicate raw grade-row counts cannot inflate analytics.

## Risks And Unresolved Decisions

- Provider lock timing: scheduled start may shift. Canonical lock should prefer
  authoritative provider start when available, otherwise prediction-time
  scheduled start.
- KBO verification: exclude unverified KBO streams from canonical analytics
  until pregame eligibility is reliable.
- Totals identity: market-line changes stay inside the same episode when the
  selected side remains unchanged; canonical grading uses the final canonical
  snapshot's stored line.
- Model version identity: stream key includes model version. If future
  analytics wants cross-version continuity, add a model-family key.
- Existing `RecommendationHistoryService` is legacy-shaped and joins legacy
  `Game`/`League` tables; it should be replaced or adapted for canonical
  episode history.
