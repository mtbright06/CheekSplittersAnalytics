# Sprint 55: Better Pitching Metrics Evaluation

**Status:** Complete research. No production metric integration approved.

## Executive Recommendation

Do not add FIP, xFIP, xERA, or SIERA to the production MLB pitcher model now.
FIP is the only candidate that can be calculated faithfully from the existing
MLB starter profile after adding a season-specific league constant. It should
remain a future, historically validated diagnostic candidate rather than an
additional scoring input. xFIP, xERA, and SIERA require data or definitions not
present in the canonical profile, and their public sources do not currently
provide an approved production-data contract.

## Current Data Inventory

`engine/mlb/pitchers.py` already aggregates starter-only innings, strikeouts,
walks, hit batters, home runs, batters faced, ground outs, and air outs. It does
not expose fly balls allowed, complete batted-ball classifications, Statcast
expected outcomes, or a league-specific FIP constant. The First Five provider
has a separate season aggregate path and does not currently expose HBP or
starter-only raw event counts.

## Metric Comparison

| Metric | Definition and overlap | Existing derivation | Coverage and source conclusion | Decision |
|---|---|---|---|---|
| FIP | ERA estimator from HR, BB, HBP, K, IP. It overlaps directly with current HR/9, K/9, and BB/9. | Yes, after obtaining the season league FIP constant. | MLB raw counts support current-season calculation. Historical and league-total endpoint behavior require a separate validation. | Defer. |
| xFIP | FIP replacing actual HR with fly balls times league HR/FB. It overlaps with FIP and HR/9. | No. `airOuts` is not fly balls allowed. | FanGraphs documents xFIP; its historical data begins in 2002. No approved production feed is available. | Defer. |
| xERA | MLB Statcast xwOBA translated to the ERA scale. It overlaps with ERA/WHIP results but adds contact-quality information. | No. It is a Statcast expected-outcome metric, not derivable from current counts. | Baseball Savant exposes it in public search/leaderboards. Full Statcast coverage begins in 2015; update SLA and production rights are not established. | Defer. |
| SIERA | Nonlinear ERA estimator using strikeout, walk, and batted-ball interactions. It overlaps with K/9, BB/9, HR/9, and ground/air inputs. | No faithful derivation. Current ground/air outs are incomplete batted-ball rates. | FanGraphs defines and publishes it, but no approved production source or full required inputs exist. | Reject for the current model architecture. |

## Source, Licensing, and Cost Findings

- The existing MLB Stats API supplies the raw player events required for FIP,
  with no extra per-pitcher request if starter aggregation is extended. It does
  not provide a documented, versioned advanced-metric contract in this repo.
- Baseball Savant is MLB's public Statcast clearinghouse and exposes xERA in its
  search and custom leaderboard. Its public interface has no documented SLA,
  and MLB website terms do not establish production redistribution rights.
- FanGraphs supplies the canonical public definitions and leaderboards for FIP,
  xFIP, and SIERA, but its terms prohibit commercial exploitation and access
  outside its provided interface without authorization. Do not scrape it for
  production use.
- `pybaseball` is already installed and can retrieve Statcast/FanGraphs data,
  but it is a scraper/convenience library, not a source license or production
  availability guarantee.
- FIP is low additional API cost after a cached league-season aggregate. xFIP
  and SIERA need broader batted-ball aggregation. xERA needs Statcast
  leaderboard or pitch-level retrieval and is the highest request/latency risk.

Sources reviewed: [MLB Stats API terms](https://inside.mlb.com/UserRegistrationForm/?GROUP=StatsAPI), [MLB Statcast search](https://baseballsavant.mlb.com/en/statcast_search), [MLB Statcast-era definition](https://www.mlb.com/glossary/miscellaneous/statcast-era), [FanGraphs FIP](https://library.fangraphs.com/pitching/fip/), [FanGraphs xFIP](https://library.fangraphs.com/pitching/xfip/), [FanGraphs SIERA](https://library.fangraphs.com/pitching/siera/), [FanGraphs terms](https://www.fangraphs.com/about/terms-of-service), and [pybaseball documentation](https://github.com/jldbc/pybaseball/blob/master/README.md).

## Coverage and Missingness

- FIP cannot be calculated without valid IP and the four event counts. A
  missing HBP value must be treated as unavailable, not silently zero, unless
  provider semantics explicitly guarantee zero.
- xFIP requires fly balls and a season-specific league HR/FB rate. Current
  `airOuts` cannot substitute for fly balls.
- xERA is limited to the Statcast era (all MLB parks from 2015) and can be
  incomplete for non-tracked batted balls. It also needs explicit source and
  freshness metadata.
- SIERA needs complete rate inputs and an exact, versioned formula. Approximating
  it from the current ground/air ratio would create an untraceable new model.

## Stabilization and Double Counting

The 50-IP stabilization helper cannot simply be applied as an additional layer
to every advanced metric. FIP is built from the same HR, walk, and strikeout
signals already scored; xFIP already regresses home-run outcomes; SIERA embeds
interactions among current skills; and xERA is itself an expected-outcome
estimate. Adding any of them as another weighted component would double-count
pitcher ability and potentially double-regress small samples.

A future experiment must calculate each candidate from raw starter-only counts,
define metric-specific reliability treatment, and compare one constrained
alternative against the current inputs. It must not add the metric alongside
its component skills without historical evidence.

## Market Assessment

| Market | Research value | Rationale |
|---|---|---|
| Moneyline | Moderate | Better starter skill estimates may improve matchup quality, but offense, bullpen, and market inputs dilute standalone pitcher effects. |
| Totals | Moderate to high | FIP/xFIP/xERA may help separate defense, sequencing, and contact quality from observed runs, but existing totals already use ERA, WHIP, and HR/9. |
| First Five | Highest | Starter influence is concentrated before bullpen effects. Any experiment must first align First Five with starter-only source data. |

## Future Integration Gate

1. Obtain written approval or a licensed API/data contract for any sourced
   advanced metric.
2. Build a cached, versioned league-context provider and historical starter-only
   dataset.
3. Test FIP first as a diagnostic or replacement candidate, not an additive
   score.
4. Measure incremental out-of-sample value separately for moneyline, totals,
   and First Five.
5. Require explicit source quality, missingness, and metric-specific
   stabilization rules before any production integration.
