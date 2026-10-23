"""Configurations and vectorised link load / MLU evaluation."""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Config:
    """x: link on/off (L,), split: per-path fraction (P,), sums to 1 per OD."""
    x: np.ndarray
    split: np.ndarray
    meta: dict = field(default_factory=dict)

    def key(self):
        return self.x.astype(np.uint8).tobytes()


def _route(topo, x, even):
    alive = topo.alive_paths(x)
    split = np.zeros(topo.P)
    for lo, hi in topo.od_slices:
        ok = np.flatnonzero(alive[lo:hi])
        if ok.size == 0:
            return None
        ln = topo.path_len[lo:hi][ok]
        best = ok[ln == ln.min()] if even else ok[[np.argmin(ln)]]
        split[lo + best] = 1.0 / best.size
    return split


def shortest_split(topo, x):
    """All traffic of each OD on its shortest alive path (None if an OD is cut)."""
    return _route(topo, x, even=False)


def ecmp_split(topo, x):
    """Even split over the alive paths of minimum hop count."""
    return _route(topo, x, even=True)


def all_on(topo):
    x = np.ones(topo.L)
    return Config(x, shortest_split(topo, x), {"name": "all_on"})


def arc_load(topo, split, d):
    """d: [T, OD] or [OD] demand -> arc load [T, A] (same units as d)."""
    d = np.atleast_2d(d)
    flows = d[:, topo.path_od] * split  # [T, P]
    return np.asarray(topo.arc_path.dot(flows.T)).T


def utilization(topo, split, d):
    return arc_load(topo, split, d) / topo.cap


def mlu(topo, split, d):
    return utilization(topo, split, d).max(axis=1)


def library_mlu(topo, library, d):
    """MLU of every config on every TM: [T, K]."""
    d = np.atleast_2d(d)
    return np.stack([mlu(topo, c.split, d) for c in library], axis=1)
