"""Sequence cost J = sum_t E(c_t, D_t) + lam_R R(c_{t-1}, c_t) + lam_W W(c_{t-1}, c_t).

All terms are tabulated over a configuration library, so evaluating a sequence is O(T).
Energy is normalised by the all-on idle link power, so one unit of cost equals one
interval of full link power and lam_R, lam_W are dimensionless prices.
"""
from dataclasses import dataclass

import numpy as np

from lira.models.routing import library_mlu


@dataclass
class CostTables:
    E: np.ndarray     # [T, K] normalised energy
    feas: np.ndarray  # [T, K] bool, MLU <= theta
    mlu: np.ndarray   # [T, K]
    R: np.ndarray     # [K, K] normalised reconfiguration cost
    Wn: np.ndarray    # [K] wear, state part (per interval)
    We: np.ndarray    # [K, K] wear, transition part

    VIOLATION_PENALTY = 1e3

    def node(self, lam_W):
        """Per-interval cost; infeasible = inf. If no config is feasible at t, the all-on
        config (index 0) stays allowed with a large penalty (the safety-layer fallback)."""
        node = np.where(self.feas, self.E + lam_W * self.Wn[None, :], np.inf)
        none = ~self.feas.any(axis=1)
        node[none, 0] = self.E[none, 0] + lam_W * self.Wn[0] + self.VIOLATION_PENALTY
        return node

    def edge(self, lam_R, lam_W):
        return lam_R * self.R + lam_W * self.We

    def sequence_cost(self, seq, lam_R, lam_W, c0=None):
        """Total cost of a config index sequence; c0 = config before t=0 (None: no switch)."""
        seq = np.asarray(seq)
        node = self.node(lam_W)[np.arange(len(seq)), seq].sum()
        prev = np.concatenate([[seq[0] if c0 is None else c0], seq[:-1]])
        return float(node + self.edge(lam_R, lam_W)[prev, seq].sum())

    def slice(self, t0, t1):
        return CostTables(self.E[t0:t1], self.feas[t0:t1], self.mlu[t0:t1],
                          self.R, self.Wn, self.We)


def build_tables(topo, library, d, power, wear, R, intervals_per_day, theta=0.8):
    E = power.library_power(topo, library, d) / power.max_link_power(topo)
    M = library_mlu(topo, library, d)
    return CostTables(E=E, feas=M <= theta + 1e-9, mlu=M, R=R,
                      Wn=wear.node_vector(library, intervals_per_day),
                      We=wear.edge_matrix(library))
