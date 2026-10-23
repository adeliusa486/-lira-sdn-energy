"""Independent MILP formulation of the library-sequence problem (validates the DP).

Variables y[t,k] in {0,1} (config k at t), z[t,i,j] >= 0 (switch i->j at t>=1).
z[t,i,j] >= y[t-1,i] + y[t,j] - 1 with non-negative edge costs gives exact pairs.
Solved with HiGHS through scipy.optimize.milp.
"""
import numpy as np
import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, milp


def solve(node, edge, time_limit=120):
    T, K = node.shape
    big = np.where(np.isfinite(node), node, 0.0)
    ny, nz = T * K, (T - 1) * K * K
    c = np.concatenate([big.ravel(), np.tile(edge.ravel(), T - 1)])
    yi = lambda t, k: t * K + k
    zi = lambda t, i, j: ny + (t - 1) * K * K + i * K + j
    rows, cols, vals, lo, hi = [], [], [], [], []
    r = 0
    for t in range(T):  # one config per interval
        for k in range(K):
            rows.append(r); cols.append(yi(t, k)); vals.append(1.0)
        lo.append(1); hi.append(1); r += 1
    for t in range(1, T):
        for i in range(K):
            for j in range(K):  # z - y[t-1,i] - y[t,j] >= -1
                rows += [r, r, r]; cols += [zi(t, i, j), yi(t - 1, i), yi(t, j)]
                vals += [1.0, -1.0, -1.0]; lo.append(-1); hi.append(np.inf); r += 1
    A = sp.csr_matrix((vals, (rows, cols)), shape=(r, ny + nz))
    ub = np.concatenate([np.where(np.isfinite(node), 1.0, 0.0).ravel(), np.full(nz, np.inf)])
    integ = np.concatenate([np.ones(ny), np.zeros(nz)])
    res = milp(c, constraints=LinearConstraint(A, lo, hi), integrality=integ,
               bounds=Bounds(np.zeros(ny + nz), ub),
               options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    if res.x is None:
        raise RuntimeError(res.message)
    seq = res.x[:ny].reshape(T, K).argmax(axis=1)
    return seq, float(res.fun)
