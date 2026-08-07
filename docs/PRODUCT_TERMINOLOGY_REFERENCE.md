# Product Terminology Reference

Canonical product language for SharpStack user-facing metrics.

| Term | Recommended meaning | Avoid implying | Status |
|---|---|---|---|
| Recommendation | The current model/Registry play label. | Guaranteed outcome. | PASS |
| Recommendation Tier | Rule-based strength tier from the current model. | Statistically validated tier performance. | DOCUMENT |
| Model Win Strength | Bounded model-implied strength for selected side. | Calibrated win probability. | RENAME |
| Model Probability | Compatibility alias for model strength unless calibrated. | True probability. | RENAME |
| Model Confidence | Model-specific trust heuristic. | Historical accuracy or certainty. | DOCUMENT |
| Confidence | Ambiguous unless qualified. | Same meaning across all pages. | RENAME |
| Hammer Score | MLB advisory confirmation score when true Hammer is used. | Recommendation authority or independent proof in all markets. | RENAME |
| Hammer Confidence | Hammer confirmation label. | Model confidence. | PASS |
| Recommendation Score | Weighted model score for recommendation strength. | Probability. | DOCUMENT |
| Projected Total | Model-estimated run total. | Proven mean/median/calibrated total. | DOCUMENT |
| Market Line | Sportsbook line. | Model projection. | PASS |
| Sportsbook | Quote source. | SharpStack endorsement of a book. | PASS |
| Market Edge | Market price/value advantage. | Recommendation authority. | RENAME |
| Run Separation | Difference between projected total and market total. | Moneyline edge. | PASS |
| EV | Expected value from price/probability context. | Official recommendation strength. | DOCUMENT |
| Model Only | No real market quote loaded. | Fake odds or real sportsbook availability. | PASS |
| Real Market | Real quote/market data loaded. | Recommendation is necessarily better. | PASS |
| Model Health Win % | Canonical graded hit rate. | Full model calibration or all-snapshot history. | PASS |
| Bomb Score / Attack Score | Bomb Lab vulnerability/research score. | HR probability. | DOCUMENT |
| First 5 Confidence | First 5 model confidence heuristic. | Historical F5 hit rate. | DOCUMENT |

## Preferred Naming Changes

| Current wording | Preferred wording | Reason |
|---|---|---|
| Model Probability | Model Win Strength | Avoid unvalidated probability implication. |
| Confidence | Model Confidence or Hammer Confidence | Avoid overloaded generic term. |
| Hammer Score for KBO/Totals compatibility values | Model Strength / Recommendation Score / Ranking Score | Avoid implying true Hammer ran. |
| Edge for totals run distance | Run Separation | Avoid mixing price edge with run separation. |
| Recommendation Score without context | Weighted Recommendation Score | Avoid probability implication. |

## Product Copy Guardrails

- Do not say a confidence value means a percent chance to win.
- Do not say Model Win Strength is calibrated probability until Phase 3 proves
  it.
- Do not present Hammer as the authority when model-specific recommendation
  contracts own the play.
- Do not imply Edge selects MLB moneyline recommendations.
- Do not treat Bomb Lab or First 5 research scores as official probability.
- Always distinguish canonical Model Health from raw snapshot history.
