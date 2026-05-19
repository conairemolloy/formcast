"""
Feedforward neural network for football match outcome prediction.
Uses 48-feature matrix from full_features.csv, xG era (2014+).
"""
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_PATH   = "data/processed/full_features.csv"
XGB_PATH    = "data/processed/full_xgb_predictions.csv"
OUT_PATH    = "data/processed/nn_predictions.csv"
MODEL_PATH  = "models/feedforward_nn.pt"
XG_START    = "2014-08-01"

FEATURE_COLS = [
    "home_elo", "away_elo", "elo_diff", "home_expected",
    "home_g2_rating", "away_g2_rating", "g2_diff", "home_g2_uncertainty",
    "home_form", "away_form", "form_diff",
    "home_goals_scored_avg", "home_goals_conceded_avg",
    "away_goals_scored_avg", "away_goals_conceded_avg",
    "home_xg_avg", "away_xg_avg",
    "home_xg_conceded_avg", "away_xg_conceded_avg",
    "home_xg_diff_avg", "away_xg_diff_avg",
    "home_result_momentum", "away_result_momentum",
    "home_score_momentum", "away_score_momentum",
    "home_elo_momentum", "away_elo_momentum",
    "home_streak", "away_streak",
    "momentum_diff",
    "home_days_rest", "away_days_rest",
    "home_matches_21d", "away_matches_21d",
    "rest_asymmetry",
    "home_fatigue_score", "away_fatigue_score",
    "h2h_home_win_rate", "h2h_goal_diff_avg",
    "h2h_meetings", "h2h_dominance",
    "revenge_factor",
    "home_unbeaten_run", "away_unbeaten_run",
    "post_loss_bounce", "post_loss_bounce_away",
    "league_encoded", "is_early_season",
]  # 48 features

LABEL_MAP = {"A": 0, "D": 1, "H": 2}
IDX_TO_RESULT = {0: "A", 1: "D", 2: "H"}

BATCH_SIZE  = 256
MAX_EPOCHS  = 100
PATIENCE    = 10
VAL_FRAC    = 0.10
LR          = 1e-3
WEIGHT_DECAY = 1e-4

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class MatchNet(nn.Module):
    def __init__(self, n_in: int = 48):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 3),
        )

    def forward(self, x):
        return self.net(x)  # logits; apply softmax externally for probabilities

    def predict_proba(self, x):
        return torch.softmax(self.forward(x), dim=1)


def print_architecture(model: nn.Module, n_in: int):
    print("=" * 55)
    print("Architecture")
    print("=" * 55)
    layers = [
        f"  Input({n_in})",
        "  Dense(256, ReLU) → BatchNorm → Dropout(0.3)",
        "  Dense(128, ReLU) → BatchNorm → Dropout(0.2)",
        "  Dense(64,  ReLU)",
        "  Dense(3,   logits) → Softmax [inference only]",
    ]
    for l in layers:
        print(l)
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n  Total params: {total:,}  |  Trainable: {trainable:,}")
    print(f"  Device: {device}")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def brier_multiclass(y_true_int: np.ndarray, probs: np.ndarray) -> float:
    n_classes = probs.shape[1]
    y_onehot = np.eye(n_classes)[y_true_int]
    return float(np.mean(np.sum((probs - y_onehot) ** 2, axis=1)))


def hit_rate(y_true_int: np.ndarray, probs: np.ndarray) -> float:
    preds = np.argmax(probs, axis=1)
    return float(np.mean(preds == y_true_int))


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train(model, train_loader, val_loader):
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    best_val_loss = float("inf")
    best_epoch    = 0
    no_improve    = 0
    best_state    = None

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= len(train_loader.dataset)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                out = model(xb)
                val_loss += criterion(out, yb).item() * len(xb)
        val_loss /= len(val_loader.dataset)

        if epoch % 10 == 0:
            print(f"  Epoch {epoch:3d}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch    = epoch
            no_improve    = 0
            best_state    = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            no_improve += 1
            if no_improve >= PATIENCE:
                print(f"  Early stopping at epoch {epoch} (no improvement for {PATIENCE} epochs)")
                break

    model.load_state_dict(best_state)
    return best_epoch, best_val_loss


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # ── Load & filter ────────────────────────────────────────────────────────
    df = pd.read_csv(DATA_PATH)
    df["match_date"] = pd.to_datetime(df["match_date"])
    df = df[df["match_date"] >= XG_START].reset_index(drop=True)
    print(f"Loaded {len(df):,} matches from {XG_START} onwards")

    df["label"] = df["result"].map(LABEL_MAP)
    assert df["label"].notna().all(), "Unexpected result values"

    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df["label"].values.astype(np.int64)

    # ── Walk-forward split (70 / 30) ─────────────────────────────────────────
    split = int(len(df) * 0.70)
    X_train_full, X_test = X[:split], X[split:]
    y_train_full, y_test = y[:split], y[split:]

    # 10 % of train → validation
    val_split = int(len(X_train_full) * (1.0 - VAL_FRAC))
    X_train, X_val = X_train_full[:val_split], X_train_full[val_split:]
    y_train, y_val = y_train_full[:val_split], y_train_full[val_split:]

    print(f"  Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}")

    # ── Normalise ─────────────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val   = scaler.transform(X_val).astype(np.float32)
    X_test  = scaler.transform(X_test).astype(np.float32)

    # ── DataLoaders ───────────────────────────────────────────────────────────
    def make_loader(X, y, shuffle=False):
        ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
        return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle)

    train_loader = make_loader(X_train, y_train, shuffle=True)
    val_loader   = make_loader(X_val, y_val)
    test_loader  = make_loader(X_test, y_test)

    # ── Build & display model ─────────────────────────────────────────────────
    model = MatchNet(n_in=len(FEATURE_COLS)).to(device)
    print_architecture(model, len(FEATURE_COLS))

    # ── Train ─────────────────────────────────────────────────────────────────
    print("\nTraining...")
    best_epoch, best_val_loss = train(model, train_loader, val_loader)
    print(f"\nBest validation loss: {best_val_loss:.4f} at epoch {best_epoch}")

    # ── Evaluate on test set ──────────────────────────────────────────────────
    model.eval()
    all_probs = []
    with torch.no_grad():
        for xb, _ in test_loader:
            all_probs.append(model.predict_proba(xb.to(device)).cpu().numpy())
    nn_probs = np.vstack(all_probs)

    nn_hit   = hit_rate(y_test, nn_probs)
    nn_brier = brier_multiclass(y_test, nn_probs)

    print("\n" + "=" * 55)
    print("Test-set results")
    print("=" * 55)
    print(f"  Neural Network  — hit rate: {nn_hit:.4f}  Brier: {nn_brier:.4f}")

    # ── Elo baseline (home_expected column) ──────────────────────────────────
    test_df = df.iloc[split:].reset_index(drop=True)
    elo_p_home = test_df["home_expected"].values
    elo_p_away = np.clip(1.0 - elo_p_home - 0.25, 0.0, None)
    elo_p_draw = np.clip(1.0 - elo_p_home - elo_p_away, 0.0, None)
    norm = elo_p_home + elo_p_draw + elo_p_away
    elo_probs = np.column_stack([elo_p_away, elo_p_draw, elo_p_home / norm])  # 0=A,1=D,2=H

    elo_hit   = hit_rate(y_test, elo_probs)
    elo_brier = brier_multiclass(y_test, elo_probs)
    print(f"  Elo baseline    — hit rate: {elo_hit:.4f}  Brier: {elo_brier:.4f}")

    # ── XGBoost comparison ────────────────────────────────────────────────────
    try:
        xgb_df = pd.read_csv(XGB_PATH)
        xgb_df["match_date"] = pd.to_datetime(xgb_df["match_date"])
        test_dates  = test_df["match_date"]
        test_home   = test_df["home_team"]
        merged = test_df[["match_date", "home_team"]].copy()
        merged = merged.merge(
            xgb_df[["match_date", "home_team", "p_home", "p_draw", "p_away"]],
            on=["match_date", "home_team"], how="inner",
        )
        if len(merged) > 0:
            mask = test_df.set_index(["match_date", "home_team"]).index.isin(
                merged.set_index(["match_date", "home_team"]).index
            )
            xgb_probs = merged[["p_away", "p_draw", "p_home"]].values.astype(np.float32)
            y_test_xgb = y_test[mask]
            xgb_hit   = hit_rate(y_test_xgb, xgb_probs)
            xgb_brier = brier_multiclass(y_test_xgb, xgb_probs)
            print(f"  XGBoost         — hit rate: {xgb_hit:.4f}  Brier: {xgb_brier:.4f}  ({len(merged):,} matched rows)")
        else:
            print("  XGBoost         — no overlapping rows found")
    except FileNotFoundError:
        print(f"  XGBoost         — {XGB_PATH} not found, skipping")

    print("=" * 55)

    # ── Save predictions ──────────────────────────────────────────────────────
    pred_labels   = np.argmax(nn_probs, axis=1)
    actual_labels = y_test

    out_df = test_df[["match_date", "league", "home_team", "away_team"]].copy()
    out_df["p_home"]          = nn_probs[:, 2]
    out_df["p_draw"]          = nn_probs[:, 1]
    out_df["p_away"]          = nn_probs[:, 0]
    out_df["predicted_result"] = [IDX_TO_RESULT[i] for i in pred_labels]
    out_df["actual_result"]    = [IDX_TO_RESULT[i] for i in actual_labels]
    out_df["correct"]          = (pred_labels == actual_labels).astype(int)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nPredictions saved → {OUT_PATH}")

    # ── Save model ────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "scaler": scaler}, MODEL_PATH)
    print(f"Model saved       → {MODEL_PATH}")


if __name__ == "__main__":
    main()
