# KBO Baseline V1.0

KBO Baseline V1.0 is a winner-first, model-only moneyline baseline. Market
price, edge, EV, implied probability, sportsbook availability, and sportsbook
identity are display/provenance inputs only and do not affect recommendation
authority.

## Official Production Formula

The model produces one signed matchup score:

```text
weighted_score =
    starter_score * 0.550
  + offense_score * 0.300
  + bullpen_score * 0.125
  + recent_form_score * 0.025

model_strength = 50 + (weighted_score * 8)
```

Positive `weighted_score` selects the away team. Negative `weighted_score`
selects the home team. Zero is neutral/no selection.

## Active Components

| Component | Weight | Source | Formula summary |
| --- | ---: | --- | --- |
| Starter | 55.0% | MyKBOStats game starter pages and pitcher profiles | ERA vs dynamic league starter ERA, WHIP, K-BB, HR/9, innings stabilizer, bounded rest/workload context |
| Offense | 30.0% | MyKBOStats team splits | Team season R/G vs dynamic league R/G |
| Bullpen | 12.5% | MyKBOStats team splits `ERA_{RP}` | Team relief ERA vs dynamic league relief ERA |
| Recent Form | 2.5% | MyKBOStats team splits Last 10G | Last 10 R/G vs season R/G, capped at 25% authority shrinkage |

## Recommendation Ladder

| Model Strength | Official Recommendation |
| ---: | --- |
| `< 52.0` | NO PLAY |
| `52.0-54.9` | LEAN |
| `55.0-56.4` | PLAYABLE |
| `56.5-56.9` | PLAY |
| `>= 57.0` | STRONG PLAY |

## Reliability

Reliability answers one question: how much should the current model inputs be
trusted?

Reliability is independent of model strength. Stronger team separation does not
raise reliability.

Current reliability deductions:

| Condition | Deduction |
| --- | ---: |
| Missing or unconfirmed starter identity | `-20` per side |
| Starter loaded without trusted profile data | `-8` per side |
| Missing required starter ERA or WHIP | `-12` per side |
| No prior starts | `-6` per side |
| Limited starting role | `-3` per side |
| Missing team offense R/G | `-10` per side |
| Static offense fallback | `-5` per side |
| Missing bullpen ERA or league bullpen ERA | `-6` per side |
| Missing recent-form R/G, season R/G, or recent games | `-3` per side |
| Missing game URL / schedule mapping | `-5` game-level |

## Fallbacks And Limitations

Live team splits are authoritative when available. Static team offense fallback
is explicit, carries a reliability penalty, and does not provide bullpen or
recent-form strength. Missing component inputs score neutral and reduce
reliability where the component is active.

Rejected authority inputs for this baseline: park R/G, raw home/away R/G, runs
allowed, Last 10 runs allowed, run differential, W/L records, streaks,
player-level OPS/OBP/SLG aggregation, pitcher handedness, pitch count, and
bullpen availability/workload.

Operational checks before relying on a new active slate: confirm schedule rows
map to the correct game pages, starters map to distinct profile pages, pitcher
game logs expose prior-start context, team splits load all ten teams, and market
enrichment remains downstream of the official model recommendation.
