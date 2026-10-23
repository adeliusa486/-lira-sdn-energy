"""Exact sequence-optimal oracle over a configuration library (Viterbi, O(T K^2)).

V_t(c) = node_t(c) + min_{c'} [ V_{t-1}(c') + edge(c', c) ]
"""
import numpy as np


def viterbi(node, edge, c0=None):
    """node: [T, K] (inf = infeasible), edge: [K, K] (from, to).

    c0: config in place before t=0 (its switching cost is charged at t=0), or None.
    Returns (sequence [T], optimal cost).
    """
    T, K = node.shape
    V = node[0] + (edge[c0] if c0 is not None else 0.0)
    back = np.empty((T, K), dtype=np.int32)
    for t in range(1, T):
        cand = V[:, None] + edge          # [from, to]
        back[t] = np.argmin(cand, axis=0)
        V = cand[back[t], np.arange(K)] + node[t]
    if not np.isfinite(V).any():
        raise ValueError("no feasible configuration sequence")
    seq = np.empty(T, dtype=np.int32)
    seq[-1] = int(np.argmin(V))
    for t in range(T - 1, 0, -1):
        seq[t - 1] = back[t, seq[t]]
    return seq, float(V[seq[-1]])


def oracle(tables, lam_R, lam_W, c0=None):
    return viterbi(tables.node(lam_W), tables.edge(lam_R, lam_W), c0)


def snapshot(tables, lam_W=0.0):
    """Per-interval cheapest feasible config (the snapshot rule, no history)."""
    return np.argmin(tables.node(lam_W), axis=1).astype(np.int32)
