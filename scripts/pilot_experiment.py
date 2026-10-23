"""Pilot experiment (small, non-learning): does sequence awareness pay off on real traffic?

On the TEST split of one topology, compares over the K-config library:
  B0 always-on, SNAP (exact snapshot rule = what a perfect B4 classifier would output),
  B6 hysteresis and B7 min-dwell on SNAP (tuned on VAL), B2 rolling horizon (naive
  forecast, H=12), and the offline oracle O*.
No ML is involved, so SNAP is an upper bound on what B4 can save.

Usage: python scripts/pilot_experiment.py abilene --K 32 --lamR 1.0 --lamW 1.0
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json

import numpy as np
import pandas as pd

from lira import RESULTS, TAG
from lira.baselines import classical as B
from lira.oracle.dp import snapshot, viterbi
from lira.oracle.make_labels import PER_DAY, load, tables_for


def segment_run(fn, sg):
    """Run fn on each gap-free segment; sg = segment id per interval of the split."""
    out = np.empty(len(sg), dtype=np.int32)
    for s in np.unique(sg):
        m = np.flatnonzero(sg == s)
        out[m] = fn(m)
    return out


def metrics(tab, seq, X, per_day, lam_R, lam_W, name):
    t = np.arange(len(seq))
    E = tab.E[t, seq]
    days = len(seq) / per_day
    x = X[seq]
    return {"method": name,
            "savings_pct": 100 * (1 - E.sum() / tab.E[:, 0].sum()),
            "config_changes_per_day": float((seq[1:] != seq[:-1]).sum() / days),
            "link_transitions_per_day": float(np.abs(np.diff(x, axis=0)).sum() / days),
            "mlu_violation_pct": float(100 * (tab.mlu[t, seq] > 0.8 + 1e-9).mean()),
            "total_cost_J": tab.sequence_cost(seq, lam_R, lam_W)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topology")
    ap.add_argument("--K", type=int, default=32)
    ap.add_argument("--lamR", type=float, default=1.0)
    ap.add_argument("--lamW", type=float, default=1.0)
    a = ap.parse_args()
    topo, od, seg, split, meta, lib = load(a.topology, a.K)
    tab_all, _, _, _ = tables_for(a.topology, a.K)
    X = np.stack([c.x for c in lib["library"]])
    per_day = PER_DAY[meta["freq"]]
    lr, lw = a.lamR, a.lamW

    def run_split(name):
        idx = np.array(split[name])
        tab = tab_all.slice(idx[0], idx[-1] + 1)
        sg = seg[idx]
        snap = snapshot(tab, lw)
        return idx, tab, sg, snap

    # tune B6 delta / B7 dwell on validation by total cost J
    _, tv, sgv, snapv = run_split("val")
    deltas = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1]
    dwells = [1, 3, 6, 12, 24, 48]
    best_d = min(deltas, key=lambda d: tv.sequence_cost(B.hysteresis(tv, snapv, d, lw), lr, lw))
    best_w = min(dwells, key=lambda w: tv.sequence_cost(B.min_dwell(tv, snapv, w, lw), lr, lw))

    idx, tab, sg, snap = run_split("test")
    node, edge = tab.node(lw), tab.edge(lr, lw)
    oracle = segment_run(lambda m: viterbi(node[m], edge)[0], sg)
    rh, _ = B.rolling_horizon(tab, lr, lw, H=12, forecast="naive")
    rows = [metrics(tab, np.zeros(len(idx), dtype=np.int32), X, per_day, lr, lw, "B0 always-on"),
            metrics(tab, snap, X, per_day, lr, lw, "SNAP (perfect snapshot rule)"),
            metrics(tab, B.hysteresis(tab, snap, best_d, lw), X, per_day, lr, lw,
                    f"B6 hysteresis (delta={best_d})"),
            metrics(tab, B.min_dwell(tab, snap, best_w, lw), X, per_day, lr, lw,
                    f"B7 min-dwell ({best_w} intervals)"),
            metrics(tab, rh, X, per_day, lr, lw, "B2 rolling horizon H=12 (naive fcst)"),
            metrics(tab, oracle, X, per_day, lr, lw, "O* offline oracle")]
    df = pd.DataFrame(rows)
    snap_row = df.iloc[1]
    df["retention_vs_SNAP_pct"] = 100 * df.savings_pct / snap_row.savings_pct
    df["change_reduction_vs_SNAP_pct"] = 100 * (1 - df.config_changes_per_day / snap_row.config_changes_per_day)
    df["J_regret_vs_oracle_pct"] = 100 * (df.total_cost_J / df.total_cost_J.iloc[-1] - 1)
    out = RESULTS / "pilot"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"pilot_{a.topology}{TAG}_K{a.K}_R{lr}_W{lw}.csv", index=False)
    pd.set_option("display.width", 250)
    print(f"{a.topology}{TAG} test: T={len(idx)} ({len(idx) / per_day:.1f} days), K={len(lib['library'])}, "
          f"lamR={lr}, lamW={lw}")
    print(df.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
