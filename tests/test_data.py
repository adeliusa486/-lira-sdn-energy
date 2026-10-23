import json

import numpy as np
import pytest

from lira import DATA_PROC
from lira.data.parse_sndlib import parse_demands, parse_topology
from lira.models.network import Topology
from lira.models.routing import all_on, mlu

# published sizes (SNDlib): nodes, undirected links
EXPECTED = {"abilene": (12, 15), "geant": (22, 36), "nobel": (17, 26)}

SAMPLE = """NODES (
  A ( 0 0 )
  B ( 1 1 )
)
LINKS (
  L1 ( A B ) 0.00 0.00 0.00 0.00 ( 40.00 1.0 100.00 2.0 )
)
DEMANDS (
  D1 ( A B ) 1 2.5 UNLIMITED
  D2 ( B A ) 1 1.0 UNLIMITED
)
"""


def test_parser():
    nodes, links = parse_topology(SAMPLE)
    assert nodes == ["A", "B"] and links[0][:3] == ("A", "B", 100.0)  # largest module
    assert parse_demands(SAMPLE) == {("A", "B"): 2.5, ("B", "A"): 1.0}


@pytest.mark.parametrize("name", list(EXPECTED))
def test_processed(name):
    p = DATA_PROC / name
    if not (p / "meta.json").exists():
        pytest.skip("run python -m lira.data.preprocess first")
    topo = Topology.load(p / "topology.json")
    assert (topo.N, topo.L) == EXPECTED[name]
    od = np.load(p / "od.npy")
    ts = np.load(p / "timestamps.npy")
    seg = np.load(p / "segment.npy")
    split = json.loads((p / "splits.json").read_text())
    assert od.shape == (len(ts), topo.OD) == (len(seg), topo.OD)
    assert np.isfinite(od).all() and (od >= 0).all()
    assert (np.diff(ts.astype("int64")) > 0).all()
    tr, va, te = split["train"], split["val"], split["test"]
    assert max(tr) < min(va) and max(va) < min(te) and len(tr) + len(va) + len(te) == len(od)
    # scaling was fitted on the training split only
    peak = np.percentile(mlu(topo, all_on(topo).split, od[tr].astype(float)), 99.9)
    assert peak == pytest.approx(0.5, rel=1e-3)
    feats = np.load(p / "features.npz")
    assert feats["X"].shape[0] == len(od) and np.isfinite(feats["X"]).all()
