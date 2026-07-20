# Sprint 41 ? MLB Totals Recommendations

## Objective

Introduce a bettor-facing recommendation layer for MLB totals without replacing the underlying projection or market-edge models.

## Delivered

- Added `TotalsRecommendation`.
- Added `build_totals_recommendation()`.
- Converted model direction and edge into bettor-facing labels:
  - PASS
  - LEAN OVER / UNDER
  - BET OVER / UNDER
  - STRONG BET OVER / UNDER
- Added recommendation score, betting confidence, stars, selection, and actionable status.
- Added a complete `betting_recommendation` payload to serialized totals output.
- Integrated recommendations into `TotalsProjection`.
- Preserved the existing projection, bullpen, park, market, and market-edge layers.

## Recommendation thresholds

- Lean edge: 0.40 runs
- Bet edge: 0.75 runs
- Strong-bet edge: 1.25 runs

Recommendation labels also require minimum composite recommendation scores.

## Score inputs

The recommendation score currently combines:

- Model-versus-market edge
- Model confidence
- Data quality
- Bullpen confidence
- Market quality and freshness

## Validation

Validation completed with:

- Python compilation checks
- `git diff --check`
- Full MLB card build
- Fifteen-game recommendation review

Observed distribution:

- 5 LEAN OVER
- 3 BET OVER
- 2 STRONG BET OVER
- 2 STRONG BET UNDER
- 3 PASS

The output avoided recommending every game and showed sensible progression from PASS to LEAN, BET, and STRONG BET as edge and score increased.

## Known follow-up

Model confidence and recommendation attractiveness are conceptually different:

- Model confidence answers: ?How trustworthy is today's projection??
- Recommendation score answers: ?How attractive is this wager??

They should eventually be represented as separate bettor-facing fields.

## Future delivery

A future deployment should run SharpStack automatically each day on the Proxmox host and eventually publish results through a Discord application.
