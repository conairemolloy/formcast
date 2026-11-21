"""
Stage 1 market-odds experiment (OFFLINE, read-only w.r.t. models/).

Question: do de-margined bookmaker odds, used as a feature, improve the
holdout PREDICTION ACCURACY of the ensemble_v2 stack?

  A. baseline    FEATURE_COLS, STACK_COLS unchanged (must reproduce holdout_metrics)
  B. stack-only  STACK_COLS + [mkt_p_home, mkt_p_draw, mkt_p_away, has_odds]
  C. both        FEATURE_COLS + market cols (NaN-tolerant, to XGBoost) AND stack + market cols

Reuse, not copy: every variant calls ensemble_v2.fit_stack_models (the real
OOF TimeSeriesSplit path). B/C are produced by temporarily rebinding the
module globals FEATURE_COLS / STACK_COLS / _build_stack that fit_stack_models
looks up at call time; they are restored after every run. Only the
data-loading / 2014 filter / COLD_START / 80-20 split lines are mirrored
from ensemble_v2.main(), because main() is not importable piecemeal.

Writes nothing under models/ or data/. The built feature frame is cached in
$EXP_CACHE_DIR (default: alongside nothing tracked) to speed reruns.

Usage: venv/bin/python scripts/exp_market_odds.py

RESULT (Nov 20 2026, holdout n=10,060, 2024-03-30 -> 2026-11-15):
  A baseline (current ensemble)   hit 0.4889  brier 0.6115
  B odds in stack                 hit 0.5065  brier 0.5985  (+1.76pp / -0.0130)
  C odds in XGBoost + stack        hit 0.5071  brier 0.5985  (+1.82pp / -0.0130)
  market odds ALONE (no model)    hit 0.5049  brier 0.5989  (+1.60pp / -0.0126)

VERDICT: REJECTED as a production feature. The +1.8pp lift is almost
entirely the bookmaker's own price, not our model: de-margined odds ALONE
already score 0.5049, so the 78-feature ensemble adds only ~0.2pp over the
market (noise). With odds in the stack the meta-learner cuts XGBoost's weight
~5x and defers to the market; in variant C XGBoost's top-2 features by gain
are the two odds columns. A model that copies the bookmaker is not a real
improvement and, by construction, can't find value against the market it
copies. The real lesson: the market beats our model by ~1.6pp = the signal
the bookmaker prices and we don't. The genuine "beat Elo" path is finding
signal the MARKET doesn't price (injuries, lineups, team news), not copying
the price. Kept as a reusable "does feature X help" harness.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ensemble_v2 as E  # noqa: E402

T0 = time.time()
BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(BASE, "..", "data", "processed", "results.csv"))
XG_PATH = os.path.normpath(os.path.join(BASE, "..", "data", "processed", "results_with_xg.csv"))
CACHE_DIR = os.environ.get("EXP_CACHE_DIR")

# Reference: ensemble row of models/holdout_metrics.json (CI run, Nov 20 2026,
# mirrored in ROADMAP.md). The JSON is not in this local checkout.
REF_HIT, REF_BRIER, REF_N = 0.4889, 0.6115, 10_060

MKT = ["mkt_p_home", "mkt_p_draw", "mkt_p_away", "has_odds"]
MKT_NAN = ["mkt_p_home_nan", "mkt_p_draw_nan", "mkt_p_away_nan", "has_odds"]
KEY = ["match_date", "home_team", "away_team"]


def banner(s):
    print("\n" + "=" * 72 + f"\n{s}\n" + "=" * 72)


# ---------------------------------------------------------------------------
# 1. Load + build features exactly as ensemble_v2.main() does
# ---------------------------------------------------------------------------
df = pd.read_csv(RESULTS, parse_dates=["match_date"], dtype={"referee": str})
df = df.sort_values("match_date").reset_index(drop=True)
df = df.dropna(subset=["home_team", "away_team", "home_goals", "away_goals", "result"])
print(f"Loaded {len(df):,} matches")

cache = os.path.join(CACHE_DIR, "feat_df.pkl") if CACHE_DIR else None
if cache and os.path.exists(cache):
    feat_df = pd.read_pickle(cache)
    print(f"Loaded cached feature frame ({len(feat_df):,} rows) from {cache}")
else:
    xg_lookup = {}
    if os.path.exists(XG_PATH):
        xg_df = pd.read_csv(XG_PATH, parse_dates=["match_date"])
        xg_df = xg_df.dropna(subset=["home_xg", "away_xg", "xg_diff"])
        for _, r in xg_df.iterrows():
            xg_lookup[(r["match_date"].date(), r["home_team"], r["away_team"], r["league"])] = (
                float(r["home_xg"]), float(r["away_xg"]), float(r["xg_diff"]))
    print(f"Loaded {len(xg_lookup):,} xG records")
    t = time.time()
    feat_df, _enc = E.build_all_features(df, xg_lookup)
    print(f"build_all_features: {time.time() - t:.0f}s")
    if cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        feat_df.to_pickle(cache)

# ---------------------------------------------------------------------------
# 2. Market features: de-margined B365 implied probs, joined on KEY
# ---------------------------------------------------------------------------
odds = df[KEY + ["home_odds", "draw_odds", "away_odds"]].copy()
oc = ["home_odds", "draw_odds", "away_odds"]
bad = (odds[oc] <= 1.0).any(axis=1)          # 0.0 / <=1.0 decimal odds are corrupt
odds.loc[bad, oc] = np.nan
valid = odds[oc].notna().all(axis=1)
imp = 1.0 / odds[oc]
overround = imp.sum(axis=1)
odds["overround"] = overround.where(valid)
for src, dst in zip(oc, ["mkt_p_home_nan", "mkt_p_draw_nan", "mkt_p_away_nan"]):
    odds[dst] = (imp[src] / overround).where(valid)
odds["has_odds"] = valid.astype(int)

# Duplicate keys (1993-96 LaLiga/Segunda double entries): must carry identical odds.
dups = odds[odds.duplicated(KEY, keep=False)]
dup_conflict = dups.groupby(KEY)[["mkt_p_home_nan", "has_odds"]].nunique(dropna=False).gt(1).any().any()
assert not dup_conflict, "duplicate keys carry conflicting odds — join ambiguous"
odds_lu = odds.drop_duplicates(KEY)[KEY + ["mkt_p_home_nan", "mkt_p_draw_nan",
                                           "mkt_p_away_nan", "has_odds", "overround"]]

n_before = len(feat_df)
feat_df = feat_df.merge(odds_lu, on=KEY, how="left", validate="many_to_one", indicator=True)
assert len(feat_df) == n_before, "join changed row count"
n_matched_all = int((feat_df["_merge"] == "both").sum())
feat_df = feat_df.drop(columns="_merge")

# ---------------------------------------------------------------------------
# 3. Filter + split exactly as ensemble_v2.main()
# ---------------------------------------------------------------------------
feat_df = feat_df[feat_df["match_date"] >= "2014-08-01"].reset_index(drop=True)
model_df = feat_df.iloc[E.COLD_START:].reset_index(drop=True)
model_df["target"] = model_df["result"].map(E.RESULT_MAP)
n = len(model_df)
split = int(n * 0.80)
train_df = model_df.iloc[:split].reset_index(drop=True)
holdout_df = model_df.iloc[split:].copy().reset_index(drop=True)

# Imputation (stack only — LogisticRegression can't take NaN): TRAIN-SPLIT base
# rate = mean de-margined prob over train rows that have odds. Causal: no
# holdout information. has_odds=0 lets the LR learn an offset for imputed rows.
base_rate = {c: float(train_df.loc[train_df["has_odds"] == 1, c + "_nan"].mean())
             for c in ["mkt_p_home", "mkt_p_draw", "mkt_p_away"]}
for d in (model_df, train_df, holdout_df):
    for c, v in base_rate.items():
        d[c] = d[c + "_nan"].fillna(v)

banner("DATA / JOIN CHECKS")
print(f"Feature rows (all eras)             : {n_before:,}")
print(f"Rows matched to results.csv on key  : {n_matched_all:,} / {n_before:,} "
      f"({'EXACT 1:1' if n_matched_all == n_before else 'INCOMPLETE'})")
print(f"Odds rows set to NaN (odds <= 1.0)  : {int(bad.sum())}")
print(f"Train   : {len(train_df):,}  ({train_df.match_date.min().date()} -> {train_df.match_date.max().date()})"
      f"  has_odds={train_df.has_odds.mean():.4%}")
print(f"Holdout : {len(holdout_df):,}  ({holdout_df.match_date.min().date()} -> {holdout_df.match_date.max().date()})"
      f"  has_odds={holdout_df.has_odds.mean():.4%}")
print(f"Pre-2003 no-odds rows are removed by the 2014-08-01 filter; missing in model_df: "
      f"{int((model_df.has_odds == 0).sum())}")
print(f"Imputation (stack): train-split base rate H/D/A = "
      f"{base_rate['mkt_p_home']:.4f}/{base_rate['mkt_p_draw']:.4f}/{base_rate['mkt_p_away']:.4f}; "
      f"XGBoost (variant C) gets raw NaN")
print(f"Mean overround (holdout)            : {holdout_df.overround.mean():.4f}")

# ---------------------------------------------------------------------------
# 4. Variant runner — patches module globals, calls the real fit_stack_models
# ---------------------------------------------------------------------------
_ORIG = (E.FEATURE_COLS, E.STACK_COLS, E._build_stack)


def _stack_with_market(df_, xgb_proba):
    # Original 12 base columns, then the 4 market cols (imputed). draw_prob is
    # appended afterwards by fit_stack_models / the holdout code, as in main().
    return np.column_stack([_ORIG[2](df_, xgb_proba), df_[MKT].values.astype(float)])


def run_variant(name, feature_cols, stack_with_mkt):
    stack_cols = (_ORIG[1][:-1] + MKT + ["draw_prob"]) if stack_with_mkt else list(_ORIG[1])
    E.FEATURE_COLS, E.STACK_COLS = list(feature_cols), stack_cols
    E._build_stack = _stack_with_market if stack_with_mkt else _ORIG[2]
    t = time.time()
    try:
        banner(f"VARIANT {name}  | XGB features={len(feature_cols)}  stack={len(stack_cols)}")
        m = E.fit_stack_models(train_df)            # real OOF path
        # Holdout prediction, mirroring ensemble_v2.main() step 3/4
        xp = m["xgb"].predict_proba(holdout_df[E.FEATURE_COLS].values)
        hs = E._build_stack(holdout_df, xp)
        dp = m["draw_clf"].predict_proba(holdout_df[E.DRAW_COLS].values)[:, 1]
        hs = np.column_stack([hs, dp])
        assert hs.shape[1] == len(E.STACK_COLS)
        proba = m["meta"].predict_proba(hs)
        pred = np.array([E.RESULT_INV[int(p)] for p in m["meta"].predict(hs)])
        actual = holdout_df["result"]
        out = {
            "variant": name,
            "hit": E._hit(pred, actual),
            "brier": E._brier_3outcome(proba, actual),
            "n": len(holdout_df),
            "secs": time.time() - t,
            "oof_stack_rows": m["oof_stack"].shape[0],
            "oof_stack_cols": m["oof_stack"].shape[1],
            "draw_pick_rate": float((pred == "D").mean()),
        }
        lr = m["meta"].named_steps["lr"]
        coefs = {c: lr.coef_[:, i] for i, c in enumerate(E.STACK_COLS)}
        out["mkt_coefs"] = {c: coefs[c] for c in MKT if c in coefs}
        out["xgb_coefs"] = {c: coefs[c] for c in ("p_home_xgb", "p_draw_xgb", "p_away_xgb")}
        if any(c.endswith("_nan") or c == "has_odds" for c in E.FEATURE_COLS):
            gain = m["xgb"].get_booster().get_score(importance_type="gain")
            ranked = sorted(((gain.get(f"f{i}", 0.0), c) for i, c in enumerate(E.FEATURE_COLS)), reverse=True)
            out["xgb_top"] = ranked[:8]
        print(f"\n{name}: hit={out['hit']:.4f}  brier={out['brier']:.4f}  n={out['n']:,}  ({out['secs']:.0f}s)")
        return out
    finally:
        E.FEATURE_COLS, E.STACK_COLS, E._build_stack = _ORIG


results = [
    run_variant("A baseline", _ORIG[0], stack_with_mkt=False),
]
a = results[0]
banner("CHECK: baseline reproduces holdout_metrics.json ensemble row")
ok = (round(a["hit"], 4) == REF_HIT and round(a["brier"], 4) == REF_BRIER and a["n"] == REF_N)
print(f"  got  hit={a['hit']:.4f} brier={a['brier']:.4f} n={a['n']:,}")
print(f"  ref  hit={REF_HIT:.4f} brier={REF_BRIER:.4f} n={REF_N:,}")
print(f"  -> {'MATCH' if ok else 'MISMATCH — harness is NOT faithful; stopping'}")
if not ok:
    sys.exit(1)

results.append(run_variant("B stack-only", _ORIG[0], stack_with_mkt=True))
results.append(run_variant("C both", _ORIG[0] + MKT_NAN, stack_with_mkt=True))

# Reference point (not a variant): the de-margined market on its own
mk = holdout_df[["mkt_p_away", "mkt_p_draw", "mkt_p_home"]].values
mk_pred = np.array(["A", "D", "H"])[mk.argmax(axis=1)]
mk_hit, mk_brier = E._hit(mk_pred, holdout_df["result"]), E._brier_3outcome(mk, holdout_df["result"])

# ---------------------------------------------------------------------------
# 5. Report
# ---------------------------------------------------------------------------
banner("LEAKAGE / SCOPE CHECKS")
print("1. SCOPE: holdout market probs come from the SAME B365 odds the value screen")
print("   uses. This experiment measures PREDICTION ACCURACY ONLY, NOT betting edge.")
print("   A model that leans on the market will look 'accurate' but cannot, by")
print("   construction, find value against that same market (Stage 2+ concern).")
for r in results:
    print(f"2. {r['variant']:<13}: meta-learner fit on fit_stack_models OOF stack "
          f"({r['oof_stack_rows']:,} rows x {r['oof_stack_cols']} cols; "
          f"rows == train {len(train_df):,}: {r['oof_stack_rows'] == len(train_df)})")
print("   XGB/draw probs in that stack are 5-fold TimeSeriesSplit OOF; market cols are")
print("   pre-kickoff row facts (like elo_diff), not fitted outputs, so no in-fold leak.")
print("3. Odds are pre-match B365 prices recorded per row (not closing); no outcome info.")
print(f"4. Baseline reproduction: {'MATCH' if ok else 'MISMATCH'} (see above)")
print(f"5. Module globals restored: {(E.FEATURE_COLS, E.STACK_COLS, E._build_stack) == _ORIG}")

banner("META-LEARNER COEFFICIENTS (standardised; columns A / D / H)")
for r in results:
    print(f"  {r['variant']}")
    for c, v in {**r["xgb_coefs"], **r["mkt_coefs"]}.items():
        print(f"    {c:<14} {v[0]:>8.3f} {v[1]:>8.3f} {v[2]:>8.3f}")
    if "xgb_top" in r:
        print("    XGB top-8 features by gain: " +
              ", ".join(f"{c} ({g:.1f})" for g, c in r["xgb_top"]))

banner(f"COMPARISON  (holdout n={len(holdout_df):,}, "
       f"{holdout_df.match_date.min().date()} -> {holdout_df.match_date.max().date()})")
print(f"  {'variant':<16}{'hit':>8}{'Brier':>9}{'d_hit':>9}{'d_Brier':>10}{'draw%':>8}{'secs':>7}")
for r in results:
    print(f"  {r['variant']:<16}{r['hit']:>8.4f}{r['brier']:>9.4f}"
          f"{r['hit'] - a['hit']:>+9.4f}{r['brier'] - a['brier']:>+10.4f}"
          f"{r['draw_pick_rate']:>8.1%}{r['secs']:>7.0f}")
print(f"  {'(market alone)':<16}{mk_hit:>8.4f}{mk_brier:>9.4f}"
      f"{mk_hit - a['hit']:>+9.4f}{mk_brier - a['brier']:>+10.4f}"
      f"{(mk_pred == 'D').mean():>8.1%}{'':>7}")
print("  (Brier: lower is better; d_Brier < 0 = improvement)")
print("  NOTE: accuracy only — not a betting-edge result.")
print(f"\nTotal wall time: {time.time() - T0:.0f}s")
