"""Pilot: a LEARNED snapshot classifier (B4-style) instead of the exact snapshot rule.

XGBoost maps the current traffic features (Phase 2 features, lags excluded so the model
is a pure snapshot model) to the snapshot-optimal library index. Trained on train,
early-stopped on val. Safety layer: an infeasible prediction is replaced by the cheapest
feasible config. B6 hysteresis is then applied on top of the learned predictions
(delta tuned on val). Compared with the exact snapshot rule and the oracle.

Usage: python scripts/pilot_learned_b4.py abilene --K 32
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

from lira import DATA_PROC, RESULTS, TAG
from lira.baselines import classical as B
from lira.oracle.dp import snapshot, viterbi
from lira.oracle.make_labels import PER_DAY, load, tables_for
from pilot_experiment import metrics, segment_run


def safe(tab, pred, lw):
    node = tab.node(lw)
    bad = ~np.isfinite(node[np.arange(len(pred)), pred])
    out = pred.copy()
    out[bad] = np.argmin(node[bad], axis=1)
    return out, float(bad.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topology")
    ap.add_argument("--K", type=int, default=32)
    ap.add_argument("--lamR", type=float, default=1.0)
    ap.add_argument("--lamW", type=float, default=1.0)
    a = ap.parse_args()
    lr, lw = a.lamR, a.lamW
    topo, od, seg, split, meta, lib = load(a.topology, a.K)
    tab_all, _, _, _ = tables_for(a.topology, a.K)
    X = np.stack([c.x for c in lib["library"]])
    per_day = PER_DAY[meta["freq"]]
    f = np.load(DATA_PROC / a.topology / "features.npz")
    names = list(f["names"])
    keep = [i for i, n in enumerate(names) if not n.startswith("d")]  # no lag deltas
    F = f["X"][:, keep]
    y_all = snapshot(tab_all, lw)
    tr, va, te = (np.array(split[k]) for k in ("train", "val", "test"))
    classes = np.unique(y_all[tr])
    enc = {c: i for i, c in enumerate(classes)}
    ytr = np.array([enc[c] for c in y_all[tr]])
    mva = np.isin(y_all[va], classes)
    yva = np.array([enc[c] for c in y_all[va][mva]])
    t0 = time.perf_counter()
    if len(classes) == 1:
        predict = lambda Z: np.full(len(Z), classes[0])
    else:
        clf = XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.1, subsample=0.8,
                            colsample_bytree=0.8, tree_method="hist", n_jobs=8,
                            early_stopping_rounds=30,
                            eval_metric="mlogloss" if len(classes) > 2 else "logloss", random_state=0)
        clf.fit(F[tr], ytr, eval_set=[(F[va][mva], yva)], verbose=False)
        predict = lambda Z: classes[clf.predict(Z)]
    train_s = time.perf_counter() - t0

    def run(idx):
        tab = tab_all.slice(idx[0], idx[-1] + 1)
        pred, fb = safe(tab, predict(F[idx]).astype(np.int32), lw)
        return tab, pred, fb

    tv, pv, _ = run(va)
    deltas = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1]
    best_d = min(deltas, key=lambda d: tv.sequence_cost(B.hysteresis(tv, pv, d, lw), lr, lw))
    tab, pred, fb = run(te)
    snap = snapshot(tab, lw)
    node, edge = tab.node(lw), tab.edge(lr, lw)
    oracle = segment_run(lambda m: viterbi(node[m], edge)[0], seg[te])
    rows = [metrics(tab, snap, X, per_day, lr, lw, "SNAP exact rule"),
            metrics(tab, pred, X, per_day, lr, lw, "B4 learned (XGBoost)+safety"),
            metrics(tab, B.hysteresis(tab, pred, best_d, lw), X, per_day, lr, lw,
                    f"B6 = B4 + hysteresis (delta={best_d})"),
            metrics(tab, oracle, X, per_day, lr, lw, "O* offline oracle")]
    df = pd.DataFrame(rows)
    b4 = df.iloc[1]
    df["retention_vs_B4_pct"] = 100 * df.savings_pct / b4.savings_pct
    df["change_reduction_vs_B4_pct"] = 100 * (1 - df.config_changes_per_day / max(b4.config_changes_per_day, 1e-12))
    df["J_regret_vs_oracle_pct"] = 100 * (df.total_cost_J / df.total_cost_J.iloc[-1] - 1)
    out = RESULTS / "pilot"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"pilot_b4_{a.topology}{TAG}_K{a.K}_R{lr}_W{lw}.csv", index=False)
    acc = accuracy_score(snap, pred)
    print(f"{a.topology}{TAG} test: {len(te) / per_day:.1f} days, classes in train={len(classes)}, "
          f"B4 accuracy={acc:.3f}, macro-F1={f1_score(snap, pred, average='macro'):.3f}, "
          f"safety fallbacks={100 * fb:.2f}%, train {train_s:.0f}s")
    pd.set_option("display.width", 250)
    print(df.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
