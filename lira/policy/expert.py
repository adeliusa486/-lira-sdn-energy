"""Exact expert for imitation: backward values of the sequence problem.

Vb[t, c] = node[t, c] + min_c' ( edge[c, c'] + Vb[t+1, c'] )  (cost-to-go incl. step t).
For any visited state (t, prev) the optimal action is argmin_c edge[prev, c] + Vb[t, c],
which is what DAgger queries. For prev = c*_{t-1} on the optimal path it returns c*_t.
Segments (unfilled gaps in the data) are solved independently.
"""
import numpy as np


def backward_values(node, edge, seg):
    T, K = node.shape
    Vb = np.empty((T, K))
    for s in np.unique(seg):
        idx = np.flatnonzero(seg == s)
        Vb[idx[-1]] = node[idx[-1]]
        for t in idx[-2::-1]:
            Vb[t] = node[t] + (edge + Vb[t + 1][None, :]).min(axis=1)
    return Vb


def expert_actions(Vb, edge, t, prev):
    """Vectorised over samples: t, prev int arrays -> (best action, cost gap to 2nd best)."""
    vals = edge[prev] + Vb[t]                   # [n, K]
    best = vals.argmin(axis=1)
    part = np.partition(vals, 1, axis=1)
    gap = np.where(np.isfinite(part[:, 1]), part[:, 1] - part[:, 0], np.nan)
    return best, gap
