# SharpStack Roadmap

## Phase 1 — Foundation ✅
Status: Complete

Built:
- Engine entry point
- Config
- Provider factory
- Pipeline
- Console report
- Logger/history
- Game object
- Team object
- Odds object
- ModelResult object
- Edge calculator
- Recommendation engine
- Calculator framework
- Mock KBO model
- Mock odds provider

Core flow:

Provider
→ Games
→ Odds
→ Model
→ Calculators
→ Edge
→ Recommendation
→ Report
→ History

---

## Phase 2 — Real Baseball Intelligence
Status: Next

Goal:
Replace fake model inputs with real baseball signals.

Target calculators:
- Starting pitching
- Offense
- Bullpen
- Recent form
- Home field
- Market movement

Definition of Done:
SharpStack produces a KBO card where at least one recommendation is based on real data instead of mock index-based scoring.

---

## Phase 3 — Real Odds
Status: Upcoming

Goal:
Replace mock odds with actual sportsbook odds.

Target:
- Moneyline first
- Run line later
- Totals later

Definition of Done:
SharpStack displays real odds, real book probability, model probability, edge, and recommendation.

---

## Phase 4 — Picks / Multiple Markets
Status: Upcoming

Goal:
One game can generate multiple picks.

Examples:
- Moneyline
- Run line
- Total
- Team total
- First five
- Props

Definition of Done:
SharpStack ranks all picks by edge, not just games.

---

## Phase 5 — Portability / GitHub
Status: Backlog

Goal:
Move project into GitHub and make it portable across Windows desktop and Mac VM.

Tasks:
- Install Git
- Create GitHub repo
- Add .gitignore
- Add requirements.txt
- Commit initial foundation
- Clone to Mac VM

---

## Phase 6 — Web Front End
Status: Future

Goal:
Expose SharpStack output in a browser.

Likely path:
1. Export JSON
2. Build simple local web page
3. Add Flask/FastAPI
4. Optional dashboard UI

---

## Guiding Rule

Every new sprint should answer:

"Does this make SharpStack better at making betting decisions?"

If no, backlog it.

If yes, build it.