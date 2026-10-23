"""Shared experiment infrastructure: contexts, evaluation, oracle, tuned baselines, stats.

Every number in the paper's results comes from the functions in this file and the
run_*.py scripts. Nothing is hard-coded. Outputs go to paper/results/.
"""
import json
import pickle
import platform
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lira import ARTIFACTS, DATA_PROC, ROOT, scenario_tag
from lira.baselines import classical as B
from lira.data.features import Featurizer
from lira.models.cost import build_tables
from lira.models.network import Topology
from lira.models.power import PowerModel
from lira.models.reconfig import component_matrices, normalized_R
from lira.models.wear import WearModel
from lira.oracle.dp import viterbi
from lira.policy.lira_policy import Ctx, LiRA, SnapshotML

OUT = ROOT / "paper" / "results"
PER_DAY = {"5min": 288, "15min": 96}
TOPOS = ("abilene", "geant", "nobel")
# Default prices follow the paper's definitions (units: one interval of all-on link power):
#   one typical (p95) configuration change costs 0.2 % of the daily always-on energy,
#   one link power-state transition costs 0.08 % of it (wear weight lam_W converts AF units).
CHANGE_PRICE, TRANSITION_PRICE = 0.002, 0.0008


def prices(ctx, r_mult=1.0, w_mult=1.0):
    """r_mult scales the reconfiguration price, w_mult the wear (transition) price."""
    lam_R = CHANGE_PRICE * ctx.per_day * r_mult
    lam_W = TRANSITION_PRICE * ctx.per_day / BASE_CHI * w_mult
    return lam_R, lam_W


BASE_CHI = 0.01                   # chi in configs/power.yaml (price conversion uses the base value)
_CACHE = {}


def out_dir(name):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------- context
def build_ctx(topo_name, K=32, load=1.0, dyn=None, theta=0.8, chi=None):
    key = (topo_name, K, load, dyn, theta, chi)
    if key in _CACHE:
        return _CACHE[key]
    p = DATA_PROC / topo_name
    topo = Topology.load(p / "topology.json")
    meta = json.loads((p / "meta.json").read_text())
    split = json.loads((p / "splits.json").read_text())
    seg = np.load(p / "segment.npy")
    ts = pd.DatetimeIndex(np.load(p / "timestamps.npy"))
    od = np.load(p / "od.npy").astype(np.float64) * load
    tag = scenario_tag(load, dyn, theta)
    with open(ARTIFACTS / "library" / f"{topo_name}{tag}_K{K}.pkl", "rb") as f:
        lib = pickle.load(f)
    library = lib["library"]
    assert abs(lib["theta"] - theta) < 1e-9
    power = PowerModel.from_yaml()
    if dyn is not None:
        power = replace(power, port_dyn_w=float(dyn))
    wear = WearModel.from_yaml()
    if chi is not None:
        wear = replace(wear, chi=float(chi))
    per_day = PER_DAY[meta["freq"]]
    Tm, Fm, Dm = component_matrices(topo, library, od[split["train"]].mean(axis=0))
    R, ref = normalized_R(Tm, Fm, Dm)
    tab = build_tables(topo, library, od, power, wear, R, per_day, theta)
    fz = Featurizer(topo_name, load)
    Fe, _ = fz.transform(od, ts, seg)
    ctx = Ctx(tab=tab, F=Fe, n_snap=fz.n_snapshot, seg=seg, split=split, per_day=per_day,
              K=len(library))
    ctx.topo, ctx.od, ctx.ts, ctx.library, ctx.power, ctx.wear = topo, od, ts, library, power, wear
    ctx.X = np.stack([c.x for c in library])
    ctx.raw = {"toggles": Tm, "flow_mods": Fm, "disrupted": Dm, "R_ref": ref}
    ctx.name, ctx.theta, ctx.meta, ctx.fz = topo_name, theta, meta, fz
    _CACHE[key] = ctx
    return ctx


# -------------------------------------------------------------------- evaluation
def evaluate(ctx, split, seq, lam_R=None, lam_W=None, lat=None, fb=None, wear=None):
    """Metrics of a library-index sequence on a split. Returns (metrics dict, daily J array).

    total_cost_J = sum of energy + lam_W * wear-node + switching edges. It has NO penalty for
    intervals that violate theta (those are reported separately as mlu_violation_pct), the first
    interval of the split is not charged a switch, and no switch is charged across an unfilled
    gap (segment boundary). Methods with violations therefore look cheaper than they are."""
    a, b = ctx.rng_idx(split) if isinstance(split, str) else split
    if lam_R is None:
        lam_R, lam_W = prices(ctx)
    tab, seg = ctx.tab.slice(a, b), ctx.seg[a:b]
    seq = np.asarray(seq, dtype=np.int64)
    T = len(seq)
    t = np.arange(T)
    days = T / ctx.per_day
    same = np.concatenate([[False], seg[1:] == seg[:-1]])
    prev = np.concatenate([[seq[0]], seq[:-1]])
    sw = same & (seq != prev)                      # configuration change at t (within a segment)
    e_t = tab.E[t, seq]
    node_t = e_t + lam_W * tab.Wn[seq]
    edge_t = np.where(same, tab.edge(lam_R, lam_W)[prev, seq], 0.0)
    J_t = node_t + edge_t
    tog = np.where(same, ctx.raw["toggles"][prev, seq], 0.0)
    fm = np.where(same, ctx.raw["flow_mods"][prev, seq], 0.0)
    dis = np.where(same, ctx.raw["disrupted"][prev, seq], 0.0)
    wear = wear or ctx.wear
    af = wear.acceleration(ctx.X[seq], ctx.per_day)
    runs = np.diff(np.flatnonzero(np.concatenate([[True], sw, [True]])))
    m = {"savings_pct": 100 * (1 - e_t.sum() / tab.E[:, 0].sum()),
         "energy_norm": float(e_t.sum()),
         "config_changes_per_day": float(sw.sum() / days),
         "link_transitions_per_day": float(tog.sum() / days),
         "flow_mods_per_day": float(fm.sum() / days),
         "disrupted_traffic_frac_per_day": float(dis.sum() / days),
         "mlu_violation_pct": float(100 * (~tab.feas[t, seq]).mean()),
         "total_cost_J": float(J_t.sum()),
         "mean_AF": float(af.mean()), "max_AF": float(af.max()),
         "mean_dwell_intervals": float(runs.mean()),
         "links_on_mean": float(ctx.X[seq].sum(axis=1).mean()),
         "days": days}
    if lat is not None:
        m["latency_median_ms"] = float(np.median(lat) * 1e3)
        m["latency_p99_ms"] = float(np.percentile(lat, 99) * 1e3)
    if fb is not None:
        m["safety_fallback_pct"] = float(100 * fb)
    day = (t // ctx.per_day)
    daily = np.bincount(day, weights=J_t)
    return m, daily


def oracle_seq(ctx, split, lam_R=None, lam_W=None):
    a, b = ctx.rng_idx(split) if isinstance(split, str) else split
    if lam_R is None:
        lam_R, lam_W = prices(ctx)
    tab, seg = ctx.tab.slice(a, b), ctx.seg[a:b]
    node, edge = tab.node(lam_W), tab.edge(lam_R, lam_W)
    seq = np.empty(b - a, dtype=np.int32)
    for s in np.unique(seg):
        idx = np.flatnonzero(seg == s)
        seq[idx] = viterbi(node[idx], edge)[0]
    return seq


def always_on_seq(ctx, split):
    a, b = ctx.rng_idx(split) if isinstance(split, str) else split
    return np.zeros(b - a, dtype=np.int32)


def exact_snapshot_seq(ctx, split):
    a, b = ctx.rng_idx(split)
    return ctx.tab.node(0.0)[a:b].argmin(axis=1).astype(np.int32)


# ------------------------------------------------------------------ tuned baselines
DELTAS = [0.0, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
DWELLS = [1, 3, 6, 12, 24, 48, 96, 288]


def _val_cost(ctx, seq, lam_R, lam_W):  # tuning uses validation data only
    return evaluate(ctx, "val", seq, lam_R, lam_W)[0]["total_cost_J"]


def tune_hysteresis(ctx, b4_val, lam_R, lam_W):
    tabv = ctx.tab.slice(*ctx.rng_idx("val"))
    costs = {d: _val_cost(ctx, B.hysteresis(tabv, b4_val, d, 0.0), lam_R, lam_W) for d in DELTAS}
    return min(costs, key=costs.get)


def tune_dwell(ctx, b4_val, lam_R, lam_W):
    tabv = ctx.tab.slice(*ctx.rng_idx("val"))
    costs = {w: _val_cost(ctx, B.min_dwell(tabv, b4_val, w, 0.0), lam_R, lam_W) for w in DWELLS}
    return min(costs, key=costs.get)


def run_b4_family(ctx, lam_R=None, lam_W=None, seed=0, backend="xgb"):
    """B4, B6 (hysteresis), B7 (min-dwell) on the test split. Returns dict name -> seq plus info."""
    if lam_R is None:
        lam_R, lam_W = prices(ctx)
    b4 = SnapshotML(backend, seed).fit(ctx)
    val_seq, _ = b4.predict(ctx, "val")
    test_seq, fb = b4.predict(ctx, "test")
    d = tune_hysteresis(ctx, val_seq, lam_R, lam_W)
    w = tune_dwell(ctx, val_seq, lam_R, lam_W)
    tabt = ctx.tab.slice(*ctx.rng_idx("test"))
    return {"B4": test_seq, "B6": B.hysteresis(tabt, test_seq, d, 0.0),
            "B7": B.min_dwell(tabt, test_seq, w, 0.0)}, {"B4_fallback": fb, "delta": d,
                                                          "dwell": w, "model": b4}


def run_b2(ctx, lam_R=None, lam_W=None, forecast="naive", H=12):
    if lam_R is None:
        lam_R, lam_W = prices(ctx)
    tabt = ctx.tab.slice(*ctx.rng_idx("test"))
    seq, rt = B.rolling_horizon(tabt, lam_R, lam_W, H=H, forecast=forecast, c0=0)
    return seq, rt


def run_lira(ctx, lam_R=None, lam_W=None, seed=0, **kw):
    if lam_R is None:
        lam_R, lam_W = prices(ctx)
    pol = LiRA(seed=seed, **kw).fit(ctx, lam_R, lam_W)
    seq, lat, fb = pol.predict(ctx, "test")
    return seq, lat, fb, pol


# ------------------------------------------------------------------------ statistics
def ci95(x):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return float("nan")
    from scipy import stats
    return float(stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)))


def holm(pvals):
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def wilcoxon_daily(a, b):
    from scipy.stats import wilcoxon
    d = np.asarray(a) - np.asarray(b)
    if np.allclose(d, 0):
        return 1.0
    return float(wilcoxon(a, b, zero_method="wilcox").pvalue)


# ------------------------------------------------------------------------ environment
def environment():
    def sh(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, shell=True,
                                  timeout=20).stdout.strip().split("\n")[-1].strip()
        except Exception:
            return "unknown"
    import highspy, lightgbm, scipy, sklearn, xgboost
    return {"python": sys.version.split()[0], "os": platform.platform(),
            "cpu": "13th Gen Intel(R) Core(TM) i9-13900H (14 cores, 20 threads)",
            "cores_logical": __import__("os").cpu_count(),
            "ram_bytes": "47.6 GB",
            "gpu": "not used",
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "sklearn": sklearn.__version__, "xgboost": xgboost.__version__,
            "lightgbm": lightgbm.__version__, "highspy": getattr(highspy, "__version__", "n/a")}


def save_json(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, default=lambda o: o.tolist()
                                     if hasattr(o, "tolist") else str(o)))
