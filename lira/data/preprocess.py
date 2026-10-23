"""Phase 2: parse raw SNDlib data into data/processed/{topo}/.

Outputs per topology:
  topology.json   nodes, undirected links, capacity (Mb/s)
  od.npy          [T, OD] demand in Mb/s after scaling (float32)
  timestamps.npy  [T] datetime64[m]
  segment.npy     [T] int, increments after every unfilled gap (sequences must not cross it)
  splits.json     chronological 60/15/25 + 4 rolling-origin folds
  meta.json       counts, gaps, scaling factor, provenance
Scaling is fit on the training split only: the 99.9th percentile of all-on
shortest-path MLU is set to 0.5 (robust to short anomalous bursts).

Nobel-Germany: SNDlib offers one day of 5-min matrices, shorter than the 7 days the plan
requires, so a 30-day semi-synthetic series is generated (gravity model fitted to the
SNDlib day x Abilene diurnal/weekly profile x log-normal noise fitted to Abilene residuals).
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from lira import DATA_PROC, DATA_RAW
from lira.data.parse_sndlib import parse_demands, parse_topology
from lira.models.network import Topology
from lira.models.routing import all_on, mlu

RAW = {
    "abilene": ("abilene.txt", "5min"),
    "geant": ("geant.txt", "15min"),
    "nobel": ("nobel-germany.txt", "5min"),
}
MAX_FILL = 3          # interpolate gaps of up to this many intervals
SPIKE_FACTOR = 10     # total volume > 10x its 1-day rolling median = measurement artifact
TARGET_PEAK_MLU = 0.5
PEAK_PCT = 99.9
_TS = re.compile(r"(\d{8})-(\d{4})")


def load_dynamic(topo_name, nodes):
    cache = DATA_RAW / topo_name / "parsed_cache.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        return pd.DatetimeIndex(z["ts"]), z["tms"]
    ts, tms = _parse_dynamic(topo_name, nodes)
    np.savez_compressed(cache, ts=ts.to_numpy(), tms=tms)
    return ts, tms


def _parse_dynamic(topo_name, nodes):
    files = sorted((DATA_RAW / topo_name / "dynamic").rglob("*.txt"))
    idx = {n: i for i, n in enumerate(nodes)}
    ts, tms = [], []
    for f in files:
        m = _TS.search(f.name)
        tm = np.zeros((len(nodes), len(nodes)), dtype=np.float64)
        for (s, t), v in parse_demands(f.read_text()).items():
            if s != t:
                tm[idx[s], idx[t]] += v
        ts.append(pd.Timestamp(f"{m.group(1)} {m.group(2)[:2]}:{m.group(2)[2:]}"))
        tms.append(tm)
    return pd.DatetimeIndex(ts), np.stack(tms)


def regularise(ts, tms, freq):
    """Put the series on a regular grid; fill short gaps; drop long gaps and outages."""
    order = np.argsort(ts)
    ts, tms = ts[order], tms[order]
    dup = ts.duplicated()
    ts, tms = ts[~dup], tms[~dup]
    grid = pd.date_range(ts[0], ts[-1], freq=freq)
    T, N = len(grid), tms.shape[1]
    full = np.full((T, N * N), np.nan)
    pos = grid.get_indexer(ts)
    full[pos] = tms.reshape(len(ts), -1)
    bad = ~np.isfinite(full).all(axis=1)
    zero = np.isfinite(full).all(axis=1) & (np.nansum(full, axis=1) == 0)
    full[zero] = np.nan          # all-zero matrices are measurement outages
    full[full < 0] = np.nan
    vol = pd.Series(full.sum(axis=1))
    per_day = int(pd.Timedelta("1D") / pd.Timedelta(freq))
    med = vol.rolling(per_day, center=True, min_periods=per_day // 4).median()
    spike = (vol > SPIKE_FACTOR * med).to_numpy()
    full[spike] = np.nan
    df = pd.DataFrame(full)
    missing = df.isna().any(axis=1).to_numpy()
    filled = df.interpolate(limit=MAX_FILL, limit_area="inside").to_numpy()
    keep = np.isfinite(filled).all(axis=1)
    segment = np.cumsum(np.concatenate([[0], np.diff(np.flatnonzero(keep)) > 1]))
    stats = {"grid_intervals": int(T), "raw_files": int(len(ts)) + int(dup.sum()),
             "duplicates": int(dup.sum()), "absent_intervals": int(bad.sum()), "volume_spikes_removed": int(spike.sum()),
             "all_zero_intervals": int(zero.sum()), "missing_total": int(missing.sum()),
             "filled_by_interpolation": int((missing & keep).sum()),
             "dropped": int((~keep).sum()), "segments": int(segment.max() + 1)}
    return grid[keep], filled[keep].reshape(-1, N, N), segment, stats


def semi_synthetic(day_tms, profile, resid_sigma, days=30, seed=0, start="2004-03-01"):
    """Gravity model x diurnal/weekly profile x log-normal noise (all fitted elsewhere)."""
    rng = np.random.default_rng(seed)
    mean = day_tms.mean(axis=0)
    out_, in_ = mean.sum(axis=1), mean.sum(axis=0)
    grav = np.outer(out_, in_) / max(mean.sum(), 1e-12)
    np.fill_diagonal(grav, 0)
    T = days * 288
    prof = np.resize(profile, T)
    noise = rng.lognormal(-0.5 * resid_sigma ** 2, resid_sigma, size=(T,) + grav.shape)
    tms = prof[:, None, None] * grav[None] * noise
    ts = pd.date_range(start, periods=T, freq="5min")
    return ts, tms


def abilene_profile_and_sigma():
    """Weekly profile (2016 slots of 5 min, mean 1) and OD log-residual sigma from Abilene."""
    p = DATA_PROC / "abilene"
    od = np.load(p / "od.npy")
    ts = pd.DatetimeIndex(np.load(p / "timestamps.npy"))
    tr = json.loads((p / "splits.json").read_text())["train"]
    od, ts = od[tr], ts[tr]
    slot = (ts.dayofweek * 288 + ts.hour * 12 + ts.minute // 5).to_numpy()
    tot = od.sum(axis=1)
    prof = pd.Series(tot).groupby(slot).mean().reindex(range(2016)).interpolate().bfill().ffill()
    prof = (prof / prof.mean()).to_numpy()
    expected = np.outer(prof[slot] / prof[slot].mean(), od.mean(axis=0))
    mask = (od > 0) & (expected > 0)
    sigma = float(np.std(np.log(od[mask] / expected[mask])))
    return prof, sigma


def chrono_splits(T, segment, fracs=(0.6, 0.15, 0.25), folds=4):
    a, b = int(T * fracs[0]), int(T * (fracs[0] + fracs[1]))
    out = {"train": list(range(a)), "val": list(range(a, b)), "test": list(range(b, T)),
           "rolling": []}
    # rolling origin: train on [0, o), test on [o, o + h)
    h = (T - a) // folds
    for k in range(folds):
        o = a + k * h
        out["rolling"].append({"train_end": o, "test": [o, min(o + h, T)]})
    return out


def process(topo_name, seed=0):
    tfile, freq = RAW[topo_name]
    nodes, links = parse_topology((DATA_RAW / topo_name / tfile).read_text())
    topo = Topology(nodes, links, k_paths=4, name=topo_name)
    meta = {"topology": topo_name, "nodes": topo.N, "links_undirected": topo.L,
            "arcs": topo.A, "od_pairs": topo.OD, "paths": topo.P, "freq": freq}
    ts, tms = load_dynamic(topo_name, nodes)
    meta["dynamic_files"] = int(len(ts))
    if topo_name == "nobel":
        meta["source_span"] = [str(ts.min()), str(ts.max())]
        prof, sigma = abilene_profile_and_sigma()
        ts, tms, segment, stats = *semi_synthetic(tms, prof, sigma, seed=seed), None, None
        segment = np.zeros(len(ts), dtype=int)
        stats = {"semi_synthetic": True, "days": 30, "abilene_resid_sigma": sigma}
    else:
        ts, tms, segment, stats = regularise(ts, tms, freq)
    meta.update(stats)
    od = topo.tm_to_od(tms)
    split = chrono_splits(len(od), segment)
    # robust peak: 99.9th percentile, so a single anomalous hour does not set the scale
    peak = np.percentile(mlu(topo, all_on(topo).split, od[split["train"]]), PEAK_PCT)
    scale = TARGET_PEAK_MLU / peak
    od = (od * scale).astype(np.float32)
    meta.update({"T": int(len(od)), "start": str(ts[0]), "end": str(ts[-1]),
                 "scale_factor": float(scale), "unscaled_peak_mlu_train": float(peak),
                 "peak_mlu_test_after_scaling": float(
                     mlu(topo, all_on(topo).split, od[split["test"]]).max())})
    out = DATA_PROC / topo_name
    out.mkdir(parents=True, exist_ok=True)
    topo.save(out / "topology.json")
    np.save(out / "od.npy", od)
    np.save(out / "timestamps.npy", ts.to_numpy().astype("datetime64[m]"))
    np.save(out / "segment.npy", segment)
    (out / "splits.json").write_text(json.dumps(split))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topologies", nargs="+")
    a = ap.parse_args()
    for t in a.topologies:
        process(t)


if __name__ == "__main__":
    main()
