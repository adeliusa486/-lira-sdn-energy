"""Phase 4: build the configuration library for one topology.

1. k-means on training TMs (log1p OD vectors) -> M clusters; design TM = per-cluster
   elementwise 95th percentile.
2. Energy ILP per design TM (+ NSGA-II Pareto sets for diversity).
3. Merge identical link states; routing = min-MLU LP on the cluster design TM.
4. Greedy coverage: solve extra ILPs for uncovered train/val TMs until >= 99.5 %.
5. Prune to K by greedy snapshot-cost reduction (all-on is always kept).

Usage: python -m lira.library.build_library abilene --M 64 --K 8 16 32 64 128
"""
import argparse
import json
import pickle

import numpy as np
from sklearn.cluster import KMeans

from lira import ARTIFACTS, DATA_PROC, LOAD, RESULTS, TAG, THETA_ENV
from lira.library.ga import run_nsga2
from lira.library.ilp import config_from_x, solve_energy_ilp
from lira.models.network import Topology
from lira.models.power import PowerModel
from lira.models.routing import all_on, library_mlu


def representative_tms(D, M, seed):
    km = KMeans(n_clusters=M, n_init=4, random_state=seed).fit(np.log1p(D))
    reps = [np.percentile(D[km.labels_ == m], 95, axis=0) for m in range(M)
            if (km.labels_ == m).any()]
    return np.array(reps), km.labels_


def enumerate_candidates(topo, max_count=5000):
    """All link states that keep every OD connected (only for small topologies)."""
    from itertools import combinations
    from math import comb
    max_sleep = topo.L - (topo.N - 1)
    if sum(comb(topo.L, s) for s in range(max_sleep + 1)) > max_count:
        return None
    out = []
    for s in range(1, max_sleep + 1):
        for off in combinations(range(topo.L), s):
            x = np.ones(topo.L)
            x[list(off)] = 0
            alive = topo.alive_paths(x)
            if all(alive[lo:hi].any() for lo, hi in topo.od_slices):
                out.append(x)
    return out


def coverage(topo, library, D, theta):
    feas = library_mlu(topo, library, D) <= theta + 1e-9
    return feas.any(axis=1), feas


def prune(topo, library, D, power, theta, K):
    """Greedy: add the config that most lowers sum_t min feasible energy. Keeps index 0."""
    E = power.library_power(topo, library, D)
    feas = library_mlu(topo, library, D) <= theta + 1e-9
    E[~feas] = 1e3 * E.max()  # infeasible = huge
    chosen = [0]
    best = E[:, 0].copy()
    while len(chosen) < min(K, len(library)):
        gain = best[:, None] - np.minimum(best[:, None], E)
        gain[:, chosen] = -1
        j = int(np.argmax(gain.sum(axis=0)))
        if gain[:, j].sum() <= 0:
            break
        chosen.append(j)
        best = np.minimum(best, E[:, j])
    # energy gains exhausted: fill up with the configs that are cheapest where feasible
    # and feasible often (near-optimal alternatives are exactly what snapshot rules flap between)
    rest = [j for j in range(len(library)) if j not in chosen and feas[:, j].mean() > 0.05]
    rest.sort(key=lambda j: (E[feas[:, j], j] / best[feas[:, j]]).mean())
    chosen += rest[:max(0, K - len(chosen))]
    return chosen


def build(topo_name, M=64, Ks=(8, 16, 32, 64, 128), theta=0.8, seed=0, ga=True,
          time_limit=300, target_cov=0.995, max_extra=200):
    pdir = DATA_PROC / topo_name
    topo = Topology.load(pdir / "topology.json")
    D = np.load(pdir / "od.npy") * LOAD
    split = json.loads((pdir / "splits.json").read_text())
    D_fit = D[split["train"]]
    D_cov = D[split["train"] + split["val"]]
    power = PowerModel.from_yaml()
    log = []

    reps, _ = representative_tms(D_fit, M, seed)
    cand = {}

    def add_x(x, d_design, source):
        key = np.asarray(x, dtype=np.uint8).tobytes()
        if key in cand:
            return
        cfg = config_from_x(topo, x, d_design, source)
        if cfg is not None:
            cand[key] = cfg

    for m, d in enumerate(reps):
        x, info = solve_energy_ilp(topo, d, power, theta, time_limit)
        log.append({"stage": "ilp_cluster", "id": m, **info,
                    "links_on": None if x is None else int(x.sum())})
        if x is not None:
            add_x(x, d, f"ilp_c{m}")
        if ga and m % 4 == 0:
            for j, xg in enumerate(run_nsga2(topo, d, theta, seed=seed + m)):
                add_x(xg, d, f"ga_c{m}_{j}")
    print(f"[{topo_name}] {len(cand)} unique configs from {len(reps)} clusters")
    enum = enumerate_candidates(topo)
    if enum is not None:
        d_peak = np.percentile(D_fit, 95, axis=0)
        for x in enum:
            add_x(x, d_peak, "enum")
        print(f"[{topo_name}] +enumeration of {len(enum)} connected link states -> {len(cand)}")

    base = all_on(topo)
    library = [base] + list(cand.values())
    covered, _ = coverage(topo, library, D_cov, theta)
    extra = 0
    while covered.mean() < target_cov and extra < max_extra:
        miss = np.flatnonzero(~covered)
        t = miss[np.argmax(D_cov[miss].sum(axis=1))]
        x, info = solve_energy_ilp(topo, D_cov[t], power, theta, time_limit)
        log.append({"stage": "ilp_cover", "id": int(t), **info})
        extra += 1
        if x is None:
            covered[t] = True  # infeasible even for the ILP: no config can cover it
            continue
        cfg = config_from_x(topo, x, D_cov[t], f"ilp_cover{t}")
        if cfg is None or cfg.key() in cand:
            covered[t] = True
            continue
        cand[cfg.key()] = cfg
        library.append(cfg)
        cov_new, _ = coverage(topo, [cfg], D_cov, theta)
        covered |= cov_new
    print(f"[{topo_name}] coverage {covered.mean():.4f} with {len(library)} configs")

    out = ARTIFACTS / "library"
    out.mkdir(parents=True, exist_ok=True)
    report = {"topology": topo_name, "M": M, "theta": theta, "seed": seed,
              "n_candidates": len(library), "coverage_trainval": float(covered.mean()),
              "allon_feasible_trainval": float(coverage(topo, [base], D_cov, theta)[0].mean()),
              "K": {}}
    for K in Ks:
        idx = prune(topo, library, D_fit[::6], power, theta, K)  # 30-min sampling for speed
        lib = [library[i] for i in idx]
        cov_val, _ = coverage(topo, lib, D[split["val"]], theta)
        report["K"][str(K)] = {"size": len(lib), "coverage_val": float(cov_val.mean())}
        with open(out / f"{topo_name}{TAG}_K{K}.pkl", "wb") as f:
            pickle.dump({"library": lib, "theta": theta, "seed": seed}, f)
    with open(out / f"{topo_name}{TAG}_all.pkl", "wb") as f:
        pickle.dump({"library": library, "theta": theta, "seed": seed}, f)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"library_{topo_name}{TAG}_report.json").write_text(json.dumps(report, indent=2))
    import pandas as pd
    pd.DataFrame(log).to_csv(RESULTS / f"library_{topo_name}{TAG}_solver_log.csv", index=False)
    print(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topology")
    ap.add_argument("--M", type=int, default=64)
    ap.add_argument("--K", type=int, nargs="+", default=[8, 16, 32, 64, 128])
    ap.add_argument("--theta", type=float, default=THETA_ENV)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-ga", action="store_true")
    ap.add_argument("--time-limit", type=float, default=300)
    a = ap.parse_args()
    build(a.topology, a.M, a.K, a.theta, a.seed, not a.no_ga, a.time_limit)


if __name__ == "__main__":
    main()
