# FormCast — Sports Prediction Platform
### Elo + Glicko-2 + Dixon-Coles + BTL + XGBoost + Neural Ensemble
*Last updated: May 2026*

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
| Top rated team | Bayern Munich (Elo 2051) |

---

## Phase 1 — Core Models (In Progress)
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

---

## Phase 2 — Feature Engineering
### Momentum (8 signals)
- [x] Result momentum — EWM(win=3, draw=1, loss=0, λ=0.6), last 5 matches
- [x] Score momentum — EWM(scored - conceded, λ=0.6), last 5 matches
- [x] Elo momentum — Elo_today minus Elo_28_days_ago
- [x] Scoring rate trend — OLS slope of goals scored, last 8 matches
- [x] Concession rate trend — OLS slope of goals conceded, last 8 matches
- [ ] First-half momentum — EWM(H1 score_diff), last 5
- [ ] Second-half momentum — EWM(H2 score_diff), last 5
- [x] Winning/losing streak — Bernoulli run length

### Fatigue & Fixture Congestion (8 factors)
- [ ] Days since last match (< 4 days = -40 Elo penalty)
- [ ] Matches in last 21 days (3+ = -20 Elo additional)
- [ ] Travel km in last 14 days
- [ ] Cup + league dual burden (-15 Elo)
- [ ] Rest asymmetry (home vs away rest days differential)
- [ ] GAA dual code — football + hurling within 5 days (-25 Elo)
- [ ] County team commitments during intercounty season (-10 Elo)
- [ ] Altitude adjustment for away venue

### Home Advantage (6 dimensions)
- [ ] Base home advantage — OLS from score_diff ~ Elo_diff
- [ ] Distance — great-circle km between grounds
- [ ] Derby factor — same region binary
- [ ] Neutral venue flag
- [ ] Ground familiarity — matches at this ground this season
- [ ] Crowd size proxy

### Psychological & Situational (10 factors)
- [ ] Manager change (binary, last 60 days, +15 Elo)
- [ ] Cup final pressure (-5% scoring rate)
- [ ] Revenge factor (+5 Elo vs opponent who beat them last)
- [ ] Title-deciding match (+3% uplift)
- [ ] Relegation pressure (+10 Elo survival instinct)
- [ ] Post-loss bounce (+8 Elo)
- [ ] Season-opener variance (widen CI 20%)
- [ ] Referee tendency (historical cards/frees per referee)
- [ ] H2H psychological dominance
- [ ] Championship vs league priority (-10 Elo squad rotation)

### Weather (7 conditions — OpenWeatherMap API)
- [ ] Wind speed > 30 km/h (-15% scoring)
- [ ] Heavy rain > 5mm/hr (-20% scoring)
- [ ] Temperature extremes (< 5°C or > 25°C)
- [ ] Pitch waterlogging proxy
- [ ] Floodlit match binary
- [ ] Wind direction advantage (H2 tactical)
- [ ] Altitude > 1500m

---

## Phase 3 — Neural Network Suite
- [x] Feedforward: Input → Dense(256,ReLU) → BN → Dropout(0.3) → Dense(128,ReLU) → Dense(3,Softmax)
- [x] LSTM: last 5 match feature vectors → LSTM(128) → Dense(64) → Dense(1,σ)
- [ ] Graph Neural Network: teams as nodes, matches as edges, GCN propagation
- [ ] Transformer: self-attention over match history sequence

---

## Phase 4 — Live In-Play Engine
- [ ] Markov chain game state model (score_diff, time_bucket, half, momentum)
- [ ] Pre-computed win probability lookup table (O(1) query)
- [ ] Bayesian in-game updater (posterior update per event, Supabase Realtime)
- [ ] Event impact quantification (goal +12-25%, red card -8-20%, etc — learned from data)
- [ ] Next-event prediction (P(goal) vs P(point), P(home scores next))
- [x] Tournament Monte Carlo simulator (100k simulations, < 5 seconds, 14 competitions)
- [ ] WebSocket live feed (< 1 second end-to-end latency target)
- [ ] Live data feed integration (The Odds API €15/mo, football-data.org free tier, Betfair Exchange API)
- [ ] Smart money tracker (odds movement > 10% in < 1hr = sharp money signal)

---

## Phase 5 — Betting Intelligence
- [x] Value bet screener (EV = P_model × odds - 1, threshold > 5%)
- [x] Kelly criterion stake sizing (half-Kelly)
- [x] Accumulator builder — optimal leg selection by EV
- [ ] Accumulator independence testing (same-league correlation correction)
- [ ] Accumulator EV matrix UI (best combinations visualised)
- [ ] Closing line value (CLV) tracking — mean(log(P_model / P_close))
- [ ] SHA256 prediction accountability ledger (hash-stamped pre-match)
- [ ] Sharpe ratio + max drawdown on simulated betting strategy
- [ ] Dutching calculator (stake across multiple outcomes)
- [ ] Arbitrage detector (Σ(1/odds) < 1 across bookmakers)

---

## Phase 6 — Validation & Statistics
- [ ] Full calibration curve (predicted prob vs empirical win rate per decile)
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

## Phase 7 — UX & Design Polish
- [x] Matches page with shot, corner, card stats and league/team filtering
- [x] Filtering and sorting on all pages (league, date, outcome, edge filters)
- [ ] Fix remaining duplicate team names (Dortmund/Borussia Dortmund, Lazio/SS Lazio etc)
- [ ] Add pagination to Matches page (currently limited to 50)
- [ ] Add team profile page (click team → full history, Elo trend, stats)
- [ ] Redesign dashboard with proper data visualisation hero section
- [ ] Elo ratings chart — animated bar chart race (top 20 teams over time)
- [ ] Calibration curve chart (predicted probability vs actual win rate by decile)
- [ ] Cumulative P&L chart (flat stake simulation over time)
- [ ] Brier score trend chart (rolling 90-match window)
- [ ] SHAP waterfall chart per match (why did the model predict this?)
- [ ] H2H comparison page (two-team selector, Elo history, head to head record)
- [x] League filter on ratings page (show only EPL, only La Liga etc)
- [ ] Mobile responsive layout
- [ ] Dark/light mode toggle
- [ ] Loading skeletons instead of spinners
- [ ] Match prediction card (upcoming fixtures with probability breakdown)
- [ ] Tournament simulation visualisation (probability treemap per team)
- [ ] Value bet history chart (CLV over time, ROI by league)
- [ ] Accumulator builder UI (interactive leg selector, real-time EV calculation)
- [ ] Custom domain (formcast.io or similar)

---

## Phase 8 — Mathematics & Methodology Documentation
- [ ] How It Works page — plain English explanation of each model
- [ ] Elo explainer (K-factor, home advantage, MoV multiplier, what ratings mean)
- [ ] Dixon-Coles explainer (bivariate Poisson, tau correction, temporal decay)
- [ ] Glicko-2 explainer (RD, volatility, inactivity penalty)
- [ ] Ensemble explainer (how models are stacked, what meta-learner weights mean)
- [ ] xG explainer (what expected goals measures, why it predicts better than goals)
- [ ] Interactive probability calculator (enter two team ratings, see win probabilities)
- [ ] Feature importance visualisation (SHAP beeswarm across all 48 features)
- [ ] Glossary page (Brier score, CLV, Kelly criterion, EV, overround etc)

---

## Phase 9 — Model Validation & Transparency
- [ ] Full backtesting results page (hit rate and Brier by league, season, year)
- [ ] Calibration diagram (reliability plot with confidence intervals)
- [ ] Model comparison table (all models side by side — Elo, G2, DC, XGB, NN, LSTM, Ensemble)
- [ ] Walk-forward accuracy chart (how hit rate changed over 32 seasons)
- [ ] Closing line value history (CLV per bet, cumulative CLV chart)
- [ ] Prediction log (every prediction ever made, timestamped, SHA256 hashed)
- [ ] Monthly accuracy report (automated, updated after each round of fixtures)
- [ ] Diebold-Mariano test results vs naive baseline
- [ ] Hosmer-Lemeshow calibration test results
- [ ] Permutation feature importance (which features matter most per league)

---

## Phase 10 — Sport Expansion
### Soccer (additional data)
- [ ] Extend history to 1993 (football-data.co.uk archive)
- [ ] Understat xG integration (2014-present, top 5 leagues)
- [ ] FBref advanced stats (2017-present)
- [ ] Kaggle European Soccer Database (25k+ matches)
- [ ] Referee statistics database
- [ ] League of Ireland — scrape from Wikipedia season pages (en.wikipedia.org/wiki/{year}_League_of_Ireland_Premier_Division)

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

### Other Sports
- [ ] Rugby (ESPN Scrum, World Rugby API)
- [ ] NBA basketball (basketball-reference, NBA API)
- [ ] Cricket T20 ball-by-ball (Cricsheet.org)
- [ ] Australian Rules (AFL Tables)

---

## Phase 11 — Frontend (React + Vite)
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

## Phase 12 — API & Deployment
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
