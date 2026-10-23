"""Common per-interval log format for every method: results/runs/{method}/{topo}/seed{s}.parquet."""
import numpy as np
import pandas as pd

from lira import RESULTS
from lira.models.reconfig import disrupted_fraction, flow_mods, link_toggles
from lira.models.routing import mlu


def evaluate(topo, cfgs, D, power, timestamps=None, runtime=None, cfg_ids=None):
    """cfgs: list of Config (one per interval). Returns the log DataFrame."""
    rows, prev = [], None
    for t, (c, d) in enumerate(zip(cfgs, D)):
        same = prev is not None and prev is c
        rows.append({
            "t": t,
            "timestamp": None if timestamps is None else timestamps[t],
            "config_id": None if cfg_ids is None else int(cfg_ids[t]),
            "links_on": int(c.x.sum()),
            "power_w": float(power.power(topo, c, d[None])[0]),
            "mlu": float(mlu(topo, c.split, d[None])[0]),
            "link_toggles": 0 if prev is None or same else link_toggles(prev, c),
            "flow_mods": 0 if prev is None or same else flow_mods(topo, prev, c),
            "disrupted": 0.0 if prev is None or same else disrupted_fraction(topo, prev, c, d),
            "decision_s": None if runtime is None else float(runtime[t]),
            "link_state": c.x.astype(np.uint8).tobytes().hex(),
        })
        prev = c
    return pd.DataFrame(rows)


def from_library(topo, library, seq, D, power, **kw):
    return evaluate(topo, [library[i] for i in seq], D, power, cfg_ids=seq, **kw)


def save(df, method, topo_name, seed=0):
    out = RESULTS / "runs" / method / topo_name
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"seed{seed}.parquet"
    df.to_parquet(path, index=False)
    return path
