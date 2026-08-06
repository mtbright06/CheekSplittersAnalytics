# KBO Moneyline Technical Audit Reference

Phase 2B audit, updated by Sprint 80.1 correctness repair and Sprint 80.2
normalization resolution. These sprints changed only objective implementation
defects; they did not tune configured weights, thresholds, confidence formulas,
or recommendation tiers.

## Closure Recommendation

**KBO MODEL INTEGRITY CERTIFIED WITH PHASE 3 VALIDATION ITEMS**

The model is market-independent after odds enrichment, its thresholds are
monotonic, and selected team assignment is now derived from weighted model
score direction. The former row-index bullpen and recent-form heuristics have
been neutralized pending genuine KBO data. Their configured weights remain
reserved, so the current starter/offense-only practical score range is
narrower than the historical full-component range.

## Files Audited

- `cheek_splitters_engine.py`
- `engine/pipeline.py`
- `engine/factory.py`
- `engine/model_factory.py`
- `providers/kbo.py`
- `providers/kbo_data_provider.py`
- `parsers/schedule_parser.py`
- `parsers/game_parser.py`
- `loaders/pitcher_loader.py`
- `models/game.py`
- `models/team.py`
- `models/model_result.py`
- `models/kbo_model.py`
- `calculators/starting_pitching.py`
- `calculators/offense.py`
- `calculators/bullpen.py`
- `calculators/recent_form.py`
- `engine/confidence.py`
- `engine/enrichers/odds_enricher.py`
- `engine/adapters/kbo_card_adapter.py`
- `engine/core/recommendation.py`
- `engine/core/ranking.py`
- `tools_build_recommendation_registry.py`
- KBO, winner-first, ranking, Hammer, and pregame tests

## PASS / REVIEW / DEFECT Matrix

| ID | Classification | Finding |
|---|---:|---|
| KBO-001 | PASS | `KBOModel.score` selects away/home from weighted model-score direction, not row index parity. |
| KBO-002 | PASS | Final KBO recommendation tier is based on ordinal model score, not edge or odds. |
| KBO-003 | PASS | Real-market reference edge is display/provenance after enrichment. |
| KBO-004 | RENAME/CLARIFY | `model_probability` is an ordinal score on roughly `42.4..59.6`, not calibrated probability. |
| KBO-005 | RENAME/CLARIFY | Final KBO confidence is normalized ordinal score strength, not historical reliability. |
| KBO-006 | REVIEW | Adapter maps KBO confidence into `hammer_score`; no true Hammer calculation runs for KBO. |
| KBO-007 | PASS | Bullpen score is intentionally neutral `0.0` until genuine KBO bullpen data exists. |
| KBO-008 | PASS | Recent-form score is intentionally neutral `0.0` until genuine KBO recent-form data exists. |
| KBO-009 | REVIEW | Starting-pitcher score uses sensible metrics but threshold buckets are unvalidated and overlapping. |
| KBO-010 | PASS | Offense score measures direct runs/game advantage. |
| KBO-011 | REVIEW | Configured component weights are applied exactly; neutral bullpen/recent-form weights are reserved, producing a narrower practical starter/offense-only range pending Phase 3 validation. |
| KBO-012 | COHERENT | Recommendation thresholds are monotonic, reachable, and non-overlapping. |
| KBO-013 | REVIEW | Home field, park, and weather do not materially influence the KBO moneyline score. |
| KBO-014 | REVIEW | Shared ranking is compatible but interprets KBO confidence through generic/Hammer-like fields. |

## Feature Audit

| Feature | Raw Source | Normalization | Expected Range | Direction | Missing Data | Effective Influence | Downstream Consumers | Audit |
|---|---|---|---:|---|---|---:|---|---:|
| Starter ERA | pitcher profile | threshold score | `-2..2` inside pitcher score | lower better | `0` | up to `0.70` through starter comparison | model score, reasons, adapter consensus | REVIEW |
| Starter WHIP | pitcher profile | threshold score | `-2..2` inside pitcher score | lower better | `0` | up to `0.70` through starter comparison | model score, reasons, adapter consensus | REVIEW |
| Starter K/9 | pitcher profile | threshold score | `-1..1` | higher better | `0` | starter comparison only | model score, reasons | REVIEW |
| Starter BB/9 | pitcher profile | threshold score | `-1..1` | lower better | `0` | starter comparison only | model score, reasons | REVIEW |
| Starter HR/9 | pitcher profile | threshold score | `-1..1` | lower better | `0` | starter comparison only | model score, reasons | REVIEW |
| Runs/game | team data | binary side advantage | `-1..1` | higher better | `0` if either side missing | `0.25` | model score, reasons, confidence data quality | PASS |
| Bullpen | none | neutral constant | `0` | none | neutral `0` | `0` | model score, reasons, adapter consensus | PASS |
| Recent form | none | neutral constant | `0` | none | neutral `0` | `0` | model score, reasons, adapter consensus | PASS |
| Market reference probability | odds enricher | SSRP reference | `0..1` | edge display only | unavailable edge | none for tier | odds, market edge | PASS |
| Park/weather | KBO card display fields | none | unknown | none | not scored | none | presentation | PASS |

## Weight Findings

Configured weights:

| Component | Weight | Raw Score Range | Max Abs Contribution | Normalized Share of Sum |
|---|---:|---:|---:|---:|
| Starting Pitching | `0.35` | `-2..2` | `0.70` | `41.2%` of configured sum |
| Offense | `0.25` | `-1..1` | `0.25` | `29.4%` of configured sum |
| Bullpen | `0.15` | `0` | `0` | reserved |
| Recent Form | `0.10` | `0` | `0` | reserved |

Findings:

- Configured weights sum to `0.85` and are applied exactly.
- Starting pitching dominates because it has both the largest weight and a
  `-2..2` raw range.
- Bullpen and recent form weights are retained for contract stability, but the
  components return neutral `0.0`; their contribution is zero while their
  configured weights remain reserved.
- Missing starter/offense values produce neutral `0`; there is no
  per-game missing-data renormalization.
- Effective influence does not always match configured importance because raw
  ranges differ.

Current production formula:

```text
contribution = round(raw_score * calculator.WEIGHT, 2)

weighted_score = sum(contribution)

model_strength / model_probability =
  round(50 + weighted_score * 8, 1)
```

With Sprint 80.1 neutral components:

```text
weighted_score =
  round(starter_score * 0.35, 2)
  + round(offense_score * 0.25, 2)
  + 0.0
  + 0.0
```

Practical starter/offense-only weighted-score range is `-0.95..0.95`, which
maps to `42.4..57.6` model strength. Bullpen and recent-form contributions are
intentionally neutral while their configured weights remain reserved. Threshold
and confidence calibration will be evaluated during KBO statistical integrity
work rather than altered without evidence.

Classification: **REVIEW** for empirical support, raw scale validation, and
compressed tier reachability.

## Winner-First Verification

Market fields do not affect final recommendation authority:

| Field | Affects Tier? | Notes |
|---|---:|---|
| edge | no | calculated after enrichment for display/provenance. |
| EV | no | not consumed by KBO model tiering. |
| implied probability | no | only creates market edge. |
| odds | no | only market quote/provenance. |
| market quality | no | not confidence/tier input. |
| sportsbook availability | no | missing market keeps edge unavailable. |

Winner-first result: **PASS**. Selection is derived from weighted score
direction: positive selects the away side under the current KBO calculator
contract, negative selects the home side, and zero remains neutral/no play.

## Probability Verdict

Current `model_probability` is:

```text
50 + weighted_score * 8
```

It is not calibrated and not a paired probability distribution.

Verdict: **RENAME/CLARIFY**. Recommended terminology: **KBO Model Score** or
**KBO Model Strength**, not probability.

## Confidence Verdict

Final exported KBO confidence is:

```text
(model_score - 42.4) / (59.6 - 42.4) * 100
```

A confidence value of `75` means the ordinal score is 75% through the active
score range. It does not measure historical reliability, market agreement, or
calibrated uncertainty.

Verdict: **RENAME/CLARIFY**.

## Feature-Overlap Findings

| Relationship | Classification | Finding |
|---|---:|---|
| Starter ERA vs WHIP/K/BB/HR | PARTIAL OVERLAP | Run prevention overlaps with underlying skill indicators. |
| Offense RPG vs recent form | INDEPENDENT IN CURRENT PATH | Recent form is neutral and has no current influence. |
| Bullpen vs team run prevention | INDEPENDENT IN CURRENT PATH | Bullpen is neutral and has no current influence. |
| Home field vs selected side | INDEPENDENT IN CURRENT PATH | Home field is not scored. |
| Park/weather vs scoring | INDEPENDENT | Not consumed by KBO moneyline score. |
| KBO score vs adapter Hammer score | LIKELY DOUBLE COUNT / MISLABEL | Adapter uses KBO confidence as Hammer score. |
| First 5 vs KBO | INDEPENDENT IN CURRENT PATH | No KBO First 5 integration found. |

## Hammer Verdict

KBO does not use `engine/decision/hammer_score.py`. The adapter maps model
confidence into `hammer_score`, so KBO Registry ranking and Best Bets can treat
model strength as Hammer-like strength.

Approximate duplication risk: `100%` of KBO Hammer score is derived from KBO
model confidence/strength rather than an independent Hammer calculation.

Verdict: **REVIEW**.

## Threshold Verdict

Thresholds are monotonic. With current neutral bullpen and recent form,
`LEAN` and `PLAYABLE` are reachable; `STRONG PLAY` is not reachable in the
starter/offense-only practical range:

```text
58.0+ -> STRONG PLAY
55.0+ -> PLAYABLE
52.0+ -> LEAN
else  -> NO PLAY
```

No branch overlap was found. Compressed tier reachability is a Phase 3
validation item, not a Sprint 80.2 tuning target.

Verdict: **COHERENT**, with Phase 3 validation required.

## Representative Walkthroughs

Sprint 80.1 regression cases cover the repaired authority contract and the
Sprint 80.2 resolution covers exact configured-weight behavior:

| Case | Contributions | Model Score | Selection | Recommendation | Result |
|---|---|---:|---|---|---:|
| Away-side model advantage | SP `0`, Offense `+0.25`, Bullpen `0`, Recent `0` | `52.0` | away | LEAN | PASS |
| Home-side model advantage | SP `0`, Offense `-0.25`, Bullpen `0`, Recent `0` | `48.0` | home | NO PLAY | PASS |
| Neutral model | SP `0`, Offense `0`, Bullpen `0`, Recent `0` | `50.0` | none | NO PLAY | PASS |

## Comparison With MLB

| Area | MLB | KBO | Classification |
|---|---|---|---:|
| Selection | higher team score selects side | weighted score direction selects side | both PASS |
| Model value semantics | `model_win_strength`, alias `model_probability` | `model_strength`, alias `model_probability` | aligned where practical |
| Confidence semantics | model confidence separated from Hammer confidence | final confidence is normalized score strength | KBO behind MLB |
| Market separation | conviction tier independent of SSRP edge | final tier independent of edge | both PASS |
| Component scoring | team scores on `0..100` | directional ordinal point system | intentional difference |
| Bullpen | ERA/WHIP heuristic | neutral until genuine KBO bullpen data | intentional deferral |
| Recent form | not in MLB SharpScore | neutral until genuine KBO recent-form data | intentional deferral |
| Hammer | explicit advisory calculation | compatibility mapping only | KBO behind MLB |
| Ranking | tier/strength/confidence/Hammer | shared ranking over adapted KBO fields | compatible but REVIEW |
| Documentation | current Phase 2A/3A docs | created in Phase 2B | now aligned |

## Final Classification

KBO is market-independent, threshold-coherent, and winner-first after Sprint
80.1. Bullpen and recent form are intentionally neutral rather than fabricated;
their configured weights remain reserved after Sprint 80.2 normalization was
reverted as unsafe against the established ordinal scale. It is therefore
**CERTIFIED WITH PHASE 3 VALIDATION ITEMS**: empirical weights, probability
calibration, confidence semantics, tier reachability, and Hammer ownership
remain research/documentation items, not Sprint 80.1 correctness defects.
