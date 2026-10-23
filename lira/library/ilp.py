"""Path-based energy ILP (also baseline B1) and min-MLU routing LP, solved with HiGHS.

ILP for one demand vector d [OD]:
  min  sum_l Pidle_l x_l + Pdyn * sum_a load_a / cap_a
  s.t. sum_{p in o} f_p = 1                    for every OD o (keeps the network connected)
       f_p <= x_l                               for every link l on path p
       sum_{p ∋ a} d_o f_p <= theta cap_a x_l(a) for every arc a
       x in {0,1}^L, f in [0,1]^P
"""
import time

import numpy as np
import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

from lira.models.routing import Config


def _od_rows(topo):
    return sp.csr_matrix((np.ones(topo.P), (topo.path_od, np.arange(topo.P))),
                         shape=(topo.OD, topo.P))


def solve_energy_ilp(topo, d, power, theta=0.8, time_limit=300, gap=0.01, fixed_on=None):
    t0 = time.perf_counter()
    L, P, A = topo.L, topo.P, topo.A
    # variable order: [x (L), f (P)]
    load_coef = topo.arc_path.multiply(d[topo.path_od][None, :]).tocsr()   # [A, P]
    c = np.concatenate([power.link_cost(topo),
                        power.port_dyn_w * np.asarray((load_coef.T @ (1 / topo.cap))).ravel()])
    blocks, lo, hi = [], [], []
    # demand
    blocks.append(sp.hstack([sp.csr_matrix((topo.OD, L)), _od_rows(topo)]))
    lo.append(np.ones(topo.OD)); hi.append(np.ones(topo.OD))
    # f_p - x_l <= 0
    pl = topo.path_link.tocoo()
    n = pl.nnz
    blocks.append(sp.csr_matrix(
        (np.concatenate([-np.ones(n), np.ones(n)]),
         (np.tile(np.arange(n), 2), np.concatenate([pl.col, L + pl.row]))), shape=(n, L + P)))
    lo.append(np.full(n, -np.inf)); hi.append(np.zeros(n))
    # capacity
    xcap = sp.csr_matrix((-theta * topo.cap, (np.arange(A), topo.arc_link)), shape=(A, L))
    blocks.append(sp.hstack([xcap, load_coef]))
    lo.append(np.full(A, -np.inf)); hi.append(np.zeros(A))
    lb = np.zeros(L + P)
    if fixed_on is not None:
        lb[:L] = fixed_on
    res = milp(c, constraints=LinearConstraint(sp.vstack(blocks).tocsr(), np.concatenate(lo),
                                               np.concatenate(hi)),
               integrality=np.concatenate([np.ones(L), np.zeros(P)]),
               bounds=Bounds(lb, np.ones(L + P)),
               options={"time_limit": time_limit, "mip_rel_gap": gap, "disp": False})
    info = {"status": int(res.status), "message": res.message,
            "runtime_s": time.perf_counter() - t0,
            "gap": float(getattr(res, "mip_gap", np.nan) or 0.0)}
    if res.x is None:
        return None, info
    x = np.round(res.x[:L])
    info["objective"] = float(res.fun)
    return x, info


def min_mlu_routing(topo, x, d, hop_penalty=1e-4):
    """LP: split traffic over alive paths to minimise MLU on demand d (plus tiny hop penalty)."""
    alive = topo.alive_paths(x)
    if not all(alive[lo:hi].any() for lo, hi in topo.od_slices):
        return None, np.inf
    P, A = topo.P, topo.A
    # variables [f (P), r]
    load_coef = topo.arc_path.multiply(d[topo.path_od][None, :]).tocsr()
    scale = max(d.max(), 1e-12)
    A_ub = sp.hstack([load_coef / scale, sp.csr_matrix(-topo.cap[:, None] / scale)]).tocsr()
    A_eq = sp.hstack([_od_rows(topo), sp.csr_matrix((topo.OD, 1))]).tocsr()
    c = np.concatenate([hop_penalty * topo.path_len, [1.0]])
    ub = np.concatenate([alive.astype(float), [np.inf]])
    res = linprog(c, A_ub=A_ub, b_ub=np.zeros(A), A_eq=A_eq, b_eq=np.ones(topo.OD),
                  bounds=list(zip(np.zeros(P + 1), ub)), method="highs")
    if res.x is None:
        return None, np.inf
    f = np.clip(res.x[:P], 0, None)
    f[f < 1e-6] = 0
    f /= np.add.reduceat(f, topo.od_first_path)[topo.path_od]
    return f, float(res.x[-1])


def config_from_x(topo, x, d_design, source):
    split, r = min_mlu_routing(topo, x, d_design)
    if split is None:
        return None
    return Config(np.asarray(x, dtype=float), split,
                  {"source": source, "design_mlu": r, "links_on": int(np.sum(x))})
