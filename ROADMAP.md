# FormCast — Sports Prediction Platform
### Elo + Glicko-2 + Dixon-Coles + BTL + XGBoost + Neural Ensemble
*Last updated: May 2026*

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

### Referee & Venue Features (6 signals)
- [ ] Referee tendencies — cards/fouls per game by referee, home bias score (data already in results.csv referee column)
- [ ] Stadium capacity proxy — crowd noise correlates with home advantage strength
- [ ] Altitude adjustment — away team performance penalty for high altitude venues (lookup table)
- [ ] Distance travelled — great-circle km between home grounds, fatigue proxy for midweek games
- [ ] Derby factor — local rivalry binary flag, form less predictive in derbies
- [ ] Neutral venue flag — cup finals, European legs at neutral grounds

### Squad & Personnel Features (8 signals)
- [ ] Manager change bounce — binary flag, teams average +8 Elo in first 5 games under new manager
- [ ] Key player availability — top scorer / goalkeeper missing (requires injury data source)
- [ ] Squad rotation signal — detect rotation from historical patterns when cup game preceded league game
- [ ] Goalkeeper form — saves above expected from xG data (already have xG, just need shot-level data)
- [ ] Set piece specialist — teams with dead ball specialists score more from corners/free kicks
- [ ] Top scorer availability impact — single player xG contribution as % of team total
- [ ] Captain continuity — same captain vs new captain (leadership stability signal)
- [ ] International break fatigue — players returning from international duty, travel and schedule disruption

### Market Intelligence Features (6 signals)
- [ ] Opening vs closing line movement — how much did odds move from open to close, direction
- [ ] Steam move detector — multiple bookmakers move simultaneously = sharp action signal
- [ ] Public vs sharp money split — bookmakers shade lines away from popular teams
- [ ] Overround tracker — monitor bookmaker margin changes as signal of confidence
- [ ] Exchange vs sportsbook divergence — Betfair price vs bookmaker price gap
- [ ] Sharp money threshold — flag when line moves > 8% in < 2 hours pre-kickoff

### Advanced Contextual Features (10 signals)
- [ ] Score effect model — teams play differently when winning (sit deep) vs losing (chase game), current models ignore game state
- [ ] Penalty shootout model — for cup competition knockout stage predictions
- [ ] Cross-competition Elo continuity — already implemented, unique vs single-league platforms
- [ ] 33-year historical dominance — psychological dominance from long-term H2H record
- [ ] Post-European game fatigue — performance drop after Thursday Europa League travel
- [ ] Congestion index — matches in last 14 days weighted by travel distance
- [ ] Season phase adjustment — teams perform differently early/mid/late season (motivation, fatigue)
- [ ] Relegation 6-pointer boost — teams in direct relegation battles show elevated performance
- [ ] Title decider uplift — teams playing title-deciding matches under increased pressure
- [ ] VAR decision tendency — some referees overturn more decisions, affects game flow

---

## Phase 2b — Individual Player Modelling
- [ ] Player-level xG contribution — individual player xG as % of team total (requires shot-level data from FBref/Understat)
- [ ] Goalkeeper save percentage above expected — shotstopping quality beyond team defence
- [ ] Player network graph — pass completion rates between specific player pairs (team cohesion signal)
- [ ] Top scorer absence model — quantify impact of missing striker on team xG
- [ ] Set piece model — corners/free kicks conversion rate by taker
- [ ] Player form streaks — individual scoring/assist streaks as momentum signal
- [ ] Injury probability model — predict injury risk from minutes played, age, fixture congestion
- [ ] International duty fatigue model — performance drop after long-haul international travel

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
- [x] Live win probability engine (football-data.org, 60s cache)
- [x] Upcoming fixtures with pre-match Elo probabilities
- [x] /api/live endpoints (now, today, upcoming)
- [ ] WebSocket live feed (< 1 second end-to-end latency target)
- [ ] Live data feed integration (The Odds API €15/mo, football-data.org free tier, Betfair Exchange API)
- [ ] Upgrade to sub-minute live feed (The Odds API €15/mo)
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
- [x] Match deep-dive page — win/draw/loss probabilities, goals markets, correct scores, BTTS, corners markets, cards markets, H2H stats

---

## Phase 6 — Validation & Statistics
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
- [ ] Loading skeletons instead of spinners
- [ ] Match prediction card (upcoming fixtures with probability breakdown)
- [ ] Tournament simulation visualisation (probability treemap per team)
- [ ] Value bet history chart (CLV over time, ROI by league)
- [ ] Accumulator builder UI (interactive leg selector, real-time EV calculation)
- [ ] Custom domain (formcast.io or similar)

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

## Phase 9 — Model Validation & Transparency
- [ ] Full backtesting results page (hit rate and Brier by league, season, year)
- [ ] Calibration diagram (reliability plot with confidence intervals)
- [x] Model comparison table (all models side by side)
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
- [ ] Player-level stats API for prop betting (FBref, Opta, or StatsBomb)
- [ ] Corners and cards historical data (football-data.co.uk has some of this already)
- [ ] Referee database — historical cards/fouls/home bias per referee (from results.csv referee column)
- [ ] Stadium coordinates database — lat/lng for all clubs to calculate travel distances
- [ ] TransferMarkt integration — injury/suspension data, market values, manager changes
- [ ] Betfair Exchange API — live exchange prices for line movement tracking
- [ ] OpenWeatherMap API — weather at kickoff time (wind, rain, temperature)

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

## Phase 13 — Business & Monetisation
> Note: All phases 13-18 apply across all sports — football, GAA, tennis, golf, NFL, basketball, horse racing, and any future sport additions. Features built for football first, then extended to each sport as data becomes available.

- [ ] Pricing page — free tier vs pro tier clearly explained
- [ ] User accounts — Supabase Auth, save favourite teams, personalised dashboard
- [ ] Pro tier features — advanced filters, more predictions, API access, no rate limits
- [ ] Email notifications — "Arsenal have a value bet this weekend, click to see" (Resend API)
- [ ] Push notifications — browser push for live value bets and match alerts
- [ ] Watchlist — users save teams and get notified when they have value bets
- [ ] API access tier — sell data access to developers, API key management
- [ ] Affiliate bookmaker links — when showing value bets, deep-link to the bookie (Bet365, Paddy Power, Betfair)
- [ ] Subscription management — Stripe integration for pro tier billing
- [ ] Referral program — share FormCast, get a month free
- [ ] Team/league following — personalised feed based on followed teams
- [ ] Usage analytics — track which pages/features users engage with most (PostHog or Mixpanel)

---

## Phase 14 — Trust & Accountability
- [ ] Public prediction log — every prediction published before kickoff, SHA256 stamped, verifiable by anyone
- [ ] Prediction audit trail — immutable record, timestamped, hash-linked like a blockchain
- [ ] Monthly accuracy report — auto-generated PDF, emailed to subscribers, shows track record
- [ ] "About the Model" page — methodology overview, who built it, why trust it, track record
- [ ] Social sharing cards — share a match preview or value bet card to Twitter/X with OG image
- [ ] Verified track record badge — independently audited hit rate displayed prominently
- [ ] Community leaderboard — who has the best prediction record this month
- [ ] Tipping competition — users submit predictions, ranked by Brier score
- [ ] Discord/Slack community integration — post value bets automatically to community channels
- [ ] Press kit — stats, methodology, screenshots for journalists and podcasters
- [ ] Academic paper — write up the methodology as a preprint (arXiv) for credibility

---

## Phase 15 — Automation & Infrastructure
- [x] Automated weekly data ingestion — GitHub Actions, runs every Monday 6am UTC
- [x] Automated model retraining — Elo, tournament, value bets, backtest all automated
- [x] Automated tournament simulator refresh
- [x] Automated value bet generation — live odds via The Odds API
- [ ] Scheduled prediction publishing — generate next gameweek predictions automatically on Thursday
- [ ] Database backup — automated daily Supabase backup to S3
- [ ] Monitoring & alerting — Sentry for errors, UptimeRobot for uptime, PagerDuty for critical failures
- [x] CI/CD pipeline — GitHub Actions
- [ ] Automated test suite — pytest for API, Playwright for frontend E2E tests
- [ ] Data quality checks — automated validation after each ingestion (row counts, nulls, date ranges)
- [ ] Railway health checks — /api/health endpoint monitored, auto-restart on failure
- [ ] Log aggregation — structured logging to Papertrail or Logtail
- [ ] Cost monitoring — Railway and Vercel spend alerts

---

## Phase 16 — Security & Rate Limiting
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

## Phase 17 — UX Excellence
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

## Phase 18 — Data Expansion
- [ ] Europa League historical data — scrape from football-data.co.uk or Kaggle
- [ ] UEFA Conference League data — 2021-present
- [ ] World Cup 2018 and 2022 full historical data
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
