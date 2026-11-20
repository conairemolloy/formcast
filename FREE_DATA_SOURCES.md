# FormCast — Free Data Sources & Expansion Plan

*Research sweep, 20 Nov 2026. A reference for expanding FormCast on free data only — both new market coverage and new model signal. Pairs with the Odds API multi-market recon (see ROADMAP queue c).*

> **Headline:** the biggest free wins are not new data feeds — they are using data we already have better. Market odds as a model feature, and corners-as-a-goals-signal, are both free, already on disk, and higher-value than chasing paid market coverage. A revived xG source is the third free win.

## 1. Highest-value free move: market odds as a model feature
Bookmaker odds are the hardest single predictor to beat; odds-inclusive models generally win on accuracy (ML for Soccer Match Result Prediction, arXiv 2403.07669). We already pull live odds AND hold football-data.co.uk historical Bet365+Pinnacle CLOSING odds back to 2005/06 — both free. Feeding de-margined implied probabilities into the ensemble is the top free "beat Elo" lever; the data is already on disk.
- CAVEAT: keep an odds-FREE model variant for the value screen. Including a book's own odds as a feature is circular when the goal is beating that book. Design the feature pipeline so odds features can be switched off for the value-screen variant.
- De-margin first (raw implied probs sum to >1). Prefer closing odds (B365C*/PC*).

## 2. Free data we already have but under-use
### football-data.co.uk (already in pipeline, free, no key)
Columns: results + HT, corners (HC/AC), cards (HY/AY, HR/AR), shots (HS/AS), shots on target (HST/AST), referee, odds from 10+ books incl. Bet365 + Pinnacle opening AND closing, Asian handicap, O/U 2.5. 22+ divisions; results from 1993/94, stats+odds from 2000/01, closing odds + AH from 2005/06. CSV, no API, free.
- Lever: CORNERS AS A GOALS SIGNAL — literature (Wheatcroft) finds shots+corners beat raw goals for O/U 2.5 forecasting. Already ingested historically; free to add to the goals model.
- Closing odds + O/U + AH odds present historically = free backtest data before any Odds API spend.
### xG — our feed died; free replacement exists
- Understat (old source) confirmed down for everyone since ~Nov 2026. Correctness run already made it fail loudly.
- xgstat.com — live free replacement; EPL/La Liga/Serie A/Bundesliga/Ligue 1/Championship (6 leagues). Website only, no API (scrape), no account. Its xG differs from Understat's — don't mix series. Check robots.txt/terms.
- FBref — LOST its Opta licence Jan 2026; historical archive only now.
- StatsBomb open data — genuinely free (non-commercial + attribution) but domestic coverage patchy (~418 PL matches, mostly 2015/16). Research/validation, not a live feed.

## 3. Market coverage — the paid reality (NOT paying for)
From the Odds API recon: Goals O/U fits free tier; BTTS needs $30/mo 20K plan; corners EPL-only+thin; cards EPL-only. Free alternatives for blocked markets — none is good:
- Betfair Exchange — LIVE key is a £499 one-off fee (free key is delayed/dev-only). NOT cheap; the $30/mo Odds API plan is far cheaper.
- Scraper-based "free" odds — grey-area vs terms, unreliable, not a basis for a trust/data product. Avoid.
Conclusion: no good free LIVE source for corners/cards/BTTS odds. The free path is model-side, not buying coverage. When coverage is worth paying for, the $30/mo Odds API 20K plan is the cheapest honest route.

## 4. Other free signal sources (lower priority)
- Transfermarkt — the one free injury source + squad market values (squad-strength proxy). Scrape; check terms. Injuries/lineups are a known model gap.
- Lineups — no clean free feed; football-data.org + some unofficial club/league APIs carry them but are undocumented.
- ESPN public API, OpenFootball/jokecamp GitHub, Kaggle — free historical results/fixtures; many Kaggle sets re-export FBref/Understat (same restrictions). Backfill, not live.

## 5. Licensing note (matters for the data-business vision)
Several free sources are non-commercial / Opta-restricted (StatsBomb, Understat/xgstat scrapes, FBref). The sell-the-signal vision makes those a real constraint later. Keep per-feature provenance so a future commercial audit can tell which signals are safe to resell. (ROADMAP already has a data-source commercial licensing audit launch requirement.)

## 6. Prioritised free-expansion plan
Tier 1 (free, high value, data already on disk):
1. Market odds as a model feature (de-margined implied probs; closing odds historical, live odds at prediction time). Keep an odds-free variant for the value screen.
2. Corners (and shots) as a goals-model signal — already ingested historically.
Tier 2 (free, moderate effort):
3. Revive xG from xgstat.com (scrape, 6 leagues incl. Championship) to replace dead Understat — or use football-data.co.uk shots as an xG proxy.
4. Goals O/U value screening on the Odds API free tier (recon Stage 1): add `totals`, the 5 missing leagues, `regions=uk`.
Tier 3 (free, lower value / higher friction):
5. Transfermarkt injuries + squad values (scrape).
6. StatsBomb open data for validation/research.
Explicitly parked (not free): Betfair Exchange (£499); BTTS/corners/cards live pricing ($30/mo plan; deferred per stay-free decision).

## Sources
- ML for Soccer Match Result Prediction (arXiv 2403.07669)
- football-data.co.uk data notes
- Betfair API costs (developer.betfair.com)
- xgstat.com (Understat alternative)
- Where to find football data in 2026 (Liam Henshaw)
- Every Free Public Soccer Data Source, Ranked (SoccerAnalytics)
