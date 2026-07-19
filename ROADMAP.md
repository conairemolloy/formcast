# FormCast — Sports Prediction Platform
### Elo + Glicko-2 + Dixon-Coles + BTL + XGBoost + Neural Ensemble
*Last updated: June 2026*

---

## Currently Live
- Dashboard with live value bets, upcoming fixtures, top ratings
- Live match tracker with real-time probabilities (football-data.org)
- Match deep dive: win probs, correct scores, BTTS, goals, corners, cards
- Elo ratings for 500+ teams across 14 competitions (1993-2026)
- Team profile pages: Elo history, form, season stats, H2H
- H2H comparison tool
- Tournament simulator (Monte Carlo, 100k simulations)
- Value Bets: live upcoming + historical track record (3,525 bets)
- Accumulators: historical tracker (708 accas)
- Backtest: 68.7% hit rate, Brier 0.156, CLV +0.19
- How It Works: methodology, models, glossary
- GitHub Actions weekly automation (Monday 6am UTC)
- Mobile responsive
- Ensemble predictions pipeline — XGBoost + meta-learner saved, predict_upcoming.py ready for August
- Walk-forward ensemble backtest — 66.79% hit rate (non-draw) vs 66.71% Elo baseline across 20k matches 2020-2024
- SHA256 prediction log — 27 predictions published, auto-settles after each gameweek
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
- 82-feature ensemble (Batch 3: +7), 15-feature meta-learner stack, 66.92% walk-forward backtest, ECE 0.0098

---

## Build Priorities — Repositioned for Commercial Launch
> Phases renumbered to reflect the actual build order.

### Stage 1 — Model Quality (Phase 2 + Phase 3 + Phase 4 + Phase 5)
- Phase 2 Tier 1 — remaining high-impact features: venue win rate, clean sheet rate, opponent-adjusted form, relegation/title pressure, league-specific home advantage, early season Elo regression
- Phase 2 Tier 2 — weather integration (OpenWeatherMap, one call per fixture)
- Phase 2 Tier 3 — model architecture: separate draw classifier, ensemble calibration (Platt scaling), league-specific home advantage
- Phase 2 Tier 6 — odds format display: American moneyline, UK fractional, decimal — shared utility used everywhere
- Phase 3 — retrain neural networks with updated feature set
- Phase 4 — betting intelligence gaps: Dutching calculator, arbitrage detector, Sharpe ratio, max drawdown, P&L simulation
- Phase 5 — model validation page: walk-forward accuracy chart, calibration curve, per-league Brier scores (trust-building content that converts free users to paid)
- [x] Market-specific models — corners, cards, BTTS, goals over/under (separate XGBoost per market)
- Ensemble auto-retraining in weekly pipeline — critical before August EPL restart

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

## Off-Season Status (May–July 2026)
European leagues finished. Pipeline fully built and tested.
Next live value bets: August 2026 when EPL/La Liga/Serie A/Bundesliga/Ligue 1 restart.
Ensemble predictions will power value bets from August — 7-model stack vs Elo-only currently.

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
| Competitions | EPL, Championship, La Liga, Segunda, Serie A, Serie B, Bundesliga, Bundesliga 2, Ligue 1, Ligue 2, Scottish Prem, Champions League, Eredivisie, Euro 2024 |
| Walk-forward hit rate | 68.7% (non-draw, optimised Elo, 128k matches) |
| Walk-forward Brier score | 0.156 |
| Ensemble v2 hit rate | 53.3% (3-outcome, 2023-25 holdout) |
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
- [~] Weather at kickoff — prediction-time display live (fetch_weather.py → upcoming_weather.csv → merged into upcoming_predictions.csv); training feature blocked on historical weather data backfill; logger running since July 2026, revisit as training feature next season
- [ ] Manager change signal — +8 Elo bounce in first 5 games under new manager, well documented in literature. TransferMarkt scrape for manager change dates, update monthly
- [x] Distance travelled — away_travel_km feature (haversine); stadiums.csv covers 442/444 teams; 0.0 fallback when stadium unknown
- [x] Altitude adjustment — altitude_diff feature (home_alt − away_home_alt, metres); same stadiums.csv source; 0.0 fallback
- [x] Stadium capacity proxy — home_capacity_log feature (log10(capacity)); fallback log10(20000) ≈ 4.30 when unknown
- [ ] Squad strength proxy — count of players per team currently playing in top leagues, use existing club Elo data as novel cross-dataset signal
- [ ] Injury/suspension impact — key player missing affects xG significantly. Free sources: BBC Sport, Rotowire, or parse football-data.org injury flags
- [ ] International break fatigue — players returning from international duty, travel disruption and schedule congestion
- [ ] Europa League fatigue — performance drop after Thursday Europa League travel, especially for teams with weak squads
- [ ] TransferMarkt market value — squad market value as proxy for squad strength, free scraping
- [ ] Stadium capacity — crowd noise correlates with home advantage strength, proxy via capacity

### Tier 3 — Model Architecture Improvements
- [x] Separate draw classifier — dedicated binary classifier trained specifically to predict draws, using features like team defensive ratings, historical draw rates by team/league/referee, closeness of Elo ratings
- [ ] Score-effect model — teams play differently when winning (sit deep) vs losing (chase game), current models ignore game state entirely **[DEFERRED Batch 3: needs in-game state data not available in results.csv]**
- [x] Home/away Glicko-2 split — venue-specific G2 dicts (g2_home/g2_away); 4 new features: home_g2_home, away_g2_away, g2_venue_diff, away_g2_uncertainty (Batch 3)
- [x] Time-decay on xG — DECAY=0.85 exponential weighting replaces flat window across all 6 xG averages (Batch 3)
- [ ] Bayesian draw model — model draw probability as a function of match competitiveness and historical draw rates **[DEFERRED Batch 3: draw classifier already covers this — enhancement not gap; revisit after SHAP analysis]**
- [x] Ensemble calibration (Platt scaling) — investigated, ECE 0.0098 already excellent
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
- [ ] Re-run ensemble_backtest.py after each major feature addition to measure uplift
- [ ] SHAP feature importance analysis — identify which new features actually contribute
- [ ] Calibration curve update — verify probability outputs remain calibrated after new features
- [ ] Update feature_cols.json and retrain all saved models after final feature set confirmed

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

### Design Principles (read before starting any Phase 6 task)
- [ ] Trust-at-a-glance hierarchy — every screen leads with ONE confident number or visual, not multiple equal-weight panels. Dashboard hero = single big metric (live CLV or edge found this week), everything else secondary
- [ ] Restraint palette — one brand colour (emerald), one positive accent, one negative accent, everything else neutral slate. No ad-hoc colours anywhere. Two heading sizes, one body size, one small size — no exceptions
- [ ] Typographic respect for numbers — tabular figures (font-variant-numeric: tabular-nums) in every table, consistent decimal places site-wide (2.50 never 2.5), consistent probability precision everywhere
- [ ] Progressive disclosure — surface states the conclusion plainly ("Model sees 12% more chance than the bookmaker"), calculations/Kelly/model breakdown one tap deeper. Methodology page carries credibility for diggers; surface stays clean
- [ ] Confidence bands — wire prediction_uncertainty metadata (built in Phase 2 Batch 3) into prediction displays as visual confidence indication
- [ ] Motion only where data changes — probability bars fill once on load, numbers tick on update, nothing else animates. Movement = "this is live"
- [ ] Designed empty states — off-season/no-value-bets/no-data states are designed screens with a next action ("Leagues return August 15 — see the World Cup Hub"), never blank tables or bare spinners. NOTE: launching into off-season means the no-live-bets state IS the first impression for many users
- [ ] One signature element — pick ONE distinctive visual (edge meter, Elo chart style, or bracket tree) and over-invest in it; that's what gets screenshotted and shared
- [ ] Design tokens doc first — before any page redesign, write frontend/DESIGN.md with colour tokens, type scale, spacing scale; every subsequent frontend task references it (same pattern as the shared feature pipeline, but for design)

### Visual Design
- [ ] Design system — **do this first; artefact is frontend/DESIGN.md** — establish colour tokens, type scale, spacing scale. Emerald green as primary, slate as background, clear hierarchy between primary/secondary/muted text. Every subsequent Phase 6 task references this doc
- [ ] Component library audit — standardise cards, badges, tables, filters across all pages so nothing looks inconsistent
- [ ] Micro-animations — subtle transitions on data loading, card hover states, probability bar fills on page load
- [ ] Icon consistency — single icon library throughout (lucide-react already imported, ensure nothing uses ad-hoc alternatives)

### Key Page Redesigns
- [ ] Dashboard redesign — hero metric strip (value bets identified, hit rate, CLV) → live value bets → upcoming fixtures → ratings snapshot. Each section visually distinct with clear heading
- [ ] Value Bets page redesign — card layout instead of table rows, visual edge meter, bookmaker logo/name prominent, Kelly stake displayed clearly
- [ ] Landing page redesign — above-fold must convert. Large headline, 3 key stats displayed huge, single Sign Up CTA, below-fold: how it works, sample value bets, track record
- [ ] International / World Cup Hub — showcase page that would make someone immediately understand what FormCast does for the World Cup

### Trust Signals
- [ ] Track record section on landing — show the prediction log numbers, CLV, hit rate prominently as social proof
- [ ] "As featured in" / methodology credibility section
- [ ] Live counter — value bets identified today, updating in real time

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
- [ ] SHAP waterfall chart per match — why did the model predict this outcome
- [ ] Cumulative P&L chart — flat stake simulation over time with drawdown shading
- [ ] Brier score trend chart — rolling 90-match window showing model improvement
- [ ] Match prediction card — shareable upcoming fixture card for social media
- [ ] Tournament probability treemap — visual probability distribution per team
- [ ] Value bet history chart — CLV over time, ROI by league breakdown
- [ ] Animated Elo bar chart race — top 20 teams over 33 seasons
- [ ] Global search — find any team, match, or league instantly across the whole site
- [ ] Loading skeletons everywhere — replace all remaining spinners
- [ ] PWA support — installable on mobile home screen, offline support
- [ ] Onboarding tour — first-time user walkthrough (Shepherd.js)
- [ ] Custom domain (formcast.io or similar)
- [ ] Design overhaul — site currently reads as a developer tool, needs to look like a premium product. Priority: dashboard hero, value bet cards, team profile pages, landing page conversion
- [ ] Dashboard hero section — big focal-point number or chart immediately communicating scale and sophistication (e.g. animated counter for value bets identified, live Elo chart)
- [ ] Value bet cards redesign — currently text-heavy rows, should look like trading cards with visual probability bars, odds highlighted, edge displayed prominently with color coding
- [ ] Landing page conversion optimisation — headline, social proof numbers (3,829 value bets, 128k matches, 68.7% hit rate) displayed large and front-and-center, single clear CTA above fold
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
- [ ] Feature importance visualisation (SHAP beeswarm across all 48 features)
- [ ] Glossary page (Brier score, CLV, Kelly criterion, EV, overround etc)

---

## Phase 9 — UX Excellence
> Note: UX improvements apply platform-wide. Mobile responsive layout is critical given the majority of sports betting happens on mobile devices.

- [ ] Onboarding tour — first-time user walkthrough explaining each page (Shepherd.js or similar)
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
- [ ] Monitoring & alerting — Sentry for errors, UptimeRobot for uptime, PagerDuty for critical failures
- [ ] Sentry error monitoring — free tier, catch Railway API errors automatically (PRIORITY — do this week)
- [ ] UptimeRobot monitoring — ping /api/health every 5 minutes, alert on downtime (PRIORITY — do this week)
- [ ] referee_fatigue_features.py in weekly pipeline — regenerate team_tendencies.csv every Monday
- [x] CI/CD pipeline — GitHub Actions
- [x] Railway health checks — /api/health endpoint verified healthy, manual full pipeline health check performed this session
- [x] Retry logic with exponential backoff — predict_upcoming.py fixture fetch now retries 3x (5s/15s/30s) on transient failures instead of immediately failing the whole pipeline
- [ ] Automated test suite — pytest for API, Playwright for frontend E2E tests
- [ ] Data quality checks — automated validation after each ingestion (row counts, nulls, date ranges)
- [ ] Log aggregation — structured logging to Papertrail or Logtail
- [ ] Cost monitoring — Railway and Vercel spend alerts
- [x] Premier League and Championship sport keys fixed — were using wrong key names (soccer_england_premier_league, soccer_england_championship) instead of correct soccer_epl and soccer_efl_champ, confirmed against The Odds API's own /v4/sports endpoint. Recovered Premier League value bets that had been silently 404ing.
- [ ] Ensemble auto-retraining in weekly pipeline — XGBoost/NN/LSTM currently only retrain manually, Elo is the only model updating automatically every Monday. Critical gap before August league restart — without this the ensemble predictions will stale out

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
- [ ] OpenWeatherMap API — weather at kickoff time (wind, rain, temperature)
- [ ] Squad rotation detection — cup game before league game pattern detection
- [ ] International break fatigue — performance drop after international duty
- [ ] Manager change tracking — manual or TransferMarkt, +8 Elo bounce signal
- [ ] Distance travelled database — stadium lat/lng for all 442 clubs, travel km calculator
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
