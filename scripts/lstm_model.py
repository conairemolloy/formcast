"""
LSTM for football match outcome prediction using per-team temporal form sequences.
For each match: last 5 matches of home team + last 5 matches of away team.
8 features per team per match × 2 teams = 16 features per timestep.
"""
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_PATH       = "data/processed/full_features.csv"
XG_RESULTS_PATH = "data/processed/results_with_xg.csv"
NN_PRED_PATH    = "data/processed/nn_predictions.csv"
OUT_PATH        = "data/processed/lstm_predictions.csv"
MODEL_PATH      = "models/lstm_nn.pt"
XG_START        = "2014-08-01"

SEQ_LEN       = 5
FEAT_PER_TEAM = 8
FEAT_TOTAL    = FEAT_PER_TEAM * 2  # 16 per timestep

BATCH_SIZE    = 256
MAX_EPOCHS    = 100
PATIENCE      = 10
VAL_FRAC      = 0.10
LR            = 1e-3
WEIGHT_DECAY  = 1e-4

LABEL_MAP     = {"A": 0, "D": 1, "H": 2}
IDX_TO_RESULT = {0: "A", 1: "D", 2: "H"}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class MatchLSTM(nn.Module):
    def __init__(self, input_size: int = FEAT_TOTAL, hidden: int = 128, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden,
            num_layers=num_layers,
            dropout=0.2,
            batch_first=True,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden, 64),
            nn.ReLU(),
            nn.Linear(64, 3),
        )

    def forward(self, x):
        # x: (batch, seq_len, input_size)
        _, (h_n, _) = self.lstm(x)
        return self.head(h_n[-1])  # last layer's final hidden state: (batch, hidden)

    def predict_proba(self, x):
        return torch.softmax(self.forward(x), dim=1)


def print_architecture(model: nn.Module):
    print("=" * 60)
    print("Architecture  (LSTM)")
    print("=" * 60)
    for line in [
        "  Input(batch, 5, 16)",
        "    home team: 8 features/match × last 5 matches",
        "    away team: 8 features/match × last 5 matches",
        "    concatenated per timestep → 16 features",
        "  LSTM(input=16, hidden=128, layers=2, dropout=0.2)",
        "  Last hidden state → Dense(64, ReLU) → Dense(3, logits)",
        "  Softmax [inference only]",
    ]:
        print(line)
    total     = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n  Total params: {total:,}  |  Trainable: {trainable:,}")
    print(f"  Device: {device}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Per-match 8-feature vector from one team's perspective
# ---------------------------------------------------------------------------
_HOME_ENC = {"H": 1.0, "D": 0.5, "A": 0.0}
_AWAY_ENC = {"A": 1.0, "D": 0.5, "H": 0.0}


def team_match_vec(
    goals_scored: float,
    goals_conceded: float,
    xg_scored: float,
    xg_conceded: float,
    result: str,     # match result H/D/A (H = home team won)
    was_home: bool,
    elo: float,
    days_rest: float,
) -> np.ndarray:
    result_enc = _HOME_ENC[result] if was_home else _AWAY_ENC[result]
    return np.array([
        min(goals_scored   / 5.0, 1.0),
        min(goals_conceded / 5.0, 1.0),
        min(xg_scored      / 3.0, 1.0),
        min(xg_conceded    / 3.0, 1.0),
        result_enc,
        1.0 if was_home else 0.0,
        (elo - 1500.0) / 200.0,
        min(days_rest / 14.0, 1.0),
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Walk-forward sequence builder
# ---------------------------------------------------------------------------
def build_sequences(df: pd.DataFrame):
    """
    Processes all matches chronologically, collecting (sequence, label) pairs
    for matches >= XG_START.  Team histories are updated AFTER each sequence
    is extracted — no future data leakage.

    Returns
    -------
    sequences : np.ndarray  (N, SEQ_LEN, FEAT_TOTAL)
    labels    : np.ndarray  (N,)  int64
    meta      : list of dicts  {match_date, league, home_team, away_team}
    """
    df = df.sort_values("match_date").reset_index(drop=True)
    xg_cutoff = pd.Timestamp(XG_START)

    # team_hist[team] = list of up to SEQ_LEN 8-feature vectors (oldest first)
    team_hist: dict[str, list[np.ndarray]] = {}
    sequences, labels, meta_out = [], [], []
    total = len(df)

    for idx in range(total):
        row    = df.iloc[idx]
        home   = row["home_team"]
        away   = row["away_team"]
        result = row["result"]
        date   = row["match_date"]

        # ── Build sequences from history (before this match) ─────────────────
        def get_seq(team: str) -> np.ndarray:
            hist = team_hist.get(team, [])
            seq  = np.zeros((SEQ_LEN, FEAT_PER_TEAM), dtype=np.float32)
            n    = min(len(hist), SEQ_LEN)
            if n:
                seq[SEQ_LEN - n:] = np.array(hist[-n:])  # pad left with zeros
            return seq

        combined = np.concatenate([get_seq(home), get_seq(away)], axis=1)  # (5, 16)

        if date >= xg_cutoff:
            sequences.append(combined)
            labels.append(LABEL_MAP[result])
            meta_out.append({
                "match_date": date,
                "league":    row["league"],
                "home_team": home,
                "away_team": away,
            })

        # ── Update team histories AFTER extracting sequences ──────────────────
        hg = float(row["home_goals"])
        ag = float(row["away_goals"])
        hx = float(row["home_xg"])
        ax = float(row["away_xg"])

        for team, is_home, gs, gc, xs, xc, elo, rest in [
            (home, True,  hg, ag, hx, ax, row["home_elo"], row["home_days_rest"]),
            (away, False, ag, hg, ax, hx, row["away_elo"], row["away_days_rest"]),
        ]:
            vec = team_match_vec(gs, gc, xs, xc, result, is_home, float(elo), float(rest))
            lst = team_hist.setdefault(team, [])
            lst.append(vec)
            if len(lst) > SEQ_LEN:
                team_hist[team] = lst[-SEQ_LEN:]  # keep most recent SEQ_LEN only

        if (idx + 1) % 2000 == 0:
            print(f"  Processed {idx+1:,}/{total:,} matches  |  xG-era samples: {len(sequences):,}")

    return (
        np.array(sequences, dtype=np.float32),
        np.array(labels,    dtype=np.int64),
        meta_out,
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def brier_mc(y: np.ndarray, p: np.ndarray) -> float:
    oh = np.eye(p.shape[1])[y]
    return float(np.mean(np.sum((p - oh) ** 2, axis=1)))


def hit_rate(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.argmax(p, axis=1) == y))


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train_model(model: nn.Module, train_loader: DataLoader, val_loader: DataLoader):
    criterion = nn.CrossEntropyLoss()
    optim     = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    best_val   = float("inf")
    best_ep    = 0
    no_imp     = 0
    best_state = None

    for ep in range(1, MAX_EPOCHS + 1):
        model.train()
        t_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optim.step()
            t_loss += loss.item() * len(xb)
        t_loss /= len(train_loader.dataset)

        model.eval()
        v_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                v_loss += criterion(model(xb), yb).item() * len(xb)
        v_loss /= len(val_loader.dataset)

        if ep % 10 == 0:
            print(f"  Epoch {ep:3d}  train={t_loss:.4f}  val={v_loss:.4f}")

        if v_loss < best_val:
            best_val   = v_loss
            best_ep    = ep
            no_imp     = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            no_imp += 1
            if no_imp >= PATIENCE:
                print(f"  Early stopping at epoch {ep}")
                break

    model.load_state_dict(best_state)
    return best_ep, best_val


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # ── Load & merge ─────────────────────────────────────────────────────────
    ff = pd.read_csv(DATA_PATH)
    ff["match_date"] = pd.to_datetime(ff["match_date"])

    xg = pd.read_csv(XG_RESULTS_PATH)
    xg = xg.drop_duplicates(subset=["match_date", "home_team", "away_team"])
    xg["match_date"] = pd.to_datetime(xg["match_date"])

    df = ff.merge(
        xg[["match_date", "home_team", "away_team", "home_goals", "away_goals", "home_xg", "away_xg"]],
        on=["match_date", "home_team", "away_team"],
        how="left",
    )
    # Fallback to rolling averages where actual xG is missing (pre-2014 era)
    df["home_xg"] = df["home_xg"].fillna(df["home_xg_avg"])
    df["away_xg"] = df["away_xg"].fillna(df["away_xg_avg"])

    n_xg = (df["match_date"] >= XG_START).sum()
    print(f"Loaded {len(df):,} total matches  |  xG-era (>={XG_START}): {n_xg:,}")

    # ── Build sequences (walk-forward, all history used for context) ──────────
    print("\nBuilding team sequences (walk-forward)...")
    seqs, labels, meta = build_sequences(df)
    print(f"  Done.  Sequences: {seqs.shape}  Labels: {labels.shape}")

    # ── Walk-forward 70/30 split ──────────────────────────────────────────────
    N     = len(seqs)
    split = int(N * 0.70)

    X_full, X_test = seqs[:split], seqs[split:]
    y_full, y_test = labels[:split], labels[split:]
    meta_test      = meta[split:]

    val_cut = int(len(X_full) * (1 - VAL_FRAC))
    X_train, X_val = X_full[:val_cut], X_full[val_cut:]
    y_train, y_val = y_full[:val_cut], y_full[val_cut:]

    print(f"\n  Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}")

    # ── StandardScaler on flattened sequences (fit on train only) ─────────────
    def flat(X):   return X.reshape(len(X), SEQ_LEN * FEAT_TOTAL)
    def unflat(X): return X.reshape(-1, SEQ_LEN, FEAT_TOTAL)

    scaler    = StandardScaler()
    X_train_s = unflat(scaler.fit_transform(flat(X_train)).astype(np.float32))
    X_val_s   = unflat(scaler.transform(flat(X_val)).astype(np.float32))
    X_test_s  = unflat(scaler.transform(flat(X_test)).astype(np.float32))

    # ── DataLoaders ───────────────────────────────────────────────────────────
    def make_loader(X: np.ndarray, y: np.ndarray, shuffle: bool = False) -> DataLoader:
        ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
        return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle)

    train_loader = make_loader(X_train_s, y_train, shuffle=True)
    val_loader   = make_loader(X_val_s,   y_val)
    test_loader  = make_loader(X_test_s,  y_test)

    # ── Model ─────────────────────────────────────────────────────────────────
    model = MatchLSTM().to(device)
    print_architecture(model)

    # ── Train ─────────────────────────────────────────────────────────────────
    print("\nTraining...")
    best_ep, best_val_loss = train_model(model, train_loader, val_loader)
    print(f"\nBest validation loss: {best_val_loss:.4f} at epoch {best_ep}")

    # ── Test-set evaluation ───────────────────────────────────────────────────
    model.eval()
    probs_all = []
    with torch.no_grad():
        for xb, _ in test_loader:
            probs_all.append(model.predict_proba(xb.to(device)).cpu().numpy())
    lstm_p = np.vstack(probs_all)

    lstm_hit   = hit_rate(y_test, lstm_p)
    lstm_brier = brier_mc(y_test, lstm_p)

    print("\n" + "=" * 60)
    print("Test-set results")
    print("=" * 60)
    print(f"  LSTM            — hit rate: {lstm_hit:.4f}  Brier: {lstm_brier:.4f}")

    # ── Feedforward NN comparison ──────────────────────────────────────────────
    try:
        nn_df = pd.read_csv(NN_PRED_PATH)
        nn_df["match_date"] = pd.to_datetime(nn_df["match_date"])
        tmeta = pd.DataFrame(meta_test)
        tmeta["match_date"] = pd.to_datetime(tmeta["match_date"])
        ov = tmeta.merge(
            nn_df[["match_date", "home_team", "p_home", "p_draw", "p_away", "actual_result"]],
            on=["match_date", "home_team"],
            how="inner",
        )
        if len(ov):
            nn_p = ov[["p_away", "p_draw", "p_home"]].values.astype(np.float32)
            nn_y = np.array([LABEL_MAP[r] for r in ov["actual_result"]])
            print(f"  Feedforward NN  — hit rate: {hit_rate(nn_y, nn_p):.4f}  "
                  f"Brier: {brier_mc(nn_y, nn_p):.4f}  ({len(ov):,} matched)")
        else:
            print("  Feedforward NN  — no overlapping rows found")
    except FileNotFoundError:
        print(f"  Feedforward NN  — {NN_PRED_PATH} not found, skipping")

    # ── Elo baseline ───────────────────────────────────────────────────────────
    # Align with sequence order: sort full df by date (same as build_sequences),
    # filter to xG era, then take test slice.
    df_xg_sorted = (
        df.sort_values("match_date")
        .reset_index(drop=True)
        .loc[lambda d: d["match_date"] >= XG_START]
        .reset_index(drop=True)
    )
    elo_ph = df_xg_sorted.iloc[split:]["home_expected"].values
    elo_pa = np.clip(1.0 - elo_ph - 0.25, 0.0, None)
    elo_pd = np.clip(1.0 - elo_ph - elo_pa, 0.0, None)
    norm   = elo_ph + elo_pd + elo_pa
    elo_p  = np.column_stack([elo_pa / norm, elo_pd / norm, elo_ph / norm])
    print(f"  Elo baseline    — hit rate: {hit_rate(y_test, elo_p):.4f}  "
          f"Brier: {brier_mc(y_test, elo_p):.4f}")
    print("=" * 60)

    # ── Save predictions ───────────────────────────────────────────────────────
    pred_lbl = np.argmax(lstm_p, axis=1)
    out_df   = pd.DataFrame(meta_test)
    out_df["p_home"]           = lstm_p[:, 2]
    out_df["p_draw"]           = lstm_p[:, 1]
    out_df["p_away"]           = lstm_p[:, 0]
    out_df["predicted_result"] = [IDX_TO_RESULT[i] for i in pred_lbl]
    out_df["actual_result"]    = [IDX_TO_RESULT[i] for i in y_test]
    out_df["correct"]          = (pred_lbl == y_test).astype(int)

    os.makedirs(os.path.dirname(OUT_PATH),   exist_ok=True)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nPredictions saved → {OUT_PATH}")

    torch.save({
        "model_state_dict": model.state_dict(),
        "scaler":           scaler,
        "seq_len":          SEQ_LEN,
        "feat_total":       FEAT_TOTAL,
    }, MODEL_PATH)
    print(f"Model saved       → {MODEL_PATH}")


if __name__ == "__main__":
    main()
