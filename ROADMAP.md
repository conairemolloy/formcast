# FormCast — Sports Prediction Platform
### Elo + Glicko-2 + Dixon-Coles + BTL + XGBoost + Feedforward NN + LSTM → stacked ensemble (78 features)
*Last updated: Nov 12 2026. Completed work and superseded decisions are in [ROADMAP_HISTORY.md](ROADMAP_HISTORY.md).*

---

## Current State & Honest Claims (Nov 12 2026)
> **Single source of truth.** Every other section (and the site copy) defers to this one. If a number anywhere else disagrees, this section wins; fix the other place.

**What production does**
- Weekly pipeline (GitHub Actions, Monday 6am UTC) re-ingests data and retrains every model (Elo, DC, BTL, XGBoost + meta-learner + draw classifier, NN, LSTM, the four market models).
- `predict_upcoming` writes 78-feature ensemble probabilities, keyed by `match_id`, to `upcoming_predictions.csv`. CI now runs `publish_predictions` **after** `predict_upcoming`, so publish reads this week's ensemble (9cb6d15).
- `publish_predictions` logs the **ensemble** probabilities tagged `source=ensemble`, falling back to Elo (`source=elo`) only for unresolved/international/missing/stale fixtures (dbad933). Hashes are unchanged; `source` is not part of the hash.
  - ⚠️ **Not yet visible in the data:** the on-disk `prediction_log.csv` does not have the `source` column yet. It is added at the next publish (~Nov 14, when fixtures re-enter the 7-day window). **Every logged row to date is Elo.**
- Settlement and the odds-join share one `FixtureMatcher` (`scripts/fixture_matching.py`): **608/608** settled predictions now have odds attached (7a35e7d).
- Live value bets are 100% from the ensemble, 108/108 join verified (these come from fetch_live_odds → upcoming_predictions.csv, a DIFFERENT pipeline from the logged predictions above — which is why the logged record is still Elo while the live value-bet feed is already ensemble).
- The live endpoint (`api/routes/live.py` `_prematch_probs`) still shows **plain Elo**, with broken name resolution (~15 of 144 teams defaulting to 1500; scope of "144" per the Nov 12 session, not recounted). See queue (e).

**Current numbers.** Each is labelled as metric, then sample, then date.

| Claim | Metric | Sample | As of |
|---|---|---|---|
| **1,110** published / **608** settled | Predictions published before kickoff, SHA-256 hashed / settled in tracked leagues | `prediction_log.csv` (617 tracked, 493 not tracked) | Nov 12 2026 |
| **64.4%** | Ensemble hit rate, **non-draw** | 2026-27 season backtest, n=913 | Nov 2026 |
| **~67.0%** | Ensemble walk-forward hit rate, **non-draw** (Elo baseline 66.7%) | 2020-2024, ~20k matches | Jul 2026 |
| **49.0%** | Ensemble hit rate, **3-way** (H/D/A) | Ensemble holdout | Jul 2026 |
| **ECE 0.0127** | Ensemble calibration error (uncalibrated, Platt retired) | Walk-forward | Jul 2026 |
| **50.3%** | **Elo-era** live logged record, **3-way incl. draws** (306/608) | Logged predictions to Nov 12 | Nov 12 2026. Superseded once ensemble rows accumulate |
| **−7% ROI** | **Elo-era 1X2 value bets only** (45 bets, flat stake) | Logged predictions | Nov 2026. **Not** a verdict on the ensemble |

**Data counts (recounted Nov 12 2026 from `data/processed/`)**
- **Club matches:** `results.csv` has 128,592 rows, 1993-07-23 → 2026-11-09, including 1,212 rows from 2026-27. It contains 1,222 duplicate (date, home, away) keys, so there are ~127,370 unique matches; the dedup fix is in the backlog. *The old "128,797" figure matches no current count. Retire it.*
- **Competitions:** **11 club leagues**: EPL, Championship, La Liga, Segunda, Serie A, Serie B, Bundesliga, Bundesliga 2, Ligue 1, Ligue 2, Scottish Prem. *"14 competitions" is unsupported. Retire it.*
- **Teams:** 446 club teams (all seasons, `results.csv` / `elo_ratings.csv`); 210 club teams in 2026-27; 337 national teams (`international_elo_ratings.csv`; earlier docs said 336); stadiums 442/444. *"500+ teams" is unsupported. Retire it.*
- **International results:** 49,425 matches (1872-2026).
- **Odds history:** `odds_history.csv` has 227,337 snapshot rows, 2026-07-20 → 2026-11-12. These are pre-match snapshots, not closing odds.

**ALLOWED public claims**
- The verifiable record: "1,110+ predictions published before kickoff, timestamped + SHA-256 hashed; 608 settled", always date-stamped.
- Transparency itself: every call logged, win or lose.
- A hit rate **only if** fully labelled (e.g. "64.4%, 2026-27 season, non-draw, n=913").

**BANNED**
- An ROI headline of any kind, until it's proven on the ensemble against real closing odds.
- **"CLV".** Our metric is log(model prob / book prob), which is positive by construction. It is not closing-line value, and the "closing" odds were Bet365 *pre-match* (B365H/D/A).
- **68.7%** (old optimised-Elo non-draw figure).
- **+8.4%** (placeholder in the v0 landing mockup).
- **+19% / +18.4%** "CLV".
- Any bare, unlabelled hit rate.
- *Purged from the live frontend Nov 12 2026: Landing, Dashboard, HowItWorks, BacktestReport. Remaining stale copy is listed in queue (b).*

**UNKNOWNS**
- **Ensemble live edge:** unmeasured. Measurable once `source=ensemble` rows settle (~Nov 14 onwards).
- **Multi-market edge** (corners/cards/goals/BTTS): entirely unmeasured. This is plausibly where the edge lives; see queue (c).

---

## Active Priority Queue
> One ordered list. Build order: **remodel → multi-market → Today's Tips**. Model/data fixes, measurement and infra run alongside.

### (a) Decisions pending
- [ ] **Brand name: PARKED, not blocking.** Keep "FormCast" for all design work now. Revisit before public launch / custom-domain purchase. Criteria: conveys trust + multi-sport + quant/analytics positioning (not "tipster"); clean available .com/.io; short; not confusable with betting brands. "Form" is football/racing-specific.
- [ ] **Re-decide public hit-rate framing** once `source=ensemble` rows accumulate (a few hundred settled). Until then: record + transparency only (see Current State). The superseded Nov 2026 decision record is in history.

### (b) Site remodel: NOW
Executes against the **Design Constitution** below. It's design work only and doesn't touch the model.
- [ ] **Rewrite `frontend/DESIGN.md`.** It exists, but describes the old emerald system. Rewrite it around the locked direction: dark warm near-black, warm orange/coral accent (pull the exact hex from the v0 code), Fraunces-style serif + grotesk, type/spacing scale. Every later frontend task references it. 25 component files still use `emerald-*`.
- [ ] **Integrate the approved v0 landing page** into the repo (replaces the old `Landing.jsx`). Wire real auth/signup into the CTAs. Feed REAL data to the Today's Tips teaser and the animated public ledger (SHA-256 log). **Do not port the +8.4% placeholder**: use the record stats. Add the founder photo/bio. Closed front door: logged-out nav = About · How it works · Log in · Sign up free.
- [ ] **About / founder bio section.** The trust differentiator vs anonymous tipsters. Currently placeholders.
- [ ] **Public proof page** (turn the Prediction Log into it). It works but opens into a ~1,110-row table: a data dump. LEAD with the honest headline (verifiable record + labelled accuracy, per Current State) + recent settled results; put the full log behind "View full log". KEEP the "Cryptographically verified · SHA-256 hashed" framing, the "How does verification work?" link and the clickable hashes. Show a `source` (ensemble/Elo) label per row once the column exists.
- [ ] **Purge the remaining stale stats in the frontend:**
  - `BacktestReport.jsx` "What the numbers mean" box: hardcoded "Hit rate (66.9%)". Read it from the API or label it; the page's own stat card shows the API value.
  - "0.156" Brier (`Landing.jsx` STATS, `Dashboard.jsx` MODEL_STATS). This is the old Elo non-draw Brier. Relabel as Elo or replace.
  - "128,797 matches" / "14 competitions" / "500+ teams" (`Landing.jsx` hero, use-case copy and STATS; `Dashboard.jsx`). Use the recounted figures from Current State.
  - "48 engineered features" (`HowItWorks.jsx` XGBoost/NN cards). Now 78.
  - Hardcoded "1,110+ / 608" (Landing/Dashboard). Replace with live counts (next item).
- [ ] **Add `/api/predictions/summary`.** A lightweight `{total, tracked, settled, pending, not_tracked}` so landing/dashboard/proof page show live counts. `/api/predictions/log` returns all rows.
- [ ] **Retire `/api/backtest/clv`** (backend). The frontend no longer calls it (Nov 12 purge). Remove it or rename the metric to what it is (model-vs-book log ratio) for internal use only.
- [ ] Component library audit: standardise cards, badges, tables and filters; single icon library (lucide-react).
- [ ] Loading skeletons instead of bare "Loading…" spinners; designed empty states.
- [ ] **Full site remodel — "bring it to life + findability" (Nov 2026 direction)** — the whole-site UX pass the Core Product Principle demands. GOALS: (1) users can actually FIND what they want — nav/IA restructured around what people come for, not a feature dump across 5 dropdowns; (2) every screen leads with ONE thing, progressive disclosure, kill flat lists (dashboard especially); (3) "bring it to life" — restrained, purposeful motion only (edge meter fill, numbers ticking, probability bars on load) — NOT decorative animation, which cuts against a trust/quant product; (4) consistency — replicate the Backtest page's honest plain-English framing and the Ratings/H2H visual quality across weaker pages; (5) DESIGN.md is OPEN TO REVISION to match current taste (clean/minimal/modern/restrained-motion) — treat as updatable, rewrite as output of the remodel. Precedes/absorbs the individual page-redesign items below. Mobile-first throughout.
- [ ] **Multi-sport framework (structural, build during remodel)** — design the nav, URL structure (/football/..., sport switcher), data shape and component props to ASSUME multiple sports from the start, even though only football ships. Football first, GAA/tennis/etc as visible "coming soon". Cheap now, expensive to retrofit. **USER SPORT-SELECTION (Nov 2026):** tips/value bets span multiple sports eventually, and users SELECT which sports they follow — sport-selection is a stored user preference that FILTERS their Today's Tips, feed, and (later) email digest. Captured at signup (see Signup & onboarding) and editable in settings; football is the only selectable sport at launch, others shown as "coming soon". Landing copy already frames it: "football now — more sports coming, pick the ones you follow." (Expands the existing "Multi-sport-ready navigation & IA" item below — see it for the journey/nav detail.)
- [ ] Everything-clickable rule + canonical Match Detail hub — HARD RULE: anything naming a match anywhere on the site (value bets list, dashboard fixtures, team profiles, results, accumulator legs) is a link to that match's full detail view. Build ONE canonical, excellent, SPORT-AGNOSTIC match detail page as the destination — designed once, works for any sport. Full progressive disclosure: seven-model contribution breakdown, H2H, form, xG, confidence band (prediction_uncertainty). Decide card→detail navigation in the Value Bets build even if the detail view ships slightly after, so it's not retrofitted. This is what makes the site feel whole rather than disconnected pages. (Merges the prior "Match detail view (card tap-through)" item.)
- [ ] International football hub (renamed from "World Cup Hub", Nov 2026) — EVERGREEN showcase for international football: World Cup, Euros, qualifiers, Nations League, friendlies — not time-locked to one tournament. Should make someone immediately understand what FormCast does for international football. Builds on the existing World Cup 2026 page/bracket work (see International section).
- [ ] Multi-sport-ready navigation & IA — even though only football ships now, design nav + URL structure to assume multiple sports (e.g. /football/value-bets not /value-bets; a sport switcher with football active and GAA/tennis/etc as visible "coming soon" siblings). Cheap to plan now, expensive to retrofit. The nav sells AND scales. JOURNEY: (1) PRIMARY JOURNEY: cold visitor sees a clear one-line promise ("Bets where the model disagrees with the bookmaker. Every result logged — win or lose.") + the proof stats allowed by Current State & Honest Claims (the verifiable record: predictions published before kickoff + settled, every one SHA-256 hashed + timestamped, verifiable; no ROI, CLV or bare hit-rate headline) + one CTA + a gated Today's Tips teaser ("sign up to unlock" — Today's Tips is free WITH AN ACCOUNT, not shown to anonymous visitors; it stays the daily hook/retention mechanic once signed up). (revised Nov 2026: free with signup, not anonymous — see Design Direction & Tooling) (2) NAV structured around the journey not features: Today's Tips · Track Record · How It Works · International · [account] — the nav sells (this is the LOGGED-IN nav; logged-out is the closed front door). (3) QUIET-DAY / OFF-SEASON HOME (next off-season: summer 2027): lead with Track Record + International football hub + Today's Tips + email capture; the empty state becomes the conversion funnel. (4) LOGGED-IN vs LOGGED-OUT states defined. Do this flow definition BEFORE the landing/dashboard/value-bets page redesigns so they serve it. (Merges the prior "Navigation & first-visit flow" item, which supersedes the Phase 7/9 "onboarding tour" items.)
- [ ] Signup & onboarding flow — minimal signup (email/password or Google, no long forms — every extra field loses users), then IMMEDIATE value (land on a dashboard with live Today's Tips, not an empty screen). During signup capture SPORT + TEAM preferences ("which sports do you follow?", "any teams?") — one light step that personalises dashboard, emails, and the Today's Tips feed from day one. Sport-selection is the stored preference that filters tips (see Multi-sport framework). Optional light guidance, NOT a forced multi-step tour (best onboarding is a product obvious enough to need almost none; a long tour is a band-aid for confusing UI). Supersedes the Phase 7/9 "onboarding tour" items.
- [ ] Peak-density design (big weekends / Champions League days) — design for high-volume days, not just quiet ones. On a big Prem Saturday or CL Tuesday there may be 8-12 value bets at once; group by matchday/competition, offer a "this weekend" view, so density never becomes an overwhelming wall. Ties to the "not overloaded with data" principle.
- [ ] Responsible gambling & compliance footer — UK betting-advice norms: 18+ notice, BeGambleAware/GamCare links, "past performance does not guarantee future results" disclaimer, clear "not financial advice" framing. Cheap to add, bad to miss pre-launch. Also review affiliate/advertising compliance if bookmaker links are used.
- **Trust signals** (built during the remodel; the proof page is above):
- [ ] Track record section on landing — show the verifiable record (published/settled, SHA-256 hashed) prominently as social proof — per Current State: no CLV, no ROI, no bare hit rate
- [ ] "Yesterday's Tips — results" — publicly show the previous day's ranked tips (led by the top tip) and how each settled. Closes the honesty loop visibly ("here's what we picked, here's what happened"). Strongest trust-building feature available; follows on from Today's Tips. Draws from the logged prediction record (win or lose, per positioning).
- [ ] Odds freshness / "price may have moved" indicator — value bets go stale as odds move, so show a small freshness signal on each pick ("odds checked 2h ago", or a subtle "price may have moved — verify at bookmaker" note). Protects trust and sets honest expectations. Minor build, meaningful for credibility. Ties to the live-odds refresh cadence (daily/near-real-time).
- [ ] Custom domain + Vercel config (~€12/yr; `formcast-blush.vercel.app` undermines premium positioning). Do it together with the brand-name decision in (a).

### (c) Multi-market value bets: NEXT
The product's real edge question. The four market models (corners, cards, BTTS, goals O/U) are built and retrain weekly, but have never been value-tested against bookmaker lines.
- [ ] Multi-market value bets (all markets, not just 1X2) — END-GOAL VISION: Today's Tips, Acca of the Day, and the value bets list surface edges across ALL modelled markets, not only match result. The four market models are built and live: corners, cards, BTTS, over/under goals. A day's Today's Tips ranks edge×confidence picks across ALL markets together — the lead tip some days a win pick, some days "over 9.5 corners", "under 2.5 goals", or "over 3.5 cards".

  **STEP 1 — RECON FIRST (small, cheap, gates everything):** Investigate The Odds API market coverage + cost for the leagues we model. Which markets are available: totals (goals), BTTS, corners lines, cards lines? What does each cost in API credits per call, and is coverage complete or patchy across EPL/Championship/La Liga/etc? Likely outcome: goals + BTTS well-covered and cheap; corners + cards more expensive or patchy — which would STAGE the rollout (do well-covered markets first). Do NOT build anything until this recon answers what's actually priceable.

  **STEP 2 — extend the value screener** (fetch_live_odds.py / value_betting.py, currently primarily 1X2) to compare each market model's output vs that market's bookmaker line, ranking all edges uniformly on one scale — for whichever markets STEP 1 confirms are viable.

  **STEP 3 — market-appropriate "why this bet"** reasoning (corners pick cites referee tendencies + team corner rates, not form/xG).

  **STEP 4 — display:** edge meter + card layout work identically across market types; build the Value Bets page / Today's Tips multi-market from the start so it's not redesigned later.

  SEQUENCING NOTE: this is a value-PIPELINE extension (backend) that Phase 6 then displays. Build the pipeline (steps 1-3) BEFORE the Value Bets page redesign, or the page gets rebuilt. This is a significant product build (~comparable to a chunk of the model work), not a display tweak — Phase 6 is now genuinely large by design.
- [ ] **Multi-market settlement.** Settlement must be provably correct for every market before any multi-market result is published. The SHA-256 log proves the prediction, not the settlement. Extend the shared `FixtureMatcher` and settle logic to corners/cards/goals/BTTS.

### (d) Today's Tips ranked-set hierarchy: AFTER multi-market
- [ ] Value Bets editorial hierarchy (Today's Tips) — **REVISED Nov 2026: "Bet of the Day" → "Today's Tips".** The daily hook is the full RANKED SET of today's value bets — "today's tips, ranked by edge" — not a single hero pick. It's still curated, not a flat list, and still LEADS with the strongest (anti-overwhelm principle: best first, full list below): (1) LEAD TIP — the top-ranked tip gets the most prominent card: full edge meter + plain-language "model sees X%, book implies Y%" + Kelly/book/odds row. (2) NEXT STRONGEST — the next 3-4 as compact edge-meter cards. (3) REST OF THE SET — the remaining ranked tips below ("View all N →"), filterable. Ranked by EDGE × CONFIDENCE, not raw edge (raw-edge sort surfaces noisy longshots — wrong thing to lead with; confidence-weighting protects trust positioning). Filtered to the sports the user follows (see Multi-sport framework → user sport-selection). All odds render in the user's chosen format (decimal/fractional/American) via the Tier 6 oddsFormat preference. FREEMIUM: Today's Tips is FREE WITH AN ACCOUNT — not visible to anonymous logged-out visitors (landing page shows a gated "sign up to unlock" teaser). It's the daily proof + marketing/screenshot asset + retention hook, behind the signup gate. The full ranked set stays FREE FOREVER — tips are never paywalled (see MONETISATION MODEL in v1.0 Launch Definition). Off-season: pulls from the International football hub so it's never empty. (Supersedes the singular "Bet of the Day" framing throughout.)
  - Note: MOBILE-FIRST — huge share of betting traffic is phone, in-the-moment. Edge-meter cards, the lead tip, the ranked list must work single-column at 375px, stacking cleanly. Build mobile-first, not desktop-retrofitted.
  - Note: DATA DEPENDENCY — "ranked by edge × confidence" requires per-bet confidence (the prediction_uncertainty metadata from Phase 2 Batch 3). Verify /api/markets exposes it before building the hero; if absent, surface it in the API first or compute a client-side proxy. Recon this before the Value Bets build.
  - Note: MULTI-SPORT SHAPE — Today's Tips is one ranked set across all the sports a user follows (filterable/groupable by sport), not a separate hero per sport. Retention mechanic: multi-sport bettor opens daily to see all their sports' tips, ranked, in one place. Football ships first; structure the data/component to accept a sport dimension from the start.
- [ ] **Emit `prediction_uncertainty` from `predict_upcoming.py`** (meta_proba is already computed). It's needed for edge × confidence ranking. The column exists in `value_bets.csv`; verify it reaches `/api/markets` and the live tips.
- [ ] "Why this bet?" plain-language transparency — every tip / value bet / acca leg explains ITSELF in plain English ("model rates Arsenal 53% vs bookmaker's 42% because of home record, recent xG, and opponent form"). Progressive disclosure applied to trust — this is what separates FormCast from anonymous tipsters. One tap deeper = the full seven-model breakdown.
- [ ] Acca of the Day — a curated daily accumulator (2-4 legs, model's best combined-value multi) as an editorial pick alongside Today's Tips. Accas are the most-screenshotted bet type in betting culture — high shareability, strong following-builder. Uses the EXISTING accumulator engine + correlation correction (Phase 4) — mostly surfacing built capability as a daily hero. FREEMIUM: PRO feature — acca builder + Acca of the Day are both in the Pro layer (see MONETISATION MODEL in v1.0 Launch Definition).
  - Note: CROSS-MARKET ACCAS — best multi is often a MIX across markets (e.g. Arsenal win + over 9.5 corners elsewhere + BTTS in a third). Accumulator engine (Phase 4) must select legs across all market types. CORRELATION CAVEAT (credibility landmine): same-match multi-market legs are correlated (team dominating → more corners AND more likely to win); an acca of "Liverpool win + Liverpool over 9.5 corners + Liverpool BTTS" looks like 3 legs of value but is ~1 correlated bet — combined odds badly overstate true edge. Sharp bettors (the best audience) spot naive correlated accas instantly and lose trust. Phase 4 correction handles same-league/same-day; same-match cross-market correlation is harder and MUST be respected — ideally accas avoid stacking correlated same-match legs unless correlation-adjusted. Correlation-awareness here is a credibility REQUIREMENT, not a nice-to-have.
- [ ] Shareable Today's Tips card image — auto-generated share image (Twitter/Telegram/social) of the day's top tips, since Today's Tips is the primary marketing asset. High-leverage for audience growth; build after the core hero ships. Full feature, not part of first Value Bets build.

### (e) Model / data fixes
- [ ] **One canonical team-name resolver.** The live endpoint's Elo name resolution is the **third** location of the same name bug (~15/144 teams default to 1500, e.g. Ath Bilbao priced at 6% to beat Espanyol). This makes `source=elo` fallback rows and displayed Elo unreliable. Unify on one resolver (single source of truth, like the feature pipeline and `FixtureMatcher`) instead of extending `_ODDS_TO_ELO`.
- [ ] **Unify the two Elo fallback formulas.** `fetch_live_odds` (HOME_ADV=50 + own draw formula) and `predict_upcoming` disagree.
- [ ] **Season-helper migration.** `predict_upcoming.py:162` `_current_season()` still uses `month >= 8`, while `api/app.py _season()` uses `month >= 7`. 2026-27 data starts 2026-07-31, so late-July matches get mislabelled. Migrate both to `scripts/season_utils.current_season()` in one change, then re-check season-filtered output.
- [ ] **~9 pending covered-league predictions + void rule** (608 of 617 tracked settle). Unresolved names: Stade Rennais FC 1901, CA Osasuna, Athletic Club, ES Troyes AC, Olympique Lyonnais, Angers SCO, Stade Brestois 29. Some are rescheduled matches: add a `void` status (bookmakers void bets not played within ~48-72h). These may be the same ~9 rows, so check before fixing twice.
- [ ] **Stale xG.** `ingest_xg_data.py` stops at 2024-25, so 2025-26 and 2026-27 xG features use defaults. Extend it, or confirm Understat has current data.
- [ ] **Weather is not actually live.** `upcoming_weather.csv` is header-only (0 rows) even though both workflows pass `secrets.OPENWEATHER_API_KEY`. Check the secret is set/valid and that `fetch_weather.py` fails loudly. After that, the historical backfill is needed for weather as a training feature.
- [ ] **Ingest dedup.** `results.csv` has 1,222 duplicate (match_date, home_team, away_team) keys: the same match ingested under two leagues (e.g. LaLiga + Segunda, 1993-94). Add a dedup step to ingest; `lstm_model.py` already guards against the merge inflation.
- [ ] "Belgium vs Mirandes" club-in-international-feed bug. The history has it both fixed and "flagged, not investigated". Verify which.

### (f) Measurement
- [ ] **Re-run ROI/calibration on the full 608 sample** now the odds-join is 608/608. This is still the Elo-era record, so it's diagnostic only, not a public claim.
- [ ] **Ensemble live edge:** once `source=ensemble` rows settle, measure hit rate, log loss vs book, and value-bet ROI on ensemble rows only. Feeds decision (a).
- [ ] **Real closing odds.** The "closing" odds in `value_betting.py` are Bet365 pre-match (B365H/D/A). Switch to B365CH/CD/CA for any closing-line measurement.
- [ ] **Tier 4 market intelligence: UNBLOCKED.** `odds_history.csv` now has ~4 months / 227k rows (Jul 20 → Nov 12), and the "revisit ~Oct 2026" date has passed. Candidates: opening→closing line movement, steam-move detector, overround tracker, sharp-money threshold (>8% move in <2h). Exchange-vs-sportsbook and public-vs-sharp need Betfair data.

### (g) Infra / ops
- [ ] **Retire the World Cup simulator CI step.** `international_update.yml` still runs `worldcup_knockout_simulator.py` daily and commits `worldcup_*.csv`. The tournament ended in July. The 65 FIFA World Cup rows in the log stay `not_tracked`; decide whether a one-off international settlement job is worth it.
- [ ] **Monitoring.** Sentry is initialised in `api/app.py` (backend, DSN hardcoded): verify alerts reach you, add frontend Sentry, and move the DSN to an env var. Add UptimeRobot on `/api/health` (15 min). Silent failures already cost 3 weeks once.
- [ ] Investigate the **Nov 8 2026 failed Railway deploy** (daily international update).
- [ ] GitHub Actions deprecation warnings: bump `actions/checkout@v4→v5` and `setup-python@v5→v6`.
- [ ] `referee_fatigue_features.py` in the weekly pipeline (regenerate `team_tendencies.csv` every Monday). Verify whether it's already a step.
- [ ] Odds API budget: the free tier (500 credits/month) covers the weekly pipeline. Daily refresh or multi-market at scale needs a paid tier. Check this before (c) step 2.

---

## Launch Requirements (public launch, free or paid)
> Most of these gate the **public** launch, even while free. Publishing betting content publicly carries legal, compliance and licensing obligations whether or not we charge. Items marked *(before charging)* only gate turning on payment.

- [ ] **v1.0 Launch Definition: FREE FIRST.** Strategic decision (July 2026): launch FREE, build an audience, let the live track record prove the edge over the season, THEN turn on payment for a product people already trust. This takes Stripe, refunds and billing law off the critical path, and is the stronger play for a trust product (don't ask strangers to pay before the edge is proven live).

  **FREE v1.0 launches when ALL of these are true:**
  1. Polished football value-bets product (component audit + Value Bets page rebuild + Today's Tips).
  2. Multi-market as far as Odds API coverage/cost allows (recon-gated; goals/BTTS likely first).
  3. LIVE, auto-settling, publicly visible track record. THE centrepiece: free-first makes the proof the entire pitch. Settlement must be correct and automatic as real games finish. *(1X2 settlement works: 608/617 tracked. Outstanding: void rule + ~9 pending, multi-market settlement.)*
  4. ~~Ensemble-join reliability fixed~~. **Met (Nov 2026):** live bets are 100% ensemble, and logged predictions are ensemble from ~Nov 14.
  5. Clean landing + minimal signup + GENUINELY good mobile. Not just "responsive": the core land → Today's Tips → signup flow is good on a phone, where most traffic lands.
  6. Trust/proof surfaces visible: public proof page, track record, yesterday's results.
  7. Legal minimum + responsible-gambling compliance footer + data-source commercial licensing cleared.
  8. Staging environment + basic monitoring (Sentry/UptimeRobot), so free users don't hit broken deploys.
  9. Account basics: password reset, email change. Subscription cancellation is deferred along with payment.

  **TO BUILD, dormant until post-launch:** Stripe integration, subscription tiers, pricing page, cancellation flow. *(None of this exists in the repo yet: no Stripe code. Build it, keep it switched off, flip it on post-launch.)*

  **MONETISATION MODEL (decided Nov 2026):** free first, then a Pro tier with a free trial. The priority now is AUDIENCE: get people on board, let the live track record prove the edge, THEN monetise.
  - **FREE FOREVER** (the audience magnet: free tips ARE the growth strategy): Today's Tips (the full ranked set, for the user's sports), the verified track record / public proof page, team ratings, the core product. Free with an account. Never paywall the tips themselves.
  - **PRO** (post-launch, the power-user layer: charge for convenience/depth/breadth, NOT access to tips): accumulators (acca builder + Acca of the Day), email/push alerts + daily digest, bet tracking / personal P&L, deeper "why this bet" analysis & advanced filters, API access, and multi-sport breadth (follow ALL sports vs your main one). The multi-sport split is TBD by which sport drives growth; GAA may stay free early to build that unique audience.
  - **FREE TRIAL** of Pro at launch (standard SaaS; converts better than a hard paywall).
  - **Discipline:** monetising = ADDING the Pro layer, never TAKING tips away from free users. Nothing is gated at launch. Exact prices/limits are a "when we have users and data" decision.

  **NOT in v1.0 (post-launch):** other sports incl. GAA, the in-play engine, email digests, accas, the API tier, a mobile app.

  **TIMING:** we're mid-season with live fixtures, so the gate is evidence, not the calendar. Launch once the remodel + launch requirements are done AND the ensemble's live record is honest to show.
- [ ] **Legal foundation.** Terms of Service, Privacy Policy (+ GDPR cookie consent and data deletion), refund/cancellation policy *(before charging)*. Clarify legal standing: is this "betting advice"? In which jurisdictions? UK gambling-adjacent services have real rules. This is genuine legal work that likely needs actual legal advice.
- [ ] **Data-source commercial licensing audit.** Several sources (football-data.co.uk, Understat, The Odds API, football-data.org, the martj42 international dataset) are "free for personal/non-commercial use". Audit every source's commercial terms before public launch, and certainly before charging. This could force paid data contracts.
- [ ] **Staging / preview environment.** Push-to-main currently deploys straight to production (Vercel/Railway). That's unacceptable once there are real users.
- [ ] **Settlement robustness & correctness** across ALL markets and sports. If a corners/cards bet settles wrong, the "verifiable track record" claim collapses. Needs explicit validation, not just the SHA-256 log (which proves the prediction, not the settlement).
- [ ] **Customer support mechanism.** Support email + help/FAQ page at minimum.
- [ ] **Security before any paid tier** *(before charging)*: Flask-Limiter rate limiting, CORS restricted to known origins, input validation, CSP/HSTS headers, Dependabot, an OWASP Top 10 pass, Cloudflare in front of Railway. Secrets: keys already rotated and in env vars (Nov 2026); keep rotating.

---

## Design Constitution
> The rules the remodel executes against. Kept verbatim from Phase 6; the `[Nov 12 note]` annotations reconcile individual lines with Current State, and the note wins where they conflict.

### The Core Product Principle

> **This is a usable PRODUCT, not a data dump.** The platform is deeply data-rich, but the user must NEVER be met with an overwhelming wall of data — no "60 rows of a table" on login. Every screen leads with the conclusion and the single most useful thing; all the depth (78 features, 7 models, full stats, SHAP, historical tables) remains ACCESSIBLE but is progressively disclosed, one deliberate click deeper. The test for every screen: "would a smart person who isn't a data scientist immediately understand what they're looking at and what to do next?" If not, it's showing too much. Clean, professional, confident, easy — the data serves the product, the product is not a wrapper around the data. This principle VETOES individual design decisions: when in doubt, show less.

### Design Principles (read before starting any Phase 6 task)
- [ ] Trust-at-a-glance hierarchy — every screen leads with ONE confident number or visual, not multiple equal-weight panels. Dashboard hero = single big metric (the verifiable record, or the edge found this week — NOT CLV, which is banned per Current State), everything else secondary
  - [Nov 12 note: "live CLV" is BANNED (see Current State). The single hero metric is the verifiable record, or the edge found this week.]
- [ ] Restraint palette — one brand colour (warm orange/coral accent — see Palette in Design Direction; was emerald), one positive accent, one negative accent, everything else warm near-black neutrals. No ad-hoc colours anywhere. Two heading sizes, one body size, one small size — no exceptions
- [ ] Typographic respect for numbers — tabular figures (font-variant-numeric: tabular-nums) in every table, consistent decimal places site-wide (2.50 never 2.5), consistent probability precision everywhere
- [ ] Progressive disclosure — surface states the conclusion plainly ("Model sees 12% more chance than the bookmaker"), calculations/Kelly/model breakdown one tap deeper. Methodology page carries credibility for diggers; surface stays clean
- [ ] Confidence bands — wire prediction_uncertainty metadata (built in Phase 2 Batch 3) into prediction displays as visual confidence indication
- [ ] Motion only where data changes — probability bars fill once on load, numbers tick on update, nothing else animates. Movement = "this is live"
- [ ] Designed empty states — off-season/no-value-bets/no-data states are designed screens with a next action ("Leagues return August 15 — see the International football hub"), never blank tables or bare spinners. NOTE: launching into off-season means the no-live-bets state IS the first impression for many users
  - [Nov 12 note: leagues are mid-season (Nov 2026). The off-season empty state applies to quiet days now and to summer 2027; there is no "August 15" date.]
- [ ] One signature element — pick ONE distinctive visual (edge meter, Elo chart style, or bracket tree) and over-invest in it; that's what gets screenshotted and shared. DECIDED: the edge meter — a stacked bar showing bookmaker-implied probability (grey) + the model's additional edge (accent colour — now warm orange/coral per the approved v0 design, was soft blue ~#3b74d4), the accent segment IS the edge. Lives on every value bet card and the lead Today's Tips card. This is the screenshot asset.
- [ ] Design tokens doc first — before any page redesign, write frontend/DESIGN.md with colour tokens, type scale, spacing scale; every subsequent frontend task references it (same pattern as the shared feature pipeline, but for design)
  - [Nov 12 note: `frontend/DESIGN.md` exists but documents the old emerald system. The task is a rewrite (queue b).]
- [ ] Product-demo imagery (not stock photos) — for a quant/betting product, imagery = the PRODUCT shown beautifully: animated edge meter filling, numbers ticking up, clean product screenshots, at most one tasteful hero graphic. AVOID stock footballer photos, generic "data" imagery, decorative gifs — they read cheaper, not premium. Credibility comes from clean typography and confident numbers (like a trading terminal), not pictures. A short looping gif of the real edge meter animating = excellent landing-page demo.
- [ ] Progressive disclosure is the antidote to overload — the platform is deeply data-rich (78 features, 7 models, SHAP); the DISCIPLINE is that every surface shows the CONCLUSION (Arsenal, +11% edge), with the data mountain one click deeper. Most users never dig; the depth being there builds trust even unused. Every screen: hide 90%, surface the 10% that matters.
- [ ] "No-bet day" honesty mechanism — some days the model finds no strong value. A trustworthy product SAYS SO ("no strong edges today — we don't force picks") rather than manufacturing weak tips to fill Today's Tips. Protects the track record from forced low-confidence picks dragging it down, and is itself a powerful trust signal — the discipline that separates FormCast from tipsters who post daily regardless. PHILOSOPHY: never force a pick to fill a slot.

### Design Direction & Tooling (Nov 2026 — direction mostly locked)

**GOAL — escape the "obviously AI-designed" look.** Shown to real people (Nov 2026): impressive but "a lot of stuff, hard to show everything" and "looks obviously designed by Claude". The makeover must be deliberately branded, not default-generated. The AI tell is a COMBINATION — breaking it needs all of:
- [x] **Palette — DECIDED: DARK + WARM ORANGE/CORAL (revised Nov 2026 v0 design session).** Warm near-black ink base (~#111214 — warm-tinted blacks, NOT cold grey) + warm orange/coral accent. All-dark across the product — no light or hybrid mode needed. Clearly away from the old dark+emerald (the #1 AI tell). Feel: premium/editorial, NOT a cold Bloomberg terminal. (The approved v0 mockup went ORANGE/coral — this supersedes the earlier-locked soft blue ~#3b74d4, which itself superseded the "Direction E" light-paper + deep-blue lean. Pull the exact accent hex from the v0 code into DESIGN.md.)
- [x] **Typography — DECIDED in the approved v0 mockup:** Fraunces-style serif for headlines + clean grotesk for body/data. Confirm the exact font files/weights when integrating the v0 code.
- [ ] Layout — break the "uniform grid of equal rounded cards" tell. Editorial/asymmetric: real hero, varied density, some full-bleed, bordered-not-boxed, confident spacing contrast (big where it matters, tight elsewhere).
- [ ] Voice/copy — opinionated and specific, not generic AI copy. E.g. "We make Villa 68%. The book says 49%." not "Track your favourite teams". Bake the honesty angle in ("logged — win or lose").
- NOTE: the last 20% (exact font, logo, brand details) is taste-driven and iterative — needs Conaire's eye, not one-pass generation. Treat as: propose specific direction → react → sharpen → THEN into DESIGN.md → build. DESIGN.md gets rewritten around this, not patched.

**TOOLING (all free / free-tier — preview first, implement if liked):**
- [ ] **v0 by Vercel (v0.dev)** — PRIMARY tool. Free tier, already in the Vercel account, outputs React + Tailwind (+ shadcn) = exact FormCast stack, drops straight into repo. Use for landing page + components. MUST feed it the locked design direction (palette/type/voice/layout) or it defaults to the generic AI-Tailwind look we're escaping.
- [ ] **Framer (free)** — optional, marketing LANDING PAGE only. Distinctive, hosted, but lives on a separate subdomain (not in the React app). Good for a standout landing page kept separate from the app.
- [ ] **Figma (free)** — optional, design the visual identity deliberately BEFORE code (best "de-genericise" move). Design-then-build workflow.
- Skip Bolt.new / Lovable — same generic shadcn output, messy to integrate into the existing repo; v0 does it cleaner.
- WORKFLOW: lock direction → generate in v0 with a direction-specific prompt → preview → if liked, copy into repo + refine with Claude Code. Optionally mock in Figma/Framer first.

**LANDING PAGE — STATUS (Nov 2026): DESIGNED, NOT BUILT.** A v0 landing-page mockup is complete and APPROVED: dark warm near-black + warm orange/coral accent; Fraunces-style serif headlines + clean grotesk body; closed-front-door structure; gated "Today's Tips" teaser; about-founder section; animated public-ledger hero; email capture; compliance footer. Copy frames multi-sport as "football now — more sports coming, pick the ones you follow."

**LANDING PAGE — build FIRST (new, high-priority).** Currently a logged-out visitor gets the Dashboard + a sign-in modal — NO real landing page. A proper landing page is the biggest "now I get it in 5 seconds" lever and the thing to show people. Built in the locked design direction. (Supersedes/absorbs the existing "Landing page redesign" item.)

- [x] **Structure — DECIDED: CLOSED FRONT DOOR.** Logged-out nav is ONLY: About · How it works · Log in · Sign up free. No browsable product nav when logged out — product nav + full features appear only AFTER login. Sections, top to bottom:
  1. **Hero** — the promise + record/transparency proof numbers (NOT ROI — see Headline framing below) + sign-up CTA (approved design: animated public-ledger hero).
  2. **Gated Today's Tips teaser** — "today's tips, ranked by edge — sign up to unlock" block, NOT live pick cards.
  3. **About** — founder photo + bio (the trust differentiator vs anonymous tipsters).
  4. **How it works** — 3 plain steps.
  5. **Feature grid** — "Everything inside, once you're in": promote breadth, one line per feature, no data shown.
  6. **Email capture** — collect addresses now; the Resend digest gets built later (Phase 10).
  7. **Compliance footer** — 18+, BeGambleAware/GamCare, not-advice/past-performance disclaimers (see Pre-Launch Compliance).
- [x] **Headline framing — DECIDED (revised Nov 2026): RECORD + TRANSPARENCY-LED, NOT ROI.** ~~ROI-led "+X% return per bet, logged"~~ is REVERSED: the live diagnostic showed value-bet ROI is −7.2% on a tiny, name-mapping-biased sample (59 of 608 settled rows have odds), so there is no honest ROI to lead with (full figures under the CRITICAL hit-rate framing decision, top of NEXT UP). Hero now leads with the verifiable record ONLY: "1,110+ predictions published before kickoff, timestamped + SHA-256 hashed; 608 settled", date-stamped. (The earlier draft paired this with "50.3% 3-way accuracy" — STRUCK: it's Elo-era and a bare hit rate, both banned per Current State.) Do NOT quote "CLV" (the current metric is model-vs-book, not closing-line value). ROI returns as a headline candidate only after the name-mapping fix, a full-sample rerun, and several hundred value bets with a positive result against real closing odds (B365C*).
  - [Nov 12 note: the reasoning stands but the figures are superseded by Current State. The odds-join is now 608/608; the −7.2% ROI was measured on **Elo** predictions; **50.3% is Elo-era and is NOT a hero/headline stat**. The hero leads with the published/settled record only.]
- [x] **Freemium on landing — DECIDED: Today's Tips gated behind signup** (teaser only on the landing page). Drives signups + the email list over anonymous browsing. (Reconciled: the Value Bets editorial hierarchy and Multi-sport nav/IA items below now say Today's Tips is free WITH AN ACCOUNT, not anonymous.)

**STILL OPEN (landing page):**
- [x] Typeface — decided in the v0 mockup (Fraunces-style serif + grotesk); see Typography above.
- [ ] ~~Real ROI number~~ — RESOLVED differently (Nov 2026): REMOVE the +8.4% placeholder (not a real live figure) and do NOT replace it with a live ROI. Replace it with the record stats only (1,110+ published / 608 settled, date-stamped — NOT 50.3%, which is Elo-era and banned per Current State). See Headline framing above.
  - [Nov 12 note: use the published/settled record only. Drop "50.3% 3-way accuracy" from the hero (it is Elo-era; see Current State).]
- [ ] Founder photo + bio — placeholders for now.

---

## Later / Backlog
> Not scheduled. Grouped by theme, one line per item. Detailed historical specs are in ROADMAP_HISTORY.md / git history.

**Model features (football)**
- Manager-change signal (+8 Elo bounce, first 5 games; TransferMarkt dates) · injury/suspension & key-player availability · squad strength / market value (TransferMarkt).
- International-break and Europa League fatigue · first-half vs second-half performance (half-time scores) · weather as a training feature (needs historical backfill).
- Cross-competition Elo continuity (needs CL/EL ingestion) · league strength / cross-league Elo normalisation (partly covered by promo/rel) · Bayesian draw model (mostly covered by the draw classifier) · score-effect model (needs in-game state) · VAR tendency (parked: no data).

**Player-level modelling** (needs FBref/StatsBomb/Understat shot data)
- Top-scorer xG share & absence impact · star-player dependency · goalkeeper saves above expected · set-piece specialists · player form streaks.
- Squad depth index · age profile · captain continuity · player network cohesion · injury-risk model · international-duty fatigue.

**Advanced architectures & statistics**
- Graph Neural Network + Transformer. *History marks these `[x]`, but no code was found in `scripts/` (Nov 12 check), so treat as not built.*
- AIC/BIC selection · Ljung-Box · KS test · Brier by time bucket · hit rate by Elo-gap band · reliability-diagram CIs.

**Match intelligence & markets**
- News sentiment · match importance index · upset-probability study · goal-timing model · referee impact on outcomes.
- Betfair Exchange prices · odds comparison widget · each-way calculator · odds CSV export.

**In-play engine**
- Markov game-state model + lookup table · Bayesian in-game updater · event-impact quantification · next-event prediction · WebSocket feed (<1s) · sub-minute odds · smart-money tracker.

**International football**
- Historical World Cup 1930-2022 / Euros / Copa América / AFCON / Asian Cup with stage tags · confederation strength adjustment · squad-depth feature (big-5-league players per nation).

**Data expansion (leagues)**
- CL / EL / Conference League · MLS · women's (WSL, NWSL, UWCL) · Brazil, Argentina, Portugal, Turkey, Greece, Belgium, Denmark, Norway, Sweden, Japan, China, Australia · League of Ireland (Wikipedia scrape).

**Other sports**
- **GAA** (unique, no global competition): Derry club results (PreGame Edge, 594) · all-county scraping · Foireann API · dual-sport fatigue · xP shot model · county-commitment & referee tendencies.
- **Tennis** (Sackmann ATP/WTA, surface-adjusted Glicko-2, point-by-point Markov) · **Horse racing** (UK/IRE first: speed ratings, going/distance/draw, trainer/jockey, Betfair SP, each-way; HRI/Racing Post/Equibase).
- **Basketball** (nba_api, Four Factors, rest/back-to-back/travel, pace, EuroLeague, March Madness) · **Golf** (DataGolf SG, course-fit) · **NFL** (nfl_data_py, EPA) · rugby · T20 cricket · AFL.

**Product / UX**
- Methodology explainers (Elo, DC, Glicko-2, ensemble, xG) · interactive probability calculator · SHAP beeswarm · glossary page.
- Charts: SHAP waterfall per match, cumulative P&L, rolling Brier, Elo bar-chart race, tournament treemap, score heatmap, momentum dashboard.
- Match preview: weather, home/away form split, last-5 form dots.
- Global search · PWA · WCAG 2.1 AA · code-splitting (the JS bundle is 836 kB) · error boundaries · breadcrumbs · recently viewed · keyboard shortcuts · notification centre · PDF/CSV export · i18n.
- *Dark/light toggle: dropped. The constitution locks all-dark.*

**Retention, monetisation & growth** (Pro layer, post-launch)
- Pricing page (Free vs Pro) + Stripe subscriptions + cancellation flow.
- Daily/weekly multi-sport digest (Resend), the PRIORITY retention engine once launched, plus notification preferences.
- Weekly "how did we do" recap (real numbers only; no ROI headline until proven).
- Bet tracking / "I placed this" (design the card hook now) · onboarding email sequence · push notifications.
- Watchlist alerts (the watchlist itself is live) · team/league feed · affiliate links (needs a compliance review) · referrals · PostHog analytics & funnel · API access tier.

**Trust & community**
- Monthly accuracy report · OG share cards · audited track-record badge · press kit · arXiv preprint · Discord/Slack bot · Brier-ranked tipping competition · embed widget.

**Infra (post-launch)**
- pytest + Playwright suite · post-ingest data-quality checks · daily DB backup · log aggregation · cost alerts · PagerDuty · admin 2FA · bot/abuse detection · pen test before the paid tier.

---

## Data Sources
**In use**

| Source | Coverage | Cost |
|--------|----------|------|
| football-data.co.uk | 11 club leagues (top 5 + Championship, Segunda, Serie B, Bundesliga 2, Ligue 2, Scottish Prem), 1993-present, results + match stats + Bet365 odds | Free (non-commercial terms: see licensing audit) |
| football-data.org API | Live scores/fixtures (free tier) | Free |
| The Odds API | Live 1X2 odds (6 leagues in the value-bet feed), odds history logger | Free tier, 500 credits/month; paid needed for daily/multi-market |
| Understat | xG, top 5 leagues, **2014-25 only** (stale: see queue e) | Free |
| martj42 international results | 49,425 matches, 1872-2026 | Free |
| OpenWeatherMap API | Weather at kickoff (**not currently producing rows**: see queue e) | Free tier |
| Supabase | Auth, profiles, watchlist | Free tier |
| Sentry | Backend error monitoring (wired in `api/app.py`) | Free tier |
| GitHub Actions | CI/CD + weekly/daily pipelines | Free |

**Planned / not yet integrated**
- **Monitoring & business:** UptimeRobot, PostHog, Cloudflare, Stripe, Resend.
- **Football data:** Betfair Exchange API, FBref/StatsBomb, TransferMarkt.
- **GAA:** Foireann API, PreGame Edge (594 GAA results, internal).
- **Other sports:** Jeff Sackmann tennis, DataGolf, nfl_data_py, nba_api / Basketball-Reference, Cricsheet, AFL Tables, Racing Post / HRI / Equibase.

---

## Architecture
*Verified against the repo, Nov 12 2026.*

| Layer | Technology |
|-------|-----------|
| Modelling | Python: pandas, scipy, scikit-learn, XGBoost, PyTorch (feedforward NN + LSTM, CPU). PyMC for the Bayesian hierarchical model: unverified |
| API | Flask + flask-cors, Sentry SDK. *No Socket.io / WebSocket (planned, in-play backlog)* |
| Data store | CSV artefacts in `data/processed/` + pickled models in `models/`, committed by CI |
| Auth / user DB | Supabase (via `api/routes/auth.py`). *Supabase Realtime is not used* |
| Frontend | React 19 + Vite 8 + Tailwind 4 + Recharts. *No D3* |
| Deployment | Vercel (frontend) + Railway (API) |
| Repo | github.com/conairemolloy/formcast |

---

## Long-Term Vision (3-5 Years)
- [ ] The "Bloomberg Terminal" of sports prediction — one platform covering every major sport with institutional-grade models
- [ ] Public API with 10,000+ developers building on FormCast data
- [ ] Proprietary dataset — largest labelled sports prediction dataset in the world, covering 20+ sports and 50+ competitions
- [ ] Partnership with sports media — provide win probabilities to broadcasters and journalists in real time
- [ ] Academic citations — methodology cited in sports analytics research papers
- [ ] White-label product — sell the prediction engine to bookmakers, media companies, and sports organisations
- [ ] Real-time data advantage — proprietary data collection (stadium sensors, social media sentiment, injury feeds) not available to the public
- [ ] GAA monopoly — only platform in the world with comprehensive GAA prediction data, unique dataset with no competition
- [ ] IPO or acquisition — build to a scale that attracts strategic investment or acquisition from a major sports media or betting company
- [ ] FormCast Pro — institutional tier for professional bettors, trading desks, and media companies
