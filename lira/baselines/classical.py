"""Phase 5 non-learning baselines. Each returns a per-interval config log.

Library-based baselines return library indices; B1/B3/B5 solve per TM and return Configs,
which are evaluated with the same power/MLU/reconfiguration code.

B0  always_on          all links on, shortest-path routing
B1  snapshot_ilp       energy ILP on each TM (energy upper bound, no switching cost)
B2  rolling_horizon    library-restricted multi-period problem, horizon H, re-solved each
                       step with exact DP; forecast = 'perfect' or 'naive' (repeat D_t)
B3  ga_snapshot        NSGA-II per TM, lowest-power feasible member
B5  elastictree        greedy: switch off least-utilised links while feasible
B6  hysteresis(seq)    switch to the snapshot choice only if gain > delta
B7  min_dwell(seq)     hold each config for at least `dwell` intervals unless infeasible
"""
import time

import numpy as np

from lira.library.ga import run_nsga2
from lira.library.ilp import config_from_x, solve_energy_ilp
from lira.models.routing import Config, all_on, ecmp_split, mlu, shortest_split
from lira.oracle.dp import viterbi


def always_on(topo, D):
    c = all_on(topo)
    return [c] * len(D), np.zeros(len(D))


def snapshot_ilp(topo, D, power, theta=0.8, time_limit=300):
    cfgs, rt = [], []
    for d in D:
        t0 = time.perf_counter()
        x, _ = solve_energy_ilp(topo, d, power, theta, time_limit)
        c = config_from_x(topo, x, d, "B1") if x is not None else None
        cfgs.append(c or all_on(topo))
        rt.append(time.perf_counter() - t0)
    return cfgs, np.array(rt)


def ga_snapshot(topo, D, power, theta=0.8, seed=0, **ga_kw):
    cfgs, rt = [], []
    for i, d in enumerate(D):
        t0 = time.perf_counter()
        best = None
        for x in sorted(run_nsga2(topo, d, theta, seed=seed + i, **ga_kw), key=lambda v: v.sum()):
            s = ecmp_split(topo, x)
            if s is not None and mlu(topo, s, d)[0] <= theta:
                best = Config(x, s, {"source": "B3"})
                break
        cfgs.append(best or all_on(topo))
        rt.append(time.perf_counter() - t0)
    return cfgs, np.array(rt)


def elastictree(topo, D, theta=0.8):
    """Greedy: repeatedly sleep the least-utilised link whose removal keeps MLU <= theta."""
    cfgs, rt = [], []
    for d in D:
        t0 = time.perf_counter()
        x = np.ones(topo.L)
        split = shortest_split(topo, x)
        while True:
            u = (np.asarray(topo.arc_path.dot((d[topo.path_od] * split))) / topo.cap)
            order = np.argsort(u.reshape(topo.L, 2).max(axis=1))
            moved = False
            for l in order:
                if x[l] == 0:
                    continue
                x2 = x.copy(); x2[l] = 0
                s2 = shortest_split(topo, x2)
                if s2 is not None and mlu(topo, s2, d)[0] <= theta:
                    x, split, moved = x2, s2, True
                    break
            if not moved:
                break
        cfgs.append(Config(x, split, {"source": "B5"}))
        rt.append(time.perf_counter() - t0)
    return cfgs, np.array(rt)


def rolling_horizon(tables, lam_R, lam_W, H=12, forecast="perfect", c0=0):
    """B2 over the library: at each t solve the H-step problem exactly, apply first action."""
    node, edge = tables.node(lam_W), tables.edge(lam_R, lam_W)
    T = node.shape[0]
    seq, rt, prev = np.empty(T, dtype=np.int32), np.empty(T), c0
    for t in range(T):
        t0 = time.perf_counter()
        if forecast == "perfect":
            win = node[t:t + H]
        else:  # naive: future = current TM (feasibility of t is known at decision time)
            win = np.repeat(node[t:t + 1], min(H, T - t), axis=0)
        s, _ = viterbi(win, edge, c0=prev)
        seq[t] = prev = s[0]
        rt[t] = time.perf_counter() - t0
    return seq, rt


def hysteresis(tables, snap_seq, delta, lam_W=0.0, c0=0):
    """Keep the current config unless the snapshot choice saves more than delta (or it breaks)."""
    node = tables.node(lam_W)
    seq, cur = np.empty(len(snap_seq), dtype=np.int32), c0
    for t, s in enumerate(snap_seq):
        if not np.isfinite(node[t, cur]) or node[t, cur] - node[t, s] > delta:
            cur = s
        seq[t] = cur
    return seq


def min_dwell(tables, snap_seq, dwell, lam_W=0.0, c0=0):
    """Hold each config for >= dwell intervals; leave early only if it becomes infeasible."""
    node = tables.node(lam_W)
    seq, cur, held = np.empty(len(snap_seq), dtype=np.int32), c0, dwell
    for t, s in enumerate(snap_seq):
        if s != cur and (held >= dwell or not np.isfinite(node[t, cur])):
            cur, held = s, 0
        held += 1
        seq[t] = cur
    return seq
