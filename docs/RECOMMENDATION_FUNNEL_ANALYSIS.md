# Recommendation Funnel Analysis

Sprint 84.0 traced the available current MLB slate through the moneyline
recommendation funnel. This was read-only analysis using local artifacts:

- `output/cards/mlb_card.json`, generated `2026-08-05T02:49:50+00:00`
- `output/cards/decision_card.json`, generated `2026-08-05T03:53:49+00:00`

## Funnel

```text
15 MLB games
  -> 15 winner-first selections available
  -> 11 clear LEAN model strength and confidence gates
  -> 0 clear PLAYABLE model strength and confidence gates
  -> 0 clear STRONG PLAY model strength and confidence gates
  -> 0 clear CHEEK RIPPER model strength and confidence gates

Hammer advisory:
  -> 7 WATCH
  -> 0 LEAN
  -> 0 BET
  -> 0 HAMMER
```

Official MLB moneyline recommendation authority is model tier, not Hammer.
Hammer is included here because product surfaces expose it and it can add
perceived confirmation pressure.

## Tier Gates

Current MLB moneyline thresholds:

| Tier | Model win strength | Model confidence |
| --- | ---: | ---: |
| CHEEK RIPPER | `>= 63.0` | `>= 85.0` |
| STRONG PLAY | `>= 59.0` | `>= 78.0` |
| PLAYABLE | `>= 56.5` | `>= 74.0` |
| LEAN | `>= 52.0` | `>= 65.0` |

Current slate maxima:

| Metric | Maximum |
| --- | ---: |
| Model win strength | 56.0 |
| Model confidence | 70.9 |
| Hammer score | 62.8 |

Therefore no game could reach PLAYABLE or higher under current thresholds.

## Per-Game Gate Analysis

| Matchup | Selection | SharpScore separation | Model strength | Model confidence | Hammer | Hammer tier | Final recommendation | Gate result |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Los Angeles Angels @ Baltimore Orioles | Baltimore Orioles | 7.8 | 55.9 | 70.7 | 59.4 | WATCH | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| New York Mets @ Cleveland Guardians | New York Mets | 1.1 | 50.8 | 63.4 | 50.4 | PASS | PASS | Failed LEAN: strength `<52.0`, confidence `<65.0` |
| Athletics @ Cincinnati Reds | Athletics | 3.1 | 52.3 | 65.6 | 54.3 | PASS | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Washington Nationals @ Philadelphia Phillies | Philadelphia Phillies | 0.2 | 50.2 | 62.4 | 53.1 | PASS | PASS | Failed LEAN: strength `<52.0`, confidence `<65.0` |
| St. Louis Cardinals @ New York Yankees | New York Yankees | 8.0 | 56.0 | 70.9 | 58.3 | WATCH | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Chicago White Sox @ Boston Red Sox | Chicago White Sox | 3.3 | 52.5 | 65.8 | 55.5 | PASS | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Miami Marlins @ Atlanta Braves | Atlanta Braves | 4.6 | 53.5 | 67.2 | 57.3 | WATCH | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Minnesota Twins @ Kansas City Royals | Minnesota Twins | 5.8 | 54.4 | 68.5 | 54.6 | PASS | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Pittsburgh Pirates @ Milwaukee Brewers | Milwaukee Brewers | 2.5 | 51.9 | 64.9 | 57.5 | WATCH | PASS | Failed LEAN: strength `<52.0`, confidence `<65.0` |
| Los Angeles Dodgers @ Chicago Cubs | Los Angeles Dodgers | 6.7 | 55.0 | 69.5 | 60.0 | WATCH | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| San Francisco Giants @ Texas Rangers | Texas Rangers | 1.1 | 50.8 | 63.4 | 47.8 | PASS | PASS | Failed LEAN: strength `<52.0`, confidence `<65.0` |
| Toronto Blue Jays @ Houston Astros | Houston Astros | 6.6 | 54.9 | 69.4 | 55.2 | PASS | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Tampa Bay Rays @ Colorado Rockies | Colorado Rockies | 4.2 | 53.2 | 66.8 | 62.8 | WATCH | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| San Diego Padres @ Arizona Diamondbacks | Arizona Diamondbacks | 4.0 | 53.0 | 66.5 | 58.7 | WATCH | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |
| Detroit Tigers @ Seattle Mariners | Detroit Tigers | 5.2 | 53.9 | 67.9 | 55.1 | PASS | LEAN | Stopped at LEAN: strength `<56.5`, confidence `<74.0` |

## Threshold Pressure Ranking

| Filter | Rejected games | Notes |
| --- | ---: | --- |
| PLAYABLE model strength | 15 / 15 | No game reached `56.5`. |
| PLAYABLE model confidence | 15 / 15 | No game reached `74.0`. |
| Hammer LEAN/BET/HAMMER advisory tier | 15 / 15 | No game reached Hammer LEAN, BET, or HAMMER. Not official MLB authority. |
| LEAN model strength | 4 / 15 | Same four games failed confidence too. |
| LEAN model confidence | 4 / 15 | Same four games failed strength too. |

## Funnel Finding

Recommendations disappear at the PLAYABLE gate. On this slate, both PLAYABLE
requirements fail for every game. The two requirements are not independent:
model confidence includes the same score-separation signal that drives model
win strength.
