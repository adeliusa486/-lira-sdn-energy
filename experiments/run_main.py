"""Main experiment campaign: E1 (main comparison), E2 (Pareto), E3/E4 (case study, wear),
E6 (library size), E7 (ablation), E9 (wear sensitivity), E12 (gap to oracle).

Usage:  python experiments/run_main.py --exp E1 E2 ... [--topos abilene geant nobel] [--force]
Outputs: results/<exp>/*.csv|json|npz   (a finished experiment is skipped unless --force)
"""
import argparse
import time
from pathlib import Path

from common import *  # noqa: F401,F403
from lira import ARTIFACTS, scenario_tag

SCENARIOS = {"base": dict(load=1.0, dyn=None),            # peak MLU 0.5, 5 W dynamic port power
             "highload": dict(load=1.6, dyn=None),        # peak MLU 0.8
             "highdyn": dict(load=1.0, dyn=15),           # 15 W dynamic port power
             "stress": dict(load=1.6, dyn=15)}            # both
SEEDS = range(5)


def scenario_available(topo, name):
    kw = SCENARIOS[name]
    return (ARTIFACTS / "library" / f"{topo}{scenario_tag(kw['load'], kw['dyn'], 0.8)}_K32.pkl").exists()


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ============================================================================ E1
def e1(topos, force):
    d = out_dir("E1_main")
    for topo in topos:
        for sc in SCENARIOS:
            tag = f"{topo}_{sc}"
            if (d / f"{tag}_runs.csv").exists() and not force:
                continue
            if not scenario_available(topo, sc):
                log("E1 skip (library missing)", tag)
                continue
            t0 = time.time()
            ctx = build_ctx(topo, 32, **SCENARIOS[sc])
            lr, lw = prices(ctx)
            rows, seqs, daily, info = [], {}, {}, {"lam_R": lr, "lam_W": lw, "K": ctx.K,
                                                   "library_size": ctx.K, "runs": []}

            def add(method, seed, seq, **kw):
                m, dly = evaluate(ctx, "test", seq, **kw)
                rows.append({"topology": topo, "scenario": sc, "method": method, "seed": seed, **m})
                seqs[f"{method}_s{seed}"] = np.asarray(seq, dtype=np.int32)
                daily[f"{method}_s{seed}"] = dly

            add("B0", 0, always_on_seq(ctx, "test"))
            add("SNAP-exact", 0, exact_snapshot_seq(ctx, "test"))
            add("O*", 0, oracle_seq(ctx, "test"))
            for fc in ("naive", "perfect"):
                seq, rt = run_b2(ctx, forecast=fc)
                add(f"B2-{fc}", 0, seq, lat=rt)
            for s in SEEDS:
                fam, finfo = run_b4_family(ctx, seed=s)
                lat = finfo["model"].latency(ctx)
                add("B4", s, fam["B4"], lat=lat, fb=finfo["B4_fallback"])
                add("B6", s, fam["B6"], lat=lat)
                add("B7", s, fam["B7"], lat=lat)
                seq, lat, fb, pol = run_lira(ctx, seed=s)
                add("LiRA", s, seq, lat=lat, fb=fb)
                info["runs"].append({"seed": s, "delta": finfo["delta"], "dwell": finfo["dwell"],
                                     "lira_best_round": pol.best_round, "lira_log": pol.log,
                                     "lira_model": type(pol.model).__name__})
                log("E1", tag, "seed", s, "done")
            pd.DataFrame(rows).to_csv(d / f"{tag}_runs.csv", index=False)
            np.savez_compressed(d / f"{tag}_seqs.npz", **seqs)
            np.savez_compressed(d / f"{tag}_daily_J.npz", **daily)
            save_json(info, d / f"{tag}_info.json")
            log("E1", tag, f"finished in {time.time() - t0:.0f}s")


def e1_derived(topos):
    """E3 (case-study week), E4 (per-link transitions and wear), E9 (wear sensitivity),
    E12 (gap to oracle) are all computed from the saved E1 decision sequences (seed 0)."""
    d1 = OUT / "E1_main"
    d3, d4, d9, d12 = out_dir("E3_case_study"), out_dir("E4_per_link_wear"), \
        out_dir("E9_wear_sensitivity"), out_dir("E12_gap_to_oracle")
    for topo in topos:
        for sc in SCENARIOS:
            f = d1 / f"{topo}_{sc}_seqs.npz"
            if not f.exists():
                continue
            ctx = build_ctx(topo, 32, **SCENARIOS[sc])
            lr, lw = prices(ctx)
            z = np.load(f)
            methods = {"B4": "B4_s0", "B6": "B6_s0", "B7": "B7_s0", "LiRA": "LiRA_s0", "O*": "O*_s0"}
            a, b = ctx.rng_idx("test")
            seg = ctx.seg[a:b]
            # ---- E3: first test week + the week with the most B4 configuration changes
            n = 7 * ctx.per_day
            b4 = z["B4_s0"]
            ch = np.concatenate([[0], (b4[1:] != b4[:-1]) & (seg[1:] == seg[:-1])]).astype(int)
            wk = np.add.reduceat(ch, np.arange(0, len(ch), n))
            for wname, w0 in (("first", 0), ("busiest", int(np.argmax(wk)) * n)):
                sl = slice(w0, min(w0 + n, len(b4)))
                df = pd.DataFrame({"t": np.arange(sl.start, sl.stop),
                                   "timestamp": ctx.ts[a:b][sl],
                                   "volume_total_mbps": ctx.od[a:b][sl].sum(axis=1)})
                for m, key in methods.items():
                    s_ = z[key][sl]
                    df[f"{m}_config"] = s_
                    df[f"{m}_energy_norm"] = ctx.tab.E[a:b][sl][np.arange(len(s_)), s_]
                    x = ctx.X[s_]
                    df[f"{m}_transitions"] = np.concatenate([[0], np.abs(np.diff(x, axis=0)).sum(axis=1)])
                df.to_csv(d3 / f"{topo}_{sc}_{wname}_week.csv", index=False)
            # ---- E4: per-link transitions and acceleration factor
            rows = []
            for m, key in list(methods.items()) + [("B0", None)]:
                s_ = np.zeros(b - a, dtype=int) if key is None else z[key]
                x = ctx.X[s_]
                same = (seg[1:] == seg[:-1])[:, None]
                tr = (np.abs(np.diff(x, axis=0)) * same).sum(axis=0)
                af = ctx.wear.acceleration(x, ctx.per_day)
                days = len(s_) / ctx.per_day
                for l in range(ctx.topo.L):
                    rows.append({"topology": topo, "scenario": sc, "method": m, "link": l,
                                 "transitions_total": tr[l], "transitions_per_day": tr[l] / days,
                                 "AF": af[l], "lifetime_change_pct_vs_alwayson": 100 * (1 / af[l] - 1)})
            pd.DataFrame(rows).to_csv(d4 / f"{topo}_{sc}_per_link.csv", index=False)
            # ---- E9: wear-parameter sensitivity of the SAME decision sequences
            rows = []
            for chi in (0.0, 0.001, 0.003, 0.01, 0.03, 0.1):
                for af_off in (0.4, 0.5, 0.6, 0.8, 1.0):
                    w = replace(ctx.wear, chi=chi, af_off=af_off)
                    for m, key in list(methods.items()) + [("B0", None)]:
                        s_ = np.zeros(b - a, dtype=int) if key is None else z[key]
                        af = w.acceleration(ctx.X[s_], ctx.per_day)
                        rows.append({"topology": topo, "scenario": sc, "chi": chi, "af_off": af_off,
                                     "method": m, "mean_AF": af.mean(), "max_AF": af.max()})
            pd.DataFrame(rows).to_csv(d9 / f"{topo}_{sc}_sensitivity.csv", index=False)
            # ---- E12: regret of every saved sequence (B2, B4, B6, B7, LiRA, ...) to the library oracle
            rows = []
            oj = evaluate(ctx, "test", z["O*_s0"])[0]["total_cost_J"]
            for key in z.files:
                m = evaluate(ctx, "test", z[key])[0]
                rows.append({"topology": topo, "scenario": sc, "run": key, "J": m["total_cost_J"],
                             "regret_vs_oracle_pct": 100 * (m["total_cost_J"] / oj - 1),
                             "regret_abs": m["total_cost_J"] - oj})
            pd.DataFrame(rows).to_csv(d12 / f"{topo}_{sc}_regret.csv", index=False)
            log("derived E3/E4/E9/E12", topo, sc)


def e1_stats(topos):
    """Wilcoxon signed-rank on per-day cost (LiRA vs B4/B6/B7), Holm-corrected per topology."""
    rows = []
    d = OUT / "E1_main"
    for topo in topos:
        for sc in SCENARIOS:
            f = d / f"{topo}_{sc}_daily_J.npz"
            if not f.exists():
                continue
            z = np.load(f)
            mean = lambda m: np.mean([z[f"{m}_s{s}"] for s in SEEDS], axis=0)
            comps = [("B4", mean("B4")), ("B6", mean("B6")), ("B7", mean("B7"))]
            p = [wilcoxon_daily(mean("LiRA"), x) for _, x in comps]
            padj = holm(p)
            for (name, x), pv, pa in zip(comps, p, padj):
                diff = mean("LiRA") - x
                rows.append({"topology": topo, "scenario": sc, "comparison": f"LiRA vs {name}",
                             "days": len(diff), "mean_daily_J_diff": float(diff.mean()),
                             "p_raw": pv, "p_holm": pa, "lira_better_days_pct": float(100 * (diff < 0).mean())})
    pd.DataFrame(rows).to_csv(out_dir("E1_main") / "stats_wilcoxon_holm.csv", index=False)


# ============================================================================ E2
def e2(topos, force):
    d = out_dir("E2_pareto")
    mults = [0.0, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100]
    for topo in topos:
        for sc in SCENARIOS:
            f = d / f"{topo}_{sc}_pareto.csv"
            if f.exists() and not force:
                continue
            if not scenario_available(topo, sc):
                continue
            ctx = build_ctx(topo, 32, **SCENARIOS[sc])
            lr0, lw0 = prices(ctx)
            tabt = ctx.tab.slice(*ctx.rng_idx("test"))
            rows = []
            b4 = SnapshotML("xgb", 0).fit(ctx)
            b4_test, _ = b4.predict(ctx, "test")
            m, _ = evaluate(ctx, "test", b4_test, lr0, lw0)
            rows.append({"method": "B4", "param": "", **m})
            for dl in DELTAS:
                m, _ = evaluate(ctx, "test", B.hysteresis(tabt, b4_test, dl, 0.0), lr0, lw0)
                rows.append({"method": "B6", "param": dl, **m})
            for w in DWELLS:
                m, _ = evaluate(ctx, "test", B.min_dwell(tabt, b4_test, w, 0.0), lr0, lw0)
                rows.append({"method": "B7", "param": w, **m})
            for mult in mults:
                lr, lw = prices(ctx, mult)
                m, _ = evaluate(ctx, "test", oracle_seq(ctx, "test", lr, lw), lr, lw)
                rows.append({"method": "O*", "param": mult, **m})
                seq, lat, fb, pol = run_lira(ctx, lr, lw, seed=0)
                m, _ = evaluate(ctx, "test", seq, lr, lw, lat=lat, fb=fb)
                rows.append({"method": "LiRA", "param": mult, "lira_model": type(pol.model).__name__, **m})
                log("E2", topo, sc, "price x", mult)
            pd.DataFrame(rows).assign(topology=topo, scenario=sc).to_csv(f, index=False)


def e2b(topos, force):
    """Joint sweep: both lam_R and lam_W scaled by the same factor. Factor 0 is the pure
    snapshot problem (no switching or wear price), so the oracle then equals the snapshot rule."""
    d = out_dir("E2_pareto")
    for topo in topos:
        for sc in SCENARIOS:
            f = d / f"{topo}_{sc}_joint.csv"
            if (f.exists() and not force) or not scenario_available(topo, sc):
                continue
            ctx = build_ctx(topo, 32, **SCENARIOS[sc])
            rows = []
            for mult in (0.0, 0.01, 0.1, 1.0, 10.0):
                lr, lw = prices(ctx, mult, mult)
                for name, seq in (("O*", oracle_seq(ctx, "test", lr, lw)),
                                  ("SNAP-exact", exact_snapshot_seq(ctx, "test"))):
                    m, _ = evaluate(ctx, "test", seq, lr, lw)
                    rows.append({"method": name, "joint_mult": mult, **m})
                seq, lat, fb, pol = run_lira(ctx, lr, lw, seed=0)
                m, _ = evaluate(ctx, "test", seq, lr, lw, lat=lat, fb=fb)
                rows.append({"method": "LiRA", "joint_mult": mult, "lira_model": type(pol.model).__name__, **m})
                log("E2b", topo, sc, "joint price x", mult)
            pd.DataFrame(rows).assign(topology=topo, scenario=sc).to_csv(f, index=False)


# ============================================================================ E6
def e6(topos, force):
    d = out_dir("E6_library_size")
    for topo in topos:
        f = d / f"{topo}_K.csv"
        if f.exists() and not force:
            continue
        rows = []
        for K in (8, 16, 32, 64, 128):
            try:
                ctx = build_ctx(topo, K)
            except FileNotFoundError:
                continue
            lr, lw = prices(ctx)
            fam, info = run_b4_family(ctx, seed=0)
            rr = [("B4", fam["B4"]), ("B6", fam["B6"]), ("B7", fam["B7"]),
                  ("O*", oracle_seq(ctx, "test"))]
            seq, lat, fb, _ = run_lira(ctx, seed=0)
            rr.append(("LiRA", seq))
            cov = float(ctx.tab.feas[slice(*ctx.rng_idx("val"))].any(axis=1).mean())
            for name, s_ in rr:
                m, _ = evaluate(ctx, "test", s_)
                rows.append({"topology": topo, "K_requested": K, "K_actual": ctx.K,
                             "val_coverage": cov, "method": name, **m})
            log("E6", topo, "K", K)
        pd.DataFrame(rows).to_csv(f, index=False)


# ============================================================================ E7
ABLATIONS = {"full": {}, "no_lag_history": dict(use_lags=False), "no_prev_config": dict(use_prev=False),
             "no_cost_sensitive": dict(cost_sensitive=False), "no_dagger": dict(rounds=0),
             "no_safety": dict(safety=False)}


def e7(topos, force):
    d = out_dir("E7_ablation")
    for topo in topos:
        for sc in SCENARIOS:
            f = d / f"{topo}_{sc}_ablation.csv"
            if (f.exists() and not force) or not scenario_available(topo, sc):
                continue
            ctx = build_ctx(topo, 32, **SCENARIOS[sc])
            rows = []
            for mult in (1.0, 0.1):          # default lam_R and a 10x cheaper lam_R (lam_W unchanged)
                lr, lw = prices(ctx, mult)
                m, _ = evaluate(ctx, "test", oracle_seq(ctx, "test", lr, lw), lr, lw)
                rows.append({"topology": topo, "scenario": sc, "price_mult": mult, "variant": "O*", "seed": 0, **m})
                for name, kw in ABLATIONS.items():
                    for s in range(3):
                        seq, lat, fb, pol = run_lira(ctx, lr, lw, seed=s, **kw)
                        m, _ = evaluate(ctx, "test", seq, lr, lw, lat=lat, fb=fb)
                        rows.append({"topology": topo, "scenario": sc, "price_mult": mult, "variant": name,
                                     "seed": s, "lira_model": type(pol.model).__name__, **m})
                log("E7", topo, sc, "price", mult)
            pd.DataFrame(rows).to_csv(f, index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["E1", "E2", "E6", "E7"])
    ap.add_argument("--topos", nargs="+", default=list(TOPOS))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    save_json(environment(), OUT / "environment.json")
    if "E1" in a.exp:
        e1(a.topos, a.force)
        e1_derived(a.topos)
        e1_stats(a.topos)
    if "E2" in a.exp:
        e2(a.topos, a.force)
    if "E2b" in a.exp:
        e2b(a.topos, a.force)
    if "E6" in a.exp:
        e6(a.topos, a.force)
    if "E7" in a.exp:
        e7(a.topos, a.force)
