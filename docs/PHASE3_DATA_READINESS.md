# Phase 3 Historical Data Readiness Audit

Read-only audit completed against the configured Azure PostgreSQL database on
2026-08-06. No production code, model logic, thresholds, weights, or data were
modified.

Sprint 81.2 rechecked the Phase 3.1 findings with read-only database queries
and source inspection. No production persistence defect was confirmed, so no
schema, code, model, recommendation, threshold, or data changes were made.

## Readiness Summary

SharpStack's historical dataset is structurally trustworthy but not yet
statistically sufficient.

Canonical lifecycle integrity is clean: no duplicate active episodes, no
duplicate canonical grades, no orphan linked snapshots, no orphan snapshot
grades, no canonical grade/result join anomalies, no timestamp-ordering
anomalies, and no conflicting final game results were found.

The blocker for Phase 3 is coverage, not schema integrity. Current official
canonical history is too small and incomplete across model families:

- `12` recommendation episodes.
- `4` canonical grades.
- MLB moneyline has `2` graded canonical recommendations.
- MLB totals has `2` graded canonical recommendations.
- KBO has `0` canonical recommendations.
- Raw snapshots exist (`242`) but most are not attached to episodes and raw
  grades are all `PENDING`, so they cannot support official validation.

## Database Inventory

| Table | Count |
|---|---:|
| `recommendation_streams` | `22` |
| `recommendation_episodes` | `12` |
| `canonical_recommendation_grades` | `4` |
| `recommendations` | `242` |
| `prediction_snapshot_grades` | `330` |
| `game_results` | `213` |
| `model_versions` | `19` |
| `model_runs` | `10` |

Game results:

| League | Status | Count |
|---|---|---:|
| MLB | FINAL | `206` |
| MLB | LIVE | `2` |
| MLB | SCHEDULED | `5` |

No KBO game results are present in the audited database.

## Canonical Recommendation Readiness

Canonical episodes by market:

| League | Market | Version | Status | Count |
|---|---|---|---|---:|
| MLB | MONEYLINE | `1.0.0` | ACTIVE | `4` |
| MLB | MONEYLINE | `1.0.0` | GRADED | `2` |
| MLB | TOTALS | `1.0.0` | ACTIVE | `2` |
| MLB | TOTALS | `1.0.0` | GRADED | `2` |
| MLB | TOTALS | `1.0.0` | LOCKED | `2` |

Canonical grades:

| League | Market | Grade | Count |
|---|---|---|---:|
| MLB | MONEYLINE | LOSS | `2` |
| MLB | TOTALS | LOSS | `1` |
| MLB | TOTALS | WIN | `1` |

Canonical structural checks:

| Check | Result |
|---|---:|
| Locked/graded episodes missing canonical snapshot | `0` |
| Locked/graded episodes missing `locked_at` | `0` |
| Missing stream provider game id | `0` |
| Missing stream model version | `0` |
| Missing episode selection | `0` |
| Duplicate ACTIVE episodes per stream | `0` |
| Duplicate canonical grades per episode | `0` |
| Canonical grade missing game result | `0` |
| Canonical grade joined to non-final result | `0` |
| Canonical grade game-result revision mismatch | `0` |
| Canonical grade provider-game mismatch | `0` |
| Lock before open | `0` |
| Close before open | `0` |
| Canonical snapshot after lock | `0` |

Verdict: **READY structurally**, **PARTIAL statistically**.

## Historical Completeness

### MLB Moneyline

| Metric | Count / Status |
|---|---:|
| Canonical episodes | `6` |
| Graded canonical recommendations | `2` |
| Pending/active canonical recommendations | `4 ACTIVE` |
| Void canonical recommendations | `0` |
| Model version | `1.0.0` |
| Canonical tier coverage | `2 LEAN`, `4 UNSPECIFIED` |
| Raw snapshots | `121` |
| Raw linked snapshots | `21` |
| Raw unlinked snapshots | `100` |
| Raw snapshot grades | `165 PENDING` |

Readiness: **PARTIAL**. Official sample is too small and tier coverage is
incomplete.

### MLB Totals

| Metric | Count / Status |
|---|---:|
| Canonical episodes | `6` |
| Graded canonical recommendations | `2` |
| Pending/active/locked canonical recommendations | `2 ACTIVE`, `2 LOCKED` |
| Void canonical recommendations | `0` |
| Model version | `1.0.0` |
| Canonical tier coverage | `3 BET`, `1 LEAN`, `2 UNSPECIFIED` |
| Raw snapshots | `121` |
| Raw linked snapshots | `16` |
| Raw unlinked snapshots | `105` |
| Raw snapshot grades | `165 PENDING` |

Readiness: **PARTIAL** for recommendation hit-rate validation. **BLOCKED**
for projected-total error unless projected totals are reliably extracted from
components or persisted to `recommendations.projection`.

### KBO

| Metric | Count / Status |
|---|---:|
| Canonical episodes | `0` |
| Graded canonical recommendations | `0` |
| Raw snapshots | `0` |
| Game results | `0` |

Readiness: **BLOCKED** for Phase 3 statistical validation.

## Required Phase 3 Field Coverage

| Field | Status | Evidence |
|---|---:|---|
| recommendation / tier | PARTIAL | Canonical tiers present for graded snapshots; active episodes can be `UNSPECIFIED`. |
| selection | PRESENT | `0` canonical episodes missing selection. |
| model strength / probability | PARTIAL | Moneyline canonical snapshots have projection; totals top-level projection is missing. |
| confidence | PARTIAL | `86/242` raw snapshots missing confidence; canonical coverage exists for current canonical snapshots. |
| projected total | PARTIAL | Not present as top-level `projection` for totals snapshots; may exist in components but requires extraction contract. |
| sportsbook line / market line | PARTIAL | Totals snapshots have market lines; moneyline market line is expected null. |
| component JSON | PRESENT | `0/242` snapshots missing components. |
| timestamps | PRESENT | recommendation time, episode open/lock times, model run times available. |
| provider_game_id | PRESENT | `0/242` snapshots and `0` streams missing provider game id. |
| model version | PRESENT | streams and model versions populated for canonical records. |
| code revision | PRESENT/PARTIAL | git commits present; several model-version rows have no snapshots. |
| model run id | PRESENT | `0/242` snapshots missing model run id. |
| grading outcome | PARTIAL | canonical grades only `4`; raw snapshot grades all `PENDING`. |
| game result final score | PRESENT for graded canonical | no missing joins or non-final joined results. |
| Hammer / score | PRESENT | components contain hammer fields for all MLB moneyline/totals snapshots. |

## Snapshot Integrity

Raw snapshot checks:

| Check | Result |
|---|---:|
| Total raw snapshots | `242` |
| Missing idempotency key | `0` |
| Missing model run id | `0` |
| Missing components | `0` |
| Missing episode link | `205` |
| Orphan linked snapshots | `0` |
| Orphan snapshot grades | `0` |
| Duplicate snapshot grades | `0` |

Repeated raw snapshots were found for the same logical game/market/selection
across multiple runs. This is expected for repeated build history and should
be used for stability analysis, not official performance counts.

Anomaly verdict: no referential anomalies. The large unlinked snapshot count
is a readiness limitation for lifecycle-based stability analysis.

### Sprint 81.2 Unlinked Snapshot Resolution

The `205` unlinked snapshots split cleanly into legacy history and intentional
PASS behavior:

| Category | Count | Explanation |
|---|---:|---|
| Legacy, pre-Sprint 79 episode architecture | `102` | Actionable rows persisted before the first `recommendation_episodes.opened_at`; no episode attachment column was populated for those historical rows. |
| PASS / ineligible recommendation | `103` | PASS rows remain persisted but unattached unless they withdraw an already active episode. This matches `RecommendationEpisodeService.process_snapshot()`. |
| Superseded snapshot intentionally left unattached | `0` | Same-selection and selection-flip actionable snapshots attach to an episode in the current service path. |
| Persistence defect | `0` | No current actionable post-lifecycle unlinked rows were found. |
| Migration omission | `0` | No evidence supports backfilling pre-lifecycle snapshots into canonical episodes. |
| Unknown | `0` | Every unlinked row matched one of the buckets above. |

Verdict: **benign legacy/design behavior**. No code change is justified.

Breakdown by market:

| Market | Legacy | PASS / ineligible | Total unlinked |
|---|---:|---:|---:|
| MLB MONEYLINE | `45` | `55` | `100` |
| MLB TOTALS | `57` | `48` | `105` |

## Game-Result Integrity

Canonical grades all join to final game results with matching provider game id
and matching result revision:

| Check | Result |
|---|---:|
| Canonical grades | `4` |
| Missing game result | `0` |
| Non-final result joined to canonical grade | `0` |
| Game-result revision mismatch | `0` |
| Provider game id mismatch | `0` |
| Conflicting final results | `0` |

Verdict: **READY** for the small canonical sample.

## Model-Version Integrity

Historical snapshots can be grouped by model version and git commit, but the
current model-version naming is coarse:

- all canonical records observed use `sharpstack_registry` / `1.0.0`;
- snapshots are distributed across multiple git commits;
- two `mlb_totals` model-version records exist with zero snapshots;
- KBO has no persisted sample.

Verdict: **PARTIAL**. Comparisons by git commit are possible. Comparisons by
semantic model version are currently weak because many registry builds share
`1.0.0`.

Sprint 81.2 verified that every persisted snapshot is attached to a
`model_run_id`, `model_version_id`, git commit, and
`prediction_snapshot_v1` artifact schema version. Historical comparisons are
safe by model run, git commit, league, and market. They are only weak by
semantic model version because `sharpstack_registry` intentionally aggregates
multi-market Registry output under `1.0.0`.

## Component Availability

| Model | Status | Evidence |
|---|---:|---|
| MLB Moneyline | PARTIAL | Components JSON present for all `121` moneyline snapshots. Starter/offense/Hammer-style component scores are present; structured confidence inputs are absent in stored JSON, and only newer rows include explicit `model_confidence`, `model_probability`, and `model_win_strength` component keys. |
| MLB Totals | PARTIAL | Components JSON present for all `121` totals snapshots. Structured `model_confidence`, `bullpen_confidence`, `data_quality`, `model_separation`, and market line fields exist, but starter/offense/projection-input breakdowns and first-class `projected_total` are not structured fields. Projected totals are preserved in explanation text, not a stable numeric JSON path. |
| KBO | BLOCKED | No canonical or raw KBO historical records in audited database. |

Sprint 81.2 verdict: component history is sufficient for high-level historical
analytics, but not yet sufficient for full feature-contribution studies. This
is missing structured persistence for future research, not a defect in current
recommendation behavior.

## Canonical Tier Resolution

Phase 3.1 reported canonical `UNSPECIFIED` tier rows. Sprint 81.2 found that
all six rows are ACTIVE episodes with no `canonical_snapshot_id` yet:

| Market | Count | Explanation |
|---|---:|---|
| MLB MONEYLINE | `4` | ACTIVE, unlocked episodes. They have selections but no locked canonical snapshot yet, so analytics labels them `UNSPECIFIED`. |
| MLB TOTALS | `2` | ACTIVE, unlocked episodes. They have selections but no locked canonical snapshot yet, so analytics labels them `UNSPECIFIED`. |

No LOCKED or GRADED canonical recommendation was missing a tier. Verdict:
**expected transitional state**. No persistence repair is justified.

## Projected Total Persistence Resolution

Totals projected runs are not persisted to `recommendations.projection`
because that column currently stores `PredictionData.model_probability` for
compatibility with moneyline-style model strength. Totals have no calibrated
probability, so the top-level projection is null for all totals rows.

Where totals projection lives today:

- `market.market_line` is structured and populated.
- `components.model_separation`, `components.model_confidence`,
  `components.bullpen_confidence`, and `components.data_quality` are structured.
- final projected totals are present in explanation prose, for example
  "Final projected game total is 9.29 runs."
- no stable numeric JSON key such as `prediction.projected_total` or
  `components.totals.projected_total` is present.

Recommendation: leave production unchanged in Sprint 81.2. For Phase 3
projection-error studies, add a future narrowly scoped persistence contract for
structured totals projection rather than overloading
`recommendations.projection` or scraping explanation text.

## KBO Readiness Resolution

KBO has no persisted recommendation snapshots, canonical episodes, canonical
grades, or game results in the audited database. The current evidence points
to deployment/ingestion coverage timing: the operational persistence history
contains only MLB Registry snapshots and MLB game results. No query evidence
showed a failed KBO persistence path or disabled KBO grading path.

Verdict: **BLOCKED for historical validation**, not a model defect and not a
tuning issue.

## READY / PARTIAL / BLOCKED Matrix

| Area | Score | Reason |
|---|---:|---|
| Canonical recommendation schema | READY | Referential integrity and uniqueness checks passed. |
| Canonical recommendation sample | PARTIAL | Only `12` episodes and `4` canonical grades. |
| Historical grades | PARTIAL | Canonical grades exist but are too few; raw grades all pending. |
| Game results | READY | Final-result joins clean for canonical grades. |
| Model versions | PARTIAL | Git commits present, semantic versions too coarse. |
| Confidence history | PARTIAL | Missing on `86/242` raw snapshots; canonical rows populated where locked. |
| Component history | PARTIAL | JSON present but model-specific extraction contracts needed. |
| Projection history | PARTIAL | Moneyline projection present; totals top-level projection missing. |
| Threshold history | PARTIAL | Tiers present for some canonical records; too few samples. |
| Snapshot lifecycle linkage | READY/PARTIAL | Current lifecycle linkage is behaving correctly; historical stability remains PARTIAL because `102` actionable rows are pre-lifecycle legacy and `103` PASS rows are intentionally unattached. |
| MLB Moneyline readiness | PARTIAL | Small canonical sample, incomplete tier diversity. |
| MLB Totals readiness | PARTIAL | Small sample; structured projected-total persistence is missing for projection-error studies. |
| KBO readiness | BLOCKED | No persisted KBO validation dataset. |

## Phase 3 Blockers

Genuine blockers only:

1. KBO has no persisted canonical/raw recommendations or game results in the
   audited database.
2. Official canonical sample size is too small for statistical validation:
   only `4` canonical grades.
3. Totals projected-total validation is blocked until projected totals are
   persisted as a structured numeric field for future rows. Explanation-text
   extraction should not be treated as a trusted Phase 3 dataset.
4. Raw snapshot stability analysis cannot include the `102` actionable
   pre-lifecycle snapshots in episode timelines; current lifecycle rows are
   otherwise linked as expected.
5. Semantic model-version comparisons are limited because active records share
   `sharpstack_registry` version `1.0.0`; git commit grouping is safer.

Items that merely need more games are not listed as blockers unless they
prevent a validation question from being answered at all.

## Recommendation

Do not begin statistical conclusions yet. Phase 3 should start with read-only
data-readiness and extraction tooling around the existing canonical read model,
then collect more canonical locked/graded episodes before calibration,
threshold, or feature-contribution claims are made.
