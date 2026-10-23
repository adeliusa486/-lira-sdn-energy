"""E17: the simplest sequence-aware rule, without learning.

"Static + fallback" holds one configuration, the one the oracle uses most often on the training
split, and applies LiRA's safety layer: whenever that configuration violates theta on the traffic
the controller sees, it takes the switching-aware fallback of Eq. (fallback), and it returns to
the static configuration as soon as that is feasible again. This is LiRA with its classifier
replaced by a constant, so it shows how much of LiRA's behaviour comes from learning.
Both information protocols of E16 are evaluated: "current" (decide with D_t) and "stale"
(decide with D_{t-1}), with and without the safety margin.

Output: paper/results/E17_static_fallback/static_fallback.csv
Usage:  python experiments/run_static.py [--force]
"""
import argparse
from collections import Counter

from common import *  # noqa: F401,F403
from lira.policy.models import ConstantModel
from run_main import SCENARIOS, log
from run_stale import MARGIN, info_F, info_tab

TOPO_SC = [(t, s) for t in TOPOS for s in SCENARIOS]


def static_config(ctx, lr, lw):
    """Most frequent oracle configuration on the training split (what a constant LiRA learns)."""
    seq = oracle_seq(ctx, "train", lr, lw)
    return Counter(seq.tolist()).most_common(1)[0][0]


def run(force):
    d = out_dir("E17_static_fallback")
    f = d / "static_fallback.csv"
    if f.exists() and not force:
        return
    rows = []
    for topo, sc in TOPO_SC:
        ctx = build_ctx(topo, 32, **SCENARIOS[sc])
        lr, lw = prices(ctx)
        a, b = ctx.rng_idx("test")
        c = static_config(ctx, lr, lw)
        pol = LiRA()
        pol.K, pol.lam_R, pol.lam_W, pol.model = ctx.K, lr, lw, ConstantModel(c)
        for mode, stale, mg in (("current", False, 0.0), ("stale", True, 0.0), ("stale", True, MARGIN)):
            seq, _, fb = pol.predict(ctx, "test", tab=info_tab(ctx, a, b, stale, mg),
                                     F=info_F(ctx, a, b, stale), seg=ctx.seg[a:b])
            m, _ = evaluate(ctx, "test", seq, lr, lw)
            rows.append({"topology": topo, "scenario": sc, "method": "Static+fallback" + ("-m" if mg else ""),
                         "mode": mode, "static_config": int(c), "fallback_pct": 100 * fb, **m})
        o, _ = evaluate(ctx, "test", oracle_seq(ctx, "test"), lr, lw)
        rows.append({"topology": topo, "scenario": sc, "method": "O*", "mode": "offline", **o})
        log("E17", topo, sc, "static config", c, rows[-4]["total_cost_J"], "O*", o["total_cost_J"])
        pd.DataFrame(rows).to_csv(f, index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    run(ap.parse_args().force)
