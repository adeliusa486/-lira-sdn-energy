"""Topology with k-shortest paths and sparse path incidence matrices.

Sleep unit = undirected link (both ports). Routing unit = directed arc.
Arc a = 2*l is u->v and a = 2*l+1 is v->u for undirected link l.
"""
import json
from itertools import islice

import networkx as nx
import numpy as np
import scipy.sparse as sp


class Topology:
    def __init__(self, nodes, links, k_paths=4, name=""):
        self.name = name
        self.nodes = list(nodes)
        self.idx = {n: i for i, n in enumerate(self.nodes)}
        self.N = len(self.nodes)
        self.links = [(self.idx[u], self.idx[v]) for u, v, *_ in links]
        self.L = len(self.links)
        self.A = 2 * self.L
        cap = np.array([c for _, _, c, *_ in links], dtype=float)
        self.cap = np.repeat(cap, 2)  # per arc
        self.arc_ends = np.array([e for (u, v) in self.links for e in ((u, v), (v, u))])
        self.arc_link = np.repeat(np.arange(self.L), 2)
        self.od = np.array([(s, t) for s in range(self.N) for t in range(self.N) if s != t])
        self.OD = len(self.od)
        self.k = k_paths
        self._build_paths()

    def _build_paths(self):
        g = nx.DiGraph()
        g.add_nodes_from(range(self.N))
        arc_of = {}
        for a, (u, v) in enumerate(self.arc_ends):
            g.add_edge(int(u), int(v), weight=1.0)
            arc_of[(int(u), int(v))] = a
        paths, path_od, path_nodes = [], [], []
        for o, (s, t) in enumerate(self.od):
            gen = nx.shortest_simple_paths(g, int(s), int(t), weight="weight")
            for p in islice(gen, self.k):
                paths.append([arc_of[(p[i], p[i + 1])] for i in range(len(p) - 1)])
                path_od.append(o)
                path_nodes.append(p)
        self.paths, self.path_nodes = paths, path_nodes
        self.P = len(paths)
        self.path_od = np.array(path_od)
        rows = np.repeat(np.arange(self.P), [len(p) for p in paths])
        cols = np.concatenate(paths)
        self.path_arc = sp.csr_matrix((np.ones(len(cols)), (rows, cols)), shape=(self.P, self.A))
        self.arc_path = self.path_arc.T.tocsr()
        self.path_link = sp.csr_matrix(
            (np.ones(len(cols)), (rows, self.arc_link[cols])), shape=(self.P, self.L))
        self.path_len = np.array([len(p) for p in paths])
        self.od_first_path = np.searchsorted(self.path_od, np.arange(self.OD))
        self.od_slices = [(self.od_first_path[o],
                           self.od_first_path[o + 1] if o + 1 < self.OD else self.P)
                          for o in range(self.OD)]

    def alive_paths(self, x):
        """Boolean mask of paths whose links are all on, for link states x (L,)."""
        off = 1 - np.asarray(x, dtype=float)
        return (self.path_link @ off) == 0

    def tm_to_od(self, tm):
        """[..., N, N] matrix -> [..., OD] vector."""
        return tm[..., self.od[:, 0], self.od[:, 1]]

    def to_dict(self):
        return {"name": self.name, "nodes": self.nodes,
                "links": [(self.nodes[u], self.nodes[v], float(self.cap[2 * i]))
                          for i, (u, v) in enumerate(self.links)], "k_paths": self.k}

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=1)

    @classmethod
    def load(cls, path):
        with open(path) as f:
            d = json.load(f)
        return cls(d["nodes"], d["links"], d.get("k_paths", 4), d.get("name", ""))
