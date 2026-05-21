# FormCast — Technical Documentation

*Last updated: May 2026*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Data Pipeline](#3-data-pipeline)
4. [Models](#4-models)
5. [Feature Engineering](#5-feature-engineering)
6. [API Reference](#6-api-reference)
7. [Frontend Pages](#7-frontend-pages)
8. [Glossary](#8-glossary)
9. [How to Run Locally](#9-how-to-run-locally)
10. [Deployment](#10-deployment)
11. [Known Issues & Limitations](#11-known-issues--limitations)
12. [Roadmap Summary](#12-roadmap-summary)

---

## 1. Project Overview

FormCast is a multi-model football match prediction platform trained on 128,797 matches across 14 competitions from 1993 to 2026. It combines seven statistical and machine-learning models — Elo, Glicko-2, Dixon-Coles, Bradley-Terry-Luce, XGBoost, a Feedforward Neural Network, and an LSTM — into a stacking ensemble. The platform exposes predictions through a Flask API and a React frontend.

### The core thesis

Football results are not random. Match outcomes are partially predictable from measurable prior signals — team strength, recent form, fixture congestion, head-to-head history, and shot quality (xG). No single model captures all of this. An ensemble that stacks different model families (frequentist ratings, probabilistic score models, gradient-boosted trees, neural architectures) extracts more signal than any individual approach.

The key claims, verified by walk-forward backtesting:

- The optimised Elo model correctly identifies the stronger team 68.7% of the time (non-draw matches, full 128k dataset).
- The ensemble achieves a 49.35% three-outcome hit rate on a 2023–2025 holdout — compared to a 33.3% naive baseline.
- The Brier score of 0.156 (binary) beats the coin-flip baseline of 0.250.

### Live URL, repo, stack

| | |
|---|---|
| **Live app** | https://formcast-blush.vercel.app |
| **Repo** | github.com/conairemolloy/formcast |
| **Modelling** | Python — pandas, scipy, scikit-learn, XGBoost, PyTorch |
| **API** | Flask + Flask-CORS |
| **Database** | Supabase (PostgreSQL) |
| **Frontend** | React 19 + Vite + Tailwind CSS + Recharts |
| **Deployment** | Vercel (frontend) + Railway (API) |

---

## 2. Architecture

### Full stack diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (User)                        │
│                React 19 + Vite + Tailwind CSS                │
│           https://formcast-blush.vercel.app                  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS (axios, VITE_API_URL)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask API  (Railway)                       │
│                      api/app.py :5001                        │
│                                                              │
│  Blueprints:                                                 │
│    /api/ratings        → routes/ratings.py                   │
│    /api/predictions    → routes/predictions.py               │
│    /api/matches        → routes/predictions.py               │
│    /api/backtest       → routes/backtest.py                  │
│    /api/value-bets     → routes/value_bets.py                │
│    /api/accumulator    → routes/accumulator.py               │
│    /api/live/*         → routes/live.py                      │
│    /api/tournament     → routes/predictions.py               │
└──────────────┬───────────────────────────┬──────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐  ┌────────────────────────────┐
│   data/processed/*.csv   │  │  football-data.org API      │
│   (pre-computed at        │  │  (live scores, upcoming     │
│    model run time)        │  │   fixtures — 60s cache)     │
└──────────────────────────┘  └────────────────────────────┘
               ▲
               │ produced by
┌──────────────────────────────────────────────────────────────┐
│                   Python model scripts                        │
│   scripts/ingest_*.py  → scripts/*model*.py  → CSVs         │
│                                                              │
│   Training data sources:                                     │
│     football-data.co.uk  (results, odds, stats)              │
│     football-data.org    (live scores)                       │
│     understat.com        (xG data)                           │
└──────────────────────────────────────────────────────────────┘
```

### How the pieces connect

1. **Ingestion scripts** (`scripts/ingest_*.py`) pull raw CSVs from football-data.co.uk and xG data from Understat, then write to `data/processed/results.csv` and `data/processed/xg_data.csv`.
2. **Model scripts** (`scripts/*.py`) read from `data/processed/` and write their output CSVs (predictions, ratings) back to the same directory.
3. **The Flask app** (`api/app.py`) loads the processed CSVs once at startup into `app.config["DATA"]` and serves them from memory. The Live endpoint makes live HTTP calls to football-data.org with a 60-second in-process cache.
4. **The React frontend** (`frontend/src/`) calls the Flask API via axios. In local development, Vite proxies `/api` to `localhost:5001`. In production, `VITE_API_URL` points to the Railway deployment.

### File structure overview

```
formcast/
├── api/
│   ├── app.py                  # Flask app factory, blueprint registration
│   ├── requirements.txt        # API dependencies
│   └── routes/
│       ├── ratings.py          # GET /api/ratings, /api/ratings/glicko2, /api/ratings/btl
│       ├── predictions.py      # GET /api/predictions, /api/matches, /api/tournament
│       ├── backtest.py         # GET /api/backtest
│       ├── value_bets.py       # GET /api/value-bets, /api/value-bets/summary, /kelly
│       ├── accumulator.py      # GET /api/accumulator, /api/accumulator/best
│       └── live.py             # GET /api/live/now, /today, /upcoming
│
├── data/
│   └── processed/              # All CSVs (git-tracked, re-generated by model runs)
│       ├── results.csv         # 128,797 match records (master dataset)
│       ├── elo_ratings.csv     # Current Elo rating per team
│       ├── elo_predictions.csv
│       ├── glicko2_ratings.csv
│       ├── glicko2_predictions.csv
│       ├── btl_ratings.csv
│       ├── btl_predictions.csv
│       ├── dc_predictions.csv
│       ├── full_features.csv   # 48-feature matrix (xG era, 2014+)
│       ├── full_xgb_predictions.csv
│       ├── nn_predictions.csv
│       ├── lstm_predictions.csv
│       ├── ensemble_v2_predictions.csv  # Primary predictions served to UI
│       ├── value_bets.csv
│       ├── kelly_simulation.csv
│       ├── accumulator_bets.csv
│       ├── tournament_simulations.csv
│       ├── backtest_predictions.csv
│       ├── momentum_features.csv
│       ├── fatigue_features.csv
│       ├── h2h_features.csv
│       └── xg_data.csv
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Root component, nav routing
│   │   ├── api.js              # axios instance (VITE_API_URL base)
│   │   └── components/
│   │       ├── Landing.jsx
│   │       ├── RatingsTable.jsx
│   │       ├── Matches.jsx
│   │       ├── Live.jsx
│   │       ├── Predictions.jsx
│   │       ├── BacktestReport.jsx
│   │       ├── Tournament.jsx
│   │       ├── ValueBets.jsx
│   │       ├── Accumulators.jsx
│   │       └── Tooltip.jsx
│   ├── package.json
│   └── vite.config.js
│
├── models/
│   ├── feedforward_nn.pt       # Saved PyTorch weights (feedforward)
│   └── lstm_nn.pt              # Saved PyTorch weights (LSTM)
│
├── scripts/
│   ├── ingest_football_data.py   # football-data.co.uk ingestion
│   ├── ingest_football_data_org.py
│   ├── ingest_xg_data.py         # Understat xG ingestion
│   ├── merge_football_data_org.py
│   ├── merge_xg_features.py
│   ├── fix_team_names.py
│   ├── elo_model.py
│   ├── glicko2.py
│   ├── dixon_coles.py
│   ├── bradley_terry.py
│   ├── bayesian_model.py
│   ├── full_feature_pipeline.py  # Builds 48-feature matrix + XGBoost
│   ├── neural_network.py
│   ├── lstm_model.py
│   ├── ensemble_v2.py
│   ├── momentum_features.py
│   ├── fatigue_features.py
│   ├── h2h_features.py
│   ├── backtest.py
│   ├── value_betting.py
│   ├── tournament_simulator.py
│   └── hyperparameter_search.py
│
├── requirements.txt            # Full Python dependencies (models + API)
├── Procfile                    # Railway start command: `web: python api/app.py`
├── runtime.txt                 # Python version pin
└── .env                        # SUPABASE_URL, SUPABASE_KEY (not committed)
```

---

## 3. Data Pipeline

### Sources

| Source | What it provides | Coverage | Cost |
|--------|-----------------|----------|------|
| football-data.co.uk | Match results, odds, shots, corners, cards | 14 competitions, 1993–2026 | Free |
| football-data.org API | Live scores, upcoming fixtures | Top 12 European competitions | Free tier |
| Understat | Expected Goals (xG) per match | Top 5 leagues, 2014–2025 | Free scrape |

### Ingestion scripts

#### `scripts/ingest_football_data.py`

Downloads CSV files from football-data.co.uk for 11 leagues and 33 seasons (1993-94 through 2025-26), normalises column names, and upserts records into Supabase. Also writes the combined dataset to `data/processed/results.csv`.

```bash
python scripts/ingest_football_data.py
```

Leagues covered: EPL (E0), La Liga (SP1), Bundesliga (D1), Serie A (I1), Ligue 1 (F1), Championship (E1), Scottish Premiership (SC0), Bundesliga 2 (D2), Serie B (I2), Ligue 2 (F2), Segunda (SP2).

The Champions League (CL), Eredivisie (DED), and Euro 2024 (EC) are merged from separate sources via `scripts/merge_football_data_org.py`.

#### `scripts/ingest_xg_data.py`

Scrapes xG data from Understat's AJAX endpoints for EPL, La Liga, Bundesliga, Serie A, and Ligue 1 for seasons 2014-15 through 2024-25.

```bash
python scripts/ingest_xg_data.py
```

Outputs: `data/processed/xg_data.csv` — 19,837 match records with `home_xg` and `away_xg`.

#### `scripts/merge_xg_features.py`

Joins xG data onto results by date and team name, producing `data/processed/results_with_xg.csv`.

```bash
python scripts/merge_xg_features.py
```

### What each script produces

| Script | Output file(s) |
|--------|---------------|
| `ingest_football_data.py` | `data/processed/results.csv` |
| `ingest_xg_data.py` | `data/processed/xg_data.csv` |
| `merge_xg_features.py` | `data/processed/results_with_xg.csv` |
| `elo_model.py` | `elo_ratings.csv`, `elo_predictions.csv` |
| `glicko2.py` | `glicko2_ratings.csv`, `glicko2_predictions.csv` |
| `dixon_coles.py` | `dc_predictions.csv` |
| `bradley_terry.py` | `btl_ratings.csv`, `btl_predictions.csv` |
| `full_feature_pipeline.py` | `full_features.csv`, `full_xgb_predictions.csv` |
| `neural_network.py` | `nn_predictions.csv`, `models/feedforward_nn.pt` |
| `lstm_model.py` | `lstm_predictions.csv`, `models/lstm_nn.pt` |
| `ensemble_v2.py` | `ensemble_v2_predictions.csv` |
| `value_betting.py` | `value_bets.csv`, `kelly_simulation.csv`, `accumulator_bets.csv` |
| `tournament_simulator.py` | `tournament_simulations.csv` |
| `backtest.py` | `backtest_predictions.csv` |
| `momentum_features.py` | `momentum_features.csv` |
| `fatigue_features.py` | `fatigue_features.csv` |
| `h2h_features.py` | `h2h_features.csv` |

### Column definitions for `results.csv`

| Column | Type | Description |
|--------|------|-------------|
| `match_date` | date | Match date (YYYY-MM-DD) |
| `home_team` | string | Home team name |
| `away_team` | string | Away team name |
| `home_goals` | int | Full-time home goals |
| `away_goals` | int | Full-time away goals |
| `result` | enum | `H` (home win), `D` (draw), `A` (away win) |
| `season` | string | e.g. `2024-25` |
| `league` | string | e.g. `EPL`, `LaLiga`, `Bundesliga` |
| `home_shots` | int | Total shots by home team (nullable before ~2000) |
| `away_shots` | int | Total shots by away team |
| `home_shots_target` | int | Shots on target — home |
| `away_shots_target` | int | Shots on target — away |
| `home_corners` | int | Corners — home |
| `away_corners` | int | Corners — away |
| `home_yellows` | int | Yellow cards — home |
| `away_yellows` | int | Yellow cards — away |
| `home_reds` | int | Red cards — home |
| `away_reds` | int | Red cards — away |
| `home_fouls` | int | Fouls — home (where available) |
| `away_fouls` | int | Fouls — away |
| `home_odds` | float | Decimal odds — home win (from football-data.co.uk average) |
| `draw_odds` | float | Decimal odds — draw |
| `away_odds` | float | Decimal odds — away win |

### Current dataset stats

| Metric | Value |
|--------|-------|
| Total matches | 128,797 |
| Competitions | 14 |
| Date range | 1993-07-23 to 2026-05-19 |
| Seasons | 33 (1993-94 through 2025-26) |
| xG matches | 19,837 (top 5 leagues, 2014–2025) |
| Competition list | EPL, Championship, La Liga, Segunda, Serie A, Serie B, Bundesliga, Bundesliga 2, Ligue 1, Ligue 2, Scottish Prem, Champions League (CL), Eredivisie (DED), Euro 2024 (EC) |

---

## 4. Models

### 4.1 Elo Rating

**What it is:** A classic paired-comparison rating system, originally designed for chess. Each team has a single numerical strength estimate that updates after every match. The update magnitude depends on how surprising the result was relative to the pre-match expectation.

**Mathematics:**

Expected score for team A against team B, with home advantage applied:

```
E_A = 1 / (1 + 10^((R_B - (R_A + HOME_ADV)) / 400))
```

Rating update with margin-of-victory multiplier:

```
MoV = min(2.0, 1 + log10(1 + |goal_diff|))
R_A_new = R_A + K × MoV × (S_A - E_A)
```

Where `S_A` is 1 for a win, 0.5 for a draw, 0 for a loss. Parameters K=16 and HOME_ADV=50 were optimised via grid search in `scripts/hyperparameter_search.py`.

**How to run:**

```bash
python scripts/elo_model.py
```

Reads `data/processed/results.csv`. All matches processed in chronological order.

**Output files:** `data/processed/elo_ratings.csv`, `data/processed/elo_predictions.csv`

**Key results:** 68.7% hit rate on non-draw matches across all 128,797 matches. Brier score: 0.156. Top-rated team: Bayern Munich (Elo 2051).

---

### 4.2 Glicko-2

**What it is:** An extension of Elo that tracks uncertainty. Each team has three parameters: a rating (μ), a Rating Deviation (RD, representing uncertainty), and a volatility (σ, representing how consistently a team performs). Teams with high RD have less certain ratings; inactivity increases RD over time.

**Mathematics:**

Internal scale conversion: `μ = (rating - 1500) / 173.7178`, `φ = RD / 173.7178`.

The g-function reduces the influence of uncertain opponents:

```
g(φ) = 1 / sqrt(1 + 3φ²/π²)
```

Expected score:

```
E(μ, μ_j, φ_j) = 1 / (1 + exp(-g(φ_j) × (μ - μ_j)))
```

Volatility σ is updated via the Illinois root-finding algorithm (Glickman 2012, eq. 11). RD update:

```
φ* = sqrt(φ² + σ_new²)
φ_new = 1 / sqrt(1/φ*² + 1/v)
μ_new = μ + φ_new² × g(φ_j) × (score - E)
```

Inactivity penalty: if a team hasn't played in 30+ days, `φ` is inflated proportionally to time absent before the next match.

**How to run:**

```bash
python scripts/glicko2.py
```

Constants: TAU=0.5, INITIAL_RD=200, INITIAL_SIGMA=0.06. First 50 matches skipped (cold start).

**Output files:** `data/processed/glicko2_ratings.csv`, `data/processed/glicko2_predictions.csv`

Ratings CSV columns: `team`, `rating`, `RD`, `sigma`, `mu`, `phi`.

**Key results:** Comparable hit rate to Elo. RD range across all teams indicates high-certainty ratings for teams with long histories in the dataset.

---

### 4.3 Dixon-Coles

**What it is:** A bivariate Poisson model that predicts the number of goals each team scores, then integrates the full score matrix to get H/D/A probabilities. Crucially, it adds a low-score correction factor (τ) that re-weights scorelines near 0-0, 0-1, 1-0, and 1-1 — the zones where the independence assumption of simple Poisson is most violated in real football data.

**Mathematics:**

Each team has an attack parameter α and a defence parameter β. Expected goals:

```
λ (home goals) = exp(α_home + β_away + home_adv)
μ (away goals) = exp(α_away + β_home)
```

Dixon-Coles τ correction for low scores (ρ is a negative correlation parameter):

```
τ(0,0) = 1 - λμρ
τ(0,1) = 1 + λρ
τ(1,0) = 1 + μρ
τ(1,1) = 1 - ρ
τ(x,y) = 1  for x+y > 2
```

The model is fit by maximising the time-weighted log-likelihood with decay factor ξ=0.005 (recent matches weighted more heavily). Optimisation uses `scipy.optimize.minimize` with an L-BFGS-B solver.

**How to run:**

```bash
python scripts/dixon_coles.py
```

Constants: XI=0.005 (temporal decay), MAX_GOALS=10 (score matrix dimension).

**Output files:** `data/processed/dc_predictions.csv`

---

### 4.4 Bradley-Terry-Luce (BTL)

**What it is:** A pairwise comparison model from psychometric theory. Each team has a latent strength parameter β. The probability of a home win is the sigmoid of the strength difference plus a learned home advantage term. Parameters are estimated by maximum likelihood with L2 regularisation.

**Mathematics:**

```
P(home wins) = σ(β_home - β_away + home_adv)
             = 1 / (1 + exp(-(β_home - β_away + home_adv)))
```

Negative log-likelihood with L2 regularisation:

```
NLL = -Σ [s_i × log P_i + (1-s_i) × log(1-P_i)] + (λ/2) × ||β||²
```

Gradients are computed analytically and passed to L-BFGS-B. The model is re-fit every 50 prediction matches using a rolling 76-week window, so team strengths adapt to form over time without forgetting too much history.

**How to run:**

```bash
python scripts/bradley_terry.py
```

Constants: LAMBDA=0.001, WINDOW_WEEKS=76, COLD_START=200, REFIT_EVERY=50.

**Output files:** `data/processed/btl_ratings.csv`, `data/processed/btl_predictions.csv`

---

### 4.5 XGBoost (full feature pipeline)

**What it is:** A gradient-boosted tree classifier trained on a 48-feature matrix that combines Elo/Glicko-2 ratings, xG statistics, momentum signals, fatigue features, and head-to-head history. Produces 3-class probabilities (H/D/A).

**How to run:**

```bash
python scripts/full_feature_pipeline.py
```

This script both builds the feature matrix and trains the XGBoost classifier end-to-end. It processes all matches chronologically, building team-level state (Elo, Glicko-2, form, fatigue, H2H) before each match using only prior data (no leakage).

**48 features used:**

See [Section 5](#5-feature-engineering) for the full list grouped by category.

**Training details:**

- Data: xG era only (2014-08-01 onwards), ~19,000 matches
- Temporal split: first 80% for training, last 20% for test
- Label encoding: A=0, D=1, H=2
- XGBClassifier with softprob objective

**Output files:** `data/processed/full_features.csv` (feature matrix), `data/processed/full_xgb_predictions.csv` (predictions)

**Key results:** 52.5% three-outcome hit rate on holdout.

---

### 4.6 Feedforward Neural Network

**What it is:** A 4-layer fully-connected network trained on the same 48-feature matrix as the XGBoost model. Uses batch normalisation and dropout for regularisation, and softmax output for 3-class probabilities.

**Architecture:**

```
Input(48)
→ Linear(48 → 256) + ReLU + BatchNorm + Dropout(0.3)
→ Linear(256 → 128) + ReLU + BatchNorm + Dropout(0.2)
→ Linear(128 → 64) + ReLU
→ Linear(64 → 3) + Softmax [inference]
```

**Training details:**

- Framework: PyTorch
- Epochs: up to 100 with early stopping (patience=10)
- Batch size: 256
- Optimizer: Adam (LR=1e-3, weight decay=1e-4)
- Validation: last 10% of time-ordered data
- Data: xG era (2014+)

**How to run:**

```bash
python scripts/neural_network.py
```

**Output files:** `data/processed/nn_predictions.csv`, `models/feedforward_nn.pt`

**Key results:** 53.1% three-outcome hit rate on 2014–2025 holdout. Brier score: 0.584 (3-outcome, lower is better relative to 0.667 baseline).

---

### 4.7 LSTM

**What it is:** A long short-term memory network that treats each match as part of a temporal sequence of team performances. For each upcoming match, it looks at the last 5 matches of both the home and away team, encoding 8 features per team per timestep (16 features total per timestep, 5 timesteps = sequence of length 5).

**Architecture:**

```
Input: (batch, seq_len=5, features=16)
  home team: 8 features/match × last 5 matches
  away team: 8 features/match × last 5 matches
  concatenated per timestep → 16 features

LSTM(input=16, hidden=128, layers=2, dropout=0.2, batch_first=True)
→ last hidden state: (batch, 128)
→ Linear(128 → 64) + ReLU
→ Linear(64 → 3)
→ Softmax [inference only]
```

**Training details:** Same as feedforward NN (Adam, early stopping, 10% temporal validation split, xG era only).

**How to run:**

```bash
python scripts/lstm_model.py
```

**Output files:** `data/processed/lstm_predictions.csv`, `models/lstm_nn.pt`

**Key results:** 53.3% three-outcome hit rate on 2014–2025 holdout.

---

### 4.8 Ensemble v2

**What it is:** A stacking meta-learner that takes the outputs of all base models as inputs and learns how to combine them optimally. The meta-learner is a logistic regression (with StandardScaler) trained on out-of-fold (OOF) base model predictions generated via 5-fold TimeSeriesSplit — ensuring no information from the future is used to train any fold.

**Stack inputs (12 features):**

```
home_expected       — Elo probability of home win
p_home_g2           — Glicko-2 probability of home win
p_home_dc           — Dixon-Coles P(home win)
p_draw_dc           — Dixon-Coles P(draw)
p_away_dc           — Dixon-Coles P(away win)
p_home_xgb          — XGBoost P(home win)
p_draw_xgb          — XGBoost P(draw)
p_away_xgb          — XGBoost P(away win)
elo_diff            — home Elo minus away Elo
h2h_goal_diff_avg   — average H2H goal difference (home perspective)
h2h_home_win_rate   — home win rate in H2H history
momentum_diff       — home result momentum minus away result momentum
```

**How to run:**

```bash
python scripts/ensemble_v2.py
```

This is the main script that runs the entire prediction pipeline end-to-end. It internally re-runs Elo, Glicko-2, Dixon-Coles, and XGBoost to generate OOF predictions, then trains and applies the meta-learner. Cold start: first 200 matches excluded.

**Output file:** `data/processed/ensemble_v2_predictions.csv` — this is the primary predictions file served to the UI.

**Key results:** 49.35% three-outcome hit rate on 10,099 predictions through May 2026 (2023–2025 holdout).

---

## 5. Feature Engineering

All features are computed with strict temporal ordering — only data from prior to each match is used.

### Momentum features (6 implemented)

| Feature | Description | Computation |
|---------|-------------|-------------|
| `home_result_momentum` | Recent results trend | EWM(win=3, draw=1, loss=0, α=0.4) over last 5 matches |
| `away_result_momentum` | Same for away team | Same formula |
| `home_score_momentum` | Goal difference trend | EWM(scored - conceded, α=0.4) over last 5 matches |
| `away_score_momentum` | Same for away team | Same formula |
| `home_elo_momentum` | Elo trajectory | Current Elo minus Elo 28 days ago |
| `away_elo_momentum` | Same for away team | Same formula |
| `home_streak` | Win/loss run | +N = won last N, -N = lost last N, Bernoulli run length |
| `away_streak` | Same for away team | Same formula |

Also computed but used indirectly: `home_scoring_rate_trend`, `away_scoring_rate_trend` (OLS slope of goals scored over last 8 matches).

### Fatigue & fixture congestion features

| Feature | Description |
|---------|-------------|
| `home_days_rest` | Days since last match (default 14 if no prior match) |
| `away_days_rest` | Same for away team |
| `home_matches_21d` | Matches played in the last 21 days |
| `away_matches_21d` | Same for away team |
| `rest_asymmetry` | `home_days_rest - away_days_rest` |
| `home_fatigue_score` | Composite fatigue index (days + match load) |
| `away_fatigue_score` | Same for away team |

Also tracked but not yet in ensemble: `matches_14d`, `matches_7d`, `season_matches`, `days_since_season_start`.

### H2H features

| Feature | Description |
|---------|-------------|
| `h2h_home_win_rate` | Home win rate in last 10 H2H meetings (default 0.45) |
| `h2h_goal_diff_avg` | Average goal difference from home perspective over last 10 H2H |
| `h2h_meetings` | Total H2H meetings in dataset |
| `h2h_dominance` | Weighted win rate accounting for recency |
| `revenge_factor` | Binary — did home team lose the most recent H2H meeting? |

H2H records are order-independent (canonical key = sorted team pair). Perspective is always adjusted to the current match's home team.

### xG integration

Expected Goals data from Understat covers the top 5 leagues from 2014-15 onwards (19,837 matches). Features derived from xG:

| Feature | Description |
|---------|-------------|
| `home_xg_avg` | Home team's average xG created in last 5 matches (as home team) |
| `away_xg_avg` | Away team's average xG created in last 5 matches (as away team) |
| `home_xg_conceded_avg` | Home team's average xG conceded in last 5 matches |
| `away_xg_conceded_avg` | Away team's average xG conceded in last 5 matches |
| `home_xg_diff_avg` | Average xG difference (created - conceded) for home team |
| `away_xg_diff_avg` | Average xG difference for away team |

For matches before 2014 or outside the top 5 leagues, these features are set to 0.

### Full 48-feature list

```python
# Elo
"home_elo", "away_elo", "elo_diff", "home_expected",
# Glicko-2
"home_g2_rating", "away_g2_rating", "g2_diff", "home_g2_uncertainty",
# Form (last 5 matches)
"home_form", "away_form", "form_diff",
"home_goals_scored_avg", "home_goals_conceded_avg",
"away_goals_scored_avg", "away_goals_conceded_avg",
# xG (last 5 matches, venue-split)
"home_xg_avg", "away_xg_avg",
"home_xg_conceded_avg", "away_xg_conceded_avg",
"home_xg_diff_avg", "away_xg_diff_avg",
# Momentum
"home_result_momentum", "away_result_momentum",
"home_score_momentum", "away_score_momentum",
"home_elo_momentum", "away_elo_momentum",
"home_streak", "away_streak",
"momentum_diff",
# Fatigue
"home_days_rest", "away_days_rest",
"home_matches_21d", "away_matches_21d",
"rest_asymmetry",
"home_fatigue_score", "away_fatigue_score",
# Head-to-head
"h2h_home_win_rate", "h2h_goal_diff_avg",
"h2h_meetings", "h2h_dominance",
"revenge_factor",
"home_unbeaten_run", "away_unbeaten_run",
"post_loss_bounce", "post_loss_bounce_away",
# Context
"league_encoded", "is_early_season",
```

---

## 6. API Reference

### Base URL

- **Local development:** `http://localhost:5001`
- **Production (Railway):** Set as `VITE_API_URL` in Vercel environment variables

All endpoints return JSON with the envelope:

```json
{
  "success": true,
  "data": [...],
  "meta": {
    "count": 42,
    "generated_at": "2026-05-21T10:00:00+00:00"
  }
}
```

Errors return `{"success": false, "error": "message"}` with an appropriate HTTP status code.

### Caching

The Live endpoints cache responses in-process for 60 seconds (CACHE_TTL). All other endpoints serve from in-memory DataFrames loaded at startup — no per-request I/O.

---

### `GET /api/health`

Returns API status.

```json
{"status": "ok", "version": "1.0.0"}
```

---

### `GET /api/ratings`

Returns current Elo ratings for all teams, sorted by rating descending.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `league` | string | Filter to a single league (e.g. `EPL`, `LaLiga`) |

**Example response:**

```json
{
  "success": true,
  "data": [
    {"team": "Bayern Munich", "elo_rating": 2051.2, "league": "Bundesliga"},
    {"team": "Man City", "elo_rating": 1982.5, "league": "EPL"}
  ],
  "meta": {"count": 487, "generated_at": "..."}
}
```

---

### `GET /api/ratings/glicko2`

Returns Glicko-2 ratings for all teams.

**Response columns:** `team`, `rating`, `RD`, `sigma`, `mu`, `phi`

---

### `GET /api/ratings/btl`

Returns Bradley-Terry-Luce ratings for all teams.

---

### `GET /api/ratings/<team>`

Returns all three ratings (Elo, Glicko-2, BTL) for a single team. Case-insensitive. Returns 404 if team not found.

---

### `GET /api/predictions`

Returns ensemble v2 predictions. These are pre-computed predictions from `ensemble_v2_predictions.csv`.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `league` | string | Filter by league |
| `date` | string | Filter by exact match date (YYYY-MM-DD) |

---

### `GET /api/matches`

Returns historical match records from `results.csv` with stats.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `league` | string | — | Filter by league |
| `team` | string | — | Filter by team (home or away) |
| `season` | string | — | Filter by season (e.g. `2024-25`) |
| `limit` | int | 50 | Max records to return |

Returns sorted by `match_date` descending. Columns: `match_date`, `league`, `season`, `home_team`, `away_team`, `home_goals`, `away_goals`, `result`, `home_shots`, `away_shots`, `home_shots_target`, `away_shots_target`, `home_corners`, `away_corners`, `home_yellows`, `away_yellows`, `home_reds`, `away_reds`.

---

### `GET /api/backtest`

Returns walk-forward backtest accuracy report.

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `league` | string | Filter to one league |

**Response structure:**

```json
{
  "success": true,
  "data": {
    "overall": {
      "hit_rate": 0.4935,
      "brier_score": 0.1234,
      "total_matches": 10099
    },
    "by_league": [
      {"league": "EPL", "hit_rate": 0.51, "brier": 0.12, "matches": 1200}
    ],
    "by_season": [
      {"season": "2024-25", "hit_rate": 0.50, "matches": 380}
    ]
  }
}
```

---

### `GET /api/value-bets`

Returns value bet opportunities where model edge exceeds threshold.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_edge` | float | 0.05 | Minimum edge (EV) threshold |
| `limit` | int | 50 | Max records |
| `league` | string | — | Filter by league |
| `outcome` | string | — | Filter by `H`, `D`, or `A` |

---

### `GET /api/value-bets/summary`

Returns aggregate betting statistics: `total_bets`, `win_rate`, `roi`, `mean_clv`, `sharpe`.

---

### `GET /api/value-bets/kelly`

Returns the Kelly criterion stake simulation data.

---

### `GET /api/accumulator`

Returns pre-computed accumulator combinations ranked by expected value.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `n_legs` | int | 2 | Number of legs: 2 or 3 |
| `limit` | int | 20 | Max combinations to return |

---

### `GET /api/accumulator/best`

Returns the top 10 accumulators across all leg counts, sorted by `acca_ev`.

---

### `GET /api/tournament`

Returns current-season tournament simulation results (Monte Carlo, 100k simulations).

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `league` | string | Filter to one league (e.g. `EPL`, `LaLiga`) |

**Response columns:** `team`, `league`, `current_pts`, `p_title`, `p_top4`, `p_top6`, `p_relegation`, `sim_pts_mean`, `sim_pts_sd`.

---

### `GET /api/live/now`

Returns matches currently in play. Calls football-data.org `/v4/matches?status=LIVE,IN_PLAY,PAUSED`. Returns live win probabilities updated for current score and minute.

---

### `GET /api/live/today`

Returns all matches scheduled or in play today. Pre-match fixtures show Elo-based pre-match probabilities; in-play fixtures show updated probabilities.

---

### `GET /api/live/upcoming`

Returns scheduled matches for the next 7 days with Elo-based pre-match probabilities.

**Live probability model:** The in-play model adjusts the pre-match logit using `score_diff × (1 - time_remaining) × 2.5`. Draw probability decays linearly with time remaining, weighted by score closeness.

---

## 7. Frontend Pages

The frontend is a single-page React app. Navigation is handled in `App.jsx` — clicking a nav button updates `active` state and renders the corresponding component. The landing page is shown when `active === null`.

### Landing

**What it shows:** Hero section with the platform name, description, and key statistics (128k matches, 68.7% accuracy, 14 competitions). Includes a model stack overview card, a scrolling data ticker, and feature cards that link to each page.

**How to use:** Click any feature card or the "Explore Predictions" button to navigate to a page.

---

### Ratings

**What it shows:** A sortable table of all team Elo ratings, grouped by league. Tabs switch between Elo, Glicko-2, and BTL rating systems.

**How to use:** Use the league filter dropdown to show only one competition. Click column headers to sort. The `RD` column in Glicko-2 view shows rating uncertainty — a lower RD means higher confidence.

**Columns:**

| Column | Meaning |
|--------|---------|
| Rank | Position by rating within the current view |
| Team | Team name |
| Elo / Rating | Numerical strength estimate |
| RD (Glicko-2 only) | Rating Deviation — 95% CI is approximately ±2×RD |
| σ (Glicko-2 only) | Volatility — how consistently the team performs |
| League | Competition |

---

### Matches

**What it shows:** Historical match results with shots, corners, and cards statistics. Default shows 50 most recent matches across all leagues.

**How to use:** Filter by league, team, or season using the dropdowns. Results sorted newest first.

**Columns:** Date, Home, Away, Score, Result, Shots (H/A), Shots on Target (H/A), Corners (H/A), Yellow Cards (H/A), Red Cards (H/A).

**Known limitations:** Shot and corner stats are null for most matches before 2000. CL, EC, and DED entries have no shot/corner data.

---

### Live

**What it shows:** Three tabs — In Play (matches happening now), Today (all today's matches), Upcoming (next 7 days). Each match shows Elo ratings for both teams and real-time win probabilities.

**How to use:** The page polls the API automatically. In-play matches show score, minute, and live-updated probabilities. Use the competition filter to narrow down to a specific league.

**Columns:** Competition, Home, Away, Score (in-play only), Minute (in-play only), P(H), P(D), P(A), Home Elo, Away Elo.

**P(H) / P(D) / P(A):** Probability of home win, draw, away win. For pre-match fixtures these are Elo-based. For in-play fixtures the model adjusts based on current score and time elapsed.

**Known limitations:** football-data.org free tier covers fewer competitions than the full dataset. Teams not found in the Elo ratings file default to 1500 (average strength).

---

### Predictions

**What it shows:** The ensemble v2 model's predictions for all matches it has predictions for, with H/D/A probabilities and the predicted outcome.

**How to use:** Filter by league or date. Sorted by match date. The `predicted` column shows the model's top prediction; `correct` shows whether it was right (for completed matches).

**Columns:** Date, League, Home, Away, P(H), P(D), P(A), Predicted, Actual (if played), Correct.

**Known limitations:** Predictions only exist from 2019 onwards (the training data window requires prior match history; the xG era starts 2014, and meaningful ensemble predictions need full feature coverage). Future matches show probabilities only.

---

### Backtest

**What it shows:** Walk-forward accuracy metrics for the ensemble model, broken down by league and season.

**How to use:** Select a league from the dropdown to filter. The summary cards at the top show overall hit rate and Brier score. The league breakdown table and season breakdown table update based on the filter.

**Metrics:**

| Metric | Meaning |
|--------|---------|
| Hit Rate | Fraction of matches where the model's top prediction matched the actual result |
| Brier Score | Mean squared error of probability estimates (lower = better; random = 0.333 for 3 classes) |
| Total Matches | Number of matches in the backtest set |

---

### Tournament

**What it shows:** Current-season league table with Monte Carlo simulation results. For each team: current points, simulated mean final points, title probability, top-4 probability, and relegation probability.

**How to use:** Use the league dropdown to switch between competitions. Sorted by current points descending.

**Columns:** Team, Current Pts, Sim Pts (mean ± SD), P(Title), P(Top 4), P(Top 6), P(Relegation).

**How probabilities are computed:** 100,000 Monte Carlo simulations of remaining fixtures. Each simulation samples a result for each unplayed match using Elo H/D/A probabilities, updates Elo after each simulated match, and aggregates final tables. Probabilities are the fraction of simulations where each outcome occurred.

**Known limitations:** When the season is effectively over (very few matches remaining), the simulator produces near-deterministic results — this is correct behaviour, not a bug. The script must be re-run to refresh probabilities after new results.

---

### Value Bets

**What it shows:** Matches where the model's probability estimate is significantly higher than the implied probability from bookmaker odds. Sorted by edge (descending).

**How to use:** Adjust the minimum edge slider to control the threshold. Filter by league or outcome type. The Kelly column shows the recommended fraction of bankroll to stake (half-Kelly).

**Columns:** Date, League, Home, Away, Outcome, Model Prob, Market Prob, Edge, Decimal Odds, Kelly Stake.

**Key terms:**

- **Edge** = `P_model × odds - 1` (also called Expected Value or EV)
- **Kelly Stake** = `edge / (odds - 1)` — the theoretically optimal stake fraction; this page shows half-Kelly as a conservative sizing strategy
- **Overround** = `Σ(1/odds)` for all outcomes — the bookmaker's margin, typically 4–8%

**Known limitations:** Odds in `results.csv` are historical averages from football-data.co.uk, not live prices. Real-time value bet identification requires a live odds API (not yet integrated).

---

### Accumulators

**What it shows:** Pre-computed multi-leg accumulator combinations, ranked by combined Expected Value. Toggle between 2-leg and 3-leg accumulators.

**How to use:** Use the legs selector (2 or 3). Each row shows the component legs, their individual probabilities and odds, the combined odds, and the accumulator EV.

**Columns:** Legs, Matches, Combined Odds, Acca EV.

**How acca EV is computed:** `acca_ev = Π(P_model_i × odds_i) - 1`. Each leg is independently selected as a value bet; the accumulator combines their individual edges. Note: this assumes leg independence (same-league correlations not yet corrected for).

---

## 8. Glossary

**Elo rating:** A numerical team strength estimate on a scale of roughly 1000–2200 for club football. 1500 is average. A 400-point gap corresponds to approximately a 91% win probability for the stronger team.

**Brier score:** Mean squared error of probability estimates. For binary outcomes: `BS = mean((p_predicted - actual)²)`. Range 0–1; lower is better. A random predictor on a 50/50 binary outcome scores 0.25. For 3-class outcomes the baseline is 0.333.

**Hit rate:** The fraction of matches where the model's top-predicted outcome matches the actual result. For binary (non-draw) Elo this can reach ~68%; for 3-outcome prediction the random baseline is 33.3%.

**Expected Value (EV):** `EV = P_model × decimal_odds - 1`. Positive EV means the model believes the bet is underpriced by the bookmaker. Also called "edge."

**Edge:** Synonymous with EV in the betting context. An edge of 0.05 means the model expects a 5% return per unit staked on that bet, long-run.

**Closing Line Value (CLV):** `CLV = log(P_model / P_closing_odds)`. Measures whether your pre-match probability was more accurate than the market's closing price. Positive CLV over many bets is a strong indicator of genuine predictive edge, since closing prices incorporate all sharp money.

**Kelly Criterion:** An optimal bankroll management formula. Full-Kelly stake fraction = `edge / (odds - 1)`. In practice, half-Kelly is used: `stake = 0.5 × edge / (odds - 1)`. This maximises log-growth of bankroll while reducing variance.

**Walk-forward backtesting:** A validation method where predictions are made only using data available up to that point in time. The model is never trained on future data. This is the correct way to validate time-series prediction models — using a random train/test split would leak future information.

**Dixon-Coles tau correction:** A bivariate correction applied to the Poisson independence assumption in football score modelling. Goals near 0-0, 0-1, 1-0, 1-1 are correlated in real data; the τ function re-weights these cells in the score probability matrix. The parameter ρ (typically small and negative) controls the strength of the correction.

**Glicko-2 RD (Rating Deviation):** The standard deviation of a team's true skill estimate. A 95% confidence interval for the true rating is approximately `rating ± 2 × RD`. New teams start with RD=200; it decreases as more matches are played and increases during periods of inactivity.

**Glicko-2 volatility (σ):** Measures how erratically a team's performance varies over time — beyond what would be expected from opponent strength. High σ means the team's results are unpredictable even controlling for quality. Typical values: 0.04–0.08.

**P(H), P(D), P(A):** Probability of home win, draw, away win. Must sum to 1. For display purposes these are the model's calibrated estimates; they are not bookmaker odds.

**Decimal odds:** European-style odds format. A decimal odds of 2.50 means a €1 stake returns €2.50 (including stake), implying a 40% win probability. Implied probability = 1 / decimal_odds.

**Fractional odds:** UK/Irish format. 3/1 means win €3 for every €1 staked. To convert: decimal = (numerator/denominator) + 1. So 3/1 = 4.00 decimal.

**Accumulator (acca):** A multi-selection bet where all legs must win. The combined odds are the product of individual leg odds. Combined probability is the product of individual probabilities (assuming independence). High potential return, lower probability.

**Monte Carlo simulation:** A method of estimating probabilities by running many random simulations. In FormCast, 100,000 independent simulations of a league season are run, sampling match results from Elo probabilities. The fraction of simulations where each outcome occurs gives the probability estimate.

**Overround:** Also called "vig" or "juice." `Σ(1/odds)` for all outcomes in a market. A fair market sums to exactly 1.0; bookmakers price at ~1.05–1.10, skimming the overround as their margin. Dividing implied probabilities by the overround gives calibrated market probabilities.

**Bradley-Terry-Luce model:** A pairwise comparison model where each entity has a scalar strength parameter. The probability of A defeating B is `σ(β_A - β_B)`, where σ is the sigmoid function. MLE fitting via L-BFGS-B gives optimal strength parameters.

---

## 9. How to Run Locally

### Prerequisites

- Python 3.11 or 3.12
- Node.js 20+
- Git

### Step 1: Clone the repo

```bash
git clone https://github.com/conairemolloy/formcast.git
cd formcast
```

### Step 2: Set up Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
```

### Step 3: Install Python dependencies

```bash
pip install -r requirements.txt
# If running neural network models also install PyTorch:
pip install torch torchvision
```

### Step 4: Set up environment variables

Create a `.env` file in the project root:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

These are only required for the Supabase upserting in `ingest_football_data.py`. The API itself reads from local CSVs and does not require Supabase at runtime.

### Step 5: Run the data pipeline

The `data/processed/` CSVs are committed to git so you can skip steps 5–6 and go straight to running the API. To re-generate from scratch:

```bash
# Pull raw results and xG data
python scripts/ingest_football_data.py
python scripts/ingest_xg_data.py
python scripts/merge_xg_features.py
```

### Step 6: Run the models

Run in order — later scripts depend on outputs of earlier ones:

```bash
python scripts/elo_model.py
python scripts/glicko2.py
python scripts/dixon_coles.py
python scripts/bradley_terry.py
python scripts/full_feature_pipeline.py   # builds feature matrix + XGBoost
python scripts/neural_network.py          # requires PyTorch
python scripts/lstm_model.py              # requires PyTorch
python scripts/ensemble_v2.py             # stacks all base models
python scripts/value_betting.py
python scripts/tournament_simulator.py
python scripts/backtest.py
```

Each script prints a summary when it completes. Typical total runtime for the full pipeline: 15–25 minutes on a modern laptop (the tournament simulator is the slowest at ~5 minutes for 100k simulations).

### Step 7: Start the Flask API

```bash
python api/app.py
```

The API will be available at `http://localhost:5001`. Verify with:

```bash
curl http://localhost:5001/api/health
```

### Step 8: Start the React frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173`. Vite proxies all `/api` requests to `localhost:5001`.

---

## 10. Deployment

### API — Railway

The API is deployed to Railway using the `Procfile`:

```
web: python api/app.py
```

**Setup:**

1. Connect the GitHub repo to Railway.
2. Set `PORT` in Railway environment variables (Railway injects this automatically).
3. Add `SUPABASE_URL` and `SUPABASE_KEY` if needed.
4. The `runtime.txt` file pins the Python version.

**To redeploy:** Push to the `main` branch. Railway auto-deploys on push.

### Frontend — Vercel

The frontend is deployed to Vercel from the `frontend/` subdirectory.

**Setup:**

1. Connect the GitHub repo to Vercel.
2. Set the root directory to `frontend/`.
3. Build command: `npm run build`
4. Output directory: `dist`
5. Add environment variable: `VITE_API_URL=https://your-railway-api-url`

**To redeploy:** Push to `main`. Vercel auto-deploys on push.

### Environment variables summary

| Variable | Where | Description |
|----------|-------|-------------|
| `SUPABASE_URL` | Python / Railway | Supabase project URL |
| `SUPABASE_KEY` | Python / Railway | Supabase anonymous key |
| `VITE_API_URL` | Vercel | Full URL of the Railway API deployment |
| `PORT` | Railway (auto) | Port for Flask to bind to |

---

## 11. Known Issues & Limitations

**South American teams default to Elo 1500.** The Live page pulls fixtures from football-data.org, which includes some competitions with teams not in the training dataset. Any unrecognised team is assigned a rating of 1500 (average). This makes probabilities unreliable for those matches.

**Predictions only from 2019 onwards.** The ensemble needs a full feature history for each team before making predictions. The xG features require data from 2014+, and the cold start of 200 matches further delays the start. Meaningful predictions are available from approximately 2019.

**CL, EC, and DED matches have no shot/corner stats.** The Champions League, Eredivisie, and Euro 2024 entries were ingested from football-data.org, which doesn't include match stats at the free tier. Shots, corners, and cards columns are null for these competitions.

**Tournament table shows near-deterministic results late in the season.** When 1–2 matches remain and the title race is decided, simulation probabilities converge to 0% or 100%. This is mathematically correct but may look surprising. The tournament simulator must be re-run to reflect the latest results.

**football-data.org free tier limited to last 2–3 seasons.** The football-data.org API (used for live scores and upcoming fixtures) restricts free accounts to recent seasons. Historical data for that source is therefore limited.

**Accumulator EV assumes leg independence.** The accumulator builder multiplies individual match EVs without correcting for within-league correlations (e.g. two EPL matches on the same day may be correlated through shared opponents or weather). This can slightly overstate accumulator EV.

**Team name normalisation is incomplete.** Some teams appear under multiple names across different sources (e.g. Borussia Dortmund vs Dortmund, Lazio vs SS Lazio). The `fix_team_names.py` script and the `_FDO_TO_ELO` dictionary in `live.py` handle the most common mismatches, but edge cases remain.

**No live odds integration.** Value bets are computed from historical closing odds in `results.csv`. Real-time value identification requires a live odds API (e.g. The Odds API at €15/mo), which is not yet integrated.

---

## 12. Roadmap Summary

### What's done (Phases 1–4 partial)

- Full data pipeline: 128,797 matches, 14 competitions, 1993–2026
- Elo model with margin-of-victory multiplier and hyperparameter optimisation
- Glicko-2 uncertainty-aware ratings
- Dixon-Coles bivariate Poisson model with tau correction and temporal decay
- Bradley-Terry-Luce pairwise comparison ratings
- XGBoost classifier with 48 features
- Feedforward neural network (53.1% hit rate)
- LSTM temporal model (53.3% hit rate)
- Stacking ensemble meta-learner (49.35% hit rate, 2023–2025 holdout)
- Walk-forward backtesting pipeline (strict temporal ordering)
- Value bet screener (EV-based, half-Kelly sizing)
- Accumulator builder (optimal leg selection by EV)
- Monte Carlo tournament simulator (100k simulations, 14 competitions)
- Live/today/upcoming fixtures with Elo probabilities (football-data.org, 60s cache)
- Full React frontend: Landing, Ratings, Matches, Live, Predictions, Backtest, Value Bets, Accumulators, Tournament
- Flask API deployed on Railway; frontend deployed on Vercel

### What's next (near-term)

- Closing Line Value (CLV) tracking
- Live odds API integration (The Odds API)
- Calibration curve and reliability diagram
- Team profile page (click team → full history, Elo trend)
- Mobile-responsive layout
- WebSocket live feed (< 1s latency)
- SHAP feature importance per match
- SHA256 prediction accountability ledger

### Phase by phase status

| Phase | Status |
|-------|--------|
| Phase 1 — Core Models | Complete |
| Phase 2 — Feature Engineering | ~60% (momentum + fatigue + H2H done; weather, psychological, home advantage dimensions pending) |
| Phase 3 — Neural Network Suite | Feedforward + LSTM done; GNN and Transformer pending |
| Phase 4 — Live In-Play Engine | Basic live endpoint done; Markov chain in-play model, WebSocket feed pending |
| Phase 5 — Betting Intelligence | EV + Kelly + accumulators done; CLV tracking, arbitrage detector, Dutching pending |
| Phase 6 — Validation & Statistics | Backtesting done; calibration curves, Hosmer-Lemeshow, Diebold-Mariano pending |
| Phase 7 — UX & Design | Landing page done; charts, mobile layout, team profiles, H2H page pending |
| Phase 8 — Methodology Docs | This file. Interactive explainers pending |
| Phase 9 — Model Validation | Walk-forward backtest done; CLV history, prediction log, monthly reports pending |
| Phase 10 — Sport Expansion | Football only. Tennis, golf, NFL, GAA planned |
| Phase 11 — Frontend | Core pages done; visualisation charts, real-time UI pending |
| Phase 12 — API & Deployment | Core endpoints deployed; WebSocket, per-match deep dives pending |
