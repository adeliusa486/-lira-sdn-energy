"""Phase 5: oracle labels c*_t for every (lam_R, lam_W) on the full series of one topology.

The R normalisation (95th percentiles) and the disruption reference TM come from the
training split only. DP runs separately on each segment (no sequence crosses a gap).
Also validates DP against the MILP on 3 real-data cases (T=48, K=8).

Usage: python -m lira.oracle.make_labels abilene --K 32
"""
import argparse
import json
import pickle
import time

import numpy as np
import pandas as pd

from lira import ARTIFACTS, DATA_PROC, LOAD, RESULTS, TAG
from lira.models.cost import build_tables
from lira.models.network import Topology
from lira.models.power import PowerModel
from lira.models.reconfig import component_matrices, normalized_R
from lira.models.wear import WearModel
from lira.oracle import milp_check
from lira.oracle.dp import snapshot, viterbi

LAM_R = (0.0, 0.1, 0.3, 1.0, 3.0, 10.0)
LAM_W = (0.0, 1.0, 10.0)
PER_DAY = {"5min": 288, "15min": 96}


def load(topo_name, K):
    p = DATA_PROC / topo_name
    topo = Topology.load(p / "topology.json")
    od = np.load(p / "od.npy").astype(np.float64) * LOAD
    seg = np.load(p / "segment.npy")
    split = json.loads((p / "splits.json").read_text())
    meta = json.loads((p / "meta.json").read_text())
    with open(ARTIFACTS / "library" / f"{topo_name}{TAG}_K{K}.pkl", "rb") as f:
        lib = pickle.load(f)
    return topo, od, seg, split, meta, lib


def tables_for(topo_name, K):
    topo, od, seg, split, meta, lib = load(topo_name, K)
    library = lib["library"]
    T_, F_, D_ = component_matrices(topo, library, od[split["train"]].mean(axis=0))
    R, ref = normalized_R(T_, F_, D_)
    tab = build_tables(topo, library, od, PowerModel.from_yaml(), WearModel.from_yaml(), R,
                       PER_DAY[meta["freq"]], lib["theta"])
    return tab, seg, split, {"R_ref_p95": ref, "raw_toggles": T_, "raw_flowmods": F_,
                             "raw_disrupt": D_}


def segment_dp(node, edge, seg):
    seq, cost = np.empty(len(node), dtype=np.int32), 0.0
    for s in np.unique(seg):
        idx = np.flatnonzero(seg == s)
        q, v = viterbi(node[idx], edge)
        seq[idx] = q
        cost += v
    return seq, cost


def validate_against_milp(tab, n_cases=3, T=48, K=8, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_cases):
        t0 = int(rng.integers(0, tab.E.shape[0] - T))
        ks = np.concatenate([[0], rng.choice(np.arange(1, tab.E.shape[1]), K - 1, replace=False)])
        node = tab.node(1.0)[t0:t0 + T][:, ks]
        edge = tab.edge(1.0, 1.0)[np.ix_(ks, ks)]
        a = time.perf_counter(); _, v_dp = viterbi(node, edge); t_dp = time.perf_counter() - a
        a = time.perf_counter(); _, v_ip = milp_check.solve(node, edge); t_ip = time.perf_counter() - a
        rows.append({"case": i, "t0": t0, "dp_cost": v_dp, "milp_cost": v_ip,
                     "abs_diff": abs(v_dp - v_ip), "dp_s": t_dp, "milp_s": t_ip})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topology")
    ap.add_argument("--K", type=int, default=32)
    a = ap.parse_args()
    tab, seg, split, extra = tables_for(a.topology, a.K)
    out = {"lam_R": np.array(LAM_R), "lam_W": np.array(LAM_W),
           "snapshot": snapshot(tab), "feasible_any": tab.feas.any(axis=1), **extra}
    labels, costs, times = {}, {}, {}
    for lr in LAM_R:
        for lw in LAM_W:
            t0 = time.perf_counter()
            seq, v = segment_dp(tab.node(lw), tab.edge(lr, lw), seg)
            key = f"R{lr}_W{lw}"
            labels[key], costs[key], times[key] = seq, v, time.perf_counter() - t0
    (ARTIFACTS / "labels").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARTIFACTS / "labels" / f"{a.topology}{TAG}_K{a.K}.npz",
                        **out, **{f"seq_{k}": v for k, v in labels.items()})
    val = validate_against_milp(tab)
    val.to_csv(RESULTS / f"dp_milp_validation_{a.topology}{TAG}.csv", index=False)
    summary = {"topology": a.topology, "K": a.K, "T": int(tab.E.shape[0]),
               "infeasible_intervals": int((~tab.feas.any(axis=1)).sum()),
               "dp_runtime_s": times, "dp_milp_max_abs_diff": float(val.abs_diff.max()),
               "R_ref_p95": list(extra["R_ref_p95"])}
    (RESULTS / f"labels_{a.topology}{TAG}_K{a.K}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
