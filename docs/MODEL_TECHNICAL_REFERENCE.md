# SharpStack Model Technical Reference

This document records the audited recommendation paths as of Sprint 78.2. It is descriptive only and does not introduce tuning.

Empirical validation status is maintained in
`docs/MODEL_VALIDATION_REPORT.md`. Current weights and thresholds should be
treated as conceptually intentional but empirically unvalidated until resolved
post-reset grades are available.

## Core Invariant

Odds, edge, expected value, implied probability, price, sportsbook, and market quality may be stored and displayed. They must not influence Hammer Score, qualification, recommendation tier, confidence, ordering, Registry order, Best Bets order, Dashboard order, or Play of the Day selection.

## Pregame Eligibility

File: `engine/core/pregame_eligibility.py`

Canonical object:

- `PregameEligibility(eligible: bool, reason: PregameEligibilityReason)`

Reasons:

- `GAME_NOT_STARTED`
- `GAME_STARTED`
- `LIVE_MARKET`
- `COMPLETED`
- `UNVERIFIED`
- `NO_START_TIME`

Publication helper:

- `engine/core/recommendation.py::is_verified_pregame_recommendation`

Verified recommendation requires `pregame_eligible is True` and reason `GAME_NOT_STARTED`.

Observed gates:

- adapters reject non-pregame rows before constructing `Recommendation`
- `RecommendationRegistry.add` rejects non-pregame recommendations
- totals recommendation disables line availability unless market payload is verified pregame
- persistence/history services are expected to consume only verified registry output

## MLB Moneyline

Primary files:

- `engine/model/sharpscore.py`
- `engine/model/component_scores.py`
- `engine/model/confidence.py`
- `engine/model/recommendations.py`
- `engine/adapters/mlb_decision_adapter.py`

Team score weights in `engine/model/sharpscore.py`:

- offense: `0.40`
- starting pitching: `0.45`
- bullpen: `0.10`
- home field: `0.05`

Selection:

- `choose_side`: higher team score wins; exact tie selects home.

Probability:

- `probability_from_scores`: `50 + score_diff * 0.75`
- clamped to `40..70`

Recommendation thresholds:

- `63.0` probability and `85.0` confidence: `CHEEK RIPPER`
- `59.0` probability and `78.0` confidence: `STRONG PLAY`
- `56.5` probability and `74.0` confidence: `PLAYABLE`
- `52.0` probability and `65.0` confidence: `LEAN`
- otherwise `PASS`

Confidence:

- base `45`
- matchup strength: `min(score_diff * 1.1, 30)`
- data quality: completeness * `20`
- starter certainty: `0`, `-10`, or `-20`
- clamped to `35..95`

Audit classification:

- Team scoring: PASS.
- Selection by model score: PASS.
- Market value label from SSRP edge: Display-only.
- `edge_pct` and EV fields: Display-only in shared ranking.
- MLB confidence is market-independent after Sprint 78.1; it uses model/data quality inputs only.
- `engine/model/recommendations.py::recommendation` and `grade_label`: LEGACY edge-based helpers.

## MLB Totals

Primary files:

- `engine/mlb/totals/totals_model.py`
- `engine/mlb/totals/recommendation.py`
- `engine/mlb/totals/market.py`
- `engine/adapters/mlb_totals_adapter.py`

Projection:

- team run projections are built from offense, opposing starter, and park
- bullpen adjustment is added to starter-based total
- `projected_total` is compared with `market_total`

Direction:

- `evaluate_market_edge` returns `OVER` when projected total is above the line and `UNDER` when below the line.
- The field name `edge` is a run-distance/projection separation term in this context.

Recommendation scoring in `build_totals_recommendation`:

- model separation score: `40 + model_separation * 30`, clamped `0..100`
- model confidence score: clamped input confidence
- data quality score: `EXCELLENT=95`, `GOOD=82`, `FAIR=68`, `LIMITED=50`
- bullpen confidence score: clamped bullpen confidence

Weights:

- model separation: `0.40`
- model confidence: `0.30`
- data quality: `0.20`
- bullpen confidence: `0.10`

Thresholds:

- `STRONG BET`: separation `>= 1.25` and score `>= 82`
- `BET`: separation `>= 0.75` and score `>= 72`
- `LEAN`: separation `>= 0.40` and score `>= 64`
- otherwise `PASS`

Audit classification:

- Winner-first side selection by projection vs line: PASS.
- Price/EV/market quality exclusion from scoring: PASS.
- Pregame market payload gate before totals recommendation: PASS.
- `market.py::recommendation_from_edge`: LEGACY/display-adjacent helper; verify it does not regain authority.

## KBO Moneyline

Primary files:

- `models/kbo_model.py`
- `engine/confidence.py`
- `engine/adapters/kbo_card_adapter.py`

Score path:

- calculators: starting pitching, offense, bullpen, recent form
- `model_probability = 50 + weighted_score * 8`
- no-market recommendation tiers:
  - `58.0`: `STRONG PLAY`
  - `55.0`: `PLAYABLE`
  - `52.0`: `LEAN`
  - otherwise `NO PLAY`

No-market confidence:

- `_model_strength_confidence` maps the active KBO ordinal range `42.4..59.6` to `0..100`.

Audit classification:

- No-market KBO model-score recommendation: PASS.
- Adapter preserves KBO row recommendation and stores market values as metadata: PASS/Display-only.
- Real-market `finalize` keeps edge as display metadata but uses the same KBO model-score recommendation and confidence path as no-market finalization.
- `engine/confidence.py::ConfidenceEngine.calculate` no longer includes market availability in data quality.
- `components["market"]` in KBO adapter: Display-only if not ranked.

## Hammer Score

File: `engine/decision/hammer_score.py`

Inputs:

- `mlb_model_score`
- `mlb_model_probability`
- `first5_score`
- `bomb_score`
- `starter_score`
- `offense_score`
- `bullpen_score`
- `park_score`
- `weather_score`
- `sample_confidence`
- `module_agreement`
- `contradiction_count`
- `real_market_loaded` metadata only

Weights:

- MLB model: `0.27`
- First 5: `0.17`
- Bomb: `0.12`
- starter: `0.15`
- offense: `0.12`
- bullpen: `0.08`
- park: `0.05`
- weather: `0.05`
- sample confidence: `0.04`

The configured weights total `1.05`, but Hammer normalizes by `used_weight`, so full-score inputs remain bounded at `100`.

Bonuses/penalties:

- agreement bonus: `min(max(module_agreement - 1, 0) * 2.5, 10)`
- contradiction penalty: `min(contradiction_count * 5, 20)`
- final score clamped `0..100`

Hammer labels:

- `86`: `HAMMER`
- `76`: `BET`
- `66`: `LEAN`
- `56`: `WATCH`
- otherwise `PASS`

Audit classification:

- Market edge/EV absent from Hammer inputs and breakdown: PASS.
- Missing components skipped and normalized: PASS.
- `real_market_loaded` has no score impact: PASS.

## Decision Builder

File: `engine/decision/decision_builder.py`

Current behavior:

- determines primary MLB side from MLB model, then First 5 fallback, then Bomb fallback
- constructs model-consensus signals from MLB, First 5, Bomb Lab
- passes model-derived components into Hammer
- stores market edge, EV, book, sportsbook, and quote metadata for display
- sorts decision rows by Hammer after Hammer is market-independent

Audit classification:

- No market-consensus vote: PASS.
- Market metadata preserved for display: PASS.
- Missing MLB model probability leaves the MLB model component unavailable; market edge is not used as Hammer fallback.

## Shared Ranking And Registry

Primary files:

- `engine/core/ranking.py`
- `engine/core/registry.py`

Ranking priority:

- canonical recommendation tier
- model probability or outcome probability
- model confidence
- market-independent Hammer Score
- stable schedule, league, market, event, and selection tie-breaker

Classification:

- Edge/EV/odds/price removed from ranking formula: PASS.
- Registry publication gate uses `is_verified_pregame_recommendation`: PASS.
- Registry preserves edge/EV fields in serialized rows: Display-only.
- Stable deterministic tie-breaks do not use UUID, edge, EV, odds, or price.

## Canonical Recommendation Episodes

Primary files:

- `app/services/recommendation_episode_lock_service.py`
- `app/services/canonical_recommendation_grading_service.py`
- `app/models/recommendation_episode.py`

Lock rule:

- the official recommendation for a stream is the final active actionable
  episode before lock.
- the canonical snapshot is the latest attached eligible snapshot with
  `recommendation_time < recommendation_streams.scheduled_start_at`.
- post-start snapshots are never canonical, even when locking runs
  retroactively after completion.

Canonical grading:

- only `LOCKED` episodes with `canonical_snapshot_id` and terminal
  authoritative result rows can create canonical grade rows.
- moneyline and totals grades use the existing immutable snapshot grading
  rules for winner side, totals direction, canonical market line, push, void,
  and ungradeable handling.
- successful canonical grading transitions `LOCKED` to `GRADED`.
- superseded, withdrawn, active, ineligible, and void episodes do not receive
  win/loss canonical grades.

Status mapping:

- `LIVE`, `FINAL`, `SUSPENDED`, `CANCELED`, and `INCOMPLETE` mean game-start or
  terminal state is authoritative enough to lock.
- `FINAL` can grade; `SUSPENDED` remains pending after lock; `CANCELED` marks
  the episode `VOID`.
- `SCHEDULED` and `POSTPONED` fail closed unless the authoritative stream
  schedule has passed. A provider replacement start must update the stream
  before lock so the old start time is not treated as authoritative.

Idempotency and legacy isolation:

- stream and episode rows are locked during canonical lock/grading.
- `canonical_recommendation_grades` enforces one grade per episode with
  `uq_canonical_recommendation_grades_episode`.
- episode-enabled result processing no longer creates new snapshot-level
  `PENDING` grades; existing `prediction_snapshot_grades` remain readable as
  legacy/audit history.

## Play Of The Day

File: `engine/core/play_of_day.py`

Eligibility:

- must be actionable
- must be verified pregame
- non-authoritative/non-MLB-moneyline candidates must clear minimum Hammer
- optional real-market requirement
- consensus veto remains possible

Selection:

- eligible recommendations are sorted by shared ranking score and Hammer Score
- edge and EV are included only in explanation text

Classification:

- Negative edge no longer disqualifies favorites: PASS.
- Positive edge no longer promotes underdogs: PASS.
- Edge/EV in explanation: Display-only.

## Tests Covering The Current Behavior

Focused tests identified:

- `tests/test_mlb_recommendation_authority.py`
- `tests/test_mlb_moneyline_classification.py`
- `tests/test_kbo_confidence.py`
- `tests/test_kbo_card_adapter.py`
- `tests/test_mlb_totals_winner_first.py`
- `tests/test_winner_first_shared_integrity.py`
- `tests/test_pregame_recommendation_boundaries.py`
- `tests/test_best_bets_workstation.py`

Tests that still encode edge-first behavior:

- `tests/test_kbo_confidence.py::test_real_market_recomputes_edge_after_enrichment`
- `tests/test_mlb_moneyline_classification.py` still covers the legacy edge-based helper.

Recommended tests to add before the next production recommendation sprint:

- MLB confidence unchanged when only `odds.book_probability` changes or disappears.
- KBO real-market recommendation unchanged when only implied probability changes.
- Decision Builder refuses edge fallback for missing MLB probability.
- Fully tied registry rows use deterministic event/market/selection order rather than UUID.

## Safest Implementation Sequence

1. Remove market probability from MLB confidence completeness and add invariant tests.
2. Retire KBO real-market edge recommendation finalization or convert it to display-only metadata.
3. Remove Decision Builder `score_from_edge` from the Hammer fallback path.
4. Replace UUID tie-break fallback with deterministic event/market/selection ordering.
5. Re-run focused winner-first and pregame-boundary tests before any model tuning.
