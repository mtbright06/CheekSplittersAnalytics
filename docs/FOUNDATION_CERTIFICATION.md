# SharpStack Foundation Certification

Sprint 79.5 audit. Documentation-only. No code changes were made for this
certification.

## Executive Summary

Recommendation Architecture is **CERTIFIED WITH OBSERVATIONS** for the local
implementation from Sprints 79.1 through 79.4.

The core local guarantees are supported by schema constraints, focused tests,
and a clear service ownership model:

- immutable snapshots attach to streams and episodes
- one active episode per stream is enforced
- canonical locking chooses one eligible pregame snapshot
- canonical grading writes at most one grade per episode
- official analytics read canonical episodes and canonical grades
- legacy snapshot grades remain isolated

Certification observations remain:

- Production/Azure is not yet deployed to the episode schema. Current Azure
  revision is `f2c8a1e6d4b7`; required episode migrations
  `a7c9e2f4b681` and `c3d9a4f7e2b1` are not applied.
- True multi-worker races are guarded by database constraints and row locks,
  but not proven by integration tests against PostgreSQL concurrent sessions.
- VOID analytics semantics remain a product decision boundary: canceled games
  mark episodes `VOID` and do not create canonical win/loss grade rows; primary
  analytics therefore do not count them as graded records.

## Architecture Diagram

```text
Registry row / PredictionSnapshot
        |
        v
PredictionSnapshotPersistenceService
        |
        +-- RecommendationEpisodeService
        |       |
        |       +-- RecommendationStream
        |       +-- RecommendationEpisode (ACTIVE / SUPERSEDED / WITHDRAWN)
        |
        v
Recommendation row (immutable snapshot, optional recommendation_episode_id)

GameResult
        |
        v
RecommendationEpisodeLockService
        |
        +-- final ACTIVE actionable episode
        +-- latest eligible attached snapshot before scheduled_start_at
        +-- canonical_snapshot_id + LOCKED + locked_at
        |
        v
CanonicalRecommendationGradingService
        |
        +-- canonical_recommendation_grades
        +-- LOCKED -> GRADED
        |
        v
CanonicalRecommendationReadModel
        |
        +-- RecommendationAnalyticsService / Model Health
        +-- RecommendationHistoryService official rows
        +-- explicit episode timeline snapshot reads
```

## Certification Matrix

| Area | Item | Status | Evidence |
|---|---|---:|---|
| A | One ACTIVE episode per stream | PASS | `RecommendationEpisode` partial unique index `uq_recommendation_episodes_one_active_per_stream`; lifecycle test preserves one active episode |
| A | Same-selection snapshots never create duplicate episodes | PASS | `RecommendationEpisodeService.process_snapshot`; `test_moneyline_same_selection_attaches_three_snapshots_to_one_episode` |
| A | Selection flips always create new episodes | PASS | `process_snapshot` supersedes active episode when `_same_action` fails; moneyline/totals flip tests |
| A | PASS transitions behave correctly | PASS | `process_snapshot` withdraws active episode and attaches PASS snapshot as evidence |
| A | Reopened recommendations create new episodes | PASS | withdrawn episode is not reopened; `test_withdrawn_episode_does_not_reopen_when_same_team_returns` |
| A | Market-line movement does not create new episodes | PASS | `_episode_selection` normalizes totals to side; metadata/line tests |
| A | Ineligible snapshots never affect episodes | PASS | `pregame_eligible=False` returns before stream/episode mutation |
| B | Exactly one canonical snapshot per locked episode | PASS | single nullable `canonical_snapshot_id`; lock service assigns once and idempotently reuses locked state |
| B | Canonical snapshot is latest eligible pregame snapshot | PASS | `_latest_eligible_snapshot` orders by `recommendation_time desc, created_at desc` with `< scheduled_start_at` |
| B | Post-start snapshots cannot become canonical | PASS | strict `< scheduled_start_at` query predicate |
| B | Retroactive locking cannot choose invalid snapshot | PASS | same predicate used even after scheduled start/result terminality |
| B | No canonical recommendation without actionable episode | PASS | lock service returns `NO_ACTIONABLE_EPISODE` when no active episode exists |
| C | One canonical grade per episode | PASS | unique constraint `uq_canonical_recommendation_grades_episode` and existing-grade lookup |
| C | Idempotent grading | PASS | `grade_episode_in_session` returns existing grade before insert |
| C | Concurrent grading cannot duplicate grades | PASS | database unique constraint plus `IntegrityError` retry path |
| C | VOID never grades as win/loss | PASS | `VOID` episode returns non-created VOID result; canceled grade status does not create win/loss grade |
| C | Superseded episodes never grade | PASS | non-LOCKED status returns pending/non-created result |
| C | Withdrawn episodes never grade | PASS | non-LOCKED status returns pending/non-created result |
| C | Totals use canonical line | PASS | canonical snapshot is passed to `determine_grade_status`; totals test uses canonical `market_line` |
| C | Push handling | PASS | shared `_grade_total` returns `PUSH`; canonical grading test covers push |
| C | Existing snapshot grades remain isolated | PASS | `PredictionSnapshotGradingService` remains legacy/audit; official daily/analytics use canonical services |
| D | Model Health counts canonical recommendations only | PASS | `RecommendationAnalyticsService._load_records` uses `CanonicalRecommendationReadModel` by default |
| D | Recommendation History counts canonical recommendations only | PASS | `RecommendationHistoryService.list_recommendations` reads canonical records only |
| D | Timeline uses snapshots only | PASS | `CanonicalRecommendationReadModel.list_episode_timeline` explicitly returns attached snapshots |
| D | Official counts cannot inflate with repeated builds | PASS | analytics consume one canonical record per `GRADED` episode |
| D | Empty canonical data never falls back to snapshot grades | PASS | canonical-empty test and default `_load_records` return empty records without legacy fallback |
| D | Legacy analytics remain explicitly legacy | PASS | only `include_legacy=True` invokes `_load_legacy_snapshot_records` |
| E | Snapshot persistence + episode attachment atomic | PASS | `PredictionSnapshotPersistenceService.persist_run` calls episode service inside `session.begin`; rollback test covers failure |
| E | Lock atomic | PASS | `lock_stream` wraps canonical assignment/status/timestamp in one transaction |
| E | Grade atomic | PASS | `grade_episode` wraps grade insert/status transition in one transaction |
| E | Rollback behavior | PASS | focused rollback tests for persistence and grading |
| E | Retry behavior | PASS | completed logical-run retry and canonical grade reuse paths |
| E | Idempotency | PASS | logical run key, snapshot idempotency key, lock reuse, canonical grade uniqueness |
| F | Required uniqueness constraints | PASS | stream identity, one active episode per stream, episode identity, one canonical grade per episode |
| F | Foreign keys | PASS | stream/episode/snapshot/result/model foreign keys present in ORM and migrations |
| F | Cascade behavior | PASS | destructive deletes restricted for canonical records; supersession links SET NULL |
| F | Downgrades | PASS | episode schema and attachment migrations drop indexes/constraints/tables in safe order |
| F | Alembic chain | PASS | local chain is linear: `f2c8a1e6d4b7 -> a7c9e2f4b681 -> c3d9a4f7e2b1` |
| F | No migration rewrites | PASS | `git diff --name-only -- alembic/versions` returned no modified migration files |
| F | No conflicting revisions | PASS | static parse found one local post-`f2c8a1e6d4b7` chain; `alembic` CLI unavailable locally |
| G | Duplicate workers | NOT PROVEN | Database constraints exist; no real concurrent PostgreSQL worker test |
| G | Concurrent persistence | NOT PROVEN | Logical-run and snapshot keys exist, but concurrent new stream insert behavior lacks integration proof |
| G | Concurrent locking | PASS | stream and episode row locks plus idempotent existing locked-state path |
| G | Concurrent grading | PASS | episode row lock plus unique canonical grade constraint and retry on `IntegrityError` |
| G | Stale reads | REVIEW | Read model is read-only and consistent per query, but no transaction isolation contract is documented for multi-query consumers |
| G | Replay scenarios | PASS | idempotency keys and completed logical-run retry prevent duplicate snapshot official counts |
| H | Recommendation definition owner | PASS | PredictionSnapshot/Registry persistence boundary owns immutable snapshot definition |
| H | Episode lifecycle owner | PASS | `RecommendationEpisodeService` |
| H | Canonical selection owner | PASS | `RecommendationEpisodeLockService` |
| H | Grading owner | PASS | `CanonicalRecommendationGradingService`; shared grading rules in snapshot grading helper |
| H | Analytics owner | PASS | `RecommendationAnalyticsService` through `CanonicalRecommendationReadModel` |
| H | History owner | PASS | `RecommendationHistoryService` through `CanonicalRecommendationReadModel` |
| H | Timeline owner | PASS | `CanonicalRecommendationReadModel.list_episode_timeline` |
| H | No duplicated business rules | REVIEW | Grading calculation is shared, but canonical grade orchestration and legacy snapshot grade orchestration coexist by design |
| I | Snapshot grades no longer authoritative | PASS | default analytics/history do not query snapshot grades |
| I | Canonical and snapshot grades cannot silently mix | PASS | only explicit `include_legacy=True` legacy analytics path |
| J | Explain selection | PASS | canonical snapshot and episode selection retained |
| J | Explain tier | PASS | canonical snapshot components/tier retained in read model |
| J | Explain Hammer | PASS | read model extracts Hammer from canonical snapshot components |
| J | Explain confidence | PASS | canonical snapshot confidence retained |
| J | Explain canonical snapshot | PASS | episode `canonical_snapshot_id` and read model expose snapshot timestamp |
| J | Explain grading | PASS | canonical grade links episode, snapshot, result, revision, status |
| J | Explain history | PASS | official history item exposes episode, canonical snapshot, lock/grade timestamps and timeline access |

## Required Review Items

### REVIEW: Stale read isolation not documented for multi-query consumers

- Files: `app/services/canonical_recommendation_read_model.py`,
  `app/services/recommendation_history_service.py`
- Functions: `CanonicalRecommendationReadModel.list_graded_records`,
  `CanonicalRecommendationReadModel.list_episode_timeline`,
  `RecommendationHistoryService.list_recommendations`,
  `RecommendationHistoryService.list_episode_timeline`
- Root cause: official rows and timeline snapshots are separate read calls with
  no shared transaction boundary. A timeline requested immediately after a
  history page could observe a newer attached snapshot set.
- Recommended correction: document read consistency semantics or add an
  optional single-session read method that returns official row plus timeline in
  one transaction.
- Implementation risk: low to medium; read-only surface change, but consumer
  contracts must stay stable.

### REVIEW: Concurrent stream creation is constraint-guarded but not integration-proven

- Files: `app/services/recommendation_episode_service.py`,
  `app/services/prediction_snapshot_persistence_service.py`
- Functions: `RecommendationEpisodeService._get_or_create_stream`,
  `PredictionSnapshotPersistenceService.persist_run`
- Root cause: two workers inserting the same new stream rely on the database
  stream identity uniqueness constraint. The service does not locally catch
  that specific stream insert race and re-select the winning row.
- Recommended correction: add PostgreSQL concurrent-session test and, if it
  fails, catch stream identity `IntegrityError`, rollback to savepoint, and
  re-select the stream inside the parent persistence transaction.
- Implementation risk: medium; transaction/savepoint handling must not weaken
  snapshot persistence atomicity.

### REVIEW: VOID visibility in analytics is intentionally limited

- Files: `app/services/canonical_recommendation_grading_service.py`,
  `app/services/canonical_recommendation_read_model.py`,
  `app/services/recommendation_analytics_service.py`
- Functions: `CanonicalRecommendationGradingService.grade_episode_in_session`,
  `CanonicalRecommendationReadModel.list_graded_records`,
  `RecommendationAnalyticsService.model_health`
- Root cause: canceled games mark episodes `VOID` and do not create canonical
  grade rows, while the canonical analytics read model includes only `GRADED`
  episodes. VOID episodes therefore do not inflate win/loss records, but they
  are not visible in primary Model Health buckets.
- Recommended correction: if product wants visible void counts in official
  analytics, add an explicit non-win/loss canonical void read path that includes
  `VOID` episodes without grade rows.
- Implementation risk: low to medium; must avoid reintroducing pending/void
  grade-row inflation.

### NOT PROVEN: true duplicate-worker behavior under PostgreSQL

- Files: `tests/test_recommendation_episode_lifecycle.py`,
  `tests/test_recommendation_episode_locking.py`,
  `tests/test_canonical_recommendation_grading_service.py`
- Functions: concurrency test coverage is synthetic, not multi-connection
  PostgreSQL.
- Root cause: current tests use in-memory SQLite or session doubles.
- Recommended correction: add read/write integration tests against disposable
  PostgreSQL for concurrent persist/lock/grade attempts.
- Implementation risk: medium; test infrastructure cost, low product risk.

## Repository Audit Findings

Search terms:

`TODO`, `FIXME`, `HACK`, `deprecated`, `legacy fallback`, `score_from_edge`,
`market fallback`, `duplicate recommendation logic`, `duplicate grading logic`,
`duplicate ranking logic`, `duplicate Hammer logic`, `unreachable code`,
`orphaned Recommendation code`

Findings:

| File | Finding | Certification Impact |
|---|---|---|
| `docs/PROJECT_HANDOFF.md` | Historical note: deprecated Streamlit dataframe keyword removed | PASS; documentation-only historical note |
| `docs/MODEL_TECHNICAL_REFERENCE.md` | Future-work note: remove `score_from_edge` from Hammer fallback path | REVIEW for Phase 2 model audit; outside Sprint 79 Recommendation Architecture scope |

No code hits were found for TODO, FIXME, HACK, legacy fallback, duplicate
recommendation/grading/ranking/Hammer logic, unreachable code, or orphaned
Recommendation code using the required search terms.

## Deployment Status

Read-only Azure verification:

| Check | Result |
|---|---:|
| Current Alembic revision | `f2c8a1e6d4b7` |
| `recommendation_streams` present | no |
| `recommendation_episodes` present | no |
| `canonical_recommendation_grades` present | no |
| Immutable snapshot count | 172 |

Deployment is behind the local Recommendation Architecture.

Missing migrations:

- `a7c9e2f4b681_add_recommendation_episode_schema.py`
- `c3d9a4f7e2b1_add_snapshot_episode_attachment.py`

Because canonical tables are not deployed, these read-only production checks
could not be executed there:

- episode count
- canonical grade count
- no multiple canonical grades
- no invalid canonical snapshots
- no superseded grades
- no withdrawn grades

## Known Limitations

- Production deployment is not certified until the two local episode migrations
  are applied.
- Race-condition evidence is mostly structural and unit-level, not
  multi-session PostgreSQL proof.
- Canonical analytics are empty by design until canonical grades exist.
- Legacy snapshot-grade rows remain audit data and must not be used to fill
  canonical-empty official reports.

## Open Risks

- A concurrent first insert for the same stream may require a retry path if the
  unique stream constraint is hit inside the larger persistence transaction.
- Timeline reads and official history reads are not guaranteed to be from the
  same database snapshot unless the caller adds a transaction boundary.
- Provider reschedule semantics still depend on authoritative
  `scheduled_start_at` being updated before lock.

## Future Work (Not Defects)

- Apply the missing episode migrations through the approved release process.
- Add disposable PostgreSQL concurrent integration tests for persist, lock, and
  grade flows.
- Decide whether VOID episodes should appear as explicit primary analytics
  rows or remain excluded from official graded samples.
- Add a combined official-history-plus-timeline read if consumers need
  snapshot-consistent timeline display.
- Phase 2 model audit should evaluate `score_from_edge` and any market fallback
  references outside the Sprint 79 architecture scope.

## Recommendation

**CERTIFIED WITH OBSERVATIONS**

Local Recommendation Architecture is structurally coherent and satisfies the
core one-official-recommendation guarantee. It should not be considered
production-deployed until Azure reaches `c3d9a4f7e2b1` and read-only
post-deployment integrity checks pass.
