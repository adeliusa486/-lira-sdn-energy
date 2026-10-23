"""E16: decisions on a one-interval-old traffic matrix.

In E1 every controller configures interval t knowing D_t itself (the estimate equals the realized
matrix), and the safety layer checks theta on D_t. A real controller configures interval t from
the last completed measurement. Here every online method uses D_{t-1}: features F[t-1], the
safety check on MLU(c, D_{t-1}), hysteresis and dwell decisions on D_{t-1}, and the rolling
horizon B2 with D_{t-1} as its persistence forecast. Costs and violations are then measured on
the realized D_t. The same trained B4 and LiRA models are evaluated under both protocols
("current" = E1 protocol, "stale" = this experiment), so the comparison is paired.
B6/B7 thresholds are tuned on validation under the protocol being evaluated; tuning adds
1e3 per violated interval to J (the selection cost LiRA uses), because J itself has no penalty.
"-m" variants run the safety check against theta - MARGIN on D_{t-1}.

Output: paper/results/E16_stale_tm/<topo>_<scenario>_stale.csv
Usage:  python experiments/run_stale.py [--force]
"""
import argparse
import time

from common import *  # noqa: F401,F403
from lira.models.cost import CostTables
from lira.policy.lira_policy import safe_batch
from run_main import SCENARIOS, log

JOBS = [("abilene", "base"), ("abilene", "highload"), ("geant", "base"), ("geant", "highload"),
        ("nobel", "base"), ("nobel", "highload"), ("nobel", "stress")]
SEEDS = range(3)
MARGIN = 0.05


def info_tab(ctx, a, b, stale, margin=0.0):
    """Cost table the controller sees when it decides intervals [a, b)."""
    tab = ctx.tab.slice(a - 1, b - 1) if stale else ctx.tab.slice(a, b)
    if margin:
        tab = CostTables(tab.E, tab.mlu <= ctx.theta - margin + 1e-9, tab.mlu, tab.R, tab.Wn, tab.We)
    return tab


def info_F(ctx, a, b, stale):
    return ctx.F[a - 1:b - 1] if stale else ctx.F[a:b]


def sel_cost(ctx, split, seq, lr, lw):
    m, _ = evaluate(ctx, split, seq, lr, lw)
    a, b = ctx.rng_idx(split)
    return m["total_cost_J"] + 1e3 * (~ctx.tab.feas[np.arange(a, b), seq]).sum()


def b4_seq(ctx, model, split, stale, margin=0.0):
    a, b = ctx.rng_idx(split)
    pred = model.predict_many(info_F(ctx, a, b, stale)[:, :ctx.n_snap]).astype(np.int32)
    return safe_batch(info_tab(ctx, a, b, stale, margin).node(0.0), pred)[0]


def run(force):
    d = out_dir("E16_stale_tm")
    for topo, sc in JOBS:
        f = d / f"{topo}_{sc}_stale.csv"
        if f.exists() and not force:
            continue
        t0 = time.time()
        ctx = build_ctx(topo, 32, **SCENARIOS[sc])
        lr, lw = prices(ctx)
        a, b = ctx.rng_idx("test")
        rows = []

        def add(method, mode, seed, seq, **extra):
            m, _ = evaluate(ctx, "test", seq, lr, lw)
            rows.append({"topology": topo, "scenario": sc, "method": method, "mode": mode, "seed": seed,
                         **extra, **m})

        add("O*", "offline", 0, oracle_seq(ctx, "test"))
        add("B0", "any", 0, always_on_seq(ctx, "test"))
        for mode, stale in (("current", False), ("stale", True)):
            seq, _ = B.rolling_horizon(info_tab(ctx, a, b, stale), lr, lw, H=12, forecast="naive", c0=0)
            add("B2-naive", mode, 0, seq)
        for s in SEEDS:
            b4 = SnapshotML("xgb", s).fit(ctx)
            pol = LiRA(seed=s).fit(ctx, lr, lw)
            for mode, stale in (("current", False), ("stale", True)):
                for mg, suffix in ((0.0, ""), (MARGIN, "-m")):
                    if mode == "current" and mg:
                        continue
                    v0, v1 = ctx.rng_idx("val")
                    val4, test4 = b4_seq(ctx, b4.model, "val", stale, mg), b4_seq(ctx, b4.model, "test", stale, mg)
                    tv, tt = info_tab(ctx, v0, v1, stale, mg), info_tab(ctx, a, b, stale, mg)
                    dl = min(DELTAS, key=lambda x: sel_cost(ctx, "val", B.hysteresis(tv, val4, x, 0.0), lr, lw))
                    dw = min(DWELLS, key=lambda x: sel_cost(ctx, "val", B.min_dwell(tv, val4, x, 0.0), lr, lw))
                    add("B4" + suffix, mode, s, test4)
                    add("B6" + suffix, mode, s, B.hysteresis(tt, test4, dl, 0.0), delta=dl)
                    add("B7" + suffix, mode, s, B.min_dwell(tt, test4, dw, 0.0), dwell=dw)
                    seq, _, fb = pol.predict(ctx, "test", tab=tt, F=info_F(ctx, a, b, stale), seg=ctx.seg[a:b])
                    add("LiRA" + suffix, mode, s, seq, fallback_pct=100 * fb)
            log("E16", topo, sc, "seed", s)
        pd.DataFrame(rows).to_csv(f, index=False)
        log("E16", topo, sc, f"finished in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    run(ap.parse_args().force)
