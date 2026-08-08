# Recommendation Root Cause

Sprint 84.2 root-cause conclusion:

RECOMMENDATION AUTHORITY IS OVER-CONSTRAINED

No implementation defect was proven. The current behavior follows the code and
the documented winner-first philosophy. The problem is that recommendation
authority is constrained by multiple dependent transforms of the same upstream
SharpScore signal.

## Evidence

Today's live slate produced:

- `11` MLB games.
- `6` LEAN.
- `5` PASS.
- `0` PLAYABLE.
- `0` STRONG PLAY.
- `0` CHEEK RIPPER.

The maximum model win strength was `56.2`; PLAYABLE requires `56.5`.

The maximum model confidence was `74.1`; PLAYABLE requires `74.0`.

This means the best game on the slate was confidence-qualified but still failed
PLAYABLE because the score-gap-to-strength transform did not reach the
threshold.

## Bottleneck

Primary bottleneck: SharpScore gap compression as expressed through Model Win
Strength.

The gate failure is not explained by market data, odds, edge, EV, sportsbook,
or quote availability. Those are not MLB moneyline authority inputs.

The gate failure is also not primarily Hammer. Hammer stayed below actionable
advisory tiers, but official MLB recommendation authority is already determined
before Hammer.

## First-Principles Evaluation

If SharpStack were designed today from scratch using the current MLB model, this
investigation would not intentionally rebuild the recommendation authority
exactly as it exists.

Reasons:

1. Model Win Strength is fully derived from SharpScore separation.
2. Model Confidence is mostly derived from the same SharpScore separation.
3. Recommendation Tier requires both derived values to clear thresholds.
4. Hammer reuses model strength and underlying model components, then appears in
   product surfaces as advisory confirmation.
5. There is no empirical evidence in the current dataset proving that this
   repeated confirmation improves betting quality.

The current design is coherent but over-constrained for the present model's
output range.

## Gates Deserving Review

Review order:

1. Model Win Strength transform: determine whether `50 + diff * 0.75` compresses
   the practical SharpScore range too tightly for current thresholds.
2. Recommendation tier mapping: determine whether thresholds are calibrated to
   the observed distribution of current model outputs.
3. Model Confidence formula: separate confidence evidence from score-gap
   repetition, especially if confidence is intended to be independent.
4. Hammer composition: test whether Hammer adds incremental predictive value
   after controlling for MLB model strength and reused components.
5. Product ranking/display: clarify when Hammer is advisory versus authority so
   users do not experience it as another hidden rejection gate.

## Final Root Cause

The best-supported statement is:

RECOMMENDATION AUTHORITY IS OVER-CONSTRAINED

The reason is significant filter stacking: SharpScore separation is evaluated as
team-score gap, transformed into model win strength, reused inside confidence,
thresholded by recommendation tier, and then partially reused again inside
Hammer.
