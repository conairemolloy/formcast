import math
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

# --- Elo constants (match backtest.py / xgboost_model.py) ---
STARTING_RATING = 1500
K = 32
HOME_ADVANTAGE = 100
COLD_START = 200
FORM_WINDOW = 5

# --- Rolling DC constants ---
DC_WINDOW = 38
DC_HOME_ADV = 0.1
DC_MAX_GOALS = 8

RESULT_MAP = {"A": 0, "D": 1, "H": 2}
RESULT_INV = {0: "A", 1: "D", 2: "H"}

# Features fed into the per-fold XGBoost base model (identical to xgboost_model.py)
XGB_FEATURE_COLS = [
    "home_elo", "away_elo", "elo_diff", "home_expected",
    "home_form", "away_form",
    "home_goals_scored_avg", "home_goals_conceded_avg",
    "away_goals_scored_avg", "away_goals_conceded_avg",
    "form_diff", "league_encoded", "is_home_advantage",
]

# Features fed into the meta-learner
STACK_COLS = [
    "home_expected",
    "p_home_dc", "p_draw_dc", "p_away_dc",
    "p_home_xgb", "p_draw_xgb", "p_away_xgb",
    "elo_diff", "home_form", "away_form", "form_diff",
]


# ---------------------------------------------------------------------------
# Elo helpers
# ---------------------------------------------------------------------------

def _mov_multiplier(goal_diff: int) -> float:
    return min(2.0, 1 + math.log(1 + abs(goal_diff)) / math.log(10))


def _elo_expected(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


# ---------------------------------------------------------------------------
# Form helpers
# ---------------------------------------------------------------------------

def _form_stats(history: deque) -> tuple[float, float, float]:
    """(form [0-1], goals_scored_avg, goals_conceded_avg) from last N matches."""
    if not history:
        return 0.5, 1.5, 1.5
    pts, gs, gc = [], [], []
    for goals_scored, goals_conceded, outcome in history:
        gs.append(goals_scored)
        gc.append(goals_conceded)
        pts.append(3 if outcome == "W" else 1 if outcome == "D" else 0)
    return (sum(pts) / len(pts)) / 3, sum(gs) / len(gs), sum(gc) / len(gc)


# ---------------------------------------------------------------------------
# Rolling Dixon-Coles helpers
# ---------------------------------------------------------------------------

def _dc_attack(scored: deque) -> float:
    """log(mean goals scored). Higher = better attack. 0.0 when no data."""
    if not scored:
        return 0.0
    return float(np.log(max(np.mean(list(scored)), 0.01)))


def _dc_defence(conceded: deque) -> float:
    """−log(mean goals conceded). Higher = better defence. 0.0 when no data.

    With lambda = exp(attack_h − defence_a + home_adv):
      good away defence (high defence_a) ↓ expected home goals ✓
    """
    if not conceded:
        return 0.0
    return float(-np.log(max(np.mean(list(conceded)), 0.01)))


def _dc_probs(lam: float, mu: float) -> tuple[float, float, float]:
    """P(home), P(draw), P(away) via independent Poisson, no low-score correction."""
    lam = max(lam, 1e-10)
    mu = max(mu, 1e-10)
    k = np.arange(DC_MAX_GOALS + 1)
    home_pmf = np.array([math.exp(-lam) * lam**i / math.factorial(i) for i in k])
    away_pmf = np.array([math.exp(-mu) * mu**i / math.factorial(i) for i in k])
    score = np.outer(home_pmf, away_pmf)          # [i,j] = P(home=i, away=j)
    i_idx, j_idx = np.meshgrid(k, k, indexing="ij")
    return (
        float(score[i_idx > j_idx].sum()),
        float(score[i_idx == j_idx].sum()),
        float(score[i_idx < j_idx].sum()),
    )


# ---------------------------------------------------------------------------
# Walk-forward feature builder (single pass, no future leakage)
# ---------------------------------------------------------------------------

def build_all_features(df: pd.DataFrame) -> pd.DataFrame:
    le = LabelEncoder()
    le.fit(df["league"])

    elo: dict[str, float] = defaultdict(lambda: float(STARTING_RATING))
    form: dict[str, deque] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    dc_scored: dict[str, deque] = defaultdict(lambda: deque(maxlen=DC_WINDOW))
    dc_conceded: dict[str, deque] = defaultdict(lambda: deque(maxlen=DC_WINDOW))

    records = []

    for row in df.itertuples(index=False):
        home, away = row.home_team, row.away_team
        home_goals, away_goals = int(row.home_goals), int(row.away_goals)
        result = row.result

        # Elo snapshot (pre-match)
        home_r = elo[home]
        away_r = elo[away]
        home_exp = _elo_expected(home_r + HOME_ADVANTAGE, away_r)

        # Form snapshot
        h_form, h_gs, h_gc = _form_stats(form[home])
        a_form, a_gs, a_gc = _form_stats(form[away])

        # Rolling DC snapshot
        atk_h = _dc_attack(dc_scored[home])
        def_h = _dc_defence(dc_conceded[home])
        atk_a = _dc_attack(dc_scored[away])
        def_a = _dc_defence(dc_conceded[away])

        lam = math.exp(atk_h - def_a + DC_HOME_ADV)
        mu = math.exp(atk_a - def_h)
        p_home_dc, p_draw_dc, p_away_dc = _dc_probs(lam, mu)

        records.append({
            "match_date": row.match_date,
            "league": row.league,
            "home_team": home,
            "away_team": away,
            # Elo
            "home_elo": home_r,
            "away_elo": away_r,
            "elo_diff": home_r - away_r,
            "home_expected": home_exp,
            # Form
            "home_form": h_form,
            "away_form": a_form,
            "home_goals_scored_avg": h_gs,
            "home_goals_conceded_avg": h_gc,
            "away_goals_scored_avg": a_gs,
            "away_goals_conceded_avg": a_gc,
            "form_diff": h_form - a_form,
            # Context
            "league_encoded": int(le.transform([row.league])[0]),
            "is_home_advantage": 1,
            # Rolling DC
            "p_home_dc": p_home_dc,
            "p_draw_dc": p_draw_dc,
            "p_away_dc": p_away_dc,
            "result": result,
        })

        # --- State updates (must happen AFTER recording pre-match features) ---
        if result == "H":
            home_score, away_score = 1.0, 0.0
        elif result == "D":
            home_score, away_score = 0.5, 0.5
        else:
            home_score, away_score = 0.0, 1.0

        away_exp = 1 - home_exp
        mov = _mov_multiplier(home_goals - away_goals)
        elo[home] = home_r + K * mov * (home_score - home_exp)
        elo[away] = away_r + K * mov * (away_score - away_exp)

        home_out = "W" if result == "H" else "D" if result == "D" else "L"
        away_out = "W" if result == "A" else "D" if result == "D" else "L"
        form[home].append((home_goals, away_goals, home_out))
        form[away].append((away_goals, home_goals, away_out))

        dc_scored[home].append(home_goals)
        dc_conceded[home].append(away_goals)
        dc_scored[away].append(away_goals)
        dc_conceded[away].append(home_goals)

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# XGBoost factory (identical hyperparams to xgboost_model.py)
# ---------------------------------------------------------------------------

def _make_xgb() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )


# ---------------------------------------------------------------------------
# Out-of-fold XGBoost predictions (TimeSeriesSplit, 5 folds)
# ---------------------------------------------------------------------------

def generate_oof_xgb(X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> np.ndarray:
    """Returns (n_train, 3) OOF probability matrix. Unfilled rows default to 1/3."""
    oof = np.full((len(X), 3), 1.0 / 3)
    tss = TimeSeriesSplit(n_splits=n_splits)
    for fold, (tr_idx, val_idx) in enumerate(tss.split(X)):
        print(f"  XGB fold {fold + 1}/{n_splits}  (train={len(tr_idx):,}, val={len(val_idx):,})")
        model = _make_xgb()
        model.fit(X[tr_idx], y[tr_idx])
        oof[val_idx] = model.predict_proba(X[val_idx])
    return oof


# ---------------------------------------------------------------------------
# Stacking feature matrix builder
# ---------------------------------------------------------------------------

def _build_stack(df: pd.DataFrame, xgb_proba: np.ndarray) -> np.ndarray:
    """Assemble the 11-column stacking feature matrix in STACK_COLS order.

    XGBoost class order: 0=A, 1=D, 2=H  →  proba cols are [P(A), P(D), P(H)].
    """
    return np.column_stack([
        df["home_expected"].values,
        df["p_home_dc"].values, df["p_draw_dc"].values, df["p_away_dc"].values,
        xgb_proba[:, 2], xgb_proba[:, 1], xgb_proba[:, 0],   # H, D, A
        df["elo_diff"].values,
        df["home_form"].values, df["away_form"].values, df["form_diff"].values,
    ])


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def _brier(p_home: np.ndarray, actual: pd.Series) -> float:
    ahs = actual.map({"H": 1.0, "D": 0.5, "A": 0.0}).values
    return float(((p_home - ahs) ** 2).mean())


def _hit_rate(pred: np.ndarray, actual: pd.Series) -> float:
    return float((pred == actual.values).mean())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base = os.path.dirname(__file__)
    results_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "results.csv"))

    df = pd.read_csv(results_path, parse_dates=["match_date"])
    df = df.sort_values("match_date").reset_index(drop=True)
    df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])

    print(f"Loaded {len(df):,} matches across {df['league'].nunique()} leagues")
    print("Building walk-forward features (Elo + form + rolling DC)...")

    feat_df = build_all_features(df)
    feat_df = feat_df.iloc[COLD_START:].reset_index(drop=True)
    feat_df["target"] = feat_df["result"].map(RESULT_MAP)

    n = len(feat_df)
    holdout_split = int(n * 0.80)

    train_df = feat_df.iloc[:holdout_split].reset_index(drop=True)
    holdout_df = feat_df.iloc[holdout_split:].copy().reset_index(drop=True)

    print(f"Train: {len(train_df):,}  |  Holdout: {len(holdout_df):,}\n")

    # ------------------------------------------------------------------
    # Step 1: OOF XGBoost on training set
    # ------------------------------------------------------------------
    X_train_xgb = train_df[XGB_FEATURE_COLS].values
    y_train = train_df["target"].values

    print("Generating OOF XGBoost predictions (5-fold TimeSeriesSplit)...")
    oof_proba = generate_oof_xgb(X_train_xgb, y_train)

    train_stack = _build_stack(train_df, oof_proba)

    # ------------------------------------------------------------------
    # Step 2: Full XGBoost trained on all of train_df (for holdout)
    # ------------------------------------------------------------------
    print("\nTraining full XGBoost on training set...")
    xgb_full = _make_xgb()
    xgb_full.fit(X_train_xgb, y_train)

    X_holdout_xgb = holdout_df[XGB_FEATURE_COLS].values
    holdout_xgb_proba = xgb_full.predict_proba(X_holdout_xgb)

    holdout_stack = _build_stack(holdout_df, holdout_xgb_proba)

    # ------------------------------------------------------------------
    # Step 3: Meta-learner (LogisticRegression, multinomial)
    # ------------------------------------------------------------------
    print("Training meta-learner (LogisticRegression, multinomial)...")
    meta = Pipeline([
        ("scaler", StandardScaler()),
        # multi_class='multinomial' removed in sklearn 1.5+; lbfgs solver uses
        # multinomial (softmax) loss by default for multiclass problems.
        ("lr", LogisticRegression(C=1.0, max_iter=1000, random_state=42)),
    ])
    meta.fit(train_stack, y_train)

    # ------------------------------------------------------------------
    # Step 4: Holdout predictions
    # ------------------------------------------------------------------
    y_holdout = holdout_df["target"].values
    meta_proba = meta.predict_proba(holdout_stack)   # cols: P(A), P(D), P(H)
    meta_pred = meta.predict(holdout_stack)

    holdout_df["p_away"] = meta_proba[:, 0]
    holdout_df["p_draw"] = meta_proba[:, 1]
    holdout_df["p_home"] = meta_proba[:, 2]
    holdout_df["predicted_result"] = [RESULT_INV[int(p)] for p in meta_pred]
    holdout_df["actual_result"] = holdout_df["result"]
    holdout_df["correct"] = (holdout_df["predicted_result"] == holdout_df["actual_result"]).astype(int)

    actual = holdout_df["actual_result"]

    ens_hit = holdout_df["correct"].mean()
    ens_brier = _brier(holdout_df["p_home"].values, actual)

    xgb_pred_str = np.array([RESULT_INV[int(p)] for p in xgb_full.predict(X_holdout_xgb)])
    xgb_hit = _hit_rate(xgb_pred_str, actual)
    xgb_brier = _brier(holdout_xgb_proba[:, 2], actual)

    elo_pred_str = np.where(holdout_df["home_expected"].values > 0.5, "H", "A")
    elo_hit = _hit_rate(elo_pred_str, actual)
    elo_brier = _brier(holdout_df["home_expected"].values, actual)

    dc_pred_idx = np.argmax(
        np.column_stack([holdout_df["p_away_dc"], holdout_df["p_draw_dc"], holdout_df["p_home_dc"]]),
        axis=1,
    )
    dc_pred_str = np.array([RESULT_INV[int(i)] for i in dc_pred_idx])
    dc_hit = _hit_rate(dc_pred_str, actual)
    dc_brier = _brier(holdout_df["p_home_dc"].values, actual)

    # ------------------------------------------------------------------
    # Step 5: Print results
    # ------------------------------------------------------------------
    lr = meta.named_steps["lr"]

    print("\n" + "=" * 60)
    print("META-LEARNER COEFFICIENTS (standardised feature space)")
    print("=" * 60)
    header = f"  {'Feature':<22}  {'Away':>8}  {'Draw':>8}  {'Home':>8}  {'|avg|':>7}"
    print(header)
    print("  " + "-" * 56)
    for i, feat in enumerate(STACK_COLS):
        row_coefs = lr.coef_[:, i]          # [coef_A, coef_D, coef_H]
        mean_abs = float(np.mean(np.abs(row_coefs)))
        print(f"  {feat:<22}  {row_coefs[0]:>8.4f}  {row_coefs[1]:>8.4f}  {row_coefs[2]:>8.4f}  {mean_abs:>7.4f}")

    best_single_hit = max(elo_hit, xgb_hit, dc_hit)
    best_single_brier = min(elo_brier, xgb_brier, dc_brier)

    print("\n" + "=" * 60)
    print("HOLDOUT EVALUATION")
    print("=" * 60)
    print(f"  Holdout matches : {len(holdout_df):,}")
    print(f"\n  {'Model':<12}  {'Hit Rate':>10}  {'Brier':>10}")
    print(f"  {'-' * 36}")
    print(f"  {'Ensemble':<12}  {ens_hit:>10.4f}  {ens_brier:>10.6f}")
    print(f"  {'XGBoost':<12}  {xgb_hit:>10.4f}  {xgb_brier:>10.6f}")
    print(f"  {'Elo':<12}  {elo_hit:>10.4f}  {elo_brier:>10.6f}")
    print(f"  {'Dixon-Coles':<12}  {dc_hit:>10.4f}  {dc_brier:>10.6f}")

    hit_delta = ens_hit - best_single_hit
    brier_delta = ens_brier - best_single_brier
    print(f"\n  Improvement over best single model:")
    print(f"    Hit rate : {hit_delta:+.4f}  ({'better' if hit_delta >= 0 else 'worse'})")
    print(f"    Brier    : {brier_delta:+.6f}  ({'better' if brier_delta <= 0 else 'worse'})")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 6: Save holdout predictions
    # ------------------------------------------------------------------
    out_cols = [
        "match_date", "league", "home_team", "away_team",
        "p_home", "p_draw", "p_away",
        "predicted_result", "actual_result", "correct",
    ]
    out_path = os.path.normpath(os.path.join(base, "..", "data", "processed", "ensemble_predictions.csv"))
    holdout_df[out_cols].to_csv(out_path, index=False)
    print(f"\nSaved predictions to {out_path}")


if __name__ == "__main__":
    main()
