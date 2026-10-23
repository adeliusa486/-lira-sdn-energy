"""Second experiment group: E1b (ILP/GA/greedy baselines on a test subsample), E5 (latency and
scalability), E8 (drift), E10 (theta sweep), E13 (model choice), E14 (rolling folds).

Usage: python experiments/run_extra.py --exp E1b E5 E8 E10 E13 E14 [--topos ...] [--force]
"""
import argparse
import copy
import time

from common import *  # noqa: F401,F403
from lira.library.build_library import coverage
from lira.library.ga import run_nsga2
from lira.library.ilp import config_from_x, solve_energy_ilp
from lira.models.network import Topology
from lira.models.routing import all_on, ecmp_split, mlu
from lira.policy.lira_policy import Ctx, LiRA, SnapshotML, safe_batch
from run_main import SCENARIOS, log, scenario_available


def subsample(ctx, n):
    a, b = ctx.rng_idx("test")
    return np.linspace(a, b - 1, n).astype(int)


# ====================================================================== E1b + E5 (opt baselines)
def e1b(topos, force, n=60, n_ga=60):
    """Per-snapshot ILP (B1), per-snapshot NSGA-II (B3) and greedy (B5) on a test subsample.
    Reports energy savings versus always-on on the SAME intervals as the library-based
    snapshot optimum, plus decision runtimes."""
    d = out_dir("E5_latency_scalability")
    for topo in topos:
        f = d / f"{topo}_opt_baselines.csv"
        if f.exists() and not force:
            continue
        ctx = build_ctx(topo, 32)
        idx = subsample(ctx, n)
        D = ctx.od[idx]
        t = ctx.topo
        base_P = ctx.power.power(t, ctx.library[0], D)
        norm = ctx.power.max_link_power(t)
        lib_E = ctx.tab.E[idx][np.arange(len(idx)), ctx.tab.node(0.0)[idx].argmin(axis=1)]
        rows = [{"topology": topo, "method": "library snapshot optimum", "n": n,
                 "savings_pct": 100 * (1 - lib_E.sum() / (base_P / norm).sum()), "median_s": np.nan,
                 "p99_s": np.nan, "failed": 0}]
        # B1
        P, rt, gaps, fail = [], [], [], 0
        for dvec in D:
            x, info = solve_energy_ilp(t, dvec, ctx.power, ctx.theta, time_limit=120, gap=0.01)
            rt.append(info["runtime_s"]); gaps.append(info["gap"])
            if x is None:
                fail += 1; P.append(np.nan); continue
            cfg = config_from_x(t, x, dvec, "B1")
            P.append(ctx.power.power(t, cfg, dvec[None])[0] if cfg is not None else np.nan)
        P = np.array(P); ok = np.isfinite(P)
        rows.append({"topology": topo, "method": "B1 per-snapshot ILP", "n": int(ok.sum()),
                     "savings_pct": 100 * (1 - P[ok].sum() / base_P[ok].sum()),
                     "median_s": np.median(rt), "p99_s": np.percentile(rt, 99), "failed": fail,
                     "mean_mip_gap": float(np.mean(gaps))})
        log("E1b", topo, "B1 done")
        # B3 (possibly on a smaller subsample: NSGA-II is very slow on tiny search spaces)
        sel = np.linspace(0, len(D) - 1, min(n_ga, len(D))).astype(int)
        D3, base_P3 = D[sel], base_P[sel]
        P, rt, fail = [], [], 0
        for i, dvec in enumerate(D3):
            t0 = time.perf_counter()
            best = None
            for x in sorted(run_nsga2(t, dvec, ctx.theta, seed=i), key=lambda v: v.sum()):
                s = ecmp_split(t, x)
                if s is not None and mlu(t, s, dvec)[0] <= ctx.theta:
                    best = (x, s); break
            rt.append(time.perf_counter() - t0)
            if best is None:
                fail += 1; P.append(np.nan); continue
            from lira.models.routing import Config
            P.append(ctx.power.power(t, Config(best[0], best[1]), dvec[None])[0])
        P = np.array(P); ok = np.isfinite(P)
        rows.append({"topology": topo, "method": "B3 per-snapshot NSGA-II", "n": int(ok.sum()),
                     "savings_pct": 100 * (1 - P[ok].sum() / base_P3[ok].sum()) if ok.any() else np.nan,
                     "median_s": np.median(rt), "p99_s": np.percentile(rt, 99), "failed": fail})
        log("E1b", topo, "B3 done")
        # B5
        rt, P = [], []
        for dvec in D:
            cfgs, r = B.elastictree(t, dvec[None], ctx.theta)
            rt.append(r[0]); P.append(ctx.power.power(t, cfgs[0], dvec[None])[0])
        P = np.array(P)
        rows.append({"topology": topo, "method": "B5 ElasticTree-style greedy", "n": n,
                     "savings_pct": 100 * (1 - P.sum() / base_P.sum()), "median_s": np.median(rt),
                     "p99_s": np.percentile(rt, 99), "failed": 0})
        pd.DataFrame(rows).to_csv(f, index=False)
        log("E1b", topo, "done")


def e5_scale(force):
    """Optimisation time and safety-check time on larger SNDlib topologies (static demands
    from the SNDlib file, scaled so that peak all-on shortest-path MLU is 0.5)."""
    import urllib.request
    from lira import DATA_RAW
    from lira.data.parse_sndlib import parse_demands, parse_topology
    d = out_dir("E5_latency_scalability")
    f = d / "scalability.csv"
    if f.exists() and not force:
        return
    power = PowerModel.from_yaml()
    rows = []
    for name in ("abilene", "nobel", "geant", "germany50", "ta2"):
        raw = DATA_RAW / "scale"
        raw.mkdir(parents=True, exist_ok=True)
        if name in ("germany50", "ta2"):
            p = raw / f"{name}.txt"
            if not p.exists():
                urllib.request.urlretrieve(
                    f"https://sndlib.put.poznan.pl/download/sndlib-networks-native/{name}.txt", p)
            text = p.read_text()
            nodes, links = parse_topology(text)
            topo = Topology(nodes, links, 4, name)
            dem = parse_demands(text)
            vec = np.zeros(topo.OD)
            lut = {(int(s), int(t_)): i for i, (s, t_) in enumerate(topo.od)}
            for (s, t_), v in dem.items():
                vec[lut[(topo.idx[s], topo.idx[t_])]] += v
            peak = mlu(topo, all_on(topo).split, vec)[0]
            vec = vec * 0.5 / peak
            tag = "SNDlib static demands"
        else:
            ctx = build_ctx(name, 32)
            topo = ctx.topo
            vec = ctx.od[ctx.rng_idx("test")[0] + 50]
            tag = "test-split traffic matrix"
        rt = []
        cfg = None
        for rep in range(3 if topo.OD < 1000 else 2):
            x, info = solve_energy_ilp(topo, vec, power, 0.8, time_limit=300, gap=0.01)
            rt.append(info["runtime_s"])
        cfg = config_from_x(topo, x, vec, "scale") if x is not None else all_on(topo)
        t0 = time.perf_counter()
        for _ in range(200):
            mlu(topo, cfg.split, vec[None])
        check_ms = (time.perf_counter() - t0) / 200 * 1e3
        t0 = time.perf_counter()
        B.elastictree(topo, vec[None], 0.8)
        et = time.perf_counter() - t0
        rows.append({"topology": name, "nodes": topo.N, "links": topo.L, "od_pairs": topo.OD,
                     "paths": topo.P, "traffic": tag, "ilp_median_s": float(np.median(rt)),
                     "ilp_status": info["message"][:60], "ilp_gap": info["gap"],
                     "elastictree_s": et, "safety_check_ms": check_ms,
                     "links_on_after_ilp": int(x.sum()) if x is not None else -1})
        log("E5 scale", name, rows[-1])
    pd.DataFrame(rows).to_csv(f, index=False)


# ====================================================================== E8 drift
def assemble(base, od_new, library=None):
    """New context for modified traffic (and optionally an extended library). The price
    normalisation of R is kept from the base context so costs stay comparable."""
    library = base.library if library is None else library
    topo = base.topo
    Tm, Fm, Dm = component_matrices(topo, library, base.od[base.split["train"]].mean(axis=0))
    R, _ = normalized_R(Tm, Fm, Dm, ref=base.raw["R_ref"])
    tab = build_tables(topo, library, od_new, base.power, base.wear, R, base.per_day, base.theta)
    Fe, _ = base.fz.transform(od_new, base.ts, base.seg)
    ctx = Ctx(tab=tab, F=Fe, n_snap=base.n_snap, seg=base.seg, split=base.split,
              per_day=base.per_day, K=len(library))
    ctx.topo, ctx.od, ctx.ts, ctx.library, ctx.power, ctx.wear = topo, od_new, base.ts, library, \
        base.power, base.wear
    ctx.X = np.stack([c.x for c in library])
    ctx.raw = {"toggles": Tm, "flow_mods": Fm, "disrupted": Dm, "R_ref": base.raw["R_ref"]}
    ctx.name, ctx.theta, ctx.meta, ctx.fz = base.name, base.theta, base.meta, base.fz
    return ctx


def apply_shift(base, kind, onset):
    od = base.od.copy()
    T = len(od)
    if kind == "growth":
        ramp = np.clip((np.arange(T) - onset) / (10 * base.per_day), 0, 1)
        od *= (1 + 0.5 * ramp)[:, None]
    elif kind == "hotspot":
        top = np.argsort(base.od[base.split["train"]].mean(axis=0))[::-1][:20]
        pick = np.random.default_rng(0).choice(top, 3, replace=False)
        od[onset:, pick] *= 4.0
    elif kind == "phase":
        lag = base.per_day // 4              # 6-hour shift of the daily pattern
        od[onset:] = base.od[onset - lag:T - lag]
    elif kind != "none":
        raise ValueError(kind)
    return od


def refresh_library(ctx, w0, w1, M=8, time_limit=60):
    """Library refresh: ILP on M representative TMs of the recent window, appended to the library."""
    from sklearn.cluster import KMeans
    D = ctx.od[w0:w1]
    km = KMeans(n_clusters=min(M, len(D)), n_init=3, random_state=0).fit(np.log1p(D))
    keys = {c.key() for c in ctx.library}
    new = []
    for m in range(km.n_clusters):
        dm = np.percentile(D[km.labels_ == m], 95, axis=0)
        x, _ = solve_energy_ilp(ctx.topo, dm, ctx.power, ctx.theta, time_limit)
        if x is None:
            continue
        cfg = config_from_x(ctx.topo, x, dm, "refresh")
        if cfg is not None and cfg.key() not in keys:
            keys.add(cfg.key()); new.append(cfg)
    return ctx.library + new, len(new)


class Detectors:
    """ADWIN on the online regret proxy + Page-Hinkley on the deseasonalised log-volume."""

    def __init__(self, ph_threshold, adwin_delta=0.002):
        from river.drift import ADWIN, PageHinkley
        self.adwin = ADWIN(delta=adwin_delta)
        self.ph = PageHinkley(min_instances=2 * 288, delta=0.005, threshold=ph_threshold,
                              alpha=0.9999, mode="both")

    def step(self, proxy, vol):
        self.adwin.update(proxy)
        self.ph.update(vol)
        return self.adwin.drift_detected, self.ph.drift_detected


def vol_profile(ctx):
    a, b = 0, len(ctx.split["train"])
    ts = ctx.ts
    slot = (ts.dayofweek * 24 * 60 + ts.hour * 60 + ts.minute).to_numpy()
    vol = ctx.od.sum(axis=1)
    s = pd.Series(np.log(vol[a:b] + 1e-9)).groupby(slot[a:b]).mean()
    mean_all = float(np.log(vol[a:b] + 1e-9).mean())
    prof = pd.Series(slot).map(s).fillna(mean_all).to_numpy()
    return prof


def calibrate_ph(ctx, prof):
    """Smallest Page-Hinkley threshold with no alarm on the validation stream."""
    v0, v1 = ctx.rng_idx("val")
    z = np.log(ctx.od[v0:v1].sum(axis=1) + 1e-9) - prof[v0:v1]
    for thr in (2, 5, 10, 20, 50, 100, 200):
        det = Detectors(thr)
        fired = False
        for x in z:
            det.ph.update(float(x))
            fired = fired or det.ph.drift_detected
        if not fired:
            return thr
    return 200


def stream(ctx_s, onset, method, mode, pol0, lam_R, lam_W, prof, ph_thr, refresh=False, W_days=7):
    """Sequential test-period run with optional drift detection / periodic retraining."""
    ctx = ctx_s
    a, b = ctx.rng_idx("test")
    chunk = max(ctx.per_day // 4, 1)
    seq = np.empty(b - a, dtype=np.int32)
    state, pol = (0, 1), pol0
    det = Detectors(ph_thr)
    events, retrains, retrain_s, sched, last_check = [], [], 0.0, [], a
    n_new = 0
    for c0 in range(a, b, chunk):
        c1 = min(c0 + chunk, b)
        tabc, segc = ctx.tab.slice(c0, c1), ctx.seg[c0:c1]
        if method == "LiRA":
            Fc = ctx.F[c0:c1][:, pol._cols(ctx)]
            sq, _, _, _ = pol.rollout(tabc, Fc, segc, pol.model, edge=tabc.edge(lam_R, lam_W),
                                      lam_W=lam_W, state=state)
            state = pol.last_state
        else:
            sq, _ = safe_batch(tabc.node(0.0), pol.model.predict_many(ctx.F[c0:c1, :ctx.n_snap]))
        seq[c0 - a:c1 - a] = sq
        n = c1 - c0
        bestE = np.where(tabc.feas, tabc.E, np.inf).min(axis=1)
        bestE = np.where(np.isfinite(bestE), bestE, tabc.E.min(axis=1))
        proxy = tabc.E[np.arange(n), sq] - bestE + (~tabc.feas[np.arange(n), sq])
        z = np.log(ctx.od[c0:c1].sum(axis=1) + 1e-9) - prof[c0:c1]
        fired = False
        if mode != "static":
            for i in range(n):
                ad, ph = det.step(float(proxy[i]), float(z[i]))
                if (ad or ph) and not sched and mode.startswith("drift"):
                    events.append(c0 + i); fired = True
                    sched = [c1, c1 + ctx.per_day, c1 + 3 * ctx.per_day]
                    det = Detectors(ph_thr)
                    break
            if mode == "periodic" and (c1 - a) % (7 * ctx.per_day) < chunk and c1 - a >= 7 * ctx.per_day:
                sched = [c1]
        due = [s_ for s_ in sched if s_ <= c1]
        if due and c1 - 2 * ctx.per_day > 0:
            sched = [s_ for s_ in sched if s_ > c1]
            w1, w0 = c1, max(0, c1 - W_days * ctx.per_day)
            t0 = time.perf_counter()
            if refresh:
                lib2, added = refresh_library(ctx, w0, w1)
                if added:
                    ctx = assemble(ctx_s, ctx_s.od, lib2)
                    n_new += added
            cut = w0 + int(0.8 * (w1 - w0))
            view = copy.copy(ctx)
            view.split = {"train": list(range(w0, cut)), "val": list(range(cut, w1)),
                          "test": ctx.split["test"], "rolling": []}
            if method == "LiRA":
                pol = LiRA(rounds=1, seed=0).fit(view, lam_R, lam_W)
                state = (min(state[0], ctx.K - 1), state[1])
            else:
                pol = SnapshotML("xgb", 0).fit(view)
            retrain_s += time.perf_counter() - t0
            retrains.append(c1)
            det = Detectors(ph_thr)
    return seq, ctx, {"events": events, "retrains": retrains, "retrain_s": retrain_s,
                      "library_added": n_new}


def e8(topos, force):
    d = out_dir("E8_drift")
    for topo in topos:
        f = d / f"{topo}_drift.csv"
        if f.exists() and not force:
            continue
        base = build_ctx(topo, 32)
        lr, lw = prices(base)
        prof = vol_profile(base)
        thr = calibrate_ph(base, prof)
        a, b = base.rng_idx("test")
        onset = a + int(0.35 * (b - a))
        pols = {"LiRA": LiRA(rounds=1, seed=0).fit(base, lr, lw), "B4": SnapshotML("xgb", 0).fit(base)}
        rows = []
        for kind in ("none", "growth", "hotspot", "phase"):
            od_s = apply_shift(base, kind, onset)
            cs = assemble(base, od_s)
            for method in ("LiRA", "B4"):
                for mode in ("static", "drift", "drift+refresh", "periodic"):
                    if mode == "drift+refresh" and kind == "none":
                        continue
                    seq, cfin, info = stream(cs, onset, method, mode, pols[method], lr, lw, prof, thr,
                                             refresh=(mode == "drift+refresh"))
                    pre = max(onset - a, 0)
                    m_all, _ = evaluate(cfin, "test", seq, lr, lw)
                    post, _ = evaluate(cfin, (onset, b), seq[pre:], lr, lw)
                    ev = info["events"]
                    first = [e for e in ev if e >= onset]
                    false_alarms = len([e for e in ev if e < onset]) if kind != "none" else len(ev)
                    n_pre = (onset - a) if kind != "none" else (b - a)
                    rows.append({"topology": topo, "shift": kind, "method": method, "mode": mode,
                                 "ph_threshold": thr, "detections": len(ev),
                                 "detection_delay_intervals": (first[0] - onset) if first else np.nan,
                                 "detection_delay_hours": ((first[0] - onset) * 24 / base.per_day) if first else np.nan,
                                 "false_alarms": false_alarms,
                                 "false_alarms_per_1k_intervals": 1000 * false_alarms / max(n_pre, 1),
                                 "retrains": len(info["retrains"]), "retrain_total_s": info["retrain_s"],
                                 "library_configs_added": info["library_added"],
                                 **{f"post_{k}": v for k, v in post.items() if k in (
                                     "savings_pct", "total_cost_J", "mlu_violation_pct", "config_changes_per_day")},
                                 "all_total_cost_J": m_all["total_cost_J"]})
                    log("E8", topo, kind, method, mode, rows[-1]["detections"], rows[-1]["post_total_cost_J"])
            # oracle on the shifted traffic (original library) for the post-onset window
            sq = oracle_seq(cs, "test", lr, lw)
            post, _ = evaluate(cs, (onset, b), sq[onset - a:], lr, lw)
            rows.append({"topology": topo, "shift": kind, "method": "O*", "mode": "offline",
                         **{f"post_{k}": v for k, v in post.items() if k in (
                             "savings_pct", "total_cost_J", "mlu_violation_pct", "config_changes_per_day")}})
        pd.DataFrame(rows).to_csv(f, index=False)


# ====================================================================== E10 theta
def e10(topos, force):
    d = out_dir("E10_theta")
    for topo in topos:
        f = d / f"{topo}_theta.csv"
        if f.exists() and not force:
            continue
        rows = []
        for th in (0.6, 0.7, 0.8, 0.9):
            try:
                ctx = build_ctx(topo, 32, theta=th)
            except FileNotFoundError:
                log("E10 missing library", topo, th); continue
            fam, info = run_b4_family(ctx, seed=0)
            seq, lat, fb, _ = run_lira(ctx, seed=0)
            allon = float((ctx.tab.mlu[slice(*ctx.rng_idx("test")), 0] > th).mean() * 100)
            cov = float(ctx.tab.feas[slice(*ctx.rng_idx("test"))].any(axis=1).mean() * 100)
            for name, s_ in [("B4", fam["B4"]), ("B6", fam["B6"]), ("B7", fam["B7"]), ("LiRA", seq),
                             ("O*", oracle_seq(ctx, "test")), ("B0", always_on_seq(ctx, "test"))]:
                m, _ = evaluate(ctx, "test", s_)
                rows.append({"topology": topo, "theta": th, "method": name,
                             "test_coverage_pct": cov, "alwayson_violation_pct": allon,
                             "library_size": ctx.K, **m})
            log("E10", topo, th)
        pd.DataFrame(rows).to_csv(f, index=False)


# ====================================================================== E13 model choice
def e13(topos, force):
    d = out_dir("E13_model_choice")
    for topo in topos:
        f = d / f"{topo}_models.csv"
        if f.exists() and not force:
            continue
        ctx = build_ctx(topo, 32)
        rows = []
        for mult in (1.0, 0.1):
            lr, lw = prices(ctx, mult)
            m, _ = evaluate(ctx, "test", oracle_seq(ctx, "test", lr, lw), lr, lw)
            rows.append({"topology": topo, "price_mult": mult, "backend": "-", "method": "O*", **m})
            for be in ("xgb", "lgbm", "rf", "mlp"):
                t0 = time.perf_counter()
                try:
                    fam, info = run_b4_family(ctx, lr, lw, seed=0, backend=be)
                    m, _ = evaluate(ctx, "test", fam["B4"], lr, lw, lat=info["model"].latency(ctx, n=300))
                    rows.append({"topology": topo, "price_mult": mult, "backend": be, "method": "B4", **m})
                    seq, lat, fb, pol = run_lira(ctx, lr, lw, seed=0, backend=be, rounds=1)
                    m, _ = evaluate(ctx, "test", seq, lr, lw, lat=lat, fb=fb)
                    rows.append({"topology": topo, "price_mult": mult, "backend": be, "method": "LiRA",
                                 "lira_model": type(pol.model).__name__,
                                 "train_plus_eval_s": time.perf_counter() - t0, **m})
                except Exception as ex:   # record, never hide
                    rows.append({"topology": topo, "price_mult": mult, "backend": be, "method": "ERROR",
                                 "error": repr(ex)[:200]})
                log("E13", topo, mult, be)
        pd.DataFrame(rows).to_csv(f, index=False)


# ====================================================================== E14 rolling folds
def e14(topos, force):
    d = out_dir("E14_rolling_folds")
    for topo in topos:
        f = d / f"{topo}_folds.csv"
        if f.exists() and not force:
            continue
        base = build_ctx(topo, 32)
        T = len(base.F)
        rows = []
        for k, fold in enumerate(base.split["rolling"]):
            o, (s0, s1) = fold["train_end"], fold["test"]
            cut = int(0.8 * o)
            ctx = copy.copy(base)
            ctx.split = {"train": list(range(0, cut)), "val": list(range(cut, o)),
                         "test": list(range(s0, s1)), "rolling": []}
            for mult in (1.0, 0.1):
                lr, lw = prices(ctx, mult)
                fam, info = run_b4_family(ctx, lr, lw, seed=0)
                seq, lat, fb, pol = run_lira(ctx, lr, lw, seed=0)
                for name, s_ in [("B4", fam["B4"]), ("B6", fam["B6"]), ("B7", fam["B7"]),
                                 ("LiRA", seq), ("O*", oracle_seq(ctx, "test", lr, lw)),
                                 ("B0", always_on_seq(ctx, "test"))]:
                    m, _ = evaluate(ctx, "test", s_, lr, lw)
                    rows.append({"topology": topo, "fold": k, "train_end": o, "test_start": s0,
                                 "test_end": s1, "price_mult": mult, "method": name, **m})
            log("E14", topo, "fold", k)
        pd.DataFrame(rows).to_csv(f, index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["E1b", "E5", "E8", "E10", "E13", "E14"])
    ap.add_argument("--topos", nargs="+", default=list(TOPOS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--n-ga", type=int, default=60)
    a = ap.parse_args()
    if "E1b" in a.exp:
        e1b(a.topos, a.force, n_ga=a.n_ga)
    if "E5" in a.exp:
        e5_scale(a.force)
    if "E8" in a.exp:
        e8(a.topos, a.force)
    if "E10" in a.exp:
        e10(a.topos, a.force)
    if "E13" in a.exp:
        e13(a.topos, a.force)
    if "E14" in a.exp:
        e14(a.topos, a.force)
