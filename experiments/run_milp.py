"""E15: how much does the configuration library cost? A lower bound that no controller can beat,
versus the library-restricted DP oracle O*.

Mode "bound" (default, used in the paper): for every test interval t, solve the exact
single-interval MILP below with T = 1 (no switching terms) to optimality. Because all switching
terms are non-negative, sum_t LB_t is a lower bound on the cost J of ANY controller, with or
without a library, including the optimum of the full multi-period mixed-integer program. If the
library oracle is close to this bound, the library restriction costs at most the difference.
Intervals in which no configuration meets theta are bounded with the capacity constraint
dropped (connectivity only), which keeps the bound valid for controllers that violate theta.
Output: paper/results/E15_full_milp/<topo>_<scenario>_bound.csv (one row per test interval)

Mode "window": the same MILP over windows of T > 1 intervals with the switching terms, solved
under a time limit (HiGHS rarely closes the gap for T = 24 within minutes; kept for completeness).

For a window of T intervals the MILP chooses link states x[t,l] in {0,1} and path splits
f[t,p] in [0,1] freely (no configuration library) and minimises the RELAXED objective
  J'(seq) = sum_t E_t(x_t, f_t) + lam_W * Wnode(x_t)
            + lam_R * (w_T * toggles_t / t95 + w_D * disrupted_t / d95) + lam_W * chi * toggles_t
  s.t. one unit of split per OD, f_p <= x_l on its links, arc load <= theta * cap * x.
J' is the paper's objective J without the flow-modification term, which is not linear. Because
that term is non-negative, J'(seq) <= J(seq) for every sequence, and every library sequence is
a feasible MILP point. Hence the MILP dual bound LB satisfies
  LB <= min over ALL sequences of J  <=  J(O*),
and (J(O*) - LB) / J(O*) bounds from above what the library restriction can cost in a window.
The best MILP solution found is also scored with the EXACT cost J (an upper bound on the
non-library optimum). Output: paper/results/E15_full_milp/<topo>_full_milp.csv

Usage: python experiments/run_milp.py [--topos ...] [--T 24] [--windows 4] [--force]
"""
import argparse
import time

import scipy.sparse as sp
from scipy.optimize import Bounds, LinearConstraint, milp

from common import *  # noqa: F401,F403
from lira.models.reconfig import disrupted_fraction, flow_mods, link_toggles
from lira.models.routing import Config, mlu
from lira.oracle.dp import viterbi
from run_main import SCENARIOS, log

W_T = W_F = W_D = 1 / 3      # weights of the three R components (lira.models.reconfig.normalized_R)


def _shift(M, off):
    M = M.tocoo()
    return sp.csr_matrix((M.data, (M.row, M.col + off)), shape=M.shape)


def offset_per_interval(ctx, lam_W):
    """Solution-independent part of J' per interval (sleep power, chassis, wear credit of all links)."""
    t_, pw, wr = ctx.topo, ctx.power, ctx.wear
    norm = pw.max_link_power(t_)
    return ((pw.chassis_w * t_.N + pw.ports_per_link * pw.port_sleep_w * t_.L) / norm
            + lam_W * (wr.af_off - wr.af_on) / ctx.per_day * t_.L)


def solve_window(ctx, a, T, lam_R, lam_W, time_limit, gap, theta=None):
    theta = ctx.theta if theta is None else theta
    t_, pw, wr = ctx.topo, ctx.power, ctx.wear
    L, P, OD, A = t_.L, t_.P, t_.OD, t_.A
    D = ctx.od[a:a + T]
    norm = pw.max_link_power(t_)
    d_ref = ctx.od[ctx.split["train"]].mean(axis=0)
    t95, _, d95 = ctx.raw["R_ref"]
    # per-step block: [x L | f P | s L | g P]   (s = |x_t - x_t-1|, g = |f_t - f_t-1|)
    nb = 2 * L + 2 * P
    ox, of, os_, og = 0, L, L + P, 2 * L + P
    nv = T * nb
    c = np.zeros(nv)
    rows, lo, hi = [], [], []
    od_rows = sp.csr_matrix((np.ones(P), (t_.path_od, np.arange(P))), shape=(OD, P))
    # aggregated linking: sum of the split of OD o over its paths that use link l <= x_l.
    # Valid (the flows of o crossing l are at most 1, and 0 if l sleeps) and much tighter in the
    # LP relaxation than the per-path form f_p <= x_l, which it implies.
    pl = t_.path_link.tocoo()
    pair = t_.path_od[pl.row] * L + pl.col
    keys, inv = np.unique(pair, return_inverse=True)
    agg_f = sp.csr_matrix((np.ones(len(pl.row)), (inv, pl.row)), shape=(len(keys), P))
    agg_x = sp.csr_matrix((np.ones(len(keys)), (np.arange(len(keys)), keys % L)), shape=(len(keys), L))
    I_L, I_P = sp.eye(L), sp.eye(P)
    for t in range(T):
        b = t * nb

        def blk(M, col0, b=b):
            M = sp.coo_matrix(M)
            return sp.csr_matrix((M.data, (M.row, M.col + b + col0)), shape=(M.shape[0], nv))
        load_coef = t_.arc_path.multiply(D[t][t_.path_od][None, :]).tocsr()
        c[b + ox:b + ox + L] = pw.link_cost(t_) / norm - lam_W * (wr.af_off - wr.af_on) / ctx.per_day
        c[b + of:b + of + P] = pw.port_dyn_w * np.asarray(load_coef.T @ (1 / t_.cap)).ravel() / norm
        if t > 0:
            c[b + os_:b + os_ + L] = lam_R * W_T / t95 + lam_W * wr.chi
            c[b + og:b + og + P] = lam_R * W_D / d95 * 0.5 * d_ref[t_.path_od] / d_ref.sum()
        rows.append(blk(od_rows, of)); lo.append(np.ones(OD)); hi.append(np.ones(OD))
        rows.append(blk(agg_f, of) - blk(agg_x, ox))
        lo.append(np.full(len(keys), -np.inf)); hi.append(np.zeros(len(keys)))
        cap = sp.hstack([sp.csr_matrix((-theta * t_.cap, (np.arange(A), t_.arc_link)), shape=(A, L)),
                         load_coef]).tocoo()
        rows.append(sp.csr_matrix((cap.data, (cap.row, cap.col + b)), shape=(A, nv)))
        lo.append(np.full(A, -np.inf)); hi.append(np.zeros(A))
        if t > 0:
            for sign in (1, -1):    # s >= +-(x_t - x_t-1),  g >= +-(f_t - f_t-1)
                rows.append(blk(I_L, os_) - sign * blk(I_L, ox) + sign * _shift(blk(I_L, ox), -nb))
                lo.append(np.zeros(L)); hi.append(np.full(L, np.inf))
                rows.append(blk(I_P, og) - sign * blk(I_P, of) + sign * _shift(blk(I_P, of), -nb))
                lo.append(np.zeros(P)); hi.append(np.full(P, np.inf))
    integ = np.zeros(nv)
    ub = np.ones(nv)
    for t in range(T):
        integ[t * nb + ox:t * nb + ox + L] = 1
    ub[os_:nb] = 0                       # no switching variables at t = 0 (free start, as for O*)
    t0 = time.perf_counter()
    res = milp(c, constraints=LinearConstraint(sp.vstack(rows).tocsr(), np.concatenate(lo), np.concatenate(hi)),
               integrality=integ, bounds=Bounds(np.zeros(nv), ub),
               options={"time_limit": time_limit, "mip_rel_gap": gap, "disp": False})
    rt = time.perf_counter() - t0
    off = T * offset_per_interval(ctx, lam_W)
    info = {"runtime_s": rt, "status": res.message[:60], "vars": nv, "binaries": int(integ.sum()),
            # the dual bound is valid when HiGHS stops optimal (0) or at a limit (1), not when infeasible
            "lower_bound_J": (float(res.mip_dual_bound) + off
                              if res.status in (0, 1) and getattr(res, "mip_dual_bound", None) is not None
                              else np.nan),
            "mip_gap": float(getattr(res, "mip_gap", np.nan) or 0.0)}
    if res.x is None:
        return None, info
    info["milp_relaxed_obj"] = float(res.fun) + off
    X = res.x.reshape(T, nb)
    cfgs = []
    for t in range(T):
        x = np.round(X[t, ox:ox + L])
        f = np.clip(X[t, of:of + P], 0, None) * t_.alive_paths(x)
        f /= np.add.reduceat(f, t_.od_first_path)[t_.path_od]
        cfgs.append(Config(x, f))
    return cfgs, info


def exact_cost(ctx, cfgs, a, lam_R, lam_W):
    """Score a free (non-library) configuration sequence with the paper's exact cost J and the
    relaxed J' (J without the flow-modification term)."""
    t_, pw, wr = ctx.topo, ctx.power, ctx.wear
    norm = pw.max_link_power(t_)
    d_ref = ctx.od[ctx.split["train"]].mean(axis=0)
    t95, f95, d95 = ctx.raw["R_ref"]
    E = np.array([pw.power(t_, c, ctx.od[a + i][None])[0] / norm for i, c in enumerate(cfgs)])
    M = np.array([mlu(t_, c.split, ctx.od[a + i][None])[0] for i, c in enumerate(cfgs)])
    node = E + lam_W * (wr.af_off - wr.af_on) / ctx.per_day * np.array([(1 - c.x).sum() for c in cfgs])
    tog = np.array([link_toggles(p, q) for p, q in zip(cfgs[:-1], cfgs[1:])])
    fm = np.array([flow_mods(t_, p, q) for p, q in zip(cfgs[:-1], cfgs[1:])])
    dis = np.array([disrupted_fraction(t_, p, q, d_ref) for p, q in zip(cfgs[:-1], cfgs[1:])])
    wear_edge = lam_W * wr.chi * tog
    J_relaxed = node.sum() + (lam_R * (W_T * tog / t95 + W_D * dis / d95) + wear_edge).sum()
    J = J_relaxed + (lam_R * W_F * fm / f95).sum()
    return {"J": float(J), "J_relaxed": float(J_relaxed), "energy_norm": float(E.sum()),
            "toggles": int(tog.sum()), "flow_mods": int(fm.sum()),
            "changes": int(((tog > 0) | (fm > 0)).sum()),
            "violation_pct": float((M > ctx.theta + 1e-6).mean() * 100)}


def run_bound(jobs, force):
    """Per-interval exact lower bound over the whole test split (see module docstring)."""
    d = out_dir("E15_full_milp")
    for topo, sc in jobs:
        f = d / f"{topo}_{sc}_bound.csv"
        if f.exists() and not force:
            continue
        ctx = build_ctx(topo, 32, **SCENARIOS[sc])
        lr, lw = prices(ctx)
        a, b = ctx.rng_idx("test")
        lib_node = ctx.tab.E[a:b] + lw * ctx.tab.Wn[None, :]          # same units as evaluate()
        feas = ctx.tab.feas[a:b]
        rows = []
        for i, t in enumerate(range(a, b)):
            _, info = solve_window(ctx, t, 1, lr, lw, 120, 1e-9)
            relaxed = False
            if not np.isfinite(info["lower_bound_J"]):       # nothing meets theta: drop capacity
                _, info = solve_window(ctx, t, 1, lr, lw, 120, 1e-9, theta=1e9)
                relaxed = True
            best_lib = float(np.where(feas[i], lib_node[i], np.inf).min()) if feas[i].any() else float(lib_node[i].min())
            rows.append({"t": t, "lower_bound": info["lower_bound_J"], "ilp_obj": info.get("milp_relaxed_obj", np.nan),
                         "mip_gap": info["mip_gap"], "status": info["status"][:40], "capacity_dropped": relaxed,
                         "best_library_node": best_lib, "alwayson_node": float(lib_node[i, 0]),
                         "runtime_s": info["runtime_s"]})
            if i % 500 == 0:
                log("E15 bound", topo, sc, f"{i}/{b - a}", rows[-1]["lower_bound"], best_lib)
        pd.DataFrame(rows).to_csv(f, index=False)
        log("E15 bound", topo, sc, "done")


def run(topos, T, n_win, time_limit, gap, force):
    d = out_dir("E15_full_milp")
    for topo in topos:
        f = d / f"{topo}_full_milp.csv"
        if f.exists() and not force:
            continue
        ctx = build_ctx(topo, 32)
        rows = []
        for mult in (1.0, 0.1):
            lr, lw = prices(ctx, mult)
            a0, b0 = ctx.rng_idx("test")
            for s in np.linspace(a0, b0 - T - 1, n_win).astype(int):
                if len(np.unique(ctx.seg[s:s + T])) > 1:      # keep windows inside one segment
                    s = s + int(np.flatnonzero(np.diff(ctx.seg[s:s + T]))[-1]) + 1
                tab = ctx.tab.slice(s, s + T)
                seq, _ = viterbi(tab.node(lw), tab.edge(lr, lw))
                o = exact_cost(ctx, [ctx.library[k] for k in seq], s, lr, lw)
                cfgs, info = solve_window(ctx, s, T, lr, lw, time_limit, gap)
                row = {"topology": topo, "price_mult": mult, "start": int(s), "T": T,
                       "oracle_J": o["J"], "oracle_J_relaxed": o["J_relaxed"], "oracle_changes": o["changes"],
                       "oracle_viol_pct": o["violation_pct"], "alwayson_energy": float(tab.E[:, 0].sum()), **info,
                       "library_loss_bound_pct": 100 * (o["J"] - info["lower_bound_J"]) / o["J"]}
                if cfgs is not None:
                    m = exact_cost(ctx, cfgs, s, lr, lw)
                    row.update({"milp_J": m["J"], "milp_J_relaxed": m["J_relaxed"], "milp_energy": m["energy_norm"],
                                "milp_changes": m["changes"], "milp_toggles": m["toggles"],
                                "milp_flow_mods": m["flow_mods"], "milp_viol_pct": m["violation_pct"],
                                "milp_vs_oracle_pct": 100 * (o["J"] - m["J"]) / o["J"],
                                "check_relaxed_obj_err": abs(m["J_relaxed"] - info["milp_relaxed_obj"])})
                rows.append(row)
                log("E15", topo, mult, s, {k: round(row[k], 4) if isinstance(row.get(k), float) else row.get(k)
                                          for k in ("oracle_J", "lower_bound_J", "milp_J", "library_loss_bound_pct",
                                                    "mip_gap", "runtime_s")})
                pd.DataFrame(rows).to_csv(f, index=False)


BOUND_JOBS = [("abilene", "base"), ("geant", "base"), ("nobel", "base"), ("nobel", "highload"),
              ("nobel", "stress")]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["bound", "window"], default="bound")
    ap.add_argument("--topos", nargs="+", default=list(TOPOS))
    ap.add_argument("--T", type=int, default=24)
    ap.add_argument("--windows", type=int, default=4)
    ap.add_argument("--time-limit", type=float, default=300)
    ap.add_argument("--gap", type=float, default=1e-4)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.mode == "bound":
        run_bound([j for j in BOUND_JOBS if j[0] in a.topos], a.force)
    else:
        run(a.topos, a.T, a.windows, a.time_limit, a.gap, a.force)
