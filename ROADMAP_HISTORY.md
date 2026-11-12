# FormCast — Roadmap History
*History archived from ROADMAP.md on Nov 12 2026.* The active roadmap is [ROADMAP.md](ROADMAP.md).

> **How to read this file.** Everything below is preserved **verbatim** from ROADMAP.md as of commit bf4c006: completed work, superseded decisions, and snapshots. It is the proof-of-work record. Do not edit history entries. Numbers here were true (or believed true) **when written**. For current figures see "Current State & Honest Claims" in ROADMAP.md. Known caveats when reading the record:
> - Anything labelled **"CLV"** (Phase 4/5, Currently-Live snapshot) measures log(model prob / book prob) against Bet365 *pre-match* odds. It is **not** closing-line value and is banned from public copy.
> - **68.7%** is the old optimised-Elo non-draw walk-forward figure. **128,797 matches / 14 competitions / 500+ teams** were not reproducible on Nov 12 2026 (recount: 128,592 rows, 11 club leagues, 446 club teams).
> - Phase 3 marks **GNN and Transformer** as built, but no GNN/Transformer code was found in `scripts/` on Nov 12 2026.
> - Pre-Nov-12 "logged prediction" accuracy/ROI figures (50.3%, −7.2%) measured **Elo**, not the ensemble.

---

## Session Logs

### Session Log — Nov 12 2026 (ensemble finally in production)
> **This section supersedes the stale "50.3% / 59-of-608 / negative-ROI" framing in NEXT UP and the QA sweep below.** Those numbers described the OLD state (plain-Elo logged predictions, broken odds-join). Five commits tonight changed the facts:

- [x] **Odds-join fixed: 59/608 → 608/608 settled predictions now matched to odds.** New scripts/fixture_matching.py — one shared FixtureMatcher (strict name resolve + opponent-anchored fallback, no name-only fuzzy) used by BOTH settle_predictions and portfolio_analytics, so they always agree on the fixture. The "only 59 of 608 got odds" blocker that gated any honest ROI measurement is CLEARED. (commit 7a35e7d)
- [x] **The live endpoint served plain Elo, never the ensemble — ROOT CAUSE of the whole stale track record.** api/routes/live.py _prematch_probs is 3 lines of Elo arithmetic (loads no models). Every logged prediction to date was Elo, with broken name resolution defaulting ~15/144 teams to 1500 (Ath Bilbao priced at 6% to beat Espanyol). The 78-feature ensemble we built was NEVER what production logged.
- [x] **Ensemble now logged, not Elo.** predict_upcoming writes match_id to upcoming_predictions.csv (commit 0aab732); publish_predictions looks up ensemble probs by match_id and logs them tagged source=ensemble, falling back to Elo (source=elo) only for unresolved/international/missing/stale fixtures (commit dbad933). New scripts/log_schema.py holds shared LOG_COLS so settle no longer strips the column. source is a PLAIN column, NOT in the hash — _make_hash recipe byte-identical for every row, all 1110 existing hashes verified unchanged. (commits dbad933, babf6d4)
- [x] **CI reordered** — publish now runs AFTER predict_upcoming so it reads this week's ensemble (commit 9cb6d15). Verified no intermediate step reads prediction_log.csv; no leakage (results.csv is played matches only).

**CURRENT HONEST STATE (what the landing page / proof page can claim):**
- The verifiable record is REAL and now reflects (from ~Nov 14, when fixtures re-enter the 7-day window) the ensemble, not Elo: "1,110+ predictions published before kickoff, timestamped + SHA-256 hashed; 608 settled." This is a STRONGER trust claim than before because the record is about to be the real model.
- **We still do NOT know if the ensemble has a live betting edge.** The earlier negative result (−7% ROI, log loss 1.036 vs book 0.967) measured ELO, not the ensemble — it says nothing about the real model. The ensemble's live edge is UNMEASURED until ensemble rows accumulate (~Nov 14+). So: still lead with TRANSPARENCY + the verified record, NOT an ROI or win-rate headline. (This resolves, at source, the CRITICAL hit-rate-framing decision in NEXT UP: option (c) — "log ensemble not Railway-Elo going forward" — is now DONE.)
- The multi-market edge (corners/cards/goals/BTTS) remains entirely unmeasured and is the next real question — plausibly where the edge lives.

**NEXT (decided):** (1) Full site remodel — design track, doesn't touch the model: DESIGN.md, landing page, About/bio, How It Works, escape the "obviously Claude-designed" look. (2) Multi-market value-testing — same settle+edge measurement as 1X2 but for the four market models. Remodel first (no model risk); edge-testing gets richer as ensemble rows accumulate.
- [ ] Parked tonight: the endpoint's broken Elo name-resolution (~15/144 at 1500 default) — same name bug, third location; makes source=elo fallback rows + displayed Elo unreliable. Fix so the endpoint and the ensemble CSV agree on names.

### Session Log — November 2026 (foundation repair)
- [x] Ensemble-join reliability FIXED — live value bets now 100% from the real 78-feature ensemble (was falling back to stale Elo on team-name misses / date-window mismatch). Root cause was two bugs: 7-day prediction window vs 21-day odds window, and suffix-strip collapsing "Man City"/"Man United" to "Manchester". Verified 108/108 join in live pipeline run.
- [x] Prediction settlement FIXED — 608 of 617 covered-league predictions now settle (was 0 — whole season's track record was empty). Name-resolution mismatch between publish (football-data.org names) and settle (football-data.co.uk names). Log hashes preserved, never rewritten.
- [x] Stale-season data FIXED — model was frozen on May 2026 data; added 2026-27 season ingestion (1,210 matches, 11 leagues). Model now current.
- [x] Leaked API keys ROTATED + moved to env vars — football-data.org and Odds API keys were hardcoded in public repo since May 2026; rotated both, moved to Railway/GitHub secrets + .env, fail-loud if unset. (Completes much of Phase 11 "Secrets management".)
- **NEW CURRENT NUMBERS (supersede stale ones below):** 2026-27 live-season backtest 64.4% (n=913); 608 settled predictions; 100% ensemble join; ~128k matches + 2026-27.

---

## Superseded Decision — Public hit-rate framing (Nov 2026)
> The record of WHY ROI is not the headline. Superseded Nov 12 2026: the ensemble is now logged (option c done), and the odds-join is fixed (608/608). The framing will be re-decided once ensemble rows accumulate (ROADMAP.md queue a).

- [ ] ⚠️ SUPERSEDED Nov 12 2026 — see top Session Log: ensemble is now logged (option c done); odds-join fixed (608/608). Re-decide framing against ensemble rows once they accumulate.
  **CRITICAL DECISION — public hit-rate framing (50% vs 64.4% vs 68.7%)** — three different numbers measure three different things and a visitor seeing them together loses trust: logged predictions settle at ~50% (3-way H/D/A, Elo-based from the Railway API, not the ensemble); the live 2026-27 ensemble backtest is 64.4% (n=913); the old marketing figure is 68.7% (non-draw, optimised Elo). Before ANY public proof page or email tips, decide ONE honest headline framing. Options: (a) lead with 64.4% current-season ensemble accuracy clearly labelled; (b) report ROI/CLV on value bets instead of raw accuracy; (c) log ensemble (not Railway-Elo) predictions going forward so the track record reflects the real model. GATES the free-first launch — the whole pitch is the honest track record.
  - **⚠️ UPDATE (Nov 2026) — option (b) REJECTED for now: ROI CANNOT BE THE HEADLINE** (confirmed by portfolio_analytics on live prediction-log data):
    - Live value-bet ROI is **NEGATIVE: −7.2% flat** (45 bets, 35.6% hit rate); half-Kelly £1,000 → £627, Sharpe −2.9. All-predictions flat ROI +1.1% = indistinguishable from zero (95% CI −27% to +30%).
    - Sample is tiny AND biased: only **59 of 608** settled predictions got odds attached, due to the settlement name-mapping bug (now HIGH PRIORITY — see Parked Technical Fixes). Bundesliga 0 matched, Ligue 1 1.
    - On the 59 matched games the **bookmaker is better calibrated than the model** (Brier 0.606 book vs 0.620 model; logloss 1.007 vs 1.039).
    - The "+0.265 CLV" is **NOT closing-line value** — it's log(model prob / book prob), positive by construction for any value bet. Never quote it. Also: the "closing odds" in value_betting.py are actually Bet365 **PRE-match** (B365H/D/A), not closing (B365CH/CD/CA). Mislabelled.
    - The +8.4% placeholder on the landing page is NOT a real live figure (likely a backtest number). REMOVE it; do NOT replace it with a live ROI.
  - **DECISION (Nov 2026): lead with the RECORD + TRANSPARENCY, not ROI.** Honest claims available now: "1,110 predictions published before kickoff, timestamped + SHA-256 hashed; 608 settled" and "50.3% accuracy (3-way, draws included)". ROI becomes a headline candidate ONLY after: (1) the name-mapping bug is fixed so all 608 get odds, (2) a rerun on the full sample, (3) several hundred value bets with a positive result against REAL closing odds (B365C*). Until then, leading with ROI would be misleading — fatal for a transparency-first product.
  - **PRODUCT REFRAME (Nov 2026): the ROI finding is about 1X2 (match-result) value bets ONLY** — 45 bets, Elo-based, tiny biased sample. FormCast's actual product is NOT "predict the winner" — it's data-driven analysis across MANY markets (match result, corners, cards, goals/over-under, BTTS, free kicks), surfacing where the model disagrees with the bookmaker on ANY of them. The four market models (corners/cards/BTTS/goals) are built but NOT yet value-tested against bookmaker lines. So the negative 1X2 result does NOT mean "no edge" — the multi-market angle is entirely unmeasured, and is plausibly where real edge lives (bookmakers price corners/cards less sharply than 1X2). Implications:
    1. The name-mapping fix (Parked Technical Fixes) unblocks measuring ANY market honestly.
    2. Extend the value screener to all markets (see "Multi-market value bets" item) — that's both the product vision and the real edge question.
    3. Trust framing stands: lead with "data-driven analysis across every market, every call logged," not a win-rate or 1X2 ROI.

---

## Live Site Bugs & Findings — November 2026 QA sweep (snapshot)
> Snapshot as written. Open items from this sweep carried into ROADMAP.md: hit-rate inconsistency → stale-stat purge (done Nov 12 for 68.7%/CLV, rest in queue b); Prediction Log overwhelm → public proof page (queue b).

> From a full page-by-page walkthrough of the live site. Technical fixes are also tracked in "Parked Technical Fixes".

**🔴 Real bugs (broken / wrong — fix before any launch/trust push):**
- [x] **DONE (fixed Nov 2026 — one-line /api prefix fix in PredictionLog.jsx, page now loads (1,110 logged / 608 settled). Commit f883357.)** **Prediction Log page — 404, completely broken** — "Failed to load: Request failed with status code 404". This IS the public track record page — the centrepiece of the free-first trust strategy. Data settled fine (608 predictions) but the page calls a dead API endpoint. HIGHEST priority of the bugs — the trust page doesn't load.
- [x] **DONE (fixed Nov 2026 — new scripts/season_utils.py current_season() helper; simulator now runs on the current season and derives remaining fixtures dynamically from unplayed home/away pairings: EPL 100 played / 280 remaining, LaLiga 119/261, SerieA 110/270, Bundesliga 81/225, Ligue1 90/216; Tournament.jsx reads season + real played/remaining counts from the API. Commit 1278797.)** **Tournament Simulator — stuck on last season (2025-26), functionally dead** — header shows "2025-26 · ~381 matches played · ~0 remaining", simulating a FINISHED prior season (100%/0% probabilities). Root cause: hardcoded TODAY="2026-05-21" (tournament_simulator.py:22) + "2025-26" (line 177). Whole feature is useless until made season-dynamic. Not cosmetic — a full page is wrong.
- [ ] **Three different public hit-rate numbers across the site (confirmed live)** — Predictions page shows 48.8% (10,058 shown / 4,906 correct, 3-way), Backtest page shows 66.2% (non-draw), plus 64.4%/68.7% in materials. A visitor browsing sees 48.8% on one page and 66.2% on another with no explanation. This is the trust-eroding inconsistency the "hit-rate framing decision" (top of NEXT UP) must resolve — now confirmed it's live across multiple pages, not hypothetical.
  - **⚠️ URGENT UPDATE (Nov 2026): now worse — the Prediction Log page is FIXED and live, showing 50.3% as a big bare stat** (3-way, draws included, Elo-based; 306 correct / 608 settled). So 50.3% (Prediction Log) + 66.2% (Backtest) are BOTH live and public at the same time, with no reconciliation. This actively UNDER-SELLS the model — a visitor reads 50.3% as "coin flip". URGENT now, not a pre-launch item. Minimum fix: label the 50.3% honestly on the page ("3-way accuracy, includes draws") and lead with the verifiable record (1,110 published / 608 settled, SHA-256 hashed). ~~Lead with ROI~~ — reversed Nov 2026: live ROI is negative on a biased sample (see CRITICAL hit-rate framing decision, top of NEXT UP).
- [ ] **Prediction Log page — overwhelm redesign (confirmed live Nov 2026)** — the page WORKS but opens straight into a ~1,110-row scrolling table with no summary or story: the exact "data dump" the Core Product Principle vetoes. KEEP the strong trust asset: the "Cryptographically verified · SHA-256 hashed" framing + "How does verification work?" link + clickable hashes. This is what separates FormCast from tipsters, so LEAD with it. FIX: (1) lead with the honest headline (verifiable record + labelled 3-way accuracy — NOT ROI, see NEXT UP) + recent settled results; (2) move the full verifiable 1,110-row table behind a "View full log" so the depth stays but doesn't overwhelm; (3) apply the uncovered-league filter (parked fix) to clear the Brazil/Eredivisie/etc PENDING noise padding the table. This page becomes the "Public proof page" (Phase 6 Trust Signals) in the remodel — one of the best trust assets.
- [x] **DONE (fixed Nov 2026 — heading reads the season from the API, which now comes from live.py's per-request current_season() (commit 1278797), so it shows 2026-27 stats; H2H.jsx fallback text changed from the literal '2025-26' to currentSeason() from frontend/src/season.js, so it auto-rolls each July.)** **H2H "2025-26 Season Stats" heading** — hardcoded last-season label (same bug family as Tournament). Shows last season's stats.

**🟢 What's GOOD (strong pages — the standard to match, do NOT redesign away):**
- Backtest page — excellent; the "What's working / Why P&L looks negative / What the numbers mean" plain-English boxes are the honest trust-building tone to replicate site-wide. THE model page.
- Ratings (club + international) — clean, current, well-designed (Bayern 2060, Spain 2277).
- H2H — strong; beautiful Elo history chart, win-prob bar.
- Matches, Match Research, Value Bets (card grid) — functional, current, close to right.

**🟡 Known/polish:** No landing page (logged-out = Dashboard + sign-in modal, not a conversion page); Dashboard flat-list (= #1 Phase 6 editorial-hierarchy priority); bare "Loading…" spinners instead of skeletons.

---

## Infrastructure items closed in NEXT UP (Nov 2026)
> Open follow-ups inside L111 (one canonical resolver, unify Elo fallback formulas, emit prediction_uncertainty) carried into ROADMAP.md queue (d)/(e).

- [x] **DONE (fixed Nov 2026, see Session Log)** **Live value bets: ensemble-join reliability (was "Elo-only")** — fetch_live_odds.py already bridges to ensemble predictions via upcoming_predictions.csv, but falls back to stale Elo SILENTLY on team-name key misses. Root cause: two divergent name-resolution pipelines — odds API → _ODDS_TO_ELO (sparse, top-leagues-only, missing most Championship/Serie B/etc) vs football-data → results.csv canonical. Instrumentation added to log hit/miss rate per run. NEXT: (1) measure real miss rate once season fixtures populate [instrumentation live], (2) fix by unifying to ONE canonical team-name resolver (single-source-of-truth, same principle as feature pipeline) rather than extending the sparse _ODDS_TO_ELO dict, (3) also unify the two divergent Elo fallback formulas (fetch_live_odds HOME_ADV=50 + own draw formula vs predict_upcoming's — they disagree), (4) emit prediction_uncertainty from predict_upcoming.py (one line — meta_proba already computed) so live Today's Tips gets edge×confidence ranking. Off-season note: miss-rate measurement only meaningful once upcoming fixtures exist.
- [x] test_club_path.py as CI canary step in weekly workflow — pipeline fails loudly instead of shipping broken predictions silently

---

## Parked Technical Fixes — done (Nov 2026)
- [x] **DONE (fixed Nov 2026, commit 9ae8a70)** — Uncovered-league filter — new scripts/league_coverage.py (COMP_TO_LEAGUE + COVERED_LEAGUE_CODES + is_covered_league(), shared by predict_upcoming / publish / settle / API); publish_predictions.py skips uncovered leagues going forward; API derives a settled | pending | not_tracked status per row with the CSV/hashes untouched; frontend shows a "NOT TRACKED" badge + tracked-only totals. Result: 617 tracked / 493 not tracked (the original ~394 estimate missed 34 rows + the 65 FIFA World Cup rows, which are not_tracked pending a separate international settlement job).
  - [x] **DONE (fixed Nov 2026, commit 1278797)** — **Tournament Simulator (functionally dead, not cosmetic)** — tournament_simulator.py:22 TODAY="2026-05-21" + line 177 "2025-26"; page simulated the finished 2025-26 season. Fix: new scripts/season_utils.py current_season() helper (July rollover rule); TODAY → date.today(); simulator derives remaining fixtures dynamically (double round-robin, with early-season fallback to last season's team list); output CSV gained season / matches_played / matches_remaining; Tournament.jsx season label + counts + "season complete" banner now read from those columns.
  - [x] **DONE (fixed Nov 2026, commit 1278797)** — **live.py stale-season spots** — line 536 (_CURRENT_SEASON, corners/cards season averages) and line 810 (team-profile current-season stats) now call current_season(date.today()) per-request (survives the July rollover without a server restart). This also makes the H2H "Season Stats" heading dynamic, since it renders the API's `season` field.
  - [x] **DONE (fixed Nov 2026)** — **Matches.jsx season filter** — SEASONS list topped out at 2025-26, so users couldn't filter to 2026-27 at all. Now generated from new frontend/src/season.js (`currentSeason()` / `recentSeasons()`, a JS mirror of season_utils.current_season() with the same July rule — keep the two in sync): current season + 3 prior, newest first.
  - [x] **DONE (fixed Nov 2026)** — **H2H.jsx:314 fallback label** — `?? '2025-26'` → `?? currentSeason()` (from frontend/src/season.js — auto-rolls each July, never goes stale). No "2025-26" literals remain anywhere in frontend/src.

---

## Feature inventory snapshot — "Currently Live" (Nov 2026)
> Feature list as written. Lines that were only duplicate/stale stats were dropped (the backtest/ensemble numbers they repeated are in the Phase 1-3 completion blocks below; current numbers live in ROADMAP.md).

- Dashboard with live value bets, upcoming fixtures, top ratings
- Live match tracker with real-time probabilities (football-data.org)
- Match deep dive: win probs, correct scores, BTTS, goals, corners, cards
- Elo ratings for 500+ teams across 14 competitions (1993-2026)
- Team profile pages: Elo history, form, season stats, H2H
- H2H comparison tool
- Tournament simulator (Monte Carlo, 100k simulations)
- Value Bets: live upcoming (100% ensemble) + historical track record
- Accumulators: historical tracker (708 accas)
- How It Works: methodology, models, glossary
- GitHub Actions weekly automation (Monday 6am UTC)
- Mobile responsive
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

## Phase 6 — design history & superseded notes
### Terminology change (Nov 2026)
> **TERMINOLOGY (Nov 2026 v0 landing-page session — supersedes earlier framing throughout):** (1) "Bet of the Day" → **"Today's Tips"** — the daily hook is the full RANKED SET of today's value bets ("today's tips, ranked by edge"), led by the strongest, NOT a single hero pick. Older "Bet of the Day" mentions below/elsewhere (incl. the Session Log) mean Today's Tips unless they describe history. (2) "World Cup Hub" → **"International football hub"** — evergreen (World Cup, Euros, qualifiers, Nations League, friendlies), not tied to one tournament. (3) Multi-sport includes **user sport-selection** — users pick which sports they follow, and that filters their tips/feed.

### Visual Assessment — November 2026 (live site reviewed; pre-orange-palette)
- Confirmed: the Dashboard is an infinite flat list of ~40 equal-weight value-bet rows — exactly the "60 rows on login" the Core Product Principle warns against. No focal point, no ranking, no curation.
- Confirmed: Value Bets page is already card-based (3-col grid, Model%/odds/edge/implied) — good foundation, close to right.
- Confirmed: visual design foundation (emerald-on-black, restraint, typography) is SOLID — needs curation/hierarchy, NOT a from-scratch redesign.
- **#1 PHASE 6 PRIORITY:** the "Value Bets editorial hierarchy (Today's Tips)" item is THE next build — kill the flat list, lead with the strongest tip + next few + collapsed rest of the ranked set. This single change fixes the "too much stuff" problem across dashboard + value bets.
- NOTE: DESIGN.md is open to revision to match current taste (clean/minimal/restrained-motion); treat it as updatable, not fixed.

### Superseded Phase 6/7/9 items
- [ ] Landing page redesign — above-fold must convert. Large headline, 3 key stats displayed huge, single Sign Up CTA, below-fold: how it works, sample value bets, track record [SUPERSEDED — absorbed by the "LANDING PAGE — build FIRST" item in Design Direction & Tooling above]
- [ ] Onboarding tour — first-time user walkthrough (Shepherd.js) [SUPERSEDED — see Phase 6 Signup & onboarding flow]
- [ ] Landing page conversion optimisation — headline, social proof numbers (3,525 value bets, 128k matches, 68.7% hit rate) displayed large and front-and-center, single clear CTA above fold [SUPERSEDED — absorbed by the "LANDING PAGE — build FIRST" item in Design Direction, which uses the record+transparency framing, not 68.7%/3,525 (stale, and 68.7% is the superseded Elo marketing figure)]
- [ ] Onboarding tour — first-time user walkthrough explaining each page (Shepherd.js or similar) [SUPERSEDED — see Phase 6 Signup & onboarding flow]

---

## Phase 7 — UX & Design Polish (completed items)
- [x] Landing page redesigned — hero, three use cases, model steps
- [x] Nav reorganisation — grouped nav with Dashboard as default
- [x] Dashboard home page — live value bets, upcoming fixtures, top ratings, model performance
- [x] Matches page with shot, corner, card stats and league/team filtering
- [x] Filtering and sorting on all pages (league, date, outcome, edge filters)
- [x] Fix remaining duplicate team names (2,718 cells fixed)
- [x] Matches page with filtering and pagination
- [x] Team profile page — Elo history, form, season stats, H2H
- [x] Calibration curve chart
- [x] Tournament tooltips and season complete warning
- [x] H2H comparison page
- [x] League filter on ratings page (show only EPL, only La Liga etc)
- [x] Mobile responsive layout
- [x] Loading skeletons instead of spinners (partially — auth loading states done, full skeleton screens pending)

## Phase 8 — Methodology (completed items)
- [x] How It Works page — model explanations, ensemble flow, glossary, data sources

## Phase 10 — Business (completed items)
- [x] User accounts — Supabase Auth, save favourite teams, personalised dashboard

## Phase 12 — Automation & Infrastructure (completed items)
- [x] Automated weekly data ingestion — GitHub Actions, runs every Monday 6am UTC
- [x] Automated model retraining — Elo, tournament, value bets, backtest all automated
- [x] Automated tournament simulator refresh
- [x] Automated value bet generation — live odds via The Odds API
- [x] Scheduled prediction publishing — publish_predictions.py runs Monday via GitHub Actions
- [x] CI/CD pipeline — GitHub Actions
- [x] Railway health checks — /api/health endpoint verified healthy, manual full pipeline health check performed this session
- [x] Retry logic with exponential backoff — predict_upcoming.py fixture fetch now retries 3x (5s/15s/30s) on transient failures instead of immediately failing the whole pipeline
- [x] Premier League and Championship sport keys fixed — were using wrong key names (soccer_england_premier_league, soccer_england_championship) instead of correct soccer_epl and soccer_efl_champ, confirmed against The Odds API's own /v4/sports endpoint. Recovered Premier League value bets that had been silently 404ing.
- [x] Ensemble auto-retraining in weekly pipeline — VERIFIED July 2026: all models retrain every Monday (workflow steps 8-16: corners, cards, BTTS, goals, NN, LSTM, Bradley-Terry, Dixon-Coles, XGBoost + meta-learner + draw classifier); fixed pickle commit (July 2026) so Railway backtest route no longer drifts from weekly retrains

## Phase 13 — Sport Expansion (completed items)
- [x] Stadium coordinates database — data/reference/stadiums.csv; 442/444 teams filled (lat, lng, altitude_m, capacity); powers away_travel_km, altitude_diff, home_capacity_log features in ensemble_v2.py
- [x] Distance travelled database — stadium lat/lng for all 442 clubs, travel km calculator — same artefact as stadiums.csv above

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

## Phase 16 — Live In-Play Engine (completed items)
- [x] Tournament Monte Carlo simulator (100k simulations, < 5 seconds, 14 competitions)
- [x] Live win probability engine (football-data.org, 60s cache)
- [x] Upcoming fixtures with pre-match Elo probabilities
- [x] /api/live endpoints (now, today, upcoming)

## Phase 17 — Trust & Accountability (completed items)
- [x] Public prediction log — every prediction published before kickoff, SHA256 stamped, verifiable by anyone
- [x] Prediction audit trail — immutable record, timestamped, hash-linked like a blockchain
- [x] "About the Model" page — methodology overview, who built it, why trust it, track record

## Phase 18 — Match Intelligence (completed items)
- [x] Home/away Elo split — maintain separate home and away Elo ratings per team
- [x] Form-weighted predictions — implemented as `late_season_form_diff` (see Phase 2 Tier 1); EWM alpha 0.6 over last 5 matches when `is_late_season == 1`

## Phase 21 — Validation & Statistics (completed items)
- [x] Full calibration curve (predicted prob vs empirical win rate per decile)

## Phase 22 — Frontend (completed items)
- [x] Project scaffold (Vite + Tailwind + Recharts)
- [x] Elo ratings table — live, sortable, filterable by league
- [x] Value bet screener UI (EV > 5%, Kelly stake shown)
- [x] Accumulator builder UI (select legs, see combined EV and optimal stake)
- [x] Tournament probability evolution (updates after each result)

## Phase 23 — API & Deployment (completed items)
- [x] Flask API scaffold
- [x] GET /api/ratings — current Elo ratings per league
- [x] GET /api/predictions — upcoming match predictions
- [x] GET /api/backtest — accuracy report
- [x] GET /api/value-bets — positive EV opportunities
- [x] GET /api/accumulator — optimal accumulator builder
- [x] GET /api/tournament/:id — tournament simulation
- [x] Deploy frontend to Vercel
- [x] Deploy API to Railway
