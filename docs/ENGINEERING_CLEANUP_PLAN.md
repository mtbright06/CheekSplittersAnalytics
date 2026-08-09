# Engineering Cleanup Plan

This plan is documentation only. Do not treat it as approval to refactor,
remove modules, tune models, or change recommendation behavior.

## Guiding Rules

1. Do not remove legacy code merely because it is old.
2. Preserve working recommendation and persistence contracts.
3. Prefer quarantining and documentation before deletion.
4. Cleanup must be covered by focused tests and run through normal sprint
   approval.
5. Use the decision test before acting: would removing or leaving this create
   a correctness, maintainability, or future-development problem?

## Phase 4 Cleanup Sequence

### 1. Mark Supported Surfaces

Goal: make it obvious which modules are production, tooling, legacy, or test
support.

Targets:

- `engine/`
- `app/`
- `dashboard/`
- top-level `models/`, `calculators/`, `providers/`, `parsers/`, `loaders/`
- `recommendation_engine/`
- root `tools_*.py` and `test_*.py`

Outcome:

- ownership map;
- no behavior change;
- no file deletion.

Trigger: before NHL/NFL model work or any KBO package rewrite. Leaving the
current ambiguity indefinitely creates future-development risk; removing paths
now risks breaking active tests/tools.

### 2. Compatibility Alias Inventory

Goal: document every compatibility alias before removing any.

Fields:

- `model_probability`
- `model_strength`
- `model_win_strength`
- `confidence`
- `model_confidence`
- `hammer_confidence`
- `hammer_score`
- totals recommendation-score compatibility mappings

Outcome:

- alias contract table;
- consumer list;
- retirement prerequisites.

Trigger: before new sport contracts, Registry contract changes, or dashboard
field migrations. Removing aliases now is unsafe; leaving them undocumented is
the actual risk.

### 3. Label Taxonomy Consolidation

Goal: reduce duplicate tier parsing and display-label drift.

Targets:

- recommendation tier labels;
- actionable/PASS detection;
- confidence labels;
- badge labels;
- analytics bucket normalization.

Outcome:

- shared taxonomy module or explicit contract document;
- tests proving no label behavior changed.

Trigger: before adding new sport tiers or changing recommendation labels.
Duplicated label parsing is acceptable today because tests cover current
contracts; the risk increases when new labels are introduced.

### 4. Structured Totals Projection Persistence

Goal: unblock future Phase 3 totals projection-error validation.

Targets:

- canonical totals snapshot payload;
- structured `projected_total` field or approved JSON extraction contract;
- migration/read-model plan if a first-class field is chosen.

Outcome:

- no explanation-text scraping for official projection-error studies;
- no overload of moneyline-style `recommendations.projection` without an
  explicit schema decision.

Trigger: before publishing totals projection-error results.

### 5. Tooling Quarantine

Goal: separate supported tools from exploratory scripts.

Targets:

- root-level `tools_*.py`;
- root-level `test_*.py`;
- `python kbo_schedule_test.py`;
- `audit_component_distribution.py`;
- root `hammer_score.py` if confirmed tool-only.

Outcome:

- `tools/` or `tools/legacy/` organization;
- no production imports from quarantined scripts.

Trigger: next tooling cleanup sprint. `python kbo_schedule_test.py` and
`models/mlb/placeholder_model.py` are deprecated candidates.

### 6. Dependency Clarification

Goal: make dependency files unambiguous.

Targets:

- `requirements.txt`
- `requirements-dev.txt`
- `requirements-current.txt`

Outcome:

- documented purpose for each file;
- optional future locked runtime dependency file;
- no package removals without import/runtime verification.

Trigger: deployment automation or dependency-upgrade sprint. This is
documentation debt today, not a correctness issue.

### 7. Large Module Decomposition Candidates

Goal: reduce future review risk without changing behavior.

Candidates:

- `engine/mlb/game_builder.py`
- `engine/decision/decision_builder.py`
- `dashboard/pages/dashboard_page.py`
- `dashboard/styles.py`

Outcome:

- decomposition proposals only;
- implement only inside approved roadmap sprints.

Trigger: before major NHL/NFL integration or broad dashboard redesign.

## Non-Goals

- model tuning;
- threshold changes;
- recommendation behavior changes;
- dashboard redesign;
- database rewrites;
- migration squashing;
- deleting legacy persistence tables without a migration plan.

## Priority Recommendation

Start with supported-surface marking and compatibility-alias inventory. Those
two steps carry the lowest implementation risk and reduce the most future
confusion.
