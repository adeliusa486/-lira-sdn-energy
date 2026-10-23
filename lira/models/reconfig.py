"""Reconfiguration cost R(c1, c2) = a*toggles + b*flow_mods + g*disrupted_traffic."""
import numpy as np


def link_toggles(c1, c2):
    return int(np.abs(c1.x - c2.x).sum())


def _next_hops(topo, split, o):
    """{node: {next_node: weight}} forwarding state of OD o."""
    lo, hi = topo.od_slices[o]
    fw = {}
    for p in range(lo, hi):
        w = split[p]
        if w <= 0:
            continue
        nodes = topo.path_nodes[p]
        for a, b in zip(nodes[:-1], nodes[1:]):
            hop = fw.setdefault(a, {})
            hop[b] = hop.get(b, 0.0) + w
    return fw


def od_split_change(topo, c1, c2):
    """Per-OD L1 change of the split vector (0..2)."""
    return np.add.reduceat(np.abs(c1.split - c2.split), topo.od_first_path)


def flow_mods(topo, c1, c2, tol=1e-6):
    """Number of (switch, OD) forwarding entries that differ between two configs."""
    n = 0
    for o in np.flatnonzero(od_split_change(topo, c1, c2) > tol):
        f1, f2 = _next_hops(topo, c1.split, o), _next_hops(topo, c2.split, o)
        for v in set(f1) | set(f2):
            a, b = f1.get(v, {}), f2.get(v, {})
            if any(abs(a.get(k, 0.0) - b.get(k, 0.0)) > tol for k in set(a) | set(b)):
                n += 1
    return n


def disrupted_fraction(topo, c1, c2, d_ref):
    """Share of reference traffic that moves to a different path (0..1)."""
    moved = 0.5 * od_split_change(topo, c1, c2)
    return float((moved * d_ref).sum() / max(d_ref.sum(), 1e-12))


def component_matrices(topo, library, d_ref):
    """K x K matrices of the three raw R components (toggles, flow-mods, disruption)."""
    K = len(library)
    T, F, D = np.zeros((K, K)), np.zeros((K, K)), np.zeros((K, K))
    for i in range(K):
        for j in range(i + 1, K):
            T[i, j] = T[j, i] = link_toggles(library[i], library[j])
            F[i, j] = F[j, i] = flow_mods(topo, library[i], library[j])
            D[i, j] = D[j, i] = disrupted_fraction(topo, library[i], library[j], d_ref)
    return T, F, D


def normalized_R(T, F, D, weights=(1 / 3, 1 / 3, 1 / 3), ref=None):
    """Scale each component so its 95th percentile over distinct pairs is 1.

    ref: optional (t95, f95, d95) fixed on training data and reused afterwards.
    """
    if ref is None:
        off = ~np.eye(T.shape[0], dtype=bool)
        ref = tuple(float(max(np.percentile(M[off], 95), 1e-12)) if off.any() else 1.0
                    for M in (T, F, D))
    a, b, g = weights
    return a * T / ref[0] + b * F / ref[1] + g * D / ref[2], ref
