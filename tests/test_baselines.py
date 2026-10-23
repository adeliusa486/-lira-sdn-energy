import numpy as np
import pytest

from lira.baselines import classical as B
from lira.baselines.runlog import evaluate, from_library
from lira.models.cost import CostTables
from lira.models.network import Topology
from lira.models.power import PowerModel
from lira.models.routing import Config, all_on, shortest_split

PW = PowerModel(0.0, 10.0, 2.0)


@pytest.fixture
def ring():
    return Topology(list("ABCD"), [("A", "B", 100), ("B", "C", 100), ("C", "D", 100),
                                   ("D", "A", 100)], k_paths=2)


def toy_tables(node, R):
    T, K = node.shape
    return CostTables(E=node, feas=np.isfinite(node), mlu=np.zeros((T, K)), R=R,
                      Wn=np.zeros(K), We=np.zeros((K, K)))


def test_elastictree_and_always_on(ring):
    D = np.full((3, ring.OD), 5.0)
    cfgs, _ = B.elastictree(ring, D)
    assert all(c.x.sum() == 3 for c in cfgs)  # ring: exactly one link can sleep
    df = evaluate(ring, cfgs, D, PW)
    assert (df.mlu <= 0.8).all() and df.link_toggles.sum() == 0
    on, _ = B.always_on(ring, D)
    assert evaluate(ring, on, D, PW).power_w.iloc[0] > df.power_w.iloc[0]


def test_hysteresis_and_dwell():
    node = np.array([[1.0, 0.95], [1.0, 0.5], [1.0, 0.95], [1.0, 0.5]])
    tab = toy_tables(node, np.array([[0, 1.0], [1.0, 0]]))
    snap = np.argmin(node, axis=1)
    assert list(B.hysteresis(tab, snap, delta=0.1)) == [0, 1, 1, 1]
    # switch at t=0, held through t=1 (dwell 2), switch back allowed at t=3
    assert list(B.min_dwell(tab, np.array([1, 0, 1, 0]), dwell=2, c0=0)) == [1, 1, 1, 0]


def test_rolling_horizon_perfect_equals_oracle_when_H_is_T():
    rng = np.random.default_rng(0)
    node = rng.uniform(0.2, 1.0, (20, 4))
    R = rng.uniform(0, 0.4, (4, 4)); R = (R + R.T) / 2; np.fill_diagonal(R, 0)
    tab = toy_tables(node, R)
    from lira.oracle.dp import oracle
    seq_o, v_o = oracle(tab, 1.0, 0.0, c0=0)
    seq_r, _ = B.rolling_horizon(tab, 1.0, 0.0, H=20, forecast="perfect", c0=0)
    assert tab.sequence_cost(seq_r, 1.0, 0.0, c0=0) == pytest.approx(v_o)


def test_runlog_library(ring):
    x = np.array([1, 1, 1, 0.0])
    lib = [all_on(ring), Config(x, shortest_split(ring, x))]
    D = np.full((4, ring.OD), 2.0)
    df = from_library(ring, lib, [0, 1, 1, 0], D, PW)
    assert list(df.link_toggles) == [0, 1, 0, 1]
    assert df.config_id.tolist() == [0, 1, 1, 0]
