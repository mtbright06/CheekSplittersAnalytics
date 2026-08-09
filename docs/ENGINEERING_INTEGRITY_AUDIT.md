# Phase 4 Engineering Integrity Audit

Read-only audit completed on 2026-08-06. No production code, model logic,
thresholds, weights, recommendation behavior, data, or migrations were
modified.

Closure recommendation: **ENGINEERING INTEGRITY CERTIFIED WITH FUTURE CLEANUP**.

Sprint 82.0 verification reevaluated every finding with this decision test:

> Would removing or leaving this create a correctness, maintainability, or
> future-development problem?

The closure recommendation remains unchanged. Several items were narrowed from
general cleanup to documentation or deprecation where leaving them does not
create a material future-development problem, and one item was raised to future
enhancement because it blocks a known Phase 3 study.

## Executive Summary

SharpStack's current engineering foundation is coherent enough to support
future model development. Recommendation authority, canonical persistence,
canonical analytics, and dashboard consumption each have identifiable owners.
No objective implementation defect was confirmed during this audit.

The main risk is not hidden incorrect behavior. It is accumulated transitional
surface area:

- legacy compatibility packages and scripts remain at repository root;
- generic recommendation labels and confidence helpers exist in several layers;
- Hammer/model-strength compatibility aliases are intentionally widespread;
- legacy snapshot grading and canonical episode grading coexist by design;
- exploratory tooling and historical documentation contain old terms that can
  confuse future maintainers.

These are future cleanup and documentation risks, not grounds for blocking the
current architecture.

## Certification Matrix

| Area | Classification | Finding |
|---|---|---|
| Legacy path audit | FUTURE ENHANCEMENT | Legacy and compatibility paths are mostly intentional, but root-level packages and scripts need retirement decisions. |
| TODO/FIXME audit | DOCUMENT | No production TODO/FIXME/HACK/XXX defects found; one standalone schedule-test placeholder remains outside production. |
| Dead-code audit | FUTURE ENHANCEMENT | Older top-level `calculators`, `models`, `providers`, `parsers`, `loaders`, and `recommendation_engine` paths are partially used by KBO/tests/tools but not cleanly owned. |
| Duplicate logic audit | FUTURE ENHANCEMENT | Safe parsing, tier labels, confidence labels, and recommendation labels exist in multiple layers; current tests protect key paths. |
| Recommendation authority | PASS | MLB, KBO, Totals, Registry, Play of the Day, History, Model Health, and Dashboard adapters consume authoritative labels rather than silently recomputing official selections. |
| Configuration | FUTURE ENHANCEMENT | Threshold constants are local to model modules; no defect found, but constants are not globally discoverable. |
| Persistence consistency | PASS | Canonical episode persistence, locking, grading, analytics, history, and legacy isolation have clear owners. |
| Test integrity | PASS | Focused tests cover winner-first behavior, canonical lifecycle, grading, analytics isolation, pregame eligibility, adapters, and dashboard import boundaries. |
| Dependency audit | FUTURE ENHANCEMENT | `requirements-current.txt` includes broader transitive/runtime packages than `requirements.txt`; no unused-package proof without import tracing. |
| Explainability | DOCUMENT | Recommendation-to-persistence-to-presentation trace is mostly deterministic; totals projected total remains prose/score structured rather than first-class numeric persistence. |

## Legacy Path Findings

| Path / Pattern | Classification | Status |
|---|---|---|
| `app/models/legacy_recommendation_settlement.py` | DOCUMENT | Explicit legacy settlement model retained for existing history consumers; official analytics do not use it silently. |
| `app/services/recommendation_grading_service.py` | DOCUMENT | Legacy settlement service remains separate from canonical grading. |
| `app/services/prediction_snapshot_grading_service.py` | DOCUMENT | Snapshot-grade/audit service remains isolated from canonical episode grades. |
| `app/services/recommendation_analytics_service.py::include_legacy` | PASS | Legacy fallback is opt-in only; canonical-empty state does not silently load legacy rows. |
| `engine/model/recommendations.py::recommendation` and `grade_label` | FUTURE ENHANCEMENT | Legacy edge-based helpers retained for non-MLB compatibility; avoid using as new recommendation authority. |
| `engine/contracts/sharpstack_card.py::normalize_legacy_kbo_game` | DOCUMENT | Compatibility normalizer for existing KBO card shape. |
| `engine/adapters/kbo_card_adapter.py::canonical_kbo_row` | DOCUMENT | Legacy adapter bridge; still required while KBO payload shape remains nested. |
| `tools_build_mlb_card.py` and `exporters/json_exporter.py` legacy output path | DOCUMENT | Maintains `output/sharpstack_card.json` compatibility for dashboard/card consumers. |
| `dashboard/card_loader.py` legacy card loading | DOCUMENT | Still required while legacy card output exists. |
| Top-level `calculators`, `models`, `providers`, `parsers`, `loaders` | FUTURE ENHANCEMENT | Mixed old KBO/test/tool surface remains partially used; should be inventoried before retirement. |
| Root `hammer_score.py` vs `engine/decision/hammer_score.py` | FUTURE ENHANCEMENT | Standalone audit/tool copy exists beside production module. Keep clearly tool-only or retire later. |

Decision-test result: legacy paths may remain when compatibility, history,
active workflows, or tests depend on them. The highest-risk item to leave
unclarified is the top-level KBO/model package surface because future sport
work could accidentally target the wrong owner.

## TODO / FIXME / Placeholder Findings

| Path | Classification | Finding |
|---|---|---|
| `python kbo_schedule_test.py` | DEPRECATED | Standalone script prints TODO placeholders for schedule, odds, and starter sources. Not imported by production. |
| `models/mlb/placeholder_model.py` | DEPRECATED | Placeholder model path exists under legacy top-level models; no production import found. Leaving it can mislead contributors. |
| `dashboard/pages/placeholder_pages.py` | DOCUMENT | Name is historical; file contains active dashboard routes/renderers. |
| `dashboard/components/explorer/recommendation_explorer.py::_render_placeholder` | DOCUMENT | UI empty-state placeholder helper, not incomplete implementation. |
| `engine/odds/quote_utils.py` placeholder book marker | DOCUMENT | Quote-provider placeholder filtering, not incomplete code. |
| `tools_validate_market_pipeline.py` placeholder marker | DOCUMENT | Tool validation marker, not production behavior. |

No production `FIXME`, `HACK`, or `XXX` correctness defect was found.

## Dead Code / Reserved Code Findings

| Area | Classification | Finding |
|---|---|---|
| Top-level KBO/model packages | FUTURE ENHANCEMENT | Several older modules are still imported by tests/tools, so they are not proven dead. Ownership is less clean than `engine/` and `app/`. |
| `recommendation_engine/` | FUTURE ENHANCEMENT | Explorer/source-inspection tooling still imports it. Treat as reserved tooling until replaced or retired. |
| Alembic migrations | PASS | Chain is linear through `c3d9a4f7e2b1`; no abandoned conflicting revision found. |
| Legacy settlement tables/read models | DOCUMENT | Obsolete for official analytics but intentionally retained for historical compatibility. |
| Dashboard placeholder routes | DOCUMENT | Active renderers despite name. |

Decision-test result: placeholder route naming is safe to leave because
renaming now risks active dashboard imports. Placeholder model/script artifacts
should be deprecated because leaving them provides no compatibility value.

## Duplicate Logic Findings

| Logic | Classification | Finding |
|---|---|---|
| Recommendation tier labels | FUTURE ENHANCEMENT | Labels are parsed/assigned in `engine/model/recommendations.py`, `engine/mlb/totals/recommendation.py`, `engine/core/ranking.py`, analytics/read models, and badges. Tests protect current behavior, but a shared label registry would reduce drift. |
| Confidence labels | FUTURE ENHANCEMENT | Label thresholds exist in First 5, totals, ranking fallback, and model-specific confidence paths. This reflects distinct domains but needs documentation when changed. |
| Safe numeric parsing | DOCUMENT | `safe_float`/normalization helpers recur in ranking, Play of Day, KBO adapter, recommendation contract, and tools. Leaving them creates minor maintenance noise only; removing them now risks incidental behavior changes. |
| Hammer calculations | PASS | Production Hammer owner is `engine/decision/hammer_score.py`; root/tool copies are audit/tool surfaces. |
| Winner determination | PASS | MLB moneyline, KBO, and Totals each own their sport/market selection logic; grading uses persisted immutable selection/side/line. |
| Persistence writes | PASS | Daily persistence uses `PredictionSnapshotPersistenceService`; canonical lock/grading own their lifecycle-specific writes. |

## Recommendation Authority Findings

| Path | Classification | Authority |
|---|---|---|
| MLB Moneyline | PASS | `engine/model/sharpscore.py` selects winner by model score and assigns conviction via `mlb_moneyline_conviction_recommendation`; Decision Builder preserves model recommendation as authority. |
| KBO | PASS | KBO model direction and adapter fields determine selection; market/edge display does not own authority after Sprint 80.1. |
| MLB Totals | PASS | `engine/mlb/totals/recommendation.py` uses projected direction, line availability, separation, confidence, data quality, and bullpen confidence; odds/EV do not own authority. |
| Best Bets / Ranking | PASS | `engine/core/ranking.py` ranks existing `Recommendation` objects; it does not choose new selections. |
| Play of the Day | PASS | `engine/core/play_of_day.py` filters/ranks existing recommendations; MLB model-authoritative exception is explicit. |
| Registry | PASS | Registry serializes recommendation objects and ranking; it does not recalculate sport models. |
| Recommendation History | PASS | Canonical history reads canonical records; it does not regrade or relabel official recommendations. |
| Model Health | PASS | Canonical analytics aggregate canonical records; legacy rows are opt-in only. |
| Dashboard adapters | DOCUMENT | Presentation consumes Registry/card fields; dashboard preview helpers have display fallback labels but do not persist or grade. |

## Configuration Findings

| Area | Classification | Finding |
|---|---|---|
| Environment settings | PASS | `app/core/config.py` centralizes app/database settings and requires `DATABASE_URL`. |
| Model constants | FUTURE ENHANCEMENT | Weights/thresholds live beside each model module. This is understandable but makes global threshold inventory manual. |
| Ranking constants | DOCUMENT | `RankingWeights` and Play of Day minimum Hammer threshold are local, explicit constants. |
| Debug behavior | DOCUMENT | No debug-only production recommendation behavior was identified. |
| Requirements files | FUTURE ENHANCEMENT | `requirements.txt`, `requirements-dev.txt`, and `requirements-current.txt` serve different purposes but should be documented to avoid dependency drift. |

Decision-test result: local constants are not defects while model ownership is
clear. Dependency manifests are primarily documentation debt until a deployment
or dependency-upgrade sprint needs a locked runtime contract.

## Persistence Consistency

| Area | Classification | Finding |
|---|---|---|
| Snapshot persistence | PASS | `PredictionSnapshotPersistenceService` owns immutable snapshot writes and episode attachment in one transaction. |
| Episode lifecycle | PASS | `RecommendationEpisodeService` owns stream/episode transitions. |
| Canonical locking | PASS | `RecommendationEpisodeLockService` owns canonical snapshot selection. |
| Canonical grading | PASS | `CanonicalRecommendationGradingService` owns official episode grades. |
| Game results | PASS | `GameResultIngestionService` owns authoritative result writes. |
| Legacy settlement | DOCUMENT | Separate from canonical grading and analytics unless explicitly opted in. |
| Migrations | PASS | No conflicting revision heads found from file inspection. |

## Test Integrity

| Area | Classification | Finding |
|---|---|---|
| Recommendation authority tests | PASS | MLB, KBO, Totals, Decision Builder, and shared winner-first tests exist. |
| Persistence/lifecycle tests | PASS | Snapshot persistence, daily persistence, episode schema/lifecycle/locking, canonical grading, and history tests exist. |
| Analytics isolation tests | PASS | Canonical-empty no-legacy-fallback behavior is covered. |
| Dashboard tests | PASS | Import boundaries and presentation behavior are covered. |
| Legacy/top-level module tests | FUTURE ENHANCEMENT | Tests still target older top-level KBO/model modules, which is useful but prolongs ambiguous ownership. |

## Dependency Findings

| Area | Classification | Finding |
|---|---|---|
| Runtime dependencies | DOCUMENT | `requirements.txt` is concise and aligned with observed stack. |
| Current environment lock | DOCUMENT | `requirements-current.txt` includes broad transitive/runtime packages such as GitHub/Starlette/Uvicorn that are not obvious core dependencies; leaving it is safe if its purpose is documented. |
| Circular dependencies | PASS | No circular import failure surfaced in compile validation. |
| Large modules | FUTURE ENHANCEMENT | `engine/mlb/game_builder.py`, `engine/decision/decision_builder.py`, `dashboard/pages/dashboard_page.py`, and `dashboard/styles.py` are large future decomposition candidates. |

## Explainability

| Step | Classification | Finding |
|---|---|---|
| Inputs | PASS | Provider, model, market, and component inputs are carried into card/registry/persistence payloads. |
| Calculation | FUTURE ENHANCEMENT | Major models expose components/reasons; totals projected total is still not first-class numeric persistence, which blocks future projection-error validation. |
| Recommendation | PASS | Recommendation labels and explanations are persisted in snapshot components/explanation. |
| Persistence | PASS | Canonical snapshot, episode, grade, game result, run, git commit, and model version are traceable. |
| Presentation | DOCUMENT | Dashboard consumes persisted/card fields; some compatibility aliases can obscure whether a score is true Hammer or compatibility rank score. |

## Final Recommendation

SharpStack is **ENGINEERING INTEGRITY CERTIFIED WITH FUTURE CLEANUP**. The
architecture is sound enough to continue Phase 4 work, but future cleanup
should retire or quarantine legacy packages, consolidate label/normalization
helpers, document compatibility aliases, and clarify dependency files.
