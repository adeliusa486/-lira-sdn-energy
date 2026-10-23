import networkx as nx
import numpy as np
import pytest

from lira.library.ilp import config_from_x, min_mlu_routing, solve_energy_ilp
from lira.models.cost import build_tables
from lira.models.network import Topology
from lira.models.power import PowerModel
from lira.models.reconfig import component_matrices, flow_mods, link_toggles, normalized_R
from lira.models.routing import Config, all_on, mlu, shortest_split
from lira.models.wear import WearModel
from lira.oracle import milp_check
from lira.oracle.dp import oracle, snapshot, viterbi

PW = PowerModel(chassis_w=0.0, port_idle_w=10.0, port_dyn_w=2.0)


@pytest.fixture
def ring():
    # A-B-C-D-A ring, 100 Mb/s links
    return Topology(list("ABCD"), [("A", "B", 100), ("B", "C", 100), ("C", "D", 100),
                                   ("D", "A", 100)], k_paths=2)


def demand(topo, pairs):
    d = np.zeros(topo.OD)
    for (s, t), v in pairs.items():
        o = np.flatnonzero((topo.od[:, 0] == topo.idx[s]) & (topo.od[:, 1] == topo.idx[t]))[0]
        d[o] = v
    return d


def test_ring_paths(ring):
    assert ring.L == 4 and ring.A == 8 and ring.OD == 12
    assert ring.P == 24  # two paths (both directions around the ring) per OD


def test_allon_power_analytic(ring):
    c = all_on(ring)
    d = demand(ring, {("A", "B"): 50})
    # 4 links * 2 ports * 10 W + 2 W * 0.5 utilisation on the A->B port
    assert PW.power(ring, c, d)[0] == pytest.approx(80 + 1.0)
    assert mlu(ring, c.split, d)[0] == pytest.approx(0.5)
    pw = PowerModel(0.0, 10.0, 2.0, port_sleep_w=1.0)
    x = np.array([1, 1, 1, 0.0])
    c3 = Config(x, shortest_split(ring, x))
    assert pw.power(ring, c3, d)[0] == pytest.approx(60 + 2 + 1.0)  # 3 on, 1 asleep, A->B 50%


def test_mlu_vs_maxflow(ring):
    d = demand(ring, {("A", "C"): 120})
    split, r = min_mlu_routing(ring, np.ones(4), d)
    # A->C has two disjoint 2-hop paths: max flow = 200, so optimal MLU = 120/200
    g = nx.DiGraph()
    for (u, v), cap in zip(ring.arc_ends, ring.cap):
        g.add_edge(int(u), int(v), capacity=cap)
    mf = nx.maximum_flow_value(g, ring.idx["A"], ring.idx["C"])
    assert r == pytest.approx(120 / mf, rel=1e-6)
    assert mlu(ring, split, d)[0] == pytest.approx(120 / mf, rel=1e-6)


def test_ilp_sleeps_one_link(ring):
    d = demand(ring, {("A", "B"): 10, ("C", "D"): 10})
    x, info = solve_energy_ilp(ring, d, PW, theta=0.8)
    # a ring stays connected with any one link off, never with two
    assert x.sum() == 3
    cfg = config_from_x(ring, x, d, "t")
    assert mlu(ring, cfg.split, d)[0] <= 0.8 + 1e-9


def test_reconfig_and_wear(ring):
    c1 = all_on(ring)
    x2 = np.array([1, 1, 1, 0.0])
    c2 = Config(x2, shortest_split(ring, x2))
    assert link_toggles(c1, c1) == 0 and flow_mods(ring, c1, c1) == 0
    assert link_toggles(c1, c2) == 1 and flow_mods(ring, c1, c2) > 0
    T, F, D = component_matrices(ring, [c1, c2], np.ones(ring.OD))
    R, _ = normalized_R(T, F, D)
    assert np.allclose(R, R.T) and np.allclose(np.diag(R), 0)
    w = WearModel(1.0, 0.6, 0.01)
    X = np.array([[1, 1, 1, 1], [1, 1, 1, 0], [1, 1, 1, 0], [1, 1, 1, 1]], float)
    af = w.acceleration(X, intervals_per_day=4)
    assert af[0] == pytest.approx(1.0)
    assert af[3] == pytest.approx(0.5 * 1.0 + 0.5 * 0.6 + 0.01 * 2)
    # linearised step terms sum to sum_e (AF_e - AF_on) over one day
    lib = [c1, c2]
    seq = [0, 1, 1, 0]
    lin = w.node_vector(lib, 4)[seq].sum() + sum(w.edge_matrix(lib)[a, b] for a, b in zip(seq, seq[1:]))
    assert lin == pytest.approx((af - 1.0).sum())


def test_tables_and_snapshot(ring):
    c1 = all_on(ring)
    x2 = np.array([1, 1, 1, 0.0])
    lib = [c1, Config(x2, shortest_split(ring, x2))]
    d = np.stack([demand(ring, {("A", "B"): v}) for v in (10, 70, 10)])
    T, F, D = component_matrices(ring, lib, d.mean(0))
    R, _ = normalized_R(T, F, D)
    tab = build_tables(ring, lib, d, PW, WearModel(), R, intervals_per_day=3)
    assert tab.feas.all()
    snap = snapshot(tab)
    assert (snap == 1).all()  # the 3-link config is always cheaper and feasible


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_dp_matches_milp(seed):
    rng = np.random.default_rng(seed)
    T, K = 48, 8
    node = rng.uniform(0.3, 1.0, (T, K))
    node[rng.random((T, K)) < 0.15] = np.inf
    node[:, 0] = rng.uniform(0.9, 1.0, T)  # an always-feasible fallback
    edge = rng.uniform(0, 0.5, (K, K))
    edge = (edge + edge.T) / 2
    np.fill_diagonal(edge, 0)
    seq, v = viterbi(node, edge)
    seq_m, v_m = milp_check.solve(node, edge)
    assert v == pytest.approx(v_m, abs=1e-6)
    cost = node[np.arange(T), seq].sum() + edge[seq[:-1], seq[1:]].sum()
    assert cost == pytest.approx(v, abs=1e-9)


def test_dp_no_switch_when_expensive():
    node = np.array([[1.0, 0.9], [1.0, 0.9], [1.0, 0.9]])
    edge = np.array([[0, 5.0], [5.0, 0]])
    seq, _ = viterbi(node, edge, c0=0)
    assert (seq == 0).all()
    seq, _ = viterbi(node, np.zeros((2, 2)), c0=0)
    assert (seq == 1).all()
