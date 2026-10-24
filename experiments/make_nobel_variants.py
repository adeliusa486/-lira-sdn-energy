"""E19 data: Nobel-Germany variants with a different noise structure.

The default series (lira/data/preprocess.py) multiplies a gravity model x Abilene weekly profile by
independent log-normal noise per OD pair and interval (sigma fitted to Abilene). The variants keep
the gravity model, the profile, the split and the scaling rule, and change only the noise:
  nobel_ar05, nobel_ar09: log-noise z_t = rho z_{t-1} + sqrt(1 - rho^2) e_t (same marginal sigma)
  nobel_s06:              independent noise with sigma halved
Usage: python experiments/make_nobel_variants.py   (then build libraries, see REPRODUCE.md)
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lira import DATA_PROC, DATA_RAW
from lira.data.parse_sndlib import parse_topology
from lira.data.preprocess import (PEAK_PCT, RAW, TARGET_PEAK_MLU, abilene_profile_and_sigma,
                                  chrono_splits, load_dynamic)
from lira.models.network import Topology
from lira.models.routing import all_on, mlu

VARIANTS = {"nobel_ar05": dict(rho=0.5, sig_mult=1.0),
            "nobel_ar09": dict(rho=0.9, sig_mult=1.0),
            "nobel_s06": dict(rho=0.0, sig_mult=0.5)}


def series(day_tms, profile, sigma, rho, days=30, seed=0, start="2004-03-01"):
    rng = np.random.default_rng(seed)
    mean = day_tms.mean(axis=0)
    grav = np.outer(mean.sum(axis=1), mean.sum(axis=0)) / max(mean.sum(), 1e-12)
    np.fill_diagonal(grav, 0)
    T = days * 288
    prof = np.resize(profile, T)
    e = rng.standard_normal((T,) + grav.shape)
    z = np.empty_like(e)
    z[0] = e[0]
    a = np.sqrt(1 - rho ** 2)
    for t in range(1, T):
        z[t] = rho * z[t - 1] + a * e[t]
    noise = np.exp(sigma * z - 0.5 * sigma ** 2)
    return pd.date_range(start, periods=T, freq="5min"), prof[:, None, None] * grav[None] * noise


def main():
    tfile, _ = RAW["nobel"]
    nodes, links = parse_topology((DATA_RAW / "nobel" / tfile).read_text())
    topo = Topology(nodes, links, k_paths=4, name="nobel")
    _, day = load_dynamic("nobel", nodes)
    prof, sigma = abilene_profile_and_sigma()
    for name, v in VARIANTS.items():
        ts, tms = series(day, prof, sigma * v["sig_mult"], v["rho"])
        od = topo.tm_to_od(tms)
        seg = np.zeros(len(od), dtype=int)
        split = chrono_splits(len(od), seg)
        peak = np.percentile(mlu(topo, all_on(topo).split, od[split["train"]]), PEAK_PCT)
        od = (od * TARGET_PEAK_MLU / peak).astype(np.float32)
        out = DATA_PROC / name
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(DATA_PROC / "nobel" / "topology.json", out / "topology.json")
        np.save(out / "od.npy", od)
        np.save(out / "timestamps.npy", ts.to_numpy().astype("datetime64[m]"))
        np.save(out / "segment.npy", seg)
        (out / "splits.json").write_text(json.dumps(split))
        meta = json.loads((DATA_PROC / "nobel" / "meta.json").read_text())
        meta.update({"topology": name, "noise_rho": v["rho"], "noise_sigma": sigma * v["sig_mult"],
                     "scale_factor": float(TARGET_PEAK_MLU / peak), "T": int(len(od))})
        (out / "meta.json").write_text(json.dumps(meta, indent=2))
        print(name, "rho", v["rho"], "sigma", round(sigma * v["sig_mult"], 3), "T", len(od))


if __name__ == "__main__":
    main()
