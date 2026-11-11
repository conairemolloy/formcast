# FormCast — Sports Prediction Platform
### Elo + Glicko-2 + Dixon-Coles + BTL + XGBoost + Neural Ensemble
*Last updated: November 2026*

---

## Session Log — November 2026 (foundation repair)
- [x] Ensemble-join reliability FIXED — live value bets now 100% from the real 78-feature ensemble (was falling back to stale Elo on team-name misses / date-window mismatch). Root cause was two bugs: 7-day prediction window vs 21-day odds window, and suffix-strip collapsing "Man City"/"Man United" to "Manchester". Verified 108/108 join in live pipeline run.
- [x] Prediction settlement FIXED — 608 of 617 covered-league predictions now settle (was 0 — whole season's track record was empty). Name-resolution mismatch between publish (football-data.org names) and settle (football-data.co.uk names). Log hashes preserved, never rewritten.
- [x] Stale-season data FIXED — model was frozen on May 2026 data; added 2026-27 season ingestion (1,210 matches, 11 leagues). Model now current.
- [x] Leaked API keys ROTATED + moved to env vars — football-data.org and Odds API keys were hardcoded in public repo since May 2026; rotated both, moved to Railway/GitHub secrets + .env, fail-loud if unset. (Completes much of Phase 11 "Secrets management".)
- **NEW CURRENT NUMBERS (supersede stale ones below):** 2026-27 live-season backtest 64.4% (n=913); 608 settled predictions; 100% ensemble join; ~128k matches + 2026-27.

---

## Live Site Bugs & Findings — November 2026 QA sweep
> From a full page-by-page walkthrough of the live site. Technical fixes are also tracked in "Parked Technical Fixes".

**🔴 Real bugs (broken / wrong — fix before any launch/trust push):**
- [x] **DONE (fixed Nov 2026 — one-line /api prefix fix in PredictionLog.jsx, page now loads (1,110 logged / 608 settled). Commit f883357.)** **Prediction Log page — 404, completely broken** — "Failed to load: Request failed with status code 404". This IS the public track record page — the centrepiece of the free-first trust strategy. Data settled fine (608 predictions) but the page calls a dead API endpoint. HIGHEST priority of the bugs — the trust page doesn't load.
- [x] **DONE (fixed Nov 2026 — new scripts/season_utils.py current_season() helper; simulator now runs on the current season and derives remaining fixtures dynamically from unplayed home/away pairings: EPL 100 played / 280 remaining, LaLiga 119/261, SerieA 110/270, Bundesliga 81/225, Ligue1 90/216; Tournament.jsx reads season + real played/remaining counts from the API. Commit 1278797.)** **Tournament Simulator — stuck on last season (2025-26), functionally dead** — header shows "2025-26 · ~381 matches played · ~0 remaining", simulating a FINISHED prior season (100%/0% probabilities). Root cause: hardcoded TODAY="2026-05-21" (tournament_simulator.py:22) + "2025-26" (line 177). Whole feature is useless until made season-dynamic. Not cosmetic — a full page is wrong.
- [ ] **Three different public hit-rate numbers across the site (confirmed live)** — Predictions page shows 48.8% (10,058 shown / 4,906 correct, 3-way), Backtest page shows 66.2% (non-draw), plus 64.4%/68.7% in materials. A visitor browsing sees 48.8% on one page and 66.2% on another with no explanation. This is the trust-eroding inconsistency the "hit-rate framing decision" (top of NEXT UP) must resolve — now confirmed it's live across multiple pages, not hypothetical.
  - **⚠️ URGENT UPDATE (Nov 2026): now worse — the Prediction Log page is FIXED and live, showing 50.3% as a big bare stat** (3-way, draws included, Elo-based; 306 correct / 608 settled). So 50.3% (Prediction Log) + 66.2% (Backtest) are BOTH live and public at the same time, with no reconciliation. This actively UNDER-SELLS the model — a visitor reads 50.3% as "coin flip". URGENT now, not a pre-launch item. Minimum fix: label the 50.3% honestly on the page ("3-way accuracy, includes draws") AND/OR lead with ROI as the hero number, per the locked ROI-led framing (see Design Direction & Tooling).
- [ ] **Prediction Log page — overwhelm redesign (confirmed live Nov 2026)** — the page WORKS but opens straight into a ~1,110-row scrolling table with no summary or story: the exact "data dump" the Core Product Principle vetoes. KEEP the strong trust asset: the "Cryptographically verified · SHA-256 hashed" framing + "How does verification work?" link + clickable hashes. This is what separates FormCast from tipsters, so LEAD with it. FIX: (1) lead with the honest headline (ROI + labelled accuracy) + recent settled results; (2) move the full verifiable 1,110-row table behind a "View full log" so the depth stays but doesn't overwhelm; (3) apply the uncovered-league filter (parked fix) to clear the Brazil/Eredivisie/etc PENDING noise padding the table. This page becomes the "Public proof page" (Phase 6 Trust Signals) in the remodel — one of the best trust assets.
- [x] **DONE (fixed Nov 2026 — heading reads the season from the API, which now comes from live.py's per-request current_season() (commit 1278797), so it shows 2026-27 stats; H2H.jsx fallback text changed from the literal '2025-26' to currentSeason() from frontend/src/season.js, so it auto-rolls each July.)** **H2H "2025-26 Season Stats" heading** — hardcoded last-season label (same bug family as Tournament). Shows last season's stats.

**🟢 What's GOOD (strong pages — the standard to match, do NOT redesign away):**
- Backtest page — excellent; the "What's working / Why P&L looks negative / What the numbers mean" plain-English boxes are the honest trust-building tone to replicate site-wide. THE model page.
- Ratings (club + international) — clean, current, well-designed (Bayern 2060, Spain 2277).
- H2H — strong; beautiful Elo history chart, win-prob bar.
- Matches, Match Research, Value Bets (card grid) — functional, current, close to right.

**🟡 Known/polish:** No landing page (logged-out = Dashboard + sign-in modal, not a conversion page); Dashboard flat-list (= #1 Phase 6 editorial-hierarchy priority); bare "Loading…" spinners instead of skeletons.

---

## Currently Live
- Dashboard with live value bets, upcoming fixtures, top ratings
- Live match tracker with real-time probabilities (football-data.org)
- Match deep dive: win probs, correct scores, BTTS, goals, corners, cards
- Elo ratings for 500+ teams across 14 competitions (1993-2026)
- Team profile pages: Elo history, form, season stats, H2H
- H2H comparison tool
- Tournament simulator (Monte Carlo, 100k simulations)
- Value Bets: live upcoming (100% ensemble) + historical track record
- Accumulators: historical tracker (708 accas)
- Backtest: 64.4% hit rate on 2026-27 live season (n=913); historical walk-forward ~67% non-draw
- How It Works: methodology, models, glossary
- GitHub Actions weekly automation (Monday 6am UTC)
- Mobile responsive
- Ensemble predictions pipeline — XGBoost + meta-learner saved, predict_upcoming.py ready for August
- Walk-forward ensemble backtest — 66.79% hit rate (non-draw) vs 66.71% Elo baseline across 20k matches 2020-2024
- SHA256 prediction log — 1,100+ predictions published, 608 settled, auto-settles after each gameweek
- Dropdown navigation — 4 groups with hover dropdowns (Analysis, Predictions, Betting, Learn)
- User accounts — Supabase Auth, signup/login/logout, FREE tier badge
- Watchlist — save favourite teams, bookmark icon on ratings page, form dots on watchlist cards
- Settings page — name editor, email alerts toggle
- Session persistence — stays logged in on refresh, token revalidated against Supabase on mount
- Match Research — pick any two teams, full match analysis with win probs, H2H, form, team profiles
- Team Profiles — disciplinary index, aggression score, fatigue, away card premium for all 442 teams
- Referee & Fatigue Features — team_tendencies.csv with 15 features per team
- International football module — separate Elo rating space, 49,425 matches (1872-2026), tournament-importance K-factor weighting, neutral-venue/host-nation home advantage handling
- International Ratings page — confederation filtering (UEFA/CONMEBOL/CONCACAF/CAF/AFC/OFC), 336 teams, top-level nav dropdown
- World Cup value bets — live odds via The Odds API (soccer_fifa_world_cup), real international Elo-based edges, free tier usage (~30 credits/month)
- CI/CD pipeline fully healthy — fixed 3-week silent failure (missing joblib/xgboost in requirements.txt), added retry logic with exponential backoff for live fixture fetching
- LSTM predictions in ensemble stack — 14-feature meta-learner, 66.83% walk-forward backtest
- 78-feature ensemble (Phase 2 final: SHAP-culled from 85), 15-feature meta-learner stack, ~67.0% non-draw walk-forward (2024 season: 67.6%, +0.9pp over Elo), ECE 0.0127 uncalibrated (serving model; Platt layer retired)

---

## NEXT UP — Priority Queue (updated November 2026)
> Work through in order before starting Phase 3+.

- [ ] **CRITICAL DECISION — public hit-rate framing (50% vs 64.4% vs 68.7%)** — three different numbers measure three different things and a visitor seeing them together loses trust: logged predictions settle at ~50% (3-way H/D/A, Elo-based from the Railway API, not the ensemble); the live 2026-27 ensemble backtest is 64.4% (n=913); the old marketing figure is 68.7% (non-draw, optimised Elo). Before ANY public proof page or email tips, decide ONE honest headline framing. Options: (a) lead with 64.4% current-season ensemble accuracy clearly labelled; (b) report ROI/CLV on value bets instead of raw accuracy; (c) log ensemble (not Railway-Elo) predictions going forward so the track record reflects the real model. GATES the free-first launch — the whole pitch is the honest track record.

**Pre-design blockers (do before any brand-facing surface)**
- [ ] **Project naming & brand decision** — "FormCast" is football-specific ("form" is a football/racing term) which fights the multi-sport future, and may have existing domain/brand conflicts. Decide a proper product name that: conveys trust/accuracy + multi-sport breadth + quant/edge positioning (read as ANALYTICS/data company, closer to a Bloomberg terminal than a betting site — NOT "tipster" or "gambling"); has a clean available .com or .io; short, sayable, not confusable with existing betting brands. Blocks: custom domain purchase, landing page copy, logo, all brand-facing design. Do this BEFORE the landing page redesign so the brand is settled before brand-facing surfaces are built. [Options being brainstormed]

**Infrastructure & monitoring (still outstanding)**
- [x] **DONE (fixed Nov 2026, see Session Log)** **Live value bets: ensemble-join reliability (was "Elo-only")** — fetch_live_odds.py already bridges to ensemble predictions via upcoming_predictions.csv, but falls back to stale Elo SILENTLY on team-name key misses. Root cause: two divergent name-resolution pipelines — odds API → _ODDS_TO_ELO (sparse, top-leagues-only, missing most Championship/Serie B/etc) vs football-data → results.csv canonical. Instrumentation added to log hit/miss rate per run. NEXT: (1) measure real miss rate once season fixtures populate [instrumentation live], (2) fix by unifying to ONE canonical team-name resolver (single-source-of-truth, same principle as feature pipeline) rather than extending the sparse _ODDS_TO_ELO dict, (3) also unify the two divergent Elo fallback formulas (fetch_live_odds HOME_ADV=50 + own draw formula vs predict_upcoming's — they disagree), (4) emit prediction_uncertainty from predict_upcoming.py (one line — meta_proba already computed) so live Today's Tips gets edge×confidence ranking. Off-season note: miss-rate measurement only meaningful once upcoming fixtures exist.
- [ ] Sentry error monitoring (15 min signup; silent failures already cost 3 weeks once)
- [ ] UptimeRobot on /api/health (15 min signup)
- [ ] OPENWEATHER_API_KEY as GitHub Actions secret + local .env (unblocks weather column in predictions)
- [ ] Custom domain purchase + Vercel config (~€12/yr; formcast-blush.vercel.app undermines premium positioning — highest ROI item in the design phase)
- [x] test_club_path.py as CI canary step in weekly workflow — pipeline fails loudly instead of shipping broken predictions silently
- [ ] Verify first Monday pipeline run end-to-end — watch the full Actions log; run now includes: elo step, xG attempt (continue-on-error), canary, weather (daily + weekly), odds logger, pickle commits
  - Note: after Monday's run, VERIFY the newly-wired columns populated: prediction_uncertainty in value_bets.csv (needs ensemble retrain) and value_bookmaker in live_value_bets.csv (needs odds fetch). Both degrade gracefully if absent but the Today's Tips edge×confidence ranking and bookmaker display depend on them.

**Then: Phase 6 Design (DESIGN.md first per Design Principles), with Phase 3 NN retrain folded in where needed**

---

## Pre-Launch Requirements (must be TRUE before charging)
> These are not features — they're the gate to launching a paid product. Absence of any of these actively bites the day after launch.

- [ ] **v1.0 Launch Definition — FREE FIRST** — Strategic decision (July 2026): launch FREE, build audience, let the live track record prove the edge over the season, THEN flip on payment for a product people already trust. Removes Stripe/refund/legal-billing complexity from the critical path and is the stronger play for a trust product (don't ask strangers to pay before the edge is proven live).

  **FREE v1.0 launches when ALL true:**
  1. Polished football value-bets product (component audit + Value Bets page rebuild + Today's Tips)
  2. Multi-market as far as Odds API coverage/cost allows (recon-gated; goals/BTTS likely first)
  3. LIVE, auto-settling, publicly-visible track record — THE centrepiece; free-first makes the proof the entire pitch. Settlement must be correct and automatic as real games finish
  4. Ensemble-join reliability fixed — live bets come from the real 78-feature ensemble, not silent Elo fallback (see NEXT UP)
  5. Clean landing + minimal signup + GENUINELY good mobile (not just "responsive" — the core land→Today's Tips→signup flow is good on a phone, where most traffic lands)
  6. Trust/proof surfaces visible (public proof page, track record, yesterday's result)
  7. Legal minimum + responsible-gambling compliance footer + data-source commercial-licensing cleared (publishing betting content publicly even when free)
  8. Staging environment + basic monitoring (Sentry/UptimeRobot) so free users don't hit broken deploys
  9. Account basics: password reset, email change (subscription-cancellation deferred with payment)

  **BUILT-BUT-DORMANT, ready to flip on post-launch:** Stripe integration, subscription tiers, pricing page, cancellation flow — wired but switched off.

  **MONETISATION MODEL — DECIDED (Nov 2026, revised for Today's Tips framing):** Free-first, then a Pro tier with a free trial. Priority at this stage is AUDIENCE — get people on board, let the live track record prove the edge, THEN monetise. (Replaces the earlier "Bet of the Day always free; full value-bets list + multi-sport become Pro" paywall line.)
  - **FREE FOREVER** (the audience magnet — tips being free IS the growth strategy): Today's Tips (full ranked set, the user's sports), the verified track record / public proof page, team ratings, core product. Never paywall the tips themselves.
  - **PRO** (post-launch, the power-user layer — charge for convenience/depth/breadth, NOT access to tips): accumulators (acca builder + Acca of the Day), email/push alerts + daily digest, bet tracking / personal P&L, deeper "why this bet" analysis & advanced filters, and multi-sport breadth (follow ALL sports vs your main one — TBD based on which sport drives growth; GAA may stay free early to build that unique audience).
  - **FREE TRIAL** of Pro at launch (standard SaaS; converts better than a hard paywall).
  - **Discipline preserved:** monetising = ADDING the Pro layer, never TAKING tips away from free users. Nothing gated at launch (free-first); Pro built-but-dormant, flipped on once audience + proven edge exist. Exact prices/limits = a "when we have users and data" decision, not now.

  **NOT in v1.0 (post-launch):** other sports incl. GAA, in-play engine, email digests, accas, API tier, mobile app, Phases 13-22.

  **TIMING:** build now → August; launch when season proves the live edge. The live track record is the gate, and it needs real fixtures.
- [ ] **Legal foundation** — Terms of Service, Privacy Policy, refund/cancellation policy. Clarify legal standing: is this "betting advice"? In which jurisdictions? UK gambling-adjacent paid services have real regulatory rules. This is not the compliance footer — it's genuine pre-revenue legal work, likely needs actual legal advice. Getting it wrong can end the product.
- [ ] **Data source commercial licensing audit** — football-data.co.uk, Understat, The Odds API, football-data.org, martj42 international dataset, etc. Several are "free for personal/non-commercial use." The moment we charge money, personal-use data may NOT be licensed for a paid product. Audit EVERY data source's commercial terms before monetising. Quiet landmine — could force paid data contracts or source changes.
- [ ] **Staging / preview environment** — currently push-to-main deploys straight to production (Vercel/Railway). Fine with no users; unacceptable with paying customers (a bad push breaks the live product). Need a staging branch/environment to test before production. Infrastructure hygiene that becomes non-negotiable at launch.
- [ ] **Settlement robustness & correctness** — the entire pitch is "every result logged, win or lose." The settlement pipeline (did the bet win?) must be provably correct and tamper-evident across ALL markets and sports. If a corners/cards bet settles wrong, the "verifiable track record" claim collapses. As multi-market expands, settlement complexity grows — needs explicit robustness work + validation, not just the SHA256 log (which proves the prediction, not the settlement).
- [ ] **Customer support mechanism** — support email + help/FAQ page at minimum. The day someone pays they'll have billing questions, bug reports, "why no email." No support channel exists anywhere currently — glaring the day after launch.

---

## Build Priorities — Repositioned for Commercial Launch
> Phases renumbered to reflect the actual build order.

### Stage 1 — Model Quality (Phase 2 + Phase 3 + Phase 4 + Phase 5)
- [x] Phase 2 Tier 1 — remaining high-impact features: venue win rate, clean sheet rate, opponent-adjusted form, relegation/title pressure, league-specific home advantage, early season Elo regression — COMPLETE July 2026
- [x] Phase 2 Tier 2 — weather infrastructure (fetch_weather.py + upcoming_weather.csv running; training feature pending historical backfill) — COMPLETE July 2026
- [x] Phase 2 Tier 3 — model architecture: separate draw classifier, ensemble calibration (Platt scaling retired, ECE 0.0127), league-specific home advantage — COMPLETE July 2026
- [x] Phase 2 Tier 6 — odds format display: American moneyline, UK fractional, decimal — shared utility used everywhere — COMPLETE July 2026
- Phase 3 — retrain neural networks with updated feature set
- Phase 4 — betting intelligence gaps: Dutching calculator, arbitrage detector, Sharpe ratio, max drawdown, P&L simulation
- [x] Phase 5 — model validation page: walk-forward accuracy chart, calibration curve, per-league Brier scores (trust-building content that converts free users to paid) — COMPLETE July 2026
- [x] Market-specific models — corners, cards, BTTS, goals over/under (separate XGBoost per market)
- [x] Ensemble auto-retraining in weekly pipeline — VERIFIED July 2026; all models retrain every Monday (workflow steps 8-16); pickle commit fixed so Railway stays in sync

### Stage 2 — Design & UX (Phase 6 + Phase 7 + Phase 8 + Phase 9)
- Phase 6 — full design overhaul: dashboard hero, value bet cards, landing page conversion optimisation
- Phase 7 — UX gaps: SHAP waterfall per match, cumulative P&L chart, form visualisation, home/away form split
- Phase 8 — methodology docs: model explainers, interactive probability calculator, glossary page
- Phase 9 — UX excellence: global search, loading skeletons everywhere, error boundaries, PWA support

### Stage 3 — Monetisation (Phase 10 + Phase 11 + Phase 12 gaps)
- Phase 10 — pricing page: Free vs Pro vs Elite tier comparison table
- Phase 10 — Stripe subscriptions: Pro tier billing, webhook handling, subscription management
- Phase 10 — email alerts: Resend API, watchlist notifications, weekly digest
- Phase 10 — affiliate bookmaker links: Bet365, Paddy Power, Betfair on value bet cards
- Phase 11 — security & rate limiting: Flask-Limiter, JWT, CORS hardening (must be done before paid tier)
- Phase 12 — remaining automation: ensemble auto-retraining, test suite, data quality checks
- Custom domain (~€12/year)

### Stage 4 — Sport Expansion (Phase 13 + Phase 14 + Phase 15 remaining)
- Phase 13 — GAA (unique market, no competition globally, use PreGame Edge data)
- Phase 13 — Tennis (Jeff Sackmann dataset, surface-adjusted Glicko-2)
- Phase 13 — Horse racing (UK/Ireland first, HRI + Racing Post free data)
- Phase 13 — NBA (nba_api, Four Factors model, back-to-back fatigue)
- Phase 14 — data expansion: more leagues, Champions League history, Conference League
- Phase 15 remaining — Euros/Copa América historical data, confederation strength adjustment
- Phase 2 Tier 4 — market intelligence: Betfair Exchange, line movement tracking
- Phase 2 Tier 5 — player features: injury impact, xG contribution, goalkeeper form

### Stage 5 — Advanced Features (Phase 16 + Phase 17 + Phase 18 + Phase 19 + Phase 20)
- Phase 16 — live in-play engine: WebSocket, Markov chain game state, Bayesian updater
- Phase 17 — trust signals: verified track record badge, monthly accuracy report, social sharing
- Phase 18 — match intelligence: distance fatigue, live odds movement, referee impact model
- Phase 19 — community: Discord bot, leaderboard, tipping competition
- Phase 20 — individual player modelling: xG contribution, goalkeeper form, squad depth
- Phase 3 — GNN and Transformer models
- Public API tier for developers
- White-label product for bookmakers and media companies

---

## Season Status (November 2026)
European leagues mid-season. Pipeline healthy and current: 2026-27 data ingested, all models retraining weekly, live value bets 100% ensemble-backed, track record settling (608 predictions). Live 2026-27 ensemble backtest: 64.4% (n=913).

---

## What This Is
A multi-model football prediction platform trained on 128,797 matches across 
14 competitions (1993-2026). Built on a seven-layer ensemble — Elo, Glicko-2, 
Dixon-Coles, Bradley-Terry, XGBoost, Feedforward NN, and LSTM — with full 
walk-forward backtesting, a value bet screener, accumulator builder, Kelly 
criterion stake sizing, Monte Carlo tournament simulator, and match stats 
including shots, corners and cards. Live at formcast-blush.vercel.app.

---

## Current Results
| Metric | Value |
|--------|-------|
| Matches in database | 128,797 (14 competitions, 1993-2026) |
| Competitions | EPL, Championship, La Liga, Segunda, Serie A, Serie B, Bundesliga, Bundesliga 2, Ligue 1, Ligue 2, Scottish Prem |
| Walk-forward hit rate | 68.7% (non-draw, optimised Elo, 128k matches) |
| Walk-forward Brier score | 0.156 |
| Ensemble v2 hit rate | 49.0% (3-outcome holdout) / ~67.0% (non-draw walk-forward) |
| Neural network hit rate | 53.1% (feedforward, 2014-25) |
| LSTM hit rate | 53.3% (temporal sequences, 2014-25) |
| Neural network Brier | 0.584 |
| xG matches integrated | 19,837 (Understat, 2014-25) |
| Baseline (coin flip) Brier | 0.250 |
| Top rated team | Bayern Munich (Elo 2059) |
| Automation | GitHub Actions weekly pipeline (Monday 6am UTC) |
| Live Value Bets | Odds API integration, 6 leagues, weekly refresh |
| Match Deep Dive | corners, cards, goals, correct scores, BTTS markets |
| Ensemble models saved | XGBoost + meta-learner + league encoder persisted to models/ |
| Users | Supabase Auth live, profiles table, watchlist, tier system ready for monetisation |

---

## Phase 1 — Core Models (Complete)
- [x] Data pipeline — football-data.co.uk, 5 leagues, 2020-25
- [x] Elo model with MoV multiplier and home advantage
- [x] Walk-forward backtesting pipeline (strict temporal ordering)
- [x] Dixon-Coles bivariate Poisson model (temporal decay, tau correction)
- [x] XGBoost classifier (Elo + form features, 13 features)
- [x] Stacking meta-learner (LogisticRegression on OOF predictions, 5-fold TimeSeriesSplit)
- [x] Hyperparameter grid search (K, home_advantage, decay, MoV cap)
- [x] Glicko-2 uncertainty-aware ratings (RD + volatility)
- [x] Bradley-Terry-Luce schedule-adjusted ratings (MLE)
- [x] Bayesian hierarchical model (PyMC — partial pooling across leagues)

### Phase 1 Completion — July 2026
- [x] Walk-forward ensemble backtest — 66.79% hit rate vs 66.71% Elo baseline across 20,271 matches (2020-2024), proves ensemble adds genuine signal
- [x] DC tau correction — added Dixon-Coles low-score rho correction (ρ=−0.13) to rolling _dc_probs, draw probabilities now properly calibrated
- [x] Draw model recalibrated — replaced invented 0.30×closeness heuristic with empirically grounded 0.265 base rate formula
- [x] International ensemble columns fixed — stopped duplicating Elo values into p_home/draw/away_ensemble for international fixtures
- [x] Elo logic deduplicated — backtest.py now imports from elo_model.py, no more copy-paste drift risk
- [x] League encoder consolidated — created exactly once in build_all_features(), saved instance used at prediction time
- [x] COMP_TO_LEAGUE expanded — 6 → 15 entries, added Bundesliga2 Ligue2 ScottishPrem SerieB Segunda and common API name variants
- [x] Always-home baseline fixed — backtest.py was printing hit rate twice under different labels, now shows genuine dumb baseline (~46% always predicting home win)
- [x] Unknown competition warning — unknown leagues now log a WARNING instead of silently defaulting to EPL
- [x] Stale docstring fixed — ensemble_v2.py header updated from "42-feature" to "48-feature"
- [x] Env-var API URL — predict_upcoming.py UPCOMING_URL now reads FORMCAST_API_URL env var, enables local testing without hitting production
- [x] feature_cols.json validation — assert fires immediately if saved feature list diverges from current FEATURE_COLS
- [x] Per-team cold start — ensemble_backtest.py drops matches where either team has fewer than 5 prior appearances
- [x] Models retrained — xgb_ensemble.pkl meta_learner.pkl league_encoder.pkl all regenerated with fixed DC tau correction and consolidated encoder

---

## Phase 2 — Feature Engineering

### Tier 1 — High Impact, Data Already Available
- [x] Result momentum — EWM(win=3, draw=1, loss=0, λ=0.6), last 5 matches
- [x] Score momentum — EWM(scored - conceded, λ=0.6), last 5 matches
- [x] Elo momentum — Elo_today minus Elo_28_days_ago
- [x] Scoring rate trend — OLS slope of goals scored, last 8 matches
- [x] Concession rate trend — OLS slope of goals conceded, last 8 matches
- [x] Winning/losing streak — Bernoulli run length
- [x] Rest asymmetry (home vs away rest days differential)
- [x] Days since last match — computed in team_tendencies.csv
- [x] Matches in last 21 days — computed in team_tendencies.csv
- [x] Revenge factor (+5 Elo vs opponent who beat them last) — in ensemble
- [x] Post-loss bounce (+8 Elo) — in ensemble
- [x] H2H psychological dominance — in ensemble
- [x] Team aggression index — normalised composite of fouls + cards (team_tendencies.csv)
- [x] Away card premium — teams get more cards away, quantified per team
- [x] Yellow trend — is team getting more or less disciplined recently
- [x] Fatigue score — days rest + fixture congestion per team
- [x] Home/away Elo split — maintain separate home and away Elo ratings per team beyond flat +50. Real signal especially for teams with strong home/weak away records (PRIORITY)
- [x] Referee tendencies — wire up referee column already in results.csv. Cards per game, fouls per game, home bias score per referee. Data exists, just not wired in (PRIORITY)
- [x] Venue-specific home win rate — per-team actual home win rate, not just global +50 constant
- [x] Relegation/title pressure — flag teams in bottom 3 or top 3 with <10 games remaining, measurable performance change
- [x] Opponent-adjusted form — distinguish wins vs top-half teams from wins vs relegation fodder
- [x] Season opener variance — widen confidence intervals for first 5 games of season, less predictable (is_early_season flag in all market models)
- [x] Early season Elo regression — REGRESSION_FACTOR=0.75, regress toward league mean, ensemble_v2.py build_all_features()
- [x] Form-weighted late season — `late_season_form_diff` feature; EWM alpha 0.6 (vs 0.4 default) over last 5 matches, non-zero only when `is_late_season == 1` (≥28 season matches per team)
- [ ] First half vs second half performance — some teams start slow or fade, use half-time scores if available in results.csv
- [x] Home bias score per referee — ref_home_bias feature, ensemble_v2.py
- [ ] VAR tendency — referees who overturn more decisions, affects game flow **[PARKED: no VAR data available from football-data.co.uk]**
- [x] League-specific home advantage — learned online per-league HA (HA_MIN_MATCHES=100), clamped [0.5×, 1.5×], ensemble_v2.py build_all_features()
- [x] Promotion/relegation Elo adjustment — 50% step toward new league mean on first appearance in new league, ensemble_v2.py build_all_features()
- [ ] Cross-competition Elo continuity — strengthen existing implementation, Champions League performance should inform league Elo more **[PARKED: no European competition data ingested; revisit if CL ingestion added via football-data.org]**
- [x] Opponent quality-adjusted form — home/away_opp_adj_form features (result × opponent Elo ratio, last 10), ensemble_v2.py
- [x] Unbeaten run momentum — home/away_unbeaten_run features (capped at 15), ensemble_v2.py
- [x] Clean sheet rate — goalkeeper/defensive form signal, rolling last 10 matches (venue-split in BTTS and goals models)
- [x] Goals per shot ratio — `home_shot_conversion` / `away_shot_conversion`; goals÷shots rolling last 10 matches with shot data (fallback 0.11); `home_shots`/`away_shots` now stored in team_hist via `update_state()`
- [x] H2H extended history — `h2h_all_time_dominance`; (home_wins − away_wins) / total meetings over full history; running totals in `state["h2h_totals"]` keyed by canonical pair, O(1) per match
- [x] Derby factor — `is_derby` binary flag; 22 hardcoded pairs (16 top-flight + 6 second-tier) in module-level `DERBY_PAIRS` frozenset; both M'Gladbach spellings covered; team names validated against results.csv at build time with warnings on typos

### Tier 2 — External Data Required (All Free Sources)
- [~] Weather at kickoff — prediction-time display live (fetch_weather.py → upcoming_weather.csv → merged into upcoming_predictions.csv); daily refresh wired into international_update.yml (5am UTC) since July 2026, also runs weekly; training feature blocked on historical weather data backfill, revisit as training feature next season
- [ ] Manager change signal — +8 Elo bounce in first 5 games under new manager, well documented in literature. TransferMarkt scrape for manager change dates, update monthly
- [x] Distance travelled — away_travel_km feature (haversine); stadiums.csv covers 442/444 teams; 0.0 fallback when stadium unknown
- [x] Altitude adjustment — altitude_diff feature (home_alt − away_home_alt, metres); same stadiums.csv source; 0.0 fallback
- [x] Stadium capacity proxy — home_capacity_log feature (log10(capacity)); fallback log10(20000) ≈ 4.30 when unknown
- [ ] Squad strength proxy — count of players per team currently playing in top leagues, use existing club Elo data as novel cross-dataset signal
- [ ] Injury/suspension impact — key player missing affects xG significantly. Free sources: BBC Sport, Rotowire, or parse football-data.org injury flags
- [ ] International break fatigue — players returning from international duty, travel disruption and schedule congestion
- [ ] Europa League fatigue — performance drop after Thursday Europa League travel, especially for teams with weak squads
- [ ] TransferMarkt market value — squad market value as proxy for squad strength, free scraping

### Tier 3 — Model Architecture Improvements
- [x] Separate draw classifier — dedicated binary classifier trained specifically to predict draws, using features like team defensive ratings, historical draw rates by team/league/referee, closeness of Elo ratings
- [ ] Score-effect model — teams play differently when winning (sit deep) vs losing (chase game), current models ignore game state entirely **[DEFERRED Batch 3: needs in-game state data not available in results.csv]**
- [x] Home/away Glicko-2 split — venue-specific G2 dicts (g2_home/g2_away); 4 new features: home_g2_home, away_g2_away, g2_venue_diff, away_g2_uncertainty (Batch 3)
- [x] Time-decay on xG — DECAY=0.85 exponential weighting replaces flat window across all 6 xG averages (Batch 3)
- [ ] Bayesian draw model — model draw probability as a function of match competitiveness and historical draw rates **[DEFERRED Batch 3: draw classifier already covers this — enhancement not gap; revisit after SHAP analysis]**
- [x] Ensemble calibration (Platt scaling) — Platt layer retired; uncalibrated ECE 0.0125 is well-calibrated and consistently beats the calibrated variant across three configs (0.0131, 0.0149, 0.0160 calibrated vs 0.0125–0.0128 uncalibrated); ECE comparison retained in training output for monitoring
- [ ] League strength adjustment — when teams move between leagues, adjust Elo to account for quality difference **[DEFERRED Batch 3: partially addressed by Batch 1 promo/rel mechanism; revisit at SHAP stage]**
- [ ] Cross-league Elo normalisation — ensure EPL Elo 1600 is comparable to Bundesliga 1600 **[DEFERRED Batch 3: partially addressed by Batch 1 promo/rel mechanism; revisit at SHAP stage]**
- [x] Feature interaction terms — elo_x_form (elo_diff × form_diff / 100), fatigue_x_congestion (rest_asymmetry × congestion_diff), derby_x_h2h (Batch 3: 3 new features)
- [x] Temporal feature decay — DECAY=0.85 EWM on goals scored/conceded averages and clean sheet rates; momentum features untouched (already EWM), form kept flat (feeds late_season_form_diff contrast), shot conversion left to observe (Batch 3)
- [x] Confidence intervals per prediction — prediction_uncertainty = (home_phi + away_phi) / (2 × G2_INITIAL_PHI), normalised by initial phi; returned as metadata key only, NOT in FEATURE_COLS (Batch 3)

### Tier 4 — Market Intelligence (Requires Betfair/Odds API)
> All Tier 4 items blocked on odds history depth. log_odds_snapshot.py running since July 2026, appending per-bookmaker rows to odds_history.csv on every weekly + daily pipeline run. Revisit ~Oct 2026 once ~3 months of snapshots exist.
- [ ] Opening vs closing line movement — odds moving significantly pre-kickoff = sharp money signal **[blocked on odds history — logger running since July 2026, revisit ~Oct 2026]**
- [ ] Steam move detector — multiple bookmakers move simultaneously = strong directional signal **[blocked on odds history — logger running since July 2026, revisit ~Oct 2026]**
- [ ] Exchange vs sportsbook divergence — Betfair efficient market price vs bookmaker line gap **[blocked on odds history — logger running since July 2026, revisit ~Oct 2026]**
- [ ] Overround tracker — monitor bookmaker margin changes as signal of confidence **[blocked on odds history — logger running since July 2026, revisit ~Oct 2026]**
- [ ] Public vs sharp money split — bookmakers shade lines away from popular teams **[blocked on odds history — logger running since July 2026, revisit ~Oct 2026]**
- [ ] Sharp money threshold — flag when line moves >8% in <2 hours pre-kickoff **[blocked on odds history — logger running since July 2026, revisit ~Oct 2026]**

### Phase 2 Completion Checklist
- [x] Re-run ensemble_backtest.py after each major feature addition to measure uplift
- [x] SHAP feature importance analysis — 85→78: culled 7 features (post-loss bounces, revenge, streaks, superseded h2h pair); season flags (is_early_season, is_late_season) restored — SHAP undervalued them due to binary/rare-activation; gating logic retained in pipeline; kept pressure trio, derby pair, unbeaten runs as rare-but-real
- [x] Calibration curve update — Platt layer retired; uncalibrated ECE 0.0125 is well-calibrated and consistently beats calibrated variant; monitoring comparison retained in training output
- [x] Update feature_cols.json and retrain all saved models after final feature set confirmed

### Phase 2 Completion — July 2026
- [x] Feature journey: 70 (Phase 1) → 85 (Batches 1–3) → 78 (SHAP cull, season flags restored); final set locked in FEATURE_COLS and regenerated to feature_cols.json
- [x] Backtest: ~66.9% walk-forward (full 2020-2024) → ~67.0%; 2024 season 67.6% (+0.9pp vs Elo baseline)
- [x] Season-boundary Elo regression (REGRESSION_FACTOR=0.75 toward league mean) — measurable reduction in start-of-season over-confidence
- [x] Per-league home advantage learned online (HA_MIN_MATCHES=100, clamped [0.5×, 1.5×]) — replaces flat +50 constant
- [x] Promotion/relegation Elo adjustment — 50% step toward new league mean on first appearance, prevents cross-league distortion
- [x] Shared architecture: init_state / compute_match_features / update_state — single canonical implementation eliminates training/prediction drift
- [x] predict_upcoming 22-feature drift bug fixed — feature vector was missing 22 columns vs training; guards added; test_club_path.py as regression canary
- [x] SHAP cull 85 → 78: removed 7 features (post-loss bounce, revenge factor, streak, superseded h2h pair); is_early_season and is_late_season restored after post-cull backtest showed consistent softening across leagues — SHAP undervalued them due to binary/rare-activation bias
- [x] Platt calibration retired — uncalibrated ECE 0.0127 consistently beats calibrated variant across three configs; Platt comparison retained in training output as monitoring signal
- [x] Tier 6 odds formats shipped to production — decimal/fractional/American via shared oddsFormat.js + dutching_arbitrage.py; user preference persisted to Supabase
- [x] Stadium geography features: stadiums.csv 442/444 teams, away_travel_km + altitude_diff + home_capacity_log in FEATURE_COLS
- [x] Weather infrastructure: fetch_weather.py + upcoming_weather.csv running since July 2026; blocked as training feature pending historical backfill (revisit next season)
- [x] Odds history infrastructure: log_odds_snapshot.py running since July 2026, appending to odds_history.csv; Tier 4 market intelligence blocked on 3-month history minimum (revisit ~Oct 2026)
- [x] Tiers 2 (scraping items) / 4 / 5 consciously parked with revisit dates; no silent deferrals

### Tier 5 — Individual Player Features (Requires Player-Level Data)
- [ ] Key player availability — top scorer or first-choice goalkeeper missing, quantify impact on team xG. Sources: BBC Sport injury feed, football-data.org, or manual flags
- [ ] Top scorer xG contribution — individual player xG as % of team total, when missing = proportional team xG reduction
- [ ] Goalkeeper form — saves above expected from shot data, shotstopping quality beyond team defence
- [ ] Captain continuity — same captain vs new captain, leadership stability signal
- [ ] Set piece specialist availability — teams with dead ball specialists score more from corners/free kicks, absence is measurable
- [ ] Player form streaks — individual scoring/assist streaks as momentum signal, beyond team-level momentum
- [ ] Squad depth index — quality drop from first XI to bench, affects performance in fixture congestion
- [ ] International duty fatigue — players returning from long-haul international travel, minutes played for national team
- [ ] Age profile — average squad age, older squads fade late season, younger squads more variance
- [ ] Player network cohesion — pass completion rates between specific player pairs, team cohesion signal (requires StatsBomb free data)
- [ ] Injury probability model — predict injury risk from minutes played, age, fixture congestion, identify overloaded players
- [ ] Star player dependency — single player xG contribution as % of team total, high dependency = high variance

### Tier 6 — Odds Format Display
- [x] American odds format — American moneyline (+150, −200); decimal≥2 → +round((d−1)×100), decimal<2 → −round(100/(d−1)); shared JS module (oddsFormat.js) ports Python logic exactly so JS and Python always agree
- [x] UK fractional odds — nearest standard UK fraction via 40-entry COMMON_FRACTIONS lookup (ported exactly from dutching_arbitrage.py); target = decimal−1 = (1−p)/p; JS and Python guaranteed to return same fraction for same decimal
- [x] Decimal odds — European format (2.50, 1.91 etc); shared formatOdds() in oddsFormat.js, user-selectable as default
- [x] Implied probability display — shown as "(43.5% impl.)" alongside odds on Value Bets table rows and Live Bets cards
- [ ] Odds comparison widget — show model probability vs best available bookmaker odds across multiple formats simultaneously (deferred — folds into Phase 6 Value Bets page redesign)
- [ ] Each-way odds calculator — for markets where each-way betting applies (primarily horse racing, outright tournament markets)
- [ ] Odds to CSV export — download current value bets with all three odds formats for use in external staking tools

- [x] Odds format converter utility function — to_decimal/to_american/to_fractional/all_formats in dutching_arbitrage.py; JS-side oddsFormat.js created, wired to Settings, Value Bets, and Accumulators pages
- [x] Value bets page updated to show all three odds formats simultaneously — shows selected format + implied probability; switchable via Dec/Frac/US segmented control at top of page and in Settings → Display; preference persisted to localStorage and server profile (odds_format column)


### Market-Specific Models — BUILT
- [x] Corners model — XGBoost regressor, MAE 2.68, Over 9.5 accuracy 53.9% vs 52.3% naive, referee tendencies #2 feature
- [x] Cards model — XGBoost regressor, MAE 1.48, Over 3.5 accuracy 62.5% vs 59.8% naive, referee_avg_yellows #1 feature at 24.3% importance
- [x] BTTS model — XGBoost binary classifier, 65.4% accuracy vs 53.4% naive, ROC-AUC 0.706, near-perfect calibration
- [x] Goals model — XGBoost regressor + Over 2.5 classifier, MAE 1.12, Over 2.5 accuracy 63.1% vs 61.5% naive
- [x] All 4 models use causal single-pass feature engineering, no data leakage
- [x] Referee tendency features confirmed as dominant signal in cards model (24.3% importance)

---

## Phase 3 — Neural Network Suite
- [x] Feedforward: Input → Dense(256,ReLU) → BN → Dropout(0.3) → Dense(128,ReLU) → Dense(3,Softmax)
- [x] LSTM: last 5 match feature vectors → LSTM(128) → Dense(64) → Dense(1,σ)

- [x] Graph Neural Network: teams as nodes, matches as edges, GCN propagation
- [x] Transformer: self-attention over match history sequence

### Phase 3 Completion — July 2026
- [x] Feedforward NN retrained with 70-feature set, NaN guard added
- [x] LSTM retrained with NaN guard — 53.6% hit rate vs 51.4% Elo, Brier 0.584
- [x] LSTM added to ensemble stack as 14th meta-feature
- [x] BTL added to ensemble stack as 15th meta-feature
- [x] XGBoost hyperparameters optimized via random search (30 trials) — max_depth=4, subsample=0.9, min_child_weight=1
- [x] Both NNs wired into weekly pipeline
- [x] Final walk-forward backtest: 66.92% vs 66.71% Elo, ECE 0.0098, 70 features, 15 stack features

---

## Phase 4 — Betting Intelligence
- [x] Value bet screener (EV = P_model × odds - 1, threshold > 5%)
- [x] Kelly criterion stake sizing (half-Kelly)
- [x] Accumulator builder — optimal leg selection by EV
- [x] Accumulator independence testing (same-league correlation correction)
- [x] Accumulator EV matrix UI — best combinations visualised as grid
- [x] Closing line value (CLV) tracking — mean(log(P_model / P_close))
- [x] SHA256 prediction accountability ledger (hash-stamped pre-match)
- [x] Sharpe ratio + max drawdown on simulated flat-stake strategy
- [x] Dutching calculator — optimal stake distribution across multiple outcomes
- [x] Arbitrage detector — Σ(1/odds) < 1 across bookmakers, flag instantly
- [x] Match deep-dive page — win/draw/loss probabilities, goals markets, correct scores, BTTS, corners markets, cards markets, H2H stats

### Phase 4 Completion — July 2026
- [x] Max drawdown added to /value-bets/summary API response
- [x] Accumulator same-league correlation correction — 8% penalty per same-league pair, 5% additional for same day
- [x] Accumulator EV matrix UI — collapsible 2-leg combination grid, colour-coded EV, correlation-adjusted
- [x] Dutching calculator — optimal stake distribution, guaranteed return calculation, odds format display
- [x] Arbitrage detector — Σ(1/odds) < 1 check across bookmakers, stakes for target profit
- [x] Sharpe ratio + max drawdown on flat-stake strategy — both in API and terminal report
- [x] Portfolio analytics — P&L tracking, Kelly sensitivity, market/league/edge breakdowns

---

## Phase 5 — Model Validation & Transparency
- [x] Full backtesting results page (hit rate and Brier by league, season, year)
- [x] Calibration diagram (reliability plot with confidence intervals)
- [x] Model comparison table (all models side by side)
- [x] Walk-forward accuracy chart (how hit rate changed over 32 seasons)
- [x] Closing line value history (CLV per bet, cumulative CLV chart)
- [x] Prediction log (every prediction ever made, timestamped, SHA256 hashed)
- [x] Monthly accuracy report (automated, updated after each round of fixtures)
- [x] Diebold-Mariano test results vs naive baseline
- [x] Hosmer-Lemeshow calibration test results
- [x] Permutation feature importance (which features matter most per league)

### Phase 5 Completion — July 2026
- [x] Walk-forward accuracy line chart — 1993–2026 with Elo baseline reference line
- [x] Hosmer-Lemeshow calibration test — χ²=9.14, p=0.33, well calibrated
- [x] Diebold-Mariano significance test — DM=-1.39, p=0.165, ensemble better but not significant
- [x] Feature importance chart — top 15 XGBoost gain features, horizontal bar chart
- [x] Model comparison table — live from API replacing hardcoded values
- [x] Statistical tests section in BacktestReport UI
- [x] Feature importance endpoint GET /api/backtest/feature-importance
- [x] DM test endpoint GET /api/backtest/dm-test

---

## Phase 6 — Design & Product Polish
> The platform is technically impressive but reads like a developer tool. This phase makes it look and feel like a premium product that justifies charging money.

> **TERMINOLOGY (Nov 2026 v0 landing-page session — supersedes earlier framing throughout):** (1) "Bet of the Day" → **"Today's Tips"** — the daily hook is the full RANKED SET of today's value bets ("today's tips, ranked by edge"), led by the strongest, NOT a single hero pick. Older "Bet of the Day" mentions below/elsewhere (incl. the Session Log) mean Today's Tips unless they describe history. (2) "World Cup Hub" → **"International football hub"** — evergreen (World Cup, Euros, qualifiers, Nations League, friendlies), not tied to one tournament. (3) Multi-sport includes **user sport-selection** — users pick which sports they follow, and that filters their tips/feed.

> Note: Several product ideas span phases — per-sport Today's Tips, email digests, notification prefs need multi-sport (Stage 4) and email (Phase 10) infrastructure to fully ship. Phase 6 builds the BUILDABLE-NOW versions and designs signup/nav/onboarding/match-detail to ASSUME all of it is coming, so nothing needs retrofitting. Football-first, multi-sport-ready.

### The Core Product Principle

> **This is a usable PRODUCT, not a data dump.** The platform is deeply data-rich, but the user must NEVER be met with an overwhelming wall of data — no "60 rows of a table" on login. Every screen leads with the conclusion and the single most useful thing; all the depth (78 features, 7 models, full stats, SHAP, historical tables) remains ACCESSIBLE but is progressively disclosed, one deliberate click deeper. The test for every screen: "would a smart person who isn't a data scientist immediately understand what they're looking at and what to do next?" If not, it's showing too much. Clean, professional, confident, easy — the data serves the product, the product is not a wrapper around the data. This principle VETOES individual design decisions: when in doubt, show less.

### Design Principles (read before starting any Phase 6 task)
- [ ] Trust-at-a-glance hierarchy — every screen leads with ONE confident number or visual, not multiple equal-weight panels. Dashboard hero = single big metric (live CLV or edge found this week), everything else secondary
- [ ] Restraint palette — one brand colour (warm orange/coral accent — see Palette in Design Direction; was emerald), one positive accent, one negative accent, everything else warm near-black neutrals. No ad-hoc colours anywhere. Two heading sizes, one body size, one small size — no exceptions
- [ ] Typographic respect for numbers — tabular figures (font-variant-numeric: tabular-nums) in every table, consistent decimal places site-wide (2.50 never 2.5), consistent probability precision everywhere
- [ ] Progressive disclosure — surface states the conclusion plainly ("Model sees 12% more chance than the bookmaker"), calculations/Kelly/model breakdown one tap deeper. Methodology page carries credibility for diggers; surface stays clean
- [ ] Confidence bands — wire prediction_uncertainty metadata (built in Phase 2 Batch 3) into prediction displays as visual confidence indication
- [ ] Motion only where data changes — probability bars fill once on load, numbers tick on update, nothing else animates. Movement = "this is live"
- [ ] Designed empty states — off-season/no-value-bets/no-data states are designed screens with a next action ("Leagues return August 15 — see the International football hub"), never blank tables or bare spinners. NOTE: launching into off-season means the no-live-bets state IS the first impression for many users
- [ ] One signature element — pick ONE distinctive visual (edge meter, Elo chart style, or bracket tree) and over-invest in it; that's what gets screenshotted and shared. DECIDED: the edge meter — a stacked bar showing bookmaker-implied probability (grey) + the model's additional edge (accent colour — now warm orange/coral per the approved v0 design, was soft blue ~#3b74d4), the accent segment IS the edge. Lives on every value bet card and the lead Today's Tips card. This is the screenshot asset.
- [ ] Design tokens doc first — before any page redesign, write frontend/DESIGN.md with colour tokens, type scale, spacing scale; every subsequent frontend task references it (same pattern as the shared feature pipeline, but for design)
- [ ] Product-demo imagery (not stock photos) — for a quant/betting product, imagery = the PRODUCT shown beautifully: animated edge meter filling, numbers ticking up, clean product screenshots, at most one tasteful hero graphic. AVOID stock footballer photos, generic "data" imagery, decorative gifs — they read cheaper, not premium. Credibility comes from clean typography and confident numbers (like a trading terminal), not pictures. A short looping gif of the real edge meter animating = excellent landing-page demo.
- [ ] Progressive disclosure is the antidote to overload — the platform is deeply data-rich (78 features, 7 models, SHAP); the DISCIPLINE is that every surface shows the CONCLUSION (Arsenal, +11% edge), with the data mountain one click deeper. Most users never dig; the depth being there builds trust even unused. Every screen: hide 90%, surface the 10% that matters.
- [ ] "No-bet day" honesty mechanism — some days the model finds no strong value. A trustworthy product SAYS SO ("no strong edges today — we don't force picks") rather than manufacturing weak tips to fill Today's Tips. Protects the track record from forced low-confidence picks dragging it down, and is itself a powerful trust signal — the discipline that separates FormCast from tipsters who post daily regardless. PHILOSOPHY: never force a pick to fill a slot.

### Visual Design
- [ ] Design system — **do this first; artefact is frontend/DESIGN.md** — establish colour tokens, type scale, spacing scale. Warm orange/coral accent as primary, warm near-black as background (per the approved v0 design — was emerald/slate), clear hierarchy between primary/secondary/muted text. Every subsequent Phase 6 task references this doc
- [ ] Component library audit — standardise cards, badges, tables, filters across all pages so nothing looks inconsistent
- [ ] Micro-animations — subtle transitions on data loading, card hover states, probability bar fills on page load
- [ ] Icon consistency — single icon library throughout (lucide-react already imported, ensure nothing uses ad-hoc alternatives)

### Key Page Redesigns
- [ ] **Full site remodel — "bring it to life + findability" (Nov 2026 direction)** — the whole-site UX pass the Core Product Principle demands. GOALS: (1) users can actually FIND what they want — nav/IA restructured around what people come for, not a feature dump across 5 dropdowns; (2) every screen leads with ONE thing, progressive disclosure, kill flat lists (dashboard especially); (3) "bring it to life" — restrained, purposeful motion only (edge meter fill, numbers ticking, probability bars on load) — NOT decorative animation, which cuts against a trust/quant product; (4) consistency — replicate the Backtest page's honest plain-English framing and the Ratings/H2H visual quality across weaker pages; (5) DESIGN.md is OPEN TO REVISION to match current taste (clean/minimal/modern/restrained-motion) — treat as updatable, rewrite as output of the remodel. Precedes/absorbs the individual page-redesign items below. Mobile-first throughout.

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
- [ ] **NEXT STEP — integrate the v0 React code into the real repo** (a proper build task, not done yet): wire real auth/signup into the CTAs, feed REAL data to the Today's Tips teaser + the animated public ledger (from the SHA-256 prediction log), replace placeholders (ROI figure, founder photo/bio), and fold the palette/type tokens into DESIGN.md.

**LANDING PAGE — build FIRST (new, high-priority).** Currently a logged-out visitor gets the Dashboard + a sign-in modal — NO real landing page. A proper landing page is the biggest "now I get it in 5 seconds" lever and the thing to show people. Built in the locked design direction. (Supersedes/absorbs the existing "Landing page redesign" item.)

- [x] **Structure — DECIDED: CLOSED FRONT DOOR.** Logged-out nav is ONLY: About · How it works · Log in · Sign up free. No browsable product nav when logged out — product nav + full features appear only AFTER login. Sections, top to bottom:
  1. **Hero** — the promise + ROI proof numbers + sign-up CTA (approved design: animated public-ledger hero).
  2. **Gated Today's Tips teaser** — "today's tips, ranked by edge — sign up to unlock" block, NOT live pick cards.
  3. **About** — founder photo + bio (the trust differentiator vs anonymous tipsters).
  4. **How it works** — 3 plain steps.
  5. **Feature grid** — "Everything inside, once you're in": promote breadth, one line per feature, no data shown.
  6. **Email capture** — collect addresses now; the Resend digest gets built later (Phase 10).
  7. **Compliance footer** — 18+, BeGambleAware/GamCare, not-advice/past-performance disclaimers (see Pre-Launch Compliance).
- [x] **Headline framing — DECIDED: ROI-LED.** "+X% return per bet, logged" is the headline number — the one metric a normal person can interpret on their own. Accuracy (64.4% non-draw) and CLV sit below it, clearly labelled. This RESOLVES part of the CRITICAL hit-rate framing decision (top of NEXT UP) — option (b). ⚠️ Confirm the REAL ROI figure from the 608 settled bets before it ships.
- [x] **Freemium on landing — DECIDED: Today's Tips gated behind signup** (teaser only on the landing page). Drives signups + the email list over anonymous browsing. (Reconciled: the Value Bets editorial hierarchy and Multi-sport nav/IA items below now say Today's Tips is free WITH AN ACCOUNT, not anonymous.)

**STILL OPEN (landing page):**
- [x] Typeface — decided in the v0 mockup (Fraunces-style serif + grotesk); see Typography above.
- [ ] Real ROI number — pull from the settled track record (608 settled bets) before the hero ships.
- [ ] Founder photo + bio — placeholders for now.

### Key Page Redesigns (continued)
- [ ] **Multi-sport framework (structural, build during remodel)** — design the nav, URL structure (/football/..., sport switcher), data shape and component props to ASSUME multiple sports from the start, even though only football ships. Football first, GAA/tennis/etc as visible "coming soon". Cheap now, expensive to retrofit. **USER SPORT-SELECTION (Nov 2026):** tips/value bets span multiple sports eventually, and users SELECT which sports they follow — sport-selection is a stored user preference that FILTERS their Today's Tips, feed, and (later) email digest. Captured at signup (see Signup & onboarding) and editable in settings; football is the only selectable sport at launch, others shown as "coming soon". Landing copy already frames it: "football now — more sports coming, pick the ones you follow." (Expands the existing "Multi-sport-ready navigation & IA" item below — see it for the journey/nav detail.)
- [ ] Dashboard redesign — hero metric strip (value bets identified, hit rate, CLV) → live value bets → upcoming fixtures → ratings snapshot. Each section visually distinct with clear heading
- [ ] Value Bets page redesign — card layout instead of table rows, visual edge meter, bookmaker logo/name prominent, Kelly stake displayed clearly
- [ ] Value Bets editorial hierarchy (Today's Tips) — **REVISED Nov 2026: "Bet of the Day" → "Today's Tips".** The daily hook is the full RANKED SET of today's value bets — "today's tips, ranked by edge" — not a single hero pick. It's still curated, not a flat list, and still LEADS with the strongest (anti-overwhelm principle: best first, full list below): (1) LEAD TIP — the top-ranked tip gets the most prominent card: full edge meter + plain-language "model sees X%, book implies Y%" + Kelly/book/odds row. (2) NEXT STRONGEST — the next 3-4 as compact edge-meter cards. (3) REST OF THE SET — the remaining ranked tips below ("View all N →"), filterable. Ranked by EDGE × CONFIDENCE, not raw edge (raw-edge sort surfaces noisy longshots — wrong thing to lead with; confidence-weighting protects trust positioning). Filtered to the sports the user follows (see Multi-sport framework → user sport-selection). All odds render in the user's chosen format (decimal/fractional/American) via the Tier 6 oddsFormat preference. FREEMIUM: Today's Tips is FREE WITH AN ACCOUNT — not visible to anonymous logged-out visitors (landing page shows a gated "sign up to unlock" teaser). It's the daily proof + marketing/screenshot asset + retention hook, behind the signup gate. The full ranked set stays FREE FOREVER — tips are never paywalled (see MONETISATION MODEL in v1.0 Launch Definition). Off-season: pulls from the International football hub so it's never empty. (Supersedes the singular "Bet of the Day" framing throughout.)
  - Note: MOBILE-FIRST — huge share of betting traffic is phone, in-the-moment. Edge-meter cards, the lead tip, the ranked list must work single-column at 375px, stacking cleanly. Build mobile-first, not desktop-retrofitted.
  - Note: DATA DEPENDENCY — "ranked by edge × confidence" requires per-bet confidence (the prediction_uncertainty metadata from Phase 2 Batch 3). Verify /api/markets exposes it before building the hero; if absent, surface it in the API first or compute a client-side proxy. Recon this before the Value Bets build.
  - Note: MULTI-SPORT SHAPE — Today's Tips is one ranked set across all the sports a user follows (filterable/groupable by sport), not a separate hero per sport. Retention mechanic: multi-sport bettor opens daily to see all their sports' tips, ranked, in one place. Football ships first; structure the data/component to accept a sport dimension from the start.
- [ ] Everything-clickable rule + canonical Match Detail hub — HARD RULE: anything naming a match anywhere on the site (value bets list, dashboard fixtures, team profiles, results, accumulator legs) is a link to that match's full detail view. Build ONE canonical, excellent, SPORT-AGNOSTIC match detail page as the destination — designed once, works for any sport. Full progressive disclosure: seven-model contribution breakdown, H2H, form, xG, confidence band (prediction_uncertainty). Decide card→detail navigation in the Value Bets build even if the detail view ships slightly after, so it's not retrofitted. This is what makes the site feel whole rather than disconnected pages. (Merges the prior "Match detail view (card tap-through)" item.)
- [ ] Landing page redesign — above-fold must convert. Large headline, 3 key stats displayed huge, single Sign Up CTA, below-fold: how it works, sample value bets, track record [SUPERSEDED — absorbed by the "LANDING PAGE — build FIRST" item in Design Direction & Tooling above]
- [ ] International football hub (renamed from "World Cup Hub", Nov 2026) — EVERGREEN showcase for international football: World Cup, Euros, qualifiers, Nations League, friendlies — not time-locked to one tournament. Should make someone immediately understand what FormCast does for international football. Builds on the existing World Cup 2026 page/bracket work (see International section).
- [ ] Multi-sport-ready navigation & IA — even though only football ships now, design nav + URL structure to assume multiple sports (e.g. /football/value-bets not /value-bets; a sport switcher with football active and GAA/tennis/etc as visible "coming soon" siblings). Cheap to plan now, expensive to retrofit. The nav sells AND scales. JOURNEY: (1) PRIMARY JOURNEY: cold visitor sees a clear one-line promise ("Bets where the model disagrees with the bookmaker. Every result logged — win or lose.") + three huge proof stats (hit rate, +19% mean CLV, ~3,500 bets logged) + one CTA + a gated Today's Tips teaser ("sign up to unlock" — Today's Tips is free WITH AN ACCOUNT, not shown to anonymous visitors; it stays the daily hook/retention mechanic once signed up). (revised Nov 2026: free with signup, not anonymous — see Design Direction & Tooling) (2) NAV structured around the journey not features: Today's Tips · Track Record · How It Works · International · [account] — the nav sells (this is the LOGGED-IN nav; logged-out is the closed front door). (3) OFF-SEASON HOME = first impression for many: lead with Track Record + International football hub + Today's Tips + "first EPL value bets Aug 15 — sign up" email capture; the empty state becomes the conversion funnel. (4) LOGGED-IN vs LOGGED-OUT states defined. Do this flow definition BEFORE the landing/dashboard/value-bets page redesigns so they serve it. (Merges the prior "Navigation & first-visit flow" item, which supersedes the Phase 7/9 "onboarding tour" items.)

- [ ] Signup & onboarding flow — minimal signup (email/password or Google, no long forms — every extra field loses users), then IMMEDIATE value (land on a dashboard with live Today's Tips, not an empty screen). During signup capture SPORT + TEAM preferences ("which sports do you follow?", "any teams?") — one light step that personalises dashboard, emails, and the Today's Tips feed from day one. Sport-selection is the stored preference that filters tips (see Multi-sport framework). Optional light guidance, NOT a forced multi-step tour (best onboarding is a product obvious enough to need almost none; a long tour is a band-aid for confusing UI). Supersedes the Phase 7/9 "onboarding tour" items.
- [ ] Acca of the Day — a curated daily accumulator (2-4 legs, model's best combined-value multi) as an editorial pick alongside Today's Tips. Accas are the most-screenshotted bet type in betting culture — high shareability, strong following-builder. Uses the EXISTING accumulator engine + correlation correction (Phase 4) — mostly surfacing built capability as a daily hero. FREEMIUM: PRO feature — acca builder + Acca of the Day are both in the Pro layer (see MONETISATION MODEL in v1.0 Launch Definition).
  - Note: CROSS-MARKET ACCAS — best multi is often a MIX across markets (e.g. Arsenal win + over 9.5 corners elsewhere + BTTS in a third). Accumulator engine (Phase 4) must select legs across all market types. CORRELATION CAVEAT (credibility landmine): same-match multi-market legs are correlated (team dominating → more corners AND more likely to win); an acca of "Liverpool win + Liverpool over 9.5 corners + Liverpool BTTS" looks like 3 legs of value but is ~1 correlated bet — combined odds badly overstate true edge. Sharp bettors (the best audience) spot naive correlated accas instantly and lose trust. Phase 4 correction handles same-league/same-day; same-match cross-market correlation is harder and MUST be respected — ideally accas avoid stacking correlated same-match legs unless correlation-adjusted. Correlation-awareness here is a credibility REQUIREMENT, not a nice-to-have.
- [ ] Multi-market value bets (all markets, not just 1X2) — END-GOAL VISION: Today's Tips, Acca of the Day, and the value bets list surface edges across ALL modelled markets, not only match result. The four market models are built and live: corners, cards, BTTS, over/under goals. A day's Today's Tips ranks edge×confidence picks across ALL markets together — the lead tip some days a win pick, some days "over 9.5 corners", "under 2.5 goals", or "over 3.5 cards".

  **STEP 1 — RECON FIRST (small, cheap, gates everything):** Investigate The Odds API market coverage + cost for the leagues we model. Which markets are available: totals (goals), BTTS, corners lines, cards lines? What does each cost in API credits per call, and is coverage complete or patchy across EPL/Championship/La Liga/etc? Likely outcome: goals + BTTS well-covered and cheap; corners + cards more expensive or patchy — which would STAGE the rollout (do well-covered markets first). Do NOT build anything until this recon answers what's actually priceable.

  **STEP 2 — extend the value screener** (fetch_live_odds.py / value_betting.py, currently primarily 1X2) to compare each market model's output vs that market's bookmaker line, ranking all edges uniformly on one scale — for whichever markets STEP 1 confirms are viable.

  **STEP 3 — market-appropriate "why this bet"** reasoning (corners pick cites referee tendencies + team corner rates, not form/xG).

  **STEP 4 — display:** edge meter + card layout work identically across market types; build the Value Bets page / Today's Tips multi-market from the start so it's not redesigned later.

  SEQUENCING NOTE: this is a value-PIPELINE extension (backend) that Phase 6 then displays. Build the pipeline (steps 1-3) BEFORE the Value Bets page redesign, or the page gets rebuilt. This is a significant product build (~comparable to a chunk of the model work), not a display tweak — Phase 6 is now genuinely large by design.
- [ ] "Why this bet?" plain-language transparency — every tip / value bet / acca leg explains ITSELF in plain English ("model rates Arsenal 53% vs bookmaker's 42% because of home record, recent xG, and opponent form"). Progressive disclosure applied to trust — this is what separates FormCast from anonymous tipsters. One tap deeper = the full seven-model breakdown.
- [ ] Peak-density design (big weekends / Champions League days) — design for high-volume days, not just quiet ones. On a big Prem Saturday or CL Tuesday there may be 8-12 value bets at once; group by matchday/competition, offer a "this weekend" view, so density never becomes an overwhelming wall. Ties to the "not overloaded with data" principle.

### Trust Signals
- [ ] Track record section on landing — show the prediction log numbers, CLV, hit rate prominently as social proof
- [ ] "As featured in" / methodology credibility section
- [ ] Live counter — value bets identified today, updating in real time
- [ ] "Yesterday's Tips — results" — publicly show the previous day's ranked tips (led by the top tip) and how each settled. Closes the honesty loop visibly ("here's what we picked, here's what happened"). Strongest trust-building feature available; follows on from Today's Tips. Draws from the logged prediction record (win or lose, per positioning).
- [ ] Shareable Today's Tips card image — auto-generated share image (Twitter/Telegram/social) of the day's top tips, since Today's Tips is the primary marketing asset. High-leverage for audience growth; build after the core hero ships. Full feature, not part of first Value Bets build.
- [ ] Public proof page — a permanent, shareable URL showing the full verified track record (the SHA256 prediction log made beautiful): every prediction ever made, timestamped, hash-stamped, with running hit rate / CLV / ROI. This is the page you LINK when someone says "prove it." Turn the existing SHA256 accountability ledger (Phase 4/17) into a public-facing, screenshot-worthy trust asset. Big conversion lever for a skeptical audience.
- [ ] Odds freshness / "price may have moved" indicator — value bets go stale as odds move, so show a small freshness signal on each pick ("odds checked 2h ago", or a subtle "price may have moved — verify at bookmaker" note). Protects trust and sets honest expectations. Minor build, meaningful for credibility. Ties to the live-odds refresh cadence (daily/near-real-time).

### Pre-Launch Compliance
- [ ] Responsible gambling & compliance footer — UK betting-advice norms: 18+ notice, BeGambleAware/GamCare links, "past performance does not guarantee future results" disclaimer, clear "not financial advice" framing. Cheap to add, bad to miss pre-launch. Also review affiliate/advertising compliance if bookmaker links are used.

### Visual Assessment — November 2026 (live site reviewed)
- Confirmed: the Dashboard is an infinite flat list of ~40 equal-weight value-bet rows — exactly the "60 rows on login" the Core Product Principle warns against. No focal point, no ranking, no curation.
- Confirmed: Value Bets page is already card-based (3-col grid, Model%/odds/edge/implied) — good foundation, close to right.
- Confirmed: visual design foundation (emerald-on-black, restraint, typography) is SOLID — needs curation/hierarchy, NOT a from-scratch redesign.
- **#1 PHASE 6 PRIORITY:** the "Value Bets editorial hierarchy (Today's Tips)" item is THE next build — kill the flat list, lead with the strongest tip + next few + collapsed rest of the ranked set. This single change fixes the "too much stuff" problem across dashboard + value bets.
- NOTE: DESIGN.md is open to revision to match current taste (clean/minimal/restrained-motion); treat it as updatable, not fixed.

---

## Parked Technical Fixes (found Nov 2026, not yet done)
- [x] **DONE (fixed Nov 2026, commit 9ae8a70)** — Uncovered-league filter — new scripts/league_coverage.py (COMP_TO_LEAGUE + COVERED_LEAGUE_CODES + is_covered_league(), shared by predict_upcoming / publish / settle / API); publish_predictions.py skips uncovered leagues going forward; API derives a settled | pending | not_tracked status per row with the CSV/hashes untouched; frontend shows a "NOT TRACKED" badge + tracked-only totals. Result: 617 tracked / 493 not tracked (the original ~394 estimate missed 34 rows + the 65 FIFA World Cup rows, which are not_tracked pending a separate international settlement job).
- [ ] Settlement name-mapping bug — ~9 covered-league predictions stay pending because settle can't resolve names like Stade Rennais FC 1901, CA Osasuna, Athletic Club, ES Troyes AC, Olympique Lyonnais, Angers SCO, Stade Brestois 29. These ARE settleable leagues (Ligue 1, La Liga) — the result exists, the name just doesn't match. Add these to the name resolver / TEAM_NAME_MAP.
- [ ] Rescheduled-match void rule — ~9 predictions stuck unsettled because the match moved dates; bookmakers void bets not played within ~48-72h. Add a void status.
- [ ] Stale xG — ingest_xg_data.py stops at 2024-25; no xG for 2025-26 or 2026-27, those features use defaults. Extend or confirm Understat has current data.
- [ ] **Prediction Log page 404** — page calls a dead API endpoint; settled data (608) exists but the public track record page doesn't load. Find the endpoint the frontend calls vs what the API serves and fix. HIGHEST priority (see QA sweep).
- [ ] Hardcoded "2025-26" season (one bug family — fix with a single dynamic current-season helper) — confirmed live in QA sweep:
  - [x] **DONE (fixed Nov 2026, commit 1278797)** — **Tournament Simulator (functionally dead, not cosmetic)** — tournament_simulator.py:22 TODAY="2026-05-21" + line 177 "2025-26"; page simulated the finished 2025-26 season. Fix: new scripts/season_utils.py current_season() helper (July rollover rule); TODAY → date.today(); simulator derives remaining fixtures dynamically (double round-robin, with early-season fallback to last season's team list); output CSV gained season / matches_played / matches_remaining; Tournament.jsx season label + counts + "season complete" banner now read from those columns.
  - [x] **DONE (fixed Nov 2026, commit 1278797)** — **live.py stale-season spots** — line 536 (_CURRENT_SEASON, corners/cards season averages) and line 810 (team-profile current-season stats) now call current_season(date.today()) per-request (survives the July rollover without a server restart). This also makes the H2H "Season Stats" heading dynamic, since it renders the API's `season` field.
  - [x] **DONE (fixed Nov 2026)** — **Matches.jsx season filter** — SEASONS list topped out at 2025-26, so users couldn't filter to 2026-27 at all. Now generated from new frontend/src/season.js (`currentSeason()` / `recentSeasons()`, a JS mirror of season_utils.current_season() with the same July rule — keep the two in sync): current season + 3 prior, newest first.
  - [x] **DONE (fixed Nov 2026)** — **H2H.jsx:314 fallback label** — `?? '2025-26'` → `?? currentSeason()` (from frontend/src/season.js — auto-rolls each July, never goes stale). No "2025-26" literals remain anywhere in frontend/src.
  - [ ] **Still outstanding — shared-helper migration:** predict_upcoming.py `_current_season()` uses an AUGUST rule (month >= 8); api/app.py `_season()` uses a JULY rule (month >= 7). They disagree, and the 2026-27 data starts 2026-07-31, so the August rule mislabels late-July matches as the previous season. Deliberately left out of the Nov 2026 fix to avoid touching the working prediction pipeline. Migrate both to scripts/season_utils.current_season() in one change, then re-check any season-filtered output from predict_upcoming.
- [ ] Investigate the Nov 8 2026 FAILED Railway deploy (daily international update) — glance at logs.
- [ ] Node 20 / Ubuntu deprecation warnings in GitHub Actions — bump actions/checkout@v4→v5, setup-python@v5→v6 sometime.

---

## Phase 7 — UX & Design Polish
- [x] Landing page redesigned — hero, three use cases, model steps
- [x] Nav reorganisation — grouped nav with Dashboard as default
- [x] Dashboard home page — live value bets, upcoming fixtures, top ratings, model performance
- [ ] Accumulator builder flow — select matches from Live/Upcoming page and add directly to accumulator builder
- [ ] User journey improvement — clear path from landing → value bets → accumulator → stake calculation
- [x] Matches page with shot, corner, card stats and league/team filtering
- [x] Filtering and sorting on all pages (league, date, outcome, edge filters)
- [x] Fix remaining duplicate team names (2,718 cells fixed)
- [x] Matches page with filtering and pagination
- [x] Team profile page — Elo history, form, season stats, H2H
- [ ] Redesign dashboard with proper data visualisation hero section
- [ ] Elo ratings chart — animated bar chart race (top 20 teams over time)
- [x] Calibration curve chart
- [x] Tournament tooltips and season complete warning
- [ ] Cumulative P&L chart (flat stake simulation over time)
- [ ] Brier score trend chart (rolling 90-match window)
- [ ] SHAP waterfall chart per match (why did the model predict this?)
- [x] H2H comparison page
- [x] League filter on ratings page (show only EPL, only La Liga etc)
- [x] Mobile responsive layout
- [ ] Dark/light mode toggle
- [x] Loading skeletons instead of spinners (partially — auth loading states done, full skeleton screens pending)
- [ ] Match prediction card (upcoming fixtures with probability breakdown)
- [ ] Tournament simulation visualisation (probability treemap per team)
- [ ] Value bet history chart (CLV over time, ROI by league)
- [ ] Accumulator builder UI (interactive leg selector, real-time EV calculation)
- [ ] Weather display on match preview — wind, rain, temp for upcoming fixtures with impact assessment
- [ ] Home/away form split on match preview — last 5 home results vs last 5 away results
- [ ] Current form visualization — last 5 results dots with goals scored/conceded
- [ ] Global search — find any team, match, or league instantly across the whole site
- [ ] PWA support — installable on mobile home screen, offline support
- [ ] Onboarding tour — first-time user walkthrough (Shepherd.js) [SUPERSEDED — see Phase 6 Signup & onboarding flow]
- [ ] Custom domain (formcast.io or similar)
- [ ] Design overhaul — site currently reads as a developer tool, needs to look like a premium product. Priority: dashboard hero, value bet cards, team profile pages, landing page conversion
- [ ] Dashboard hero section — big focal-point number or chart immediately communicating scale and sophistication (e.g. animated counter for value bets identified, live Elo chart)
- [ ] Value bet cards redesign — currently text-heavy rows, should look like trading cards with visual probability bars, odds highlighted, edge displayed prominently with color coding
- [ ] Landing page conversion optimisation — headline, social proof numbers (3,525 value bets, 128k matches, 68.7% hit rate) displayed large and front-and-center, single clear CTA above fold
- [ ] Typography and spacing overhaul — more whitespace, larger headings, consistent type scale, premium feel without changing functionality
- [ ] Team profile page visual hierarchy — breathing room, better section structure, Elo chart more prominent
- [ ] Color-coded probability displays — win/draw/loss shown with green/grey/red visual bars throughout, not just numbers

---

## Phase 8 — Mathematics & Methodology Documentation
- [x] How It Works page — model explanations, ensemble flow, glossary, data sources
- [ ] Elo explainer (K-factor, home advantage, MoV multiplier, what ratings mean)
- [ ] Dixon-Coles explainer (bivariate Poisson, tau correction, temporal decay)
- [ ] Glicko-2 explainer (RD, volatility, inactivity penalty)
- [ ] Ensemble explainer (how models are stacked, what meta-learner weights mean)
- [ ] xG explainer (what expected goals measures, why it predicts better than goals)
- [ ] Interactive probability calculator (enter two team ratings, see win probabilities)
- [ ] Feature importance visualisation (SHAP beeswarm across all 78 features)
- [ ] Glossary page (Brier score, CLV, Kelly criterion, EV, overround etc)

---

## Phase 9 — UX Excellence
> Note: UX improvements apply platform-wide. Mobile responsive layout is critical given the majority of sports betting happens on mobile devices.

- [ ] Onboarding tour — first-time user walkthrough explaining each page (Shepherd.js or similar) [SUPERSEDED — see Phase 6 Signup & onboarding flow]
- [ ] Global search — find any team, match, or league instantly across the whole site
- [ ] Keyboard shortcuts — power user navigation (G+R = ratings, G+P = predictions etc)
- [ ] Notification centre — in-app notification bell for value bets and match alerts
- [ ] Print/export — download predictions, value bets, or match previews as PDF or CSV
- [ ] Embed widget — let other sites embed FormCast win probabilities via iframe or JS snippet
- [ ] Progressive Web App (PWA) — installable on mobile home screen, offline support
- [ ] Accessibility audit — WCAG 2.1 AA compliance, screen reader support, keyboard navigation
- [ ] Internationalisation — Spanish, German, French, Italian language support
- [ ] Performance optimisation — lazy loading, code splitting, sub-2s load time target
- [ ] Dark/light mode toggle — respect system preference by default
- [ ] Loading skeletons — replace all spinners with skeleton screens
- [ ] Error boundaries — graceful degradation when individual components fail
- [ ] Breadcrumb navigation — clear location context on all pages
- [ ] Recently viewed — quick access to last 5 teams or matches viewed

---

## Phase 10 — Business & Monetisation
> Note: All business, security, UX, and data phases apply across all sports — football, GAA, tennis, golf, NFL, basketball, horse racing, and any future sport additions. Features built for football first, then extended to each sport as data becomes available.

- [ ] Pricing page — Free vs Pro vs Elite tiers clearly explained with feature comparison table (PRIORITY — blocks revenue)
- [x] User accounts — Supabase Auth, save favourite teams, personalised dashboard
- [ ] Pro tier features — advanced filters, more predictions, API access, no rate limits
- [ ] Email alerts — Resend API, weekly digest + instant alerts for watchlist teams (free tier = 3k emails/month)
- [ ] Push notifications — browser push for live value bets and match alerts
- [ ] Watchlist — users save teams and get notified when they have value bets
- [ ] API access tier — sell data access to developers with key management
- [ ] Affiliate bookmaker links — deep-link to Bet365, Paddy Power, Betfair on value bet cards
- [ ] Stripe subscriptions — Pro tier billing, webhook handling, subscription management (PRIORITY — blocks revenue)
- [ ] Referral program — share FormCast, get a month free
- [ ] Team/league following — personalised feed based on followed teams
- [ ] PostHog analytics — track which pages and features users actually use
- [ ] Daily/weekly multi-sport email digest — THE retention & re-engagement engine for a subscription product (pulls users back when they forget to open the app). "Today's Tips across the sports you follow (football, GAA, tennis...)" + acca of the day + how-we-did recap. FREEMIUM: PRO feature — alerts + daily digest are in the Pro layer (see MONETISATION MODEL in v1.0 Launch Definition); the tips themselves stay free in-app. Resend API (free tier 3k emails/month). This is central to the product, not a minor alert feature — flag as PRIORITY retention.
- [ ] Notification preferences & control — granular control or users unsubscribe entirely: which sports, daily vs weekly, which bet types (singles/accas), email vs push. Under-designed notification prefs kill email programs. Powered by the sport/team preferences captured at signup.
- [ ] Weekly "how did we do" recap — periodic honesty-loop recap (email + page): "this week: 23 value bets found, 14 won, +8% ROI, best pick was X." Turns skeptics into believers — critical for a trust-first product. Extends the "Yesterday's Tips — results" trust signal.
- [ ] Bet tracking / "I placed this" — let users mark value bets they actually took, building a personal P&L and bet history. Strong stickiness/retention feature (their own track record living in the app). Powered by existing settle/results logic. Likely post-launch polish but design the value-bet card to accommodate a "track this bet" action so it's not retrofitted.
- [ ] Onboarding email sequence — first-week emails converting signup → active user ("how to read a value bet", "your first Today's Tips"). Distinct from the daily digest; known retention lever.
- [ ] Product analytics & funnel observability — beyond Sentry (errors): which features get used, where users drop off in signup, what converts free→paid (PostHog). Can't improve what you can't see; guides all post-launch decisions.

> NOTE: Odds API free tier = 500 credits/month. Weekly pipeline is fine; DAILY multi-sport odds refresh would exceed it — paid tier needed before daily cadence or multi-market expansion at scale.

---

## Phase 11 — Security & Rate Limiting
> Note: Security and rate limiting applies to the entire platform regardless of sport. Must be implemented before any paid tier launch.

- [ ] API rate limiting — per-IP rate limits (100 req/min free, 1000 req/min pro) using Flask-Limiter
- [ ] API key authentication — JWT tokens for pro tier API access
- [ ] CORS hardening — restrict allowed origins to known domains only
- [ ] Input validation — sanitise all query parameters, prevent injection attacks
- [ ] SQL injection protection — parameterised queries everywhere (Supabase handles most of this)
- [ ] XSS protection — Content Security Policy headers on all responses
- [ ] HTTPS enforcement — HSTS headers, redirect all HTTP to HTTPS
- [ ] Secrets management — rotate API keys regularly, never commit secrets to git
- [ ] Dependency scanning — GitHub Dependabot for vulnerable packages
- [ ] OWASP Top 10 audit — systematic review of common web vulnerabilities
- [ ] DDoS protection — Cloudflare in front of Railway API
- [ ] Bot detection — identify and throttle scraper bots
- [ ] Abuse prevention — detect and block unusual usage patterns
- [ ] Privacy compliance — GDPR cookie consent, data deletion requests, privacy policy
- [ ] Penetration testing — scheduled security audit before any paid tier launch
- [ ] Two-factor authentication — for admin/superuser accounts

---

## Phase 12 — Automation & Infrastructure
- [x] Automated weekly data ingestion — GitHub Actions, runs every Monday 6am UTC
- [x] Automated model retraining — Elo, tournament, value bets, backtest all automated
- [x] Automated tournament simulator refresh
- [x] Automated value bet generation — live odds via The Odds API
- [x] Scheduled prediction publishing — publish_predictions.py runs Monday via GitHub Actions
- [ ] Database backup — automated daily Supabase backup to S3
- [ ] Monitoring & alerting — Sentry for errors, UptimeRobot for uptime, PagerDuty for critical failures (Sentry + UptimeRobot broken out as PRIORITY items below and in NEXT UP; PagerDuty deferred until paid tier)
- [ ] Sentry error monitoring — free tier, catch Railway API errors automatically (PRIORITY — do this week)
- [ ] UptimeRobot monitoring — ping /api/health every 5 minutes, alert on downtime (PRIORITY — do this week)
- [ ] referee_fatigue_features.py in weekly pipeline — regenerate team_tendencies.csv every Monday
- [x] CI/CD pipeline — GitHub Actions
- [x] Railway health checks — /api/health endpoint verified healthy, manual full pipeline health check performed this session
- [x] Retry logic with exponential backoff — predict_upcoming.py fixture fetch now retries 3x (5s/15s/30s) on transient failures instead of immediately failing the whole pipeline
- [ ] Automated test suite — pytest for API, Playwright for frontend E2E tests
- [ ] Data quality checks — automated validation after each ingestion (row counts, nulls, date ranges)
- [ ] Ingest dedup — results.csv has 1,222 duplicate (match_date, home_team, away_team) key pairs (2,444 rows) where the same match was ingested under two different leagues (e.g. LaLiga + Segunda for 1993-94 Spanish teams); lstm_model.py now guards against merge inflation but root cause should be fixed in the ingest pipeline with a dedup step keyed on (match_date, home_team, away_team)
- [ ] Log aggregation — structured logging to Papertrail or Logtail
- [ ] Cost monitoring — Railway and Vercel spend alerts
- [x] Premier League and Championship sport keys fixed — were using wrong key names (soccer_england_premier_league, soccer_england_championship) instead of correct soccer_epl and soccer_efl_champ, confirmed against The Odds API's own /v4/sports endpoint. Recovered Premier League value bets that had been silently 404ing.
- [x] Ensemble auto-retraining in weekly pipeline — VERIFIED July 2026: all models retrain every Monday (workflow steps 8-16: corners, cards, BTTS, goals, NN, LSTM, Bradley-Terry, Dixon-Coles, XGBoost + meta-learner + draw classifier); fixed pickle commit (July 2026) so Railway backtest route no longer drifts from weekly retrains

---

## Phase 13 — Sport Expansion
### Soccer (additional data)
- [ ] Extend history to 1993 (football-data.co.uk archive)
- [ ] Understat xG integration (2014-present, top 5 leagues)
- [ ] FBref advanced stats (2017-present)
- [ ] Kaggle European Soccer Database (25k+ matches)
- [ ] Referee statistics database
- [ ] League of Ireland — scrape from Wikipedia season pages (en.wikipedia.org/wiki/{year}_League_of_Ireland_Premier_Division)
- [ ] Player-level stats API for prop betting (FBref, Opta, or StatsBomb)
- [ ] Corners and cards historical data (football-data.co.uk has some of this already)
- [ ] Referee database — historical cards/fouls/home bias per referee (from results.csv referee column)
- [x] Stadium coordinates database — data/reference/stadiums.csv; 442/444 teams filled (lat, lng, altitude_m, capacity); powers away_travel_km, altitude_diff, home_capacity_log features in ensemble_v2.py
- [ ] TransferMarkt integration — injury/suspension data, market values, manager changes
- [ ] Betfair Exchange API — live exchange prices for line movement tracking
- [ ] OpenWeatherMap API — weather at kickoff time (wind, rain, temperature) — infrastructure built (fetch_weather.py); only API key setup remains — see NEXT UP queue
- [ ] Squad rotation detection — cup game before league game pattern detection
- [ ] International break fatigue — performance drop after international duty
- [ ] Manager change tracking — manual or TransferMarkt, +8 Elo bounce signal
- [x] Distance travelled database — stadium lat/lng for all 442 clubs, travel km calculator — same artefact as stadiums.csv above
- [ ] Europa League historical data
- [ ] UEFA Conference League data 2021-present
- [ ] World Cup 2018 and 2022 full data
- [ ] MLS data — Major League Soccer 2010-present
- [ ] Women's football — WSL, NWSL, UWCL
- [ ] Brazilian Série A
- [ ] Argentine Primera División
- [ ] Portuguese Primeira Liga
- [ ] Turkish Süper Lig
- [ ] 8 more European leagues (Greek, Belgian, Danish, Norwegian, Swedish, Japanese, Chinese, Australian)

### Tennis
- [ ] Jeff Sackmann ATP dataset (500k+ matches, 1968-present)
- [ ] Jeff Sackmann WTA dataset
- [ ] Surface-adjusted Glicko-2 ratings
- [ ] Point-by-point Markov chain live model

### Golf
- [ ] DataGolf Strokes Gained API (free tier)
- [ ] Course-fit model (SG decomposition × course demand weights)
- [ ] Ordinal regression (P(top 5), P(top 10), P(make cut))
- [ ] Each-way market pricing

### NFL
- [ ] nfl_data_py play-by-play (free, 1999-present)
- [ ] EPA-based win probability model
- [ ] Drive-by-drive Markov chain
- [ ] Injury report integration

### GAA
- [ ] Import Derry club results from PreGame Edge (594 matches)
- [ ] All 32 county club results (scraping)
- [ ] Foireann API for live fixtures
- [ ] Dual-sport fatigue model (football + hurling — unique globally)
- [ ] xP (expected points) shot model
- [ ] GAA dual sport fatigue model — unique globally, football + hurling within 5 days performance penalty
- [ ] County team commitment model — intercounty players unavailable for club during championship
- [ ] GAA referee tendencies — cards and free counts vary significantly by referee

### Basketball
- [ ] NBA data — nba_api Python package (free, play-by-play, box scores, 1946-present)
- [ ] Elo ratings for all 30 NBA teams (adapt existing Elo pipeline)
- [ ] Four Factors model — eFG%, TOV%, ORB%, FT/FGA (Dean Oliver's framework)
- [ ] Player efficiency model — PER, BPM, VORP from basketball-reference
- [ ] Home court advantage model — NBA home teams win ~60% vs football ~55%
- [ ] Back-to-back fatigue model — teams playing second night of back-to-back perform measurably worse
- [ ] Rest days advantage — teams with more rest days win significantly more
- [ ] Travel fatigue — coast-to-coast travel within 24 hours
- [ ] Injury/load management — star player rest (load management) tracking
- [ ] Pace adjustment — high/low pace teams affect over/under significantly
- [ ] EuroLeague data — Basketball-Reference covers European competitions
- [ ] NCAA March Madness simulator — bracket prediction with seed-adjusted Elo

### Horse Racing
- [ ] Historical results data — Racing API, Timeform, or free Kaggle datasets (UK/Ireland/US)
- [ ] Speed ratings model — convert finishing times to standardised speed figures adjusted for going and distance
- [ ] Going adjustment — horses perform differently on Firm, Good, Soft, Heavy ground
- [ ] Distance preference model — horses have optimal trip ranges, performance degrades outside them
- [ ] Trainer form — trainer win % by course, distance, going, and season phase
- [ ] Jockey form — jockey win % by trainer combination, course, and class
- [ ] Draw bias model — starting stall position significantly affects win probability at certain tracks
- [ ] Course specialist — horses with multiple wins at the same track outperform
- [ ] Class drop/rise — horses dropping in class are statistically more likely to win
- [ ] Days since last run — optimal return windows vary by horse age and trainer
- [ ] Weight carried — every extra pound reduces speed by approximately 1 length per mile
- [ ] Sectional times — early pace vs late pace split times (requires premium data)
- [ ] Market model — Betfair Exchange SP as a benchmark probability (most efficient horse racing market globally)
- [ ] Each-way value model — identify races where place market offers better EV than win market
- [ ] Ante-post vs day-of price movement — early movers vs morning movers vs steamer patterns
- [ ] Irish racing — Horse Racing Ireland results free via HRI website
- [ ] UK racing — Racing Post historical results (some free via scraping)
- [ ] US racing — Equibase free past performances for North American racing

### Other Sports
- [ ] Rugby (ESPN Scrum, World Rugby API)
- [ ] Cricket T20 ball-by-ball (Cricsheet.org)
- [ ] Australian Rules (AFL Tables)

---

## Phase 14 — Data Expansion
- [ ] Europa League historical data — football-data.co.uk has this free, needed for cross-competition Elo continuity and Champions League qualification modelling
- [ ] Champions League historical data — group stage + knockout, needed to improve tournament simulator accuracy
- [ ] UEFA Conference League data — 2021-present
- [ ] World Cup 2018 and 2022 match-level data with stage tags (group/R16/QF/SF/Final) — needed for international model knockout-stage calibration
- [ ] MLS data — Major League Soccer 2010-present
- [ ] Women's football — WSL (England), NWSL (USA), UWCL (Champions League)
- [ ] Brazilian Série A — largest football market in South America
- [ ] Argentine Primera División — historical data back to 1990
- [ ] Portuguese Primeira Liga — already partially covered via football-data.org
- [ ] Turkish Süper Lig — large market, good odds availability
- [ ] Greek Super League
- [ ] Belgian First Division A
- [ ] Danish Superliga
- [ ] Norwegian Eliteserien
- [ ] Swedish Allsvenskan
- [ ] Japanese J1 League
- [ ] Chinese Super League
- [ ] Australian A-League

---

## Phase 15 — International Football
> The World Cup (June-July 2026) exposed a real gap: national teams
> default to Elo 1500 with no signal, since our dataset is club
> football only. This phase builds a proper international football
> module — separate rating space, tournament-aware modelling, and
> fixes the live feed showing meaningless confident-looking predictions.

### Data Pipeline
- [x] International results dataset — Kaggle/GitHub martj42 dataset, 49,425 played matches (1872-2026), confirmed and filtered to exclude future placeholder fixtures
- [ ] World Cup historical results 1930-2022 — tagged by stage (group/R16/QF/SF/Final), knockout dynamics differ from friendlies
- [x] Confederation mapping — every nation tagged UEFA/CONMEBOL/CONCACAF/CAF/AFC/OFC/Other-Non-FIFA (211 FIFA members + 118 non-FIFA entities across 336 total teams)
- [ ] Euros, Copa América, AFCON, Asian Cup historical results
- [x] World Cup 2026 fixture list and group stage data — live via football-data.org, cross-referenced against international Elo
- [ ] Squad-based club strength proxy — count of players per national team from "big 5 league" clubs, using existing club Elo data as a novel cross-dataset signal no competitor has

### Modelling
- [x] Separate international Elo space — distinct K-factor (20/25/40/50 by tournament importance) and home advantage calibration from club Elo
- [x] Match importance weighting — friendly/qualifier/continental championship/World Cup K-factor tiers implemented in international_elo_model.py
- [ ] Confederation strength adjustment — historical cross-confederation gap correction (AFC/CAF vs UEFA/CONMEBOL)
- [ ] Squad depth feature — big-5-league player count per national team as input to win probability model
- [ ] Tournament bracket Monte Carlo simulator — extend existing 100k-sim engine to 48-team group + knockout structure for World Cup 2026
- [ ] Group qualification probability model — live-updating odds of finishing top 2 in group, updated after every match

### Product & Bug Fixes
- [x] Fix live feed — real international Elo now powering /api/live/upcoming, predict_upcoming.py, and fetch_live_odds.py (all three independently fixed for neutral-venue/host-nation home advantage handling)
- [x] Fix team-name resolution bug — "Belgium vs Mirandes" type errors, club teams incorrectly appearing as national team fixtures in the football-data.org live feed during tournament windows
- [x] International ratings page — live at /international, confederation filtering, min_matches toggle for non-FIFA entities
- [x] World Cup Hub page — live group tables, qualification probabilities, Round of 16 bracket prediction tree, "path to the final" probability per team (TIME-SENSITIVE — tournament ends mid-July 2026)
- [x] International team profile pages — extend existing TeamProfile component to work for national teams (different stats shape than club)

### Known Bugs Fixed This Session
- [x] Three independent files (predict_upcoming.py, api/routes/live.py, scripts/fetch_live_odds.py) each had duplicate, independently-broken home-advantage logic that incorrectly applied home advantage to neutral-venue World Cup matches — all three fixed with identical HOST_NATIONS/is_tournament_finals pattern
- [x] Team name alias mismatches between live data sources and international_elo_ratings.csv — fixed Czechia/Czech Republic, Bosnia-Herzegovina/Bosnia and Herzegovina, USA/United States, Bosnia & Herzegovina (ampersand variant)
- [x] requirements.txt missing joblib and xgboost — caused 3 weeks of silent GitHub Actions failures (June 1, 8, 15), root-caused via clean-venv reproduction and fixed
- [x] "Belgium vs Mirandes" — Mirandes is a Spanish club incorrectly appearing as a World Cup fixture in the football-data.org live feed; flagged but not yet investigated/fixed

### World Cup Knockout Intelligence — BUILT
- [x] Round of 32 bracket data structure — all 16 ties hardcoded with real results auto-detected from international_results.csv + shootouts
- [x] Elo-based win probability for every R32 tie
- [x] Monte Carlo bracket simulator — 100k sims, single-elimination 32-team structure, settled ties use real results
- [x] Per-team path-to-final probabilities (R16/QF/SF/Final/Champion %)
- [x] Title odds leaderboard — all 32 teams ranked by simulated championship probability
- [x] Bracket tree visualisation — R32→R16→QF→SF→Final columns with win % labels
- [x] Draw side analysis — left vs right half aggregate Elo comparison
- [x] GET /api/international/worldcup/bracket endpoint
- [x] GET /api/international/worldcup/team-path endpoint
- [x] Dedicated World Cup 2026 page under International nav
- [x] Daily automated bracket refresh via GitHub Actions
- [x] Fixed Railway CSV cache bug — endpoint now runs Monte Carlo simulator inline at request time with 1-hour TTL cache, no stale data possible
- [x] Corrected official 2026 World Cup bracket pairings (all 16 R32 ties, correct R16/QF/SF paths matching FIFA match numbers M73-M104)
- [x] Horizontal scrollable bracket tree layout — R32→R16→QF→SF→Final→SF→QF→R16→R32 in single row
- [x] Fixed NaN serialization bug in API response causing silent JSON parse failure in browser

---

## Phase 16 — Live In-Play Engine
- [ ] Markov chain game state model (score_diff, time_bucket, half, momentum)
- [ ] Pre-computed win probability lookup table (O(1) query)
- [ ] Bayesian in-game updater (posterior update per event, Supabase Realtime)
- [ ] Event impact quantification (goal +12-25%, red card -8-20%, etc — learned from data)
- [ ] Next-event prediction (P(goal) vs P(point), P(home scores next))
- [x] Tournament Monte Carlo simulator (100k simulations, < 5 seconds, 14 competitions)
- [x] Live win probability engine (football-data.org, 60s cache)
- [x] Upcoming fixtures with pre-match Elo probabilities
- [x] /api/live endpoints (now, today, upcoming)
- [ ] WebSocket live feed (< 1 second end-to-end latency target)
- [ ] Live data feed integration (The Odds API €15/mo, football-data.org free tier, Betfair Exchange API)
- [ ] Upgrade to sub-minute live feed (The Odds API €15/mo)
- [ ] Smart money tracker (odds movement > 10% in < 1hr = sharp money signal)

---

## Phase 17 — Trust & Accountability
- [x] Public prediction log — every prediction published before kickoff, SHA256 stamped, verifiable by anyone
- [x] Prediction audit trail — immutable record, timestamped, hash-linked like a blockchain
- [ ] Monthly accuracy report — auto-generated PDF, emailed to subscribers, shows track record
- [x] "About the Model" page — methodology overview, who built it, why trust it, track record
- [ ] Social sharing cards — share a match preview or value bet card to Twitter/X with OG image
- [ ] Verified track record badge — independently audited hit rate displayed prominently
- [ ] Community leaderboard — who has the best prediction record this month
- [ ] Tipping competition — users submit predictions, ranked by Brier score
- [ ] Discord/Slack community integration — post value bets automatically to community channels
- [ ] Press kit — stats, methodology, screenshots for journalists and podcasters
- [ ] Academic paper — write up the methodology as a preprint (arXiv) for credibility

---

## Phase 18 — Match Intelligence
- [ ] Weather-adjusted predictions — incorporate OpenWeatherMap data into Elo probability adjustments
- [ ] Distance fatigue model — penalise away teams based on travel distance for midweek games
- [x] Home/away Elo split — maintain separate home and away Elo ratings per team
- [x] Form-weighted predictions — implemented as `late_season_form_diff` (see Phase 2 Tier 1); EWM alpha 0.6 over last 5 matches when `is_late_season == 1`
- [ ] Pre-match news sentiment — scan team news for injury/suspension signals
- [ ] Live odds movement tracker — detect line movement pre-kickoff as sharp money signal
- [ ] Match importance index — weight predictions by how much the match matters (title, relegation, cup final)
- [ ] Upset probability model — when does Elo underestimate upset probability
- [ ] Score timeline model — predict when goals are most likely in a match (minute distribution)
- [ ] Referee impact model — quantify how specific referee assignment affects match outcome probability

---

## Phase 19 — Community & Social
- [ ] Public prediction leaderboard — rank users by Brier score on their predictions
- [ ] Tipping competition — weekly competition, users submit predictions, ranked by accuracy
- [ ] Discord/Slack bot — post value bets and predictions automatically
- [ ] Social sharing — one-click share match preview or value bet to Twitter/X
- [ ] Embed widget — let other sites embed FormCast win probabilities via iframe
- [ ] Press kit — stats, methodology screenshots for journalists and podcasters
- [ ] Academic paper — arXiv preprint of the methodology for credibility

---

## Phase 20 — Individual Player Modelling
- [ ] Player-level xG contribution — individual player xG as % of team total (requires shot-level data from FBref/Understat)
- [ ] Goalkeeper save percentage above expected — shotstopping quality beyond team defence
- [ ] Player network graph — pass completion rates between specific player pairs (team cohesion signal)
- [ ] Top scorer absence model — quantify impact of missing striker on team xG
- [ ] Set piece model — corners/free kicks conversion rate by taker
- [ ] Player form streaks — individual scoring/assist streaks as momentum signal
- [ ] Injury probability model — predict injury risk from minutes played, age, fixture congestion
- [ ] International duty fatigue model — performance drop after long-haul international travel

---

## Phase 21 — Validation & Statistics
- [x] Full calibration curve (predicted prob vs empirical win rate per decile)
- [ ] Reliability diagram with confidence intervals
- [ ] Hosmer-Lemeshow goodness of fit test
- [ ] Diebold-Mariano test vs naive baseline
- [ ] Permutation feature importance
- [ ] AIC/BIC model selection
- [ ] Ljung-Box test (residual autocorrelation)
- [ ] KS test (predicted vs empirical distribution)
- [ ] Brier score by time bucket (early season vs late season)
- [ ] Hit rate by Elo gap band

---

## Phase 22 — Frontend (React + Vite)
- [x] Project scaffold (Vite + Tailwind + Recharts)
- [x] Elo ratings table — live, sortable, filterable by league
- [ ] Calibration curve — predicted prob vs actual win rate
- [ ] Brier score over time (rolling 90-match window)
- [ ] Cumulative P&L chart (flat stake simulation)
- [ ] SHAP feature importance (beeswarm + waterfall per match)
- [ ] Elo history chart — animated, all teams, 2020-present
- [ ] H2H Elo trajectory — two-team selector
- [ ] Score distribution heatmap (actual vs model predicted)
- [x] Value bet screener UI (EV > 5%, Kelly stake shown)
- [x] Accumulator builder UI (select legs, see combined EV and optimal stake)
- [ ] Win probability timeline (live match, Supabase Realtime)
- [x] Tournament probability evolution (updates after each result)
- [ ] Momentum dashboard (8 signals per team)
- [ ] Smart money tracker (odds movement visualised)
- [ ] Model ensemble weight evolution chart

---

## Phase 23 — API & Deployment
- [x] Flask API scaffold
- [x] GET /api/ratings — current Elo ratings per league
- [x] GET /api/predictions — upcoming match predictions
- [x] GET /api/backtest — accuracy report
- [x] GET /api/value-bets — positive EV opportunities
- [ ] GET /api/match/:id — single match deep dive + SHAP values
- [x] GET /api/accumulator — optimal accumulator builder
- [x] GET /api/tournament/:id — tournament simulation
- [ ] WebSocket /live — real-time win probability stream
- [x] Deploy frontend to Vercel
- [x] Deploy API to Railway

---

## Architecture
| Layer | Technology |
|-------|-----------|
| Modelling | Python — pandas, scipy, sklearn, XGBoost, PyTorch |
| API | Flask + Socket.io |
| Database | Supabase (PostgreSQL + Realtime) |
| Frontend | React + Vite + Tailwind + Recharts + D3 |
| Deployment | Vercel (frontend) + Railway (API) |
| Repo | github.com/conairemolloy/formcast |

---

## Data Sources
| Source | Sport | Coverage | Cost |
|--------|-------|----------|------|
| football-data.co.uk | Soccer | 5 leagues, 1993-present | Free |
| Understat | Soccer | xG, top 5 leagues, 2014-present | Free |
| FBref / StatsBomb | Soccer | Advanced stats, 2017-present | Free |
| Kaggle European Soccer DB | Soccer | 25k+ matches | Free |
| Jeff Sackmann tennis_atp/wta | Tennis | 500k+ matches, 1968-present | Free |
| DataGolf.com | Golf | SG data, 2004-present | Free tier |
| nfl_data_py | NFL | Play-by-play, 1999-present | Free |
| Cricsheet.org | Cricket T20 | Ball-by-ball, 2008-present | Free |
| AFL Tables | Aus Rules | Full AFL history | Free |
| OpenWeatherMap API | All | Weather | Free tier |
| The Odds API | All | Live odds, 40+ bookmakers | €15/mo |
| Betfair Exchange API | All | Live prices + volume | Free (account required) |
| football-data.org API | Soccer | Live scores (free tier) | Free |
| Foireann API | GAA | Fixtures + results | Free |
| PreGame Edge | GAA | 594 club results (unique) | Internal |
| Sentry | All | Error monitoring | Free tier |
| PostHog | All | Product analytics | Free tier |
| Cloudflare | All | DDoS protection, CDN | Free tier |
| Stripe | All | Payment processing | % per transaction |
| Resend | All | Email notifications | Free tier |
| GitHub Actions | All | CI/CD automation | Free |
| UptimeRobot | All | Uptime monitoring | Free tier |
| Racing Post | Horse Racing | UK/Ireland results | Scraping |
| HRI | Horse Racing | Irish racing free data | Free |
| Equibase | Horse Racing | US racing past performances | Free |
| nba_api | Basketball | NBA play-by-play 1946-present | Free |
| Basketball-Reference | Basketball | EuroLeague, advanced stats | Free scraping |

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
