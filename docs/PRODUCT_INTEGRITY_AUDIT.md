# Phase 5 Product Integrity Audit

Read-only product audit completed on 2026-08-06. No production code, UI code,
model logic, thresholds, recommendations, data, or migrations were modified.

Product Integrity verdict:

**PRODUCT INTEGRITY CERTIFIED WITH CLARIFICATIONS**

## Executive Summary

SharpStack generally tells the truth: recommendations, market context,
canonical history, and Model Health are traceable to identifiable model,
registry, persistence, and presentation owners. No objectively incorrect
user-facing behavior was corrected in this sprint.

The product risk is semantic clarity. Several displayed fields are accurate as
internal SharpStack metrics but can be misunderstood as calibrated
probability, historical accuracy, independent Hammer evidence, or betting
authority. These require concise product explanations before SharpStack can be
called fully self-explanatory to a non-developer user.

## Metric Inventory

| Metric | Source | Calculation owner | Persistence owner | Presentation owner | Classification |
|---|---|---|---|---|---|
| Recommendation | Model/adapters/Registry row | MLB `sharpscore`, KBO model/adapter, Totals recommendation model | `Recommendation` snapshot and canonical episode | Best Bets, Registry, Dashboard, History | PASS |
| Recommendation Tier | Model-specific label or totals tier | MLB/KBO/Totals model paths | Snapshot components and canonical read model | Badges, Registry, Model Health | DOCUMENT |
| Model Win Strength | `model_win_strength` / `model_probability` compatibility value | MLB SharpScore, KBO finalize/adapter | Snapshot `projection` for moneyline and components | Registry, Dashboard, Best Bets | RENAME |
| Model Probability | Compatibility alias for model strength | Model/adapters | Snapshot prediction payload | Registry/table/adapters | RENAME |
| Confidence | Model confidence or compatibility display label depending page | Model-specific confidence functions/adapters | Snapshot `confidence` and components | Registry, KBO, First 5, Best Bets | RENAME |
| Model Confidence | Model-specific trust/strength heuristic | MLB confidence, KBO ordinal scale, Totals confidence inputs | Snapshot confidence/components | Model-specific pages/adapters | DOCUMENT |
| Hammer Confidence | Hammer confirmation label | Decision Builder/Hammer | Snapshot components | Best Bets/Registry | PASS |
| Hammer Score | True Hammer for MLB moneyline; compatibility score for KBO/Totals | Decision Builder for MLB, adapters for KBO/Totals | Snapshot prediction/components | Registry, Best Bets, Dashboard | RENAME |
| Recommendation Score | Totals/compatibility ranking score | Totals recommendation model/adapters | Registry row/components where present | Totals/Registry/Best Bets | DOCUMENT |
| Projected Total | Totals/First 5 projected runs | Totals model, First 5 model | Current totals persistence does not store first-class numeric projected total | Totals console, First 5 cards, explanations | FUTURE ENHANCEMENT |
| Edge | Market-vs-model value or totals run separation depending context | SSRP/market edge or totals model separation | Snapshot market/components | Registry, Best Bets, First 5 | RENAME |
| Market Line | Sportsbook total/line | Odds provider/enricher | Snapshot `market_line` | Registry, Totals, First 5 | PASS |
| Sportsbook | Selected quote book | Odds provider/enricher | Snapshot market payload | Registry, KBO, Bomb Lab, Best Bets | PASS |
| First 5 metrics | F5 model output | `engine/first5/first5_model.py` | JSON card artifact | First 5 page/Dashboard preview | DOCUMENT |
| Bomb Lab metrics | Bomb Lab research output | Bomb Lab engine/tools | JSON card artifact | Bomb Lab page/Dashboard preview | DOCUMENT |
| Model Health metrics | Canonical grades and results | `RecommendationAnalyticsService` | Canonical episodes/grades/game results | Model Health page | PASS |
| Registry metrics | Registry summary/ranking | Registry/ranking pipeline | JSON Registry artifact | Best Bets/Registry/Dashboard | DOCUMENT |
| Dashboard metrics | Registry/card summaries | Dashboard helpers over artifacts | JSON artifacts | Command Center | DOCUMENT |

## Semantic Findings

| Displayed concept | Classification | Product truthfulness finding |
|---|---|---|
| Model Win Strength | RENAME | Accurate as bounded model-implied strength, but can sound like calibrated win probability. |
| Model Probability | RENAME | Compatibility alias; should not be presented as calibrated probability. |
| Confidence | RENAME | Means different things by surface: model confidence, Hammer confidence, or ordinal KBO confidence. |
| Hammer Score | RENAME | True Hammer for MLB moneyline, compatibility/ranking score for KBO and Totals. |
| Recommendation Score | DOCUMENT | Totals score is a weighted recommendation-strength score, not probability. |
| Projected Total | DOCUMENT | Means deterministic expected-runs-style estimate; not proven mean/median/calibrated projection. |
| Edge | RENAME | Moneyline edge is price/value; totals edge can mean run separation. The label needs market-specific context. |
| Market Line | PASS | Describes sportsbook line accurately. |
| Sportsbook | PASS | Describes quote source accurately. |
| Model Health Win % | PASS | Derived from canonical graded recommendations and labeled as read-only performance. |
| Bomb Score / Attack Score | DOCUMENT | Research/vulnerability score, not HR probability. |
| First 5 Confidence | DOCUMENT | Model confidence heuristic, not historical hit probability. |
| KBO Model Strength | RENAME | KBO workstation currently displays `confidence` under "Model Strength" while also showing model probability/strength separately. |

No `DEFECT` was confirmed because the displayed values are traceable and not
known to be numerically wrong. The main issue is naming/context.

## Explainability Findings

| Product area | Classification | Traceability |
|---|---|---|
| MLB Moneyline | PASS | Inputs, component scores, model recommendation, market value, Hammer context, Registry row, snapshot, canonical episode, and grade are traceable. |
| MLB Totals | DOCUMENT | Recommendation path is traceable, but projected total is not first-class persisted numeric history. |
| KBO | DOCUMENT | Model-only recommendation path is explainable, but model strength/probability/confidence terminology is easy to confuse. |
| Best Bets | DOCUMENT | Uses Registry order and rows; concise explanation exists, but Edge/Hammer/Confidence labels need context. |
| Registry | DOCUMENT | Component expander helps trace model reasons; compatibility aliases need explanation. |
| Model Health | PASS | Canonical-only performance source is stated and traceable. |
| Bomb Lab | DOCUMENT | Research metrics are visible and reason-backed, but not framed as probabilities. |
| First 5 | DOCUMENT | Projected runs, lean, margin, and confidence are visible; confidence semantics need short help text. |
| History | PASS | Canonical read model can trace recommendation, grade, result, model run, and snapshot. |
| Hall | DOCUMENT | No distinct Hall surface was identified in the audited dashboard files. |

## Consistency Findings

| Concept family | Classification | Finding |
|---|---|---|
| Confidence/model confidence/Hammer confidence | RENAME | Same word "confidence" carries different meanings across MLB, KBO, Totals, First 5, and Best Bets. |
| Model probability/model strength/model win strength | RENAME | Same bounded score appears under probability-like and strength-like names. |
| Hammer/Hammer score | RENAME | True Hammer and compatibility score share the same display field. |
| Tier labels | DOCUMENT | MLB, Totals, KBO, Bomb Lab, and shared badges use related but not identical labels. |
| Selection labels | PASS | Team/OVER/UNDER selections remain understandable. |
| Winner labels | PASS | Grading uses immutable selection side and game-result winner side. |
| Market labels | PASS | Moneyline/totals/market-only labels are generally clear. |
| Edge labels | RENAME | Edge can be price/value percentage or run separation depending surface. |

## UI Truthfulness Findings

| Surface | Classification | Finding |
|---|---|---|
| Dashboard Command Center | DOCUMENT | High-level preview is truthful but compact; users may not know Hammer/Confidence semantics from preview alone. |
| Best Bets | DOCUMENT | "Hammer Confidence" is accurate when sourced from Hammer, but quick explanation can imply edge is why SharpStack likes all plays. |
| Registry cards | RENAME | Presents Model Win Strength, Market Win, Edge, EV, Hammer Score, and Rank together; values are traceable but need context to avoid probability/authority confusion. |
| Decision Board | DOCUMENT | Under redesign message avoids overclaiming. |
| Model Health | PASS | Clearly states canonical recommendation episodes and grades. |
| Bomb Lab | DOCUMENT | Metrics are research diagnostics, but "Confidence" or "Strong Play" style badges can be mistaken for official betting probability. |
| First 5 | DOCUMENT | Projections/leans are clear; confidence is heuristic. |
| KBO workstation | RENAME | "Model Strength" currently uses confidence while "Model Prob." displays the model-strength/probability alias. |
| History | PASS | Canonical history is traceable and avoids legacy fallback. |

## Cross-Page Consistency

| Page / Area | Classification | Consistency finding |
|---|---|---|
| Dashboard | GOOD | Summaries follow Registry/card artifacts. |
| Best Bets | GOOD | Uses Registry rows and Registry-owned ranking. |
| Registry | GOOD | Most complete user-facing trace with reasons and components. |
| Decision Board | PASS | Does not present stale/full decision semantics while under redesign. |
| Model Health | PASS | Uses canonical analytics only. |
| Hall | DOCUMENT | No active Hall page found in audited dashboard routes. |
| Bomb Lab | GOOD | Research metrics are internally consistent with Bomb Lab payloads. |
| First 5 | GOOD | First 5 cards/table tell the same story. |
| History | PASS | Canonical read model supports traceable history. |

## Missing Context Recommendations

Concise explanatory copy would reduce misunderstanding for:

- Model Win Strength: bounded model-implied strength, not calibrated probability.
- Confidence: model-specific trust heuristic, not historical accuracy.
- Hammer Score: advisory confirmation for MLB; compatibility/ranking score for
  some non-MLB/totals surfaces.
- Recommendation Tier: rule-based current-model tier, not statistically
  validated performance band.
- Projected Total: model-estimated runs, not proven mean/median.
- Recommendation Score: weighted score, not probability.
- Edge: market-specific value/separation; not recommendation authority.

## Transparency Score

| Dimension | Score | Reason |
|---|---|---|
| Explainability | GOOD | Reasons/components/history exist, but totals projected total and compatibility aliases need clearer context. |
| Consistency | NEEDS IMPROVEMENT | Confidence, probability/strength, Hammer, and Edge labels vary by surface. |
| Truthfulness | GOOD | No knowingly false displayed value found; risk is implication, not data fabrication. |
| Terminology | NEEDS IMPROVEMENT | Several labels are overloaded. |
| Presentation | GOOD | Pages are readable and mostly artifact-driven. |
| Traceability | GOOD | Canonical persistence and Registry artifacts provide trace paths. |

## Final Verdict

**PRODUCT INTEGRITY CERTIFIED WITH CLARIFICATIONS**

SharpStack is truthful enough to continue product development, but before broad
release or new sport expansion it needs terminology clarifications for
confidence, model strength/probability, Hammer, Edge, recommendation score, and
projected totals.
