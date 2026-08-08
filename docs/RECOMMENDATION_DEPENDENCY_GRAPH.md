# Recommendation Dependency Graph

Sprint 84.2 traces the MLB moneyline recommendation authority path only. No
code, thresholds, formulas, UI, persistence, data, or migrations were changed.

## Graph

```text
Raw MLB inputs
    |
    |-- team offense profile
    |-- probable starter profile
    |-- bullpen profile
    |-- home/away context
    |-- First 5 model output
    |-- Bomb Lab output
    |-- park/weather/context
    |
    v
SharpScore team scores
    |
    |-- selected_score
    |-- opponent_score
    |-- score_diff
    |
    +-----------------------------+
    |                             |
    v                             v
Model Win Strength           Model Confidence
50 + score_diff * 0.75       45 + score_diff * 1.1
                              + data completeness
                              + starter certainty
    |                             |
    +-------------+---------------+
                  |
                  v
MLB Recommendation Tier
requires both strength and confidence thresholds
                  |
                  v
Decision Builder / Hammer context
    |
    |-- MLB model strength
    |-- First 5 score
    |-- Bomb score
    |-- starter score
    |-- offense score
    |-- bullpen score
    |-- park/weather
    |-- sample confidence
    |-- module agreement / contradictions
    |
    v
Displayed recommendation + advisory Hammer confirmation
```

## Arrow Analysis

| Arrow | Information added | Classification |
| --- | --- | --- |
| Raw stats -> offense score | Team offense profile is normalized into a bounded component. | NEW INFORMATION at this stage |
| Raw stats -> starter score | Probable starter metrics are normalized into a bounded component. | NEW INFORMATION at this stage |
| Raw stats -> bullpen score | Bullpen metrics are normalized into a bounded component. | NEW INFORMATION at this stage |
| Home/away -> home-field score | Home side receives contextual component. | NEW INFORMATION at this stage |
| Component scores -> SharpScore | Offense, starter, bullpen, and home field are weighted into team totals. | DERIVED INFORMATION |
| SharpScore -> selected side | Higher team score determines winner-first selection. | DERIVED INFORMATION |
| SharpScore gap -> Model Win Strength | Score gap is linearly transformed: `50 + diff * 0.75`, clamped `40..70`. | FULLY DERIVED INFORMATION |
| SharpScore gap -> Model Confidence | Score gap is reused as matchup strength, then data completeness and starter certainty are added. | MOSTLY DERIVED INFORMATION |
| Strength + confidence -> tier | Threshold lookup only; no new evidence. | FULLY DERIVED INFORMATION |
| SharpScore/model outputs -> Hammer | Reuses model strength and component scores, then adds First 5, Bomb, park/weather, sample confidence, agreement, contradiction penalties. | MIXED: NEW + DUPLICATED INFORMATION |
| Tier + Hammer -> displayed decision | MLB model recommendation remains authority; Hammer is advisory context. | DERIVED INFORMATION |

## Stage Inventory

| Stage | Inputs consumed | Outputs produced | Information classification |
| --- | --- | --- | --- |
| SharpScore | offense, starter, bullpen, home field | selected/opponent component scores, team totals, score gap, side | DERIVED from raw components |
| Model Win Strength | selected score, opponent score | bounded strength/probability alias | FULLY DERIVED |
| Model Confidence | score gap, starter data availability, offense data availability, unknown-starter count | numeric model confidence, confidence breakdown | MOSTLY DERIVED |
| Recommendation Tier | model win strength, model confidence | PASS/LEAN/PLAYABLE/STRONG/CHEEK | FULLY DERIVED |
| Hammer | model strength, First 5, Bomb, starter, offense, bullpen, park, weather, sample confidence, agreement, contradictions | Hammer score, Hammer tier, Hammer confidence label | MIXED; partially new, partially duplicated |
| Recommendation Authority | model recommendation from tier | final MLB moneyline recommendation | FULLY DERIVED |

## Key Dependency Finding

The official MLB moneyline recommendation is not gated by independent evidence
after SharpScore. It is a thresholded restatement of SharpScore separation plus
data availability/starter certainty. Hammer adds some outside context, but it
does not own official MLB moneyline authority and still reuses SharpScore-derived
signals.
