# Sprint 39 Handoff — First5 Integration Complete

## How to Use This File

Always pair this handoff with:

- `ARCHITECTURE.md`
- `ROADMAP.md`
- `CHAT_PROTOCOL.md`

A new chat must read all four before proposing code.

## Sprint Summary

Sprint 39 repaired the Decision Builder signal pipeline without changing Hammer scoring logic.

The goal was to ensure MLB, Bomb Lab, First5, and Market signals contribute correctly before future score calibration.

## Completed

### Hammer Observability

Decision Builder now persists:

- `agreement_bonus`
- `contradiction_penalty`
- `market_status_penalty`
- `real_market_loaded`

### First5 Game Matching

The matcher now accepts identical game IDs and falls back to normalized matchup comparison when IDs differ.

### First5 Recommendation Extraction

Decision Builder now recognizes `f5_ml.lean`. PASS remains neutral and does not count toward agreement.

### First5 Score Source

Decision Builder prioritizes `decision_score` before legacy confidence fields.

### Market Fallback Repair

Decision Builder no longer accepts empty market objects as real sportsbook markets. When First5 market data lacks usable odds, line, or implied probability, MLB market extraction may supply the real market.

This restored Market Edge, Expected Value, and `real_market_loaded`.

## Validation

- First5 available: 16 / 16 games
- Real sportsbook markets: 16 / 16 games
- LEAN: 4
- WATCH: 6
- PASS: 6
- Mean Hammer: 59.03
- Median Hammer: 58.75
- First5 directional picks: 7
- First5 PASS/neutral outcomes: 9

Washington example:

- Hammer: 68.2
- Base: 65.7
- First5: 59.2
- Agreement: +2.5
- Recommendation: LEAN
- Market Edge: 10.68%
- Expected Value: 18.89%

## Important Conclusions

Hammer weights were not modified. The issue was signal plumbing, not score calibration. Current recommendation thresholds remain unchanged.

## Intentionally Uncommitted Files

Keep these separate from Recommendation History analytics work:

- `engine/mlb/game_builder.py`
- `engine/odds/the_odds_api_provider.py`
- `engine/odds/models.py`

Do not sweep these into an unrelated commit.

## Current Architecture Guardrails

- Prediction engines remain independent.
- No SQLAlchemy imports in engine/model code.
- Decision Builder owns signal integration.
- Hammer remains explainable.
- Recommendation history is immutable.
- Odds history is append-only.
- Persistence occurs through services.
- No score calibration until historical evidence supports it.
- No architecture redesign without an approved feature need.

See `ARCHITECTURE.md` for authoritative design.

## Next Sprint

# Sprint 40 — Recommendation History Analytics

### Primary Goals

- query recommendation history,
- grade results,
- calculate win percentage,
- calculate units,
- calculate ROI,
- produce rolling 7-day and 30-day summaries,
- analyze performance by recommendation tier,
- analyze performance by signal combination,
- analyze performance by market and model version.

### Secondary Planning Items

- Play of the Day audit
- Model Health report

### Explicit Non-Goals

- no Hammer-weight changes,
- no dashboard,
- no unrelated provider refactor,
- no architecture redesign,
- no mixing intentionally uncommitted files into this sprint.

## Required New-Chat Opening Prompt

> We are continuing SharpStack.  
> Read PROJECT_HANDOFF.md, ARCHITECTURE.md, ROADMAP.md, and CHAT_PROTOCOL.md before proposing code.  
> Treat ARCHITECTURE.md as authoritative.  
> Continue Sprint 40 Recommendation History Analytics.  
> Do not redesign architecture, modify Hammer weights, or include intentionally uncommitted provider/game-builder files.  
> Before writing code, summarize the sprint goal, constraints, expected files, and any ambiguity.  
> End the chat by updating PROJECT_HANDOFF.md and ROADMAP.md.

## End-of-Sprint Requirements

- feature works,
- tests pass,
- migration is applied if required,
- branch and commit are confirmed,
- push succeeds,
- intentionally uncommitted files are listed,
- handoff is updated,
- roadmap is updated,
- exact next-chat prompt is provided.
