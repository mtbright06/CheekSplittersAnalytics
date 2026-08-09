# Engineering Debt Register

Read-only register created during Sprint 82.0 and reevaluated with the Sprint
82.0 verification decision test:

> Would removing or leaving this create a correctness, maintainability, or
> future-development problem?

Classifications are limited to `PASS`, `DOCUMENT`, `FUTURE ENHANCEMENT`,
`DEFECT`, and `DEPRECATED`.

No `DEFECT` item was confirmed.

| ID | Area | Risk of leaving it | Risk of removing it now | Current classification | Final classification | Cleanup priority | Trigger for action |
|---|---|---|---|---|---|---|---|
| EDR-001 | Legacy top-level KBO/model packages: `calculators/`, `models/`, `providers/`, `parsers/`, `loaders/` | Future NHL/NFL/KBO contributors may edit ambiguous old paths or duplicate model behavior. | Current KBO tests/tools still import these paths; removal could break active verification. | FUTURE ENHANCEMENT | FUTURE ENHANCEMENT | High | Before NHL/NFL model expansion or any KBO package rewrite. |
| EDR-002 | Legacy recommendation engine tooling: `recommendation_engine/`, `tools_inspect_recommendation_sources.py` | Could be mistaken for production authority by future developers. | Tooling may still support source inspection; removal could lose audit utility. | FUTURE ENHANCEMENT | FUTURE ENHANCEMENT | Medium | When recommendation explorer/source tooling is replaced or documented. |
| EDR-003 | Compatibility aliases for model/probability/confidence/Hammer fields | Leaving them undocumented creates semantic drift and future integration mistakes. | Removing now could break dashboard, Registry, persistence, and history consumers. | FUTURE ENHANCEMENT | FUTURE ENHANCEMENT | High | Before adding NHL/NFL contracts or changing Registry field names. |
| EDR-004 | Duplicate recommendation/tier label parsing | Divergence can affect ranking, badges, analytics buckets, or active/PASS detection. | Centralizing now risks behavior changes across presentation and analytics. | FUTURE ENHANCEMENT | FUTURE ENHANCEMENT | High | Before adding new sport tiers or changing recommendation labels. |
| EDR-005 | Duplicate safe numeric parsing | Leaving it is minor maintainability noise; no current correctness problem found. | Removing now could create incidental behavior differences in adapters/tools. | FUTURE ENHANCEMENT | DOCUMENT | Low | Consolidate only while touching affected modules for another approved reason. |
| EDR-006 | Legacy settlement isolation | Leaving it is safe while opt-in remains explicit. | Removing now could break existing history consumers and auditability. | DOCUMENT | DOCUMENT | Low | Only after canonical history fully replaces all legacy consumers. |
| EDR-007 | Snapshot grading isolation | Leaving it preserves audit history and raw diagnostics. | Removing now would lose historical diagnostic capability. | DOCUMENT | DOCUMENT | Low | Only if snapshot grades are formally retired with migration plan. |
| EDR-008 | Large modules: `game_builder`, `decision_builder`, dashboard page/styles | Future development cost rises as sports/features expand. | Decomposition now could destabilize core flows without a feature driver. | FUTURE ENHANCEMENT | FUTURE ENHANCEMENT | Medium | Before major NHL/NFL integration or broad dashboard redesign. |
| EDR-009 | Dependency manifests | Leaving them unclear can confuse deployment versus local environment setup. | Removing/rewriting now risks environment drift without import/runtime verification. | FUTURE ENHANCEMENT | DOCUMENT | Medium | Before deployment automation or dependency upgrade sprint. |
| EDR-010 | Placeholder schedule script: `python kbo_schedule_test.py` | Leaving noisy TODO script can mislead contributors; no production risk. | Removing now has low risk but still outside documentation-only verification. | DEPRECATED | DEPRECATED | Medium | Delete or quarantine in next approved tooling cleanup. |
| EDR-011 | Placeholder model path: `models/mlb/placeholder_model.py` | Leaving it can mislead model contributors into using an unsupported model path. | Removing now is probably low risk, but should follow import verification. | FUTURE ENHANCEMENT | DEPRECATED | Medium | Delete/quarantine after confirming no imports outside tests/tools. |
| EDR-012 | Dashboard placeholder naming | Leaving name is confusing but active workflows depend on the file. | Renaming now could break imports/tests/routes. | DOCUMENT | DOCUMENT | Low | Rename only during dashboard route cleanup. |
| EDR-013 | Totals projected-total explainability | Leaving it blocks future projection-error studies, not current recommendations. | Forcing persistence now would be a schema/contract change outside this audit. | DOCUMENT | FUTURE ENHANCEMENT | High | Before Phase 3 totals projection-error analysis. |
| EDR-014 | Root-level scripts/tests | Leaving them makes tool/test ownership harder to scan. | Moving now can break ad hoc operational workflows. | FUTURE ENHANCEMENT | FUTURE ENHANCEMENT | Medium | When tool ownership is documented or CI/test discovery is formalized. |
| EDR-015 | Alembic chain | Leaving it preserves applied migration history. | Removing/rewriting would be a correctness risk. | PASS | PASS | None | Continue no-rewrite migration discipline. |
| EDR-016 | Recommendation authority | Leaving current ownership preserves correctness. | Changing now could create hidden alternate authority. | PASS | PASS | None | Reaudit when adding new sport/model authority paths. |
