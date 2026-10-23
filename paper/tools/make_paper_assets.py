"""Generate every number, table and plot-data file used by paper/main.tex from paper/results/.

Outputs (all in paper/generated/):  results_macros.tex, tab_*.tex, *.dat
Nothing is typed by hand: re-run this script after any experiment and recompile the paper.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments"))
from common import build_ctx, prices  # noqa: E402
R = ROOT / "paper" / "results"
G = ROOT / "paper" / "generated"
G.mkdir(exist_ok=True)
TOPOS = ("abilene", "geant", "nobel")
NAME = {"abilene": "Abilene", "geant": "G\\'{E}ANT", "nobel": "Nobel-Germany"}
SC_NAME = {"base": "base", "highload": "high load", "highdyn": "high dynamic power", "stress": "stress"}
macros = {}


def ci95(x):
    from scipy import stats
    x = np.asarray(x, float)
    return float(stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0


def f(x, nd=2):
    return "--" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def pm(x, nd=2):
    x = np.asarray(x, float)
    if len(x) > 1 and ci95(x) > 0:
        return f"{x.mean():.{nd}f}$\\pm${ci95(x):.{nd}f}"
    return f"{x.mean():.{nd}f}"


W_ = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}


def mname(k):
    """LaTeX control-sequence names may only contain letters."""
    return "".join(W_.get(c, c) for c in k)


def write(name, text):
    with open(G / name, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def runs(t, sc):
    p = R / "E1_main" / f"{t}_{sc}_runs.csv"
    return pd.read_csv(p) if p.exists() else None


# ------------------------------------------------------------------------------ macros
meta = {t: json.loads((ROOT / "data" / "processed" / t / "meta.json").read_text()) for t in TOPOS}
head = pd.read_csv(R / "headline.csv")
hd = head.set_index(["topology", "scenario"])
macros["nobB4chg"] = f(hd.loc[("Nobel-Germany", "base"), "B4 changes/day"], 1)
macros["nobLiRAchg"] = f(hd.loc[("Nobel-Germany", "base"), "LiRA changes/day"], 2)
macros["nobY"] = f(hd.loc[("Nobel-Germany", "base"), "Y change reduction %"], 1)
macros["nobZ"] = f(hd.loc[("Nobel-Germany", "base"), "Z transition reduction %"], 1)
macros["nobX"] = f(hd.loc[("Nobel-Germany", "base"), "X retention %"], 1)
macros["nobhlB4chg"] = f(hd.loc[("Nobel-Germany", "highload"), "B4 changes/day"], 2)
macros["nobhlLiRAchg"] = f(hd.loc[("Nobel-Germany", "highload"), "LiRA changes/day"], 2)
macros["nobhlY"] = f(hd.loc[("Nobel-Germany", "highload"), "Y change reduction %"], 0)
macros["nobhlZ"] = f(hd.loc[("Nobel-Germany", "highload"), "Z transition reduction %"], 0)
for t in ("abilene", "geant"):
    d = runs(t, "base")
    for m, key in (("B4", "B4chg"), ("LiRA", "LiRAchg")):
        macros[f"{t[:3]}{key}"] = f(d[d.method == m].config_changes_per_day.mean(), 3)
    macros[f"{t[:3]}Sav"] = f(d[d.method == "O*"].savings_pct.mean(), 1)
d = runs("nobel", "base")
macros["nobSav"] = f(d[d.method == "O*"].savings_pct.mean(), 1)
macros["nobSnapChg"] = f(d[d.method == "SNAP-exact"].config_changes_per_day.mean(), 1)
macros["nobBsixChg"] = f(d[d.method == "B6"].config_changes_per_day.mean(), 2)
# nobel highload costs
d = runs("nobel", "highload")
for m in ("B4", "B6", "B7", "LiRA", "O*"):
    macros[f"nobhlJ{m.replace('*', 'star')}"] = f(d[d.method == m].total_cost_J.mean(), 1)
macros["nobhlBsixChg"] = f(d[d.method == "B6"].config_changes_per_day.mean(), 2)
# stats
st = pd.read_csv(R / "E1_main" / "stats_wilcoxon_holm.csv").set_index(["topology", "scenario", "comparison"])
macros["nobhlPbsix"] = f(st.loc[("nobel", "highload", "LiRA vs B6"), "p_holm"], 2)
macros["nobPbfour"] = f(st.loc[("nobel", "base", "LiRA vs B4"), "p_holm"], 3)
macros["nobPbsix"] = f(st.loc[("nobel", "base", "LiRA vs B6"), "p_holm"], 2)
# dp vs milp
vals = []
for t in TOPOS:
    p = ROOT / "results" / f"dp_milp_validation_{t}.csv"
    if p.exists():
        vals.append(pd.read_csv(p).abs_diff.max())
macros["dpMilpDiff"] = f"{max(vals):.0e}".replace("e-", "\\times10^{-").replace("e+", "\\times10^{") + "}" if vals else "n/a"
# test lengths
for t in TOPOS:
    macros[f"{t[:3]}TestDays"] = f(runs(t, "base").days.iloc[0], 1)
# scalability + opt baselines
scal = pd.read_csv(R / "E5_latency_scalability" / "scalability.csv").set_index("topology")
macros["ilpGermany"] = f(scal.loc["germany50", "ilp_median_s"], 1)
macros["ilpTA"] = f(scal.loc["ta2", "ilp_median_s"], 1)
macros["ilpGeant"] = f(scal.loc["geant", "ilp_median_s"], 1)
macros["safetyTA"] = f(scal.loc["ta2", "safety_check_ms"], 2)
ob = {t: pd.read_csv(R / "E5_latency_scalability" / f"{t}_opt_baselines.csv").set_index("method") for t in TOPOS}
macros["nobIlpMs"] = f(1000 * ob["nobel"].loc["B1 per-snapshot ILP", "median_s"], 0)
macros["geaIlpS"] = f(ob["geant"].loc["B1 per-snapshot ILP", "median_s"], 1)
macros["nobGaS"] = f(ob["nobel"].loc["B3 per-snapshot NSGA-II", "median_s"], 0)
macros["geaGaS"] = f(ob["geant"].loc["B3 per-snapshot NSGA-II", "median_s"], 0)
# latency
for t in TOPOS:
    d = runs(t, "base")
    macros[f"{t[:3]}LatB4"] = f(d[d.method == "B4"].latency_median_ms.mean(), 2)
    macros[f"{t[:3]}LatLiRA"] = f(d[d.method == "LiRA"].latency_median_ms.mean(), 3)
# data
macros["abiIntervals"] = f"{meta['abilene']['T']:,}".replace(",", "\\,")
macros["geaIntervals"] = f"{meta['geant']['T']:,}".replace(",", "\\,")
macros["nobIntervals"] = f"{meta['nobel']['T']:,}".replace(",", "\\,")
# emulation
ep = R / "E11_emulation" / "emulation_summary.csv"
if ep.exists():
    e = pd.read_csv(ep)
    b4 = e[e.method == "B4"]
    macros["emuTrans"] = f"{b4.transitions.mean():.0f}"
    macros["emuRuleMs"] = f(b4.rule_install_ms_mean.mean(), 0)
    macros["emuLossWin"] = f(b4.loss_pct_in_windows.mean(), 2)
    macros["emuLossAll"] = f(b4.loss_pct.mean(), 3)
    macros["emuTransS"] = f(b4.transition_total_s_mean.mean(), 2)
    li = e[e.method == "LiRA"]
    if len(li):
        macros["emuLiRALoss"] = f(li.loss_pct.mean(), 3)
        macros["emuLiRAtrans"] = f"{li.transitions.mean():.0f}"
    macros["emuLostPerTrans"] = f(b4.lost_pkts.mean() / max(b4.transitions.mean(), 1), 1)
    b0 = e[e.method == "B0"]
    if len(b0) and len(li):
        macros["emuLinkSave"] = f(100 * (1 - li.link_on_seconds.mean() / b0.link_on_seconds.mean()), 0)
    macros["emuProbePkts"] = "{:,}".format(int(b4.probe_pkts.mean())).replace(",", "\\,")
    macros["emuHaveData"] = "1"

# ---- extra macros (models, ablation, K, theta, drift, folds, wear)
dm = pd.read_csv(R / "E13_model_choice" / "nobel_models.csv")
dm = dm[(dm.price_mult == 1.0) & (dm.method == "B4")].set_index("backend")
for be, key in (("xgb", "Xgb"), ("lgbm", "Lgbm"), ("rf", "Rf"), ("mlp", "Mlp")):
    macros[f"mod{key}Chg"] = f(dm.loc[be, "config_changes_per_day"], 1)
    macros[f"mod{key}J"] = f(dm.loc[be, "total_cost_J"], 1)
for sc_, tag in (("stress", "Stress"), ("highload", "Hl")):
    da = pd.read_csv(R / "E7_ablation" / f"nobel_{sc_}_ablation.csv")
    da = da[da.price_mult == 1.0].groupby("variant").mean(numeric_only=True)
    for v, key in (("O*", "O"), ("full", "Full"), ("no_prev_config", "NoPrev"), ("no_cost_sensitive", "NoCS"),
                   ("no_dagger", "NoDagger"), ("no_lag_history", "NoLag"), ("no_safety", "NoSafe")):
        macros[f"abl{tag}{key}"] = f(da.loc[v, "total_cost_J"], 1)
    macros[f"abl{tag}NoSafeViol"] = f(da.loc["no_safety", "mlu_violation_pct"], 2)
dk = pd.read_csv(R / "E6_library_size" / "nobel_K.csv")
for K in (8, 64):
    g = dk[dk.K_requested == K]
    macros[f"KB4at{K}"] = f(g[g.method == "B4"].total_cost_J.iloc[0], 1)
    macros[f"KBsixAt{K}"] = f(g[g.method == "B6"].total_cost_J.iloc[0], 1)
macros["KactualMax"] = str(int(dk.K_actual.max()))
dth = pd.read_csv(R / "E10_theta" / "nobel_theta.csv")
g6 = dth[dth.theta == 0.6].set_index("method")
macros["thSixB4chg"] = f(g6.loc["B4", "config_changes_per_day"], 1)
macros["thSixLiRAchg"] = f(g6.loc["LiRA", "config_changes_per_day"], 2)
for t, key in (("abilene", "Abi"), ("geant", "Gea"), ("nobel", "Nob")):
    dd = pd.read_csv(R / "E8_drift" / f"{t}_drift.csv")
    c = dd[(dd["shift"] == "none") & (dd.method == "LiRA") & (dd["mode"] == "drift")].iloc[0]
    macros[f"driftFa{key}"] = f(c.false_alarms_per_1k_intervals, 2)
    macros[f"driftThr{key}"] = f"{int(c.ph_threshold)}"
df_ = pd.read_csv(R / "E14_rolling_folds" / "nobel_folds.csv")
df_ = df_[df_.price_mult == 1.0].groupby("method").total_cost_J.mean()
for m, key in (("B4", "B4"), ("B6", "B6"), ("B7", "B7"), ("LiRA", "LiRA"), ("O*", "O")):
    macros[f"foldNob{key}"] = f(df_[m], 1)
d = runs("nobel", "base")
macros["nobAFfour"] = f(d[d.method == "B4"].mean_AF.mean(), 3)
macros["nobAFlira"] = f(d[d.method == "LiRA"].mean_AF.mean(), 3)
macros["nobAFsnap"] = f(d[d.method == "SNAP-exact"].mean_AF.mean(), 3)
macros["nobB4trans"] = f(d[d.method == "B4"].link_transitions_per_day.mean(), 1)
macros["nobLiRAtrans"] = f(d[d.method == "LiRA"].link_transitions_per_day.mean(), 2)
macros["nobJfour"] = f(d[d.method == "B4"].total_cost_J.mean(), 1)
macros["nobJsix"] = f(d[d.method == "B6"].total_cost_J.mean(), 1)
macros["nobJlira"] = f(d[d.method == "LiRA"].total_cost_J.mean(), 1)
macros["nobJstar"] = f(d[d.method == "O*"].total_cost_J.mean(), 1)
macros["nobJzero"] = f(d[d.method == "B0"].total_cost_J.mean(), 1)
dw = pd.read_csv(R / "E9_wear_sensitivity" / "nobel_base_sensitivity.csv")
dw = dw[(dw.af_off == 0.5)]
big = dw[dw.chi == 0.1].set_index("method").mean_AF
macros["wearBigChiB4"] = f(big["B4"], 2)
macros["wearBigChiLiRA"] = f(big["LiRA"], 2)
macros["wearCrossB4"] = ("none" if (dw[dw.method == "B4"].mean_AF <= 1).all() else
                         f(dw[(dw.method == "B4") & (dw.mean_AF > 1)].chi.min(), 3))


# ---- how often the trained LiRA policy degenerates to a constant classifier
import glob
_tot = _const = 0
for _f in glob.glob(str(R / "E1_main" / "*_info.json")):
    _runs = json.loads(Path(_f).read_text())["runs"]
    _tot += len(_runs)
    _const += sum(r["lira_model"] == "ConstantModel" for r in _runs)
macros["liraConstRuns"] = str(_const)
macros["liraTotalRuns"] = str(_tot)

write("results_macros.tex", "% generated by paper/tools/make_paper_assets.py\n" + "\n".join(
    f"\\newcommand{{\\{mname(k)}}}{{{v}}}" for k, v in macros.items()) + "\n")

# ------------------------------------------------------------------------------ data table
rows = []
THIN = "\,"
for t in TOPOS:
    m = meta[t]
    span = m["start"][:10] + " to " + m["end"][:10]
    interval = m["freq"].replace("min", THIN + "min")
    n_int = f"{m['T']:,}".replace(",", THIN)
    kind = "semi-synthetic" if m.get("semi_synthetic") else "real (SNDlib)"
    rows.append(f"{NAME[t]} & {m['nodes']} & {m['links_undirected']} & {interval} & {n_int} & {span} & {kind} \\\\")
write("tab_data.tex", "\\begin{tabular}{@{}lcccccc@{}}\n\\toprule\nTopology & $|V|$ & $|E|$ & $\\Delta$ & Intervals & Span & Traffic \\\\\n\\midrule\n"
      + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ main table (base)
order = [("B0", "B0 always-on"), ("B4", "B4 snapshot ML"), ("B6", "B6 B4+hysteresis"), ("B7", "B7 B4+min-dwell"),
         ("B2-naive", "B2 rolling horizon"), ("LiRA", "LiRA"), ("O*", "Oracle O$^\\star$")]
lines = []
for t in TOPOS:
    d = runs(t, "base")
    lines.append(f"\\multicolumn{{8}}{{@{{}}l}}{{\\textit{{{NAME[t]}}}}} \\\\")
    for key, lab in order:
        g = d[d.method == key]
        lat = g.latency_median_ms.dropna()
        lines.append(f"{lab} & {pm(g.savings_pct, 2)} & {pm(g.config_changes_per_day, 2)} & "
                     f"{pm(g.link_transitions_per_day, 2)} & {pm(g.mlu_violation_pct, 2)} & {pm(g.total_cost_J, 1)} & "
                     f"{pm(g.mean_AF, 3)} & {f(lat.mean(), 3) if len(lat) else '--'} \\\\")
    lines.append("\\midrule" if t != TOPOS[-1] else "")
write("tab_main.tex", "\\begin{tabular}{@{}lccccccc@{}}\n\\toprule\nMethod & $S$ (\\%) & Changes/d & Transitions/d & MLU viol. (\\%) & $J$ & $\\overline{\\mathrm{AF}}$ & Latency (ms) \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ scenarios (headline + stats)
lines = []
for t in TOPOS:
    for sc in ("base", "highload", "highdyn", "stress"):
        d = runs(t, sc)
        if d is None:
            continue
        b4, b6, b2, li, o = (d[d.method == m] for m in ("B4", "B6", "B2-naive", "LiRA", "O*"))
        s = lambda c: st.loc[(t, sc, c), "p_holm"]
        lines.append(f"{NAME[t]} & {SC_NAME[sc]} & {f(b4.config_changes_per_day.mean(), 2)} & {f(b6.config_changes_per_day.mean(), 2)} & "
                     f"{f(b2.config_changes_per_day.mean(), 2)} & {f(li.config_changes_per_day.mean(), 2)} & {f(b4.total_cost_J.mean(), 1)} & "
                     f"{f(b6.total_cost_J.mean(), 1)} & {f(b2.total_cost_J.mean(), 1)} & "
                     f"{f(li.total_cost_J.mean(), 1)} & {f(o.total_cost_J.mean(), 1)} & {f(s('LiRA vs B4'), 3)} & {f(s('LiRA vs B6'), 3)} \\\\")
    lines.append("\\midrule" if t != TOPOS[-1] else "")
write("tab_scen.tex", "\\begin{tabular}{@{}llccccccccccc@{}}\n\\toprule\n & & \\multicolumn{4}{c}{Changes/d} & \\multicolumn{5}{c}{Total cost $J$} & \\multicolumn{2}{c}{$p_{\\mathrm{Holm}}$} \\\\\n\\cmidrule(lr){3-6}\\cmidrule(lr){7-11}\\cmidrule(lr){12-13}\nTopology & Scenario & B4 & B6 & B2 & LiRA & B4 & B6 & B2 & LiRA & O$^\\star$ & vs B4 & vs B6 \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ ablation (Nobel stress + highload)
lines = []
for sc in ("highload", "stress"):
    p = R / "E7_ablation" / f"nobel_{sc}_ablation.csv"
    if not p.exists():
        continue
    d = pd.read_csv(p)
    d = d[d.price_mult == 1.0]
    lines.append(f"\\multicolumn{{5}}{{@{{}}l}}{{\\textit{{Nobel-Germany, {SC_NAME[sc]}}}}} \\\\")
    names = {"O*": "Oracle O$^\\star$", "full": "LiRA (full)", "no_lag_history": "no lag features",
             "no_prev_config": "no previous config.", "no_cost_sensitive": "no cost-sensitive weights",
             "no_dagger": "no DAgger", "no_safety": "no safety layer"}
    for v, lab in names.items():
        g = d[d.variant == v]
        if g.empty:
            continue
        lines.append(f"{lab} & {pm(g.savings_pct, 2)} & {pm(g.config_changes_per_day, 2)} & {pm(g.mlu_violation_pct, 2)} & {pm(g.total_cost_J, 1)} \\\\")
    lines.append("\\midrule" if sc == "highload" else "")
write("tab_ablation.tex", "\\begin{tabular}{@{}lcccc@{}}\n\\toprule\nVariant & $S$ (\\%) & Changes/d & MLU viol. (\\%) & $J$ \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ library size and theta (Nobel)
d = pd.read_csv(R / "E6_library_size" / "nobel_K.csv")
lines = []
for K, g in d.groupby("K_requested"):
    row = {m: g[g.method == m].total_cost_J.iloc[0] for m in ("B4", "B6", "LiRA", "O*")}
    kreq, kact = int(K), int(g.K_actual.iloc[0])
    klab = str(kact) if kreq == kact else f"{kreq} ({kact})"
    # coverage on the TEST split: validation matrices were used to build the library
    cK = build_ctx("nobel", kreq)
    test_cov = 100 * cK.tab.feas[slice(*cK.rng_idx("test"))].any(axis=1).mean()
    lines.append(f"{klab} & {f(test_cov, 1)} & {f(row['B4'], 1)} & {f(row['B6'], 1)} & {f(row['LiRA'], 1)} & {f(row['O*'], 1)} \\\\")
write("tab_K.tex", "\\begin{tabular}{@{}cccccc@{}}\n\\toprule\n$K$ & Test coverage (\\%) & B4 & B6 & LiRA & O$^\\star$ \\\\\n\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
lines = []
for t in TOPOS:
    d = pd.read_csv(R / "E10_theta" / f"{t}_theta.csv")
    for th, g in d.groupby("theta"):
        gg = g.set_index("method")
        lines.append(f"{NAME[t]} & {th:g} & {f(gg.loc['B0', 'alwayson_violation_pct'], 2)} & {f(gg.loc['O*', 'savings_pct'], 2)} & {f(gg.loc['B4', 'config_changes_per_day'], 2)} & {f(gg.loc['LiRA', 'config_changes_per_day'], 2)} & {f(gg.loc['LiRA', 'mlu_violation_pct'], 2)} & {f(gg.loc['LiRA', 'total_cost_J'], 1)} \\\\")
    lines.append("\\midrule" if t != TOPOS[-1] else "")
write("tab_theta.tex", "\\begin{tabular}{@{}lccccccc@{}}\n\\toprule\nTopology & $\\theta$ & All-on viol. (\\%) & $S_{\\mathrm{O}^\\star}$ (\\%) & B4 chg/d & LiRA chg/d & LiRA viol. (\\%) & LiRA $J$ \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ model choice (Nobel, price 0.1x and 1x)
d = pd.read_csv(R / "E13_model_choice" / "nobel_models.csv")
d = d[(d.price_mult == 1.0) & d.backend.isin(["xgb", "lgbm", "rf", "mlp"])]
nm = {"xgb": "XGBoost", "lgbm": "LightGBM", "rf": "Random forest", "mlp": "MLP ($2\\times256$)"}
lines = []
for be in ("xgb", "lgbm", "rf", "mlp"):
    b4 = d[(d.backend == be) & (d.method == "B4")].iloc[0]
    li = d[(d.backend == be) & (d.method == "LiRA")].iloc[0]
    lines.append(f"{nm[be]} & {f(b4.config_changes_per_day, 2)} & {f(b4.total_cost_J, 1)} & {f(b4.latency_median_ms, 2)} & {f(li.config_changes_per_day, 2)} & {f(li.total_cost_J, 1)} \\\\")
write("tab_models.tex", "\\begin{tabular}{@{}lccccc@{}}\n\\toprule\n & \\multicolumn{3}{c}{B4 (snapshot)} & \\multicolumn{2}{c}{LiRA} \\\\\n\\cmidrule(lr){2-4}\\cmidrule(lr){5-6}\nModel & Chg/d & $J$ & Latency (ms) & Chg/d & $J$ \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ optimisation baselines + scalability
lines = []
for t in TOPOS:
    o = ob[t]
    for m, lab in (("library snapshot optimum", "Library snapshot optimum"), ("B1 per-snapshot ILP", "B1 per-snapshot ILP"),
                   ("B3 per-snapshot NSGA-II", "B3 NSGA-II"), ("B5 ElasticTree-style greedy", "B5 greedy")):
        r = o.loc[m]
        lines.append(f"{NAME[t]} & {lab} & {int(r.n)} & {f(r.savings_pct, 2)} & {f(r.median_s, 2) if not np.isnan(r.median_s) else '--'} \\\\")
    lines.append("\\midrule" if t != TOPOS[-1] else "")
write("tab_opt.tex", "\\begin{tabular}{@{}llccc@{}}\n\\toprule\nTopology & Method & $n$ & $S$ (\\%) & Median time (s) \\\\\n\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
lines = []
PRETTY = {"germany50": "Germany50", "ta2": "TA2", "abilene": "Abilene", "geant": NAME["geant"], "nobel": NAME["nobel"]}
for t, r in scal.iterrows():
    lines.append(f"{PRETTY[t]} & {int(r.nodes)} & {int(r.links)} & {int(r.od_pairs)} & {f(r.ilp_median_s, 2)} & {f(r.elastictree_s, 2)} & {f(r.safety_check_ms, 3)} \\\\")
write("tab_scale.tex", "\\begin{tabular}{@{}lcccccc@{}}\n\\toprule\nTopology & $|V|$ & $|E|$ & OD pairs & ILP (s) & Greedy (s) & Safety check (ms) \\\\\n\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ drift
lines = []
for t in TOPOS:
    d = pd.read_csv(R / "E8_drift" / f"{t}_drift.csv")
    ctrl = d[(d["shift"] == "none") & (d.method == "LiRA") & (d["mode"] == "drift")].iloc[0]
    for sh in ("growth", "hotspot", "phase"):
        g = d[(d["shift"] == sh) & (d.method == "LiRA")].set_index("mode")
        lines.append(f"{NAME[t]} & {sh} & {f(g.loc['static', 'post_total_cost_J'], 1)} & {f(g.loc['drift', 'post_total_cost_J'], 1)} & "
                     f"{int(g.loc['drift', 'detections'])} & {f(ctrl.false_alarms_per_1k_intervals, 2)} \\\\")
    lines.append("\\midrule" if t != TOPOS[-1] else "")
write("tab_drift.tex", "\\begin{tabular}{@{}llcccc@{}}\n\\toprule\nTopology & Shift & $J$ once & $J$ retrained & Detections & FA/1k \\\\\n\\midrule\n"
      + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ rolling folds (Nobel + Abilene summary)
lines = []
for t in TOPOS:
    d = pd.read_csv(R / "E14_rolling_folds" / f"{t}_folds.csv")
    d = d[d.price_mult == 1.0]
    for m, lab in (("B4", "B4"), ("B6", "B6"), ("LiRA", "LiRA"), ("O*", "O$^\\star$")):
        g = d[d.method == m]
        lines.append(f"{NAME[t] if m == 'B4' else ''} & {lab} & {f(g.savings_pct.mean(), 2)} & {f(g.config_changes_per_day.mean(), 2)} & {f(g.total_cost_J.mean(), 1)}$\\pm${f(g.total_cost_J.std(), 1)} \\\\")
    lines.append("\\midrule" if t != TOPOS[-1] else "")
write("tab_folds.tex", "\\begin{tabular}{@{}llccc@{}}\n\\toprule\nTopology & Method & $S$ (\\%) & Chg/d & $J$ (mean$\\pm$std over folds) \\\\\n\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ emulation table
if ep.exists():
    e = pd.read_csv(ep)
    lines = []
    for m, g in e.groupby("method"):
        lines.append(f"{m} & {len(g)} & {g.transitions.mean():.0f} & {f(g.rule_install_ms_mean.mean(), 0) if g.transitions.mean() > 0 else '--'} & "
                     f"{f(g.transition_total_s_mean.mean(), 2) if g.transitions.mean() > 0 else '--'} & {f(g.loss_pct.mean(), 3)} & "
                     f"{f(g.loss_pct_in_windows.mean(), 2) if g.transitions.mean() > 0 else '--'} & {f(g.delay_ms_p50.mean(), 2)} & {f(g.delay_ms_p99.mean(), 1)} & {f(g.link_on_seconds.mean() / 3600, 2)} \\\\")
    write("tab_emu.tex", "\\begin{tabular}{@{}lccccccccc@{}}\n\\toprule\nMethod & Runs & Trans. & Rule install (ms) & Trans. time (s) & Loss (\\%) & Loss in windows (\\%) & Delay p50 (ms) & p99 (ms) & Link-hours \\\\\n\\midrule\n"
          + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")

# ------------------------------------------------------------------------------ plot data
# (1) energy gain of each B4 change on Nobel (base)
ctx = build_ctx("nobel", 32)
z = np.load(R / "E1_main" / "nobel_base_seqs.npz")
a, b = ctx.rng_idx("test")
s = z["B4_s0"]
E = ctx.tab.E[a:b]
idx = np.flatnonzero(s[1:] != s[:-1]) + 1
gain = 100 * np.abs(E[idx, s[idx - 1]] - E[idx, s[idx]]) / E[idx, s[idx - 1]]
bins = [0, 0.1, 0.5, 1, 2, 100]
labels = ["<0.1", "0.1-0.5", "0.5-1", "1-2", ">2"]
cnt = np.histogram(gain, bins)[0]
share = 100 * cnt / max(cnt.sum(), 1)
pd.DataFrame({"bin": range(len(labels)), "label": labels, "share": share, "n": cnt}).to_csv(G / "gain_hist.dat", sep=" ", index=False)
macros_extra = {"gainChanges": str(int(cnt.sum())), "gainLowShare": f(100 * (gain < 1).mean(), 0), "gainMedian": f(float(np.median(gain)), 2),
                "gainTenthShare": f(100 * (gain < 0.1).mean(), 0), "gainMax": f(float(gain.max()), 2),
                "gainMedianBelow": "0.01" if np.median(gain) < 0.01 else f(float(np.median(gain)), 2)}
# (2) case study: Nobel busiest week, step series of config index
d = pd.read_csv(R / "E3_case_study" / "nobel_base_busiest_week.csv")
step = max(len(d) // 700, 1)
cs = d.iloc[::step][["t", "B4_config", "B6_config", "LiRA_config", "O*_config"]].copy()
cs["t"] = (cs.t - cs.t.min()) / 288.0
cs.columns = ["day", "B4", "B6", "LiRA", "Ostar"]
cs.to_csv(G / "case_week.dat", sep=" ", index=False)
macros_extra["caseB4chg"] = str(int((d.B4_config.diff().fillna(0) != 0).sum()))
macros_extra["caseLiRAchg"] = str(int((d.LiRA_config.diff().fillna(0) != 0).sum()))
# (3) Pareto: cost vs changes (Nobel base and highload)
for sc in ("base", "highload"):
    p = R / "E2_pareto" / f"nobel_{sc}_pareto.csv"
    if not p.exists():
        continue
    d = pd.read_csv(p)
    for m in ("B6", "B7", "LiRA", "O*", "B4"):
        g = d[d.method == m][["param", "config_changes_per_day", "total_cost_J"]].copy()
        g["param"] = g["param"].fillna(-1)
        g.to_csv(G / f"pareto_{sc}_{m.replace('*', 'star')}.dat", sep=" ", index=False)
# (4) wear sensitivity: mean AF vs chi (Nobel base, af_off=0.5)
d = pd.read_csv(R / "E9_wear_sensitivity" / "nobel_base_sensitivity.csv")
d = d[d.af_off == 0.5]
piv = d.pivot_table(index="chi", columns="method", values="mean_AF").reset_index().rename(columns={"O*": "Ostar", "B0": "B0"})
piv = piv[piv.chi > 0]  # chi = 0 cannot be drawn on a log axis (all methods equal 0.846 there)
piv.to_csv(G / "wear_chi.dat", sep=" ", index=False)
# (5) emulation: transition durations
tp = R / "E11_emulation" / "emulation_transitions.csv"
if tp.exists():
    t = pd.read_csv(tp)
    t[["method", "rep", "links_woken", "links_slept", "switches_updated", "rule_install_ms", "total_s"]].to_csv(G / "emu_transitions.dat", sep=" ", index=False)
# (6) E15: per-interval exact lower bound that no controller can beat (run_milp.py --mode bound)
SC_KEY = {"base": "base", "highload": "hl", "highdyn": "hd", "stress": "st"}
lines, gaps, losses, n_int, n_opt, ms, mipgaps = [], [], [], 0, 0, [], []
for t, sc in (("abilene", "base"), ("geant", "base"), ("nobel", "base"), ("nobel", "highload"), ("nobel", "stress")):
    p = R / "E15_full_milp" / f"{t}_{sc}_bound.csv"
    if not p.exists():
        continue
    bd = pd.read_csv(p)
    lb, snap = bd.lower_bound.sum(), bd.best_library_node.sum()
    jm = runs(t, sc).groupby("method").total_cost_J.mean()
    loss = 100 * (snap - lb) / jm["O*"]          # library restriction, per interval, summed
    gap = 100 * (jm["O*"] - lb) / jm["O*"]       # O* above the bound: library loss + holding/switching
    gaps.append(gap); losses.append(loss); ms += list(1000 * bd.runtime_s); mipgaps.append(float(bd.mip_gap.max()))
    n_int += len(bd); n_opt += int(bd.status.str.startswith("Optimization terminated successfully").sum())
    key = f"{t[:3]}{SC_KEY[sc]}"
    macros_extra[f"bound{key}Gap"] = f(gap, 3)
    macros_extra[f"bound{key}Loss"] = f(loss, 3)
    setting = NAME[t] if t != "nobel" else f"Nobel, {SC_NAME[sc]}"
    lines.append(f"{setting} & {f(lb, 1)} & {f(snap, 1)} & {f(jm['O*'], 1)} & {f(jm['LiRA'], 1)} & "
                 f"{f(loss, 3)} & {f(gap, 3)} \\\\")
if lines:
    write("tab_bound.tex", "\\begin{tabular}{@{}lcccccc@{}}\n\\toprule\nSetting & Bound & Lib. snapshot & O$^\\star$ & LiRA & Lib. loss (\\%) & O$^\\star$ gap (\\%) \\\\\n\\midrule\n"
          + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
    macros_extra["boundMaxLoss"] = f(max(losses), 3)
    macros_extra["boundMaxGap"] = f(max(gaps), 2)
    macros_extra["boundIntervals"] = f"{n_int:,}".replace(",", "\\,")
    macros_extra["boundAllOptimal"] = "all" if n_opt == n_int else f"{n_opt} of {n_int}"
    macros_extra["boundMedianMs"] = f(float(np.median(ms)), 0)
    _g = f"{max(mipgaps):.0e}"
    macros_extra["boundMaxMipGap"] = _g.replace("e-0", "\\times10^{-").replace("e-", "\\times10^{-") + "}"

# (7) E16 (decisions on D_{t-1}) and E17 (static configuration + LiRA's fallback)
e16 = {sc: pd.read_csv(R / "E16_stale_tm" / f"{t}_{sc}_stale.csv") for t, sc in
       [(t, sc) for t in TOPOS for sc in ("base", "highload", "stress")]
       if (R / "E16_stale_tm" / f"{t}_{sc}_stale.csv").exists() and t == "nobel"}
e16_all = [pd.read_csv(p) for p in sorted((R / "E16_stale_tm").glob("*_stale.csv"))] if (R / "E16_stale_tm").exists() else []
e17p = R / "E17_static_fallback" / "static_fallback.csv"
if e16_all and e17p.exists():
    s17 = pd.read_csv(e17p)
    lines = []
    for sc, d in e16.items():
        st_ = s17[(s17.topology == "nobel") & (s17.scenario == sc)]
        lines.append(f"\\multicolumn{{6}}{{@{{}}l}}{{\\textit{{Nobel-Germany, {SC_NAME[sc]}}}}} \\\\")
        for m, lab in (("B2-naive", "B2 rolling horizon"), ("B4", "B4 snapshot ML"), ("B6", "B6 hysteresis"),
                       ("Static+fallback", "Static + fallback"), ("LiRA", "LiRA")):
            src = st_ if m == "Static+fallback" else d
            cur = src[(src.method == m) & (src["mode"] == "current")]
            sta = src[(src.method == m) & (src["mode"] == "stale")]
            mar = src[src.method == m + "-m"]
            lines.append(f"{lab} & {f(cur.total_cost_J.mean(), 1)} & {f(sta.total_cost_J.mean(), 1)} & "
                         f"{f(sta.mlu_violation_pct.mean(), 2)} & "
                         f"{f(mar.total_cost_J.mean(), 1) if len(mar) else '--'} & {f(mar.mlu_violation_pct.mean(), 2) if len(mar) else '--'} \\\\")
        o = d[d.method == "O*"].iloc[0]
        lines.append(f"Oracle O$^\\star$ & {f(o.total_cost_J, 1)} & -- & -- & -- & -- \\\\")
        lines.append("\\midrule")
    lines = lines[:-1]
    write("tab_info.tex", "\\begin{tabular}{@{}lccccc@{}}\n\\toprule\n & $D_t$ known & \\multicolumn{2}{c}{$D_{t-1}$} & \\multicolumn{2}{c}{$D_{t-1}$, margin 0.05} \\\\\n"
          "\\cmidrule(lr){2-2}\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\nMethod & $J$ & $J$ & Viol. (\\%) & $J$ & Viol. (\\%) \\\\\n\\midrule\n"
          + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n")
    allx = pd.concat(e16_all)
    real = allx[allx.topology.isin(["abilene", "geant"])]
    piv = real[real["mode"].isin(["current", "stale"])].groupby(["topology", "scenario", "method", "mode"]).total_cost_J.mean().unstack("mode")
    _dj = float((100 * (piv.stale / piv.current - 1)).abs().max())
    macros_extra["staleRealMaxDJ"] = f(_dj, 3)
    macros_extra["staleRealDJtext"] = "less than 0.001" if _dj < 0.001 else f"at most {_dj:.3f}"
    macros_extra["staleRealMaxViol"] = f(float(real[real["mode"] == "stale"].mlu_violation_pct.max()), 3)
    nob = allx[allx.topology == "nobel"]
    pn = nob[nob["mode"].isin(["current", "stale"]) & ~nob.method.str.endswith("-m")].groupby(
        ["scenario", "method", "mode"]).total_cost_J.mean().unstack("mode")
    macros_extra["staleNobMaxDJ"] = f(float((100 * (pn.stale / pn.current - 1)).abs().max()), 3)
    sv = nob[(nob["mode"] == "stale") & ~nob.method.str.endswith("-m")].groupby(["scenario", "method"]).mlu_violation_pct.mean()
    macros_extra["staleNobViolMin"] = f(float(sv.min()), 2)
    macros_extra["staleNobViolMax"] = f(float(sv.max()), 2)
    for sc in ("base", "highload", "stress"):
        b0 = nob[(nob.scenario == sc) & (nob.method == "B0")].mlu_violation_pct.iloc[0]
        macros_extra[f"staleBzero{SC_KEY[sc]}"] = f(float(b0), 2)
        macros_extra[f"staleLiRAViol{SC_KEY[sc]}"] = f(float(sv[(sc, "LiRA")]), 2)
    mg = nob[nob.method.str.endswith("-m")].groupby(["scenario", "method"]).mlu_violation_pct.mean()
    macros_extra["marginSameViol"] = "yes" if all(abs(mg[(sc, m)] - sv[(sc, m[:-2])]) < 1e-9 for sc, m in mg.index) else "no"
    hl = nob[nob.scenario == "highload"]
    macros_extra["marginLiRAhlJ"] = f(hl[hl.method == "LiRA-m"].total_cost_J.mean(), 1)
    macros_extra["staleSeeds"] = str(int(allx[allx.method == "LiRA"].seed.nunique()))
    # E17 over all 12 settings: static + fallback against LiRA (E1, 5 seeds)
    same, tot = 0, 0
    for (t, sc), g in s17[s17.method == "Static+fallback"].groupby(["topology", "scenario"]):
        jl = runs(t, sc).query("method == 'LiRA'").total_cost_J.mean()
        js = g[g["mode"] == "current"].total_cost_J.iloc[0]
        tot += 1; same += abs(js / jl - 1) < 1e-4
        if t == "nobel":
            macros_extra[f"staticJ{SC_KEY[sc]}"] = f(js, 1)
    macros_extra["staticSame"] = str(same)
    macros_extra["staticTotal"] = str(tot)
    # Where do the D_{t-1} violations happen? Static rule (no training) against the always-on network.
    from run_static import static_config  # noqa: E402
    from run_stale import info_F, info_tab  # noqa: E402
    from run_main import SCENARIOS  # noqa: E402
    from lira.policy.lira_policy import LiRA  # noqa: E402
    from lira.policy.models import ConstantModel  # noqa: E402
    jumps, subset = [], True
    for sc in ("base", "highload", "stress"):
        cS = build_ctx("nobel", 32, **SCENARIOS[sc])
        lr_, lw_ = prices(cS)
        a_, b_ = cS.rng_idx("test")
        pol_ = LiRA()
        pol_.K, pol_.lam_R, pol_.lam_W, pol_.model = cS.K, lr_, lw_, ConstantModel(static_config(cS, lr_, lw_))
        sq_, _, _ = pol_.predict(cS, "test", tab=info_tab(cS, a_, b_, True), F=info_F(cS, a_, b_, True), seg=cS.seg[a_:b_])
        tt_ = np.arange(a_, b_)
        vi = np.flatnonzero(~cS.tab.feas[tt_, sq_])
        subset &= set(vi) <= set(np.flatnonzero(cS.tab.mlu[tt_, 0] > cS.theta + 1e-9))
        jumps += list(cS.tab.mlu[tt_, sq_][vi] - cS.tab.mlu[tt_ - 1, sq_][vi])
    macros_extra["staleJumpMin"] = f(min(jumps), 2)
    macros_extra["staleJumpMax"] = f(max(jumps), 2)
    macros_extra["staleViolAtBzero"] = "yes" if subset else "no"

# (8) numbers that the text used to type by hand
fo = pd.read_csv(R / "E14_rolling_folds" / "nobel_folds.csv").query("price_mult == 1.0")
fp = fo.pivot_table(index="fold", columns="method", values="total_cost_J")
macros_extra["foldMaxGap"] = f(float(100 * (fp[["B6", "LiRA"]].max(axis=1) / fp["O*"] - 1).max()), 2)
macros_extra["foldBfourWorst"] = "yes" if bool((fp["B4"] > fp[["B6", "LiRA"]].max(axis=1)).all()) else "no"
d = {t: runs(t, "base").groupby("method").total_cost_J.mean() for t in ("abilene", "geant")}
macros_extra["realSpread"] = f(max(100 * (g[["B4", "B6", "B7", "LiRA", "O*"]].max() / g[["B4", "B6", "B7", "LiRA", "O*"]].min() - 1)
                                   for g in d.values()), 3)
ab = runs("abilene", "base").groupby("method")[["total_cost_J", "config_changes_per_day"]].mean()
macros_extra["snapAbiGap"] = f(100 * (ab.loc["SNAP-exact", "total_cost_J"] / ab.loc["O*", "total_cost_J"] - 1), 2)
macros_extra["snapAbiChg"] = f(ab.loc["SNAP-exact", "config_changes_per_day"], 2)
macros_extra["bfourAbiGap"] = f(100 * (ab.loc["B4", "total_cost_J"] / ab.loc["O*", "total_cost_J"] - 1), 3)
macros_extra["boneGapPP"] = f(max(abs(ob[t].loc["library snapshot optimum", "savings_pct"] - ob[t].loc["B1 per-snapshot ILP", "savings_pct"])
                                  for t in TOPOS), 3)
pl = pd.read_csv(R / "E4_per_link_wear" / "nobel_base_per_link.csv").groupby("method").AF.max()
macros_extra["maxAFfour"] = f(pl["B4"], 3)
macros_extra["maxAFlira"] = f(pl["LiRA"], 4)
macros_extra["maxAFothers"] = f(max(pl["B6"], pl["B7"], pl["O*"]), 3)
dd = pd.read_csv(R / "E8_drift" / "nobel_drift.csv")
s8 = dd[(dd.method == "LiRA") & (dd["mode"] == "static")].set_index("shift")
macros_extra["driftNobSwNone"] = f(s8.loc["none", "post_config_changes_per_day"], 2)
macros_extra["driftNobSwHot"] = f(s8.loc["hotspot", "post_config_changes_per_day"], 2)
mx = 0.0
for t in TOPOS:
    s_ = pd.read_csv(R / "E8_drift" / f"{t}_drift.csv").query("method == 'LiRA' and mode == 'static'").set_index("shift").post_total_cost_J
    mx = max(mx, float((100 * (s_ / s_["none"] - 1)).max()))
macros_extra["driftMaxCostPct"] = f(mx, 2)
lab_ = json.loads((ROOT / "results" / "labels_abilene_K32.json").read_text())
macros_extra["dpRunAbi"] = f(max(lab_["dp_runtime_s"].values()), 1)
_rounds = [r["lira_best_round"] for p_ in R.glob("E1_main/*_info.json") for r in json.loads(p_.read_text())["runs"]]
macros_extra["daggerRoundZero"] = str(sum(r == 0 for r in _rounds))
macros_extra["daggerRuns"] = str(len(_rounds))
macros_extra["nobCand"] = str(json.loads((ROOT / "results" / "library_nobel_report.json").read_text())["n_candidates"])
dn = runs("nobel", "highload")
macros_extra["nobhlOchg"] = f(dn[dn.method == "O*"].config_changes_per_day.mean(), 2)
for sc in ("base", "highload", "highdyn", "stress"):
    g = runs("nobel", sc).groupby("method").total_cost_J.mean()
    macros_extra[f"nobJBtwo{SC_KEY[sc]}"] = f(g["B2-naive"], 1)
    macros_extra[f"nobJLiRA{SC_KEY[sc]}"] = f(g["LiRA"], 1)
    macros_extra[f"nobJBsix{SC_KEY[sc]}"] = f(g["B6"], 1)
    macros_extra[f"nobJO{SC_KEY[sc]}"] = f(g["O*"], 1)
zs = np.load(R / "E1_main" / "nobel_base_seqs.npz")
held = np.bincount(zs["LiRA_s0"]).max()
macros_extra["liraHold"] = f"{int(held):,}".replace(",", "\\,")
macros_extra["nobTestIntervals"] = f"{len(zs['LiRA_s0']):,}".replace(",", "\\,")
zh = np.load(R / "E1_main" / "nobel_highload_seqs.npz")
macros_extra["hlLiraOracleDiff"] = str(int(sum((zh[f"LiRA_s{s}"] != zh["O*_s0"]).sum() for s in range(5))))
from lira.models.power import PowerModel  # noqa: E402
from lira.models.wear import WearModel  # noqa: E402
_pw, _wr = PowerModel.from_yaml(), WearModel.from_yaml()
macros_extra["wearCredit"] = f(0.0008 / _wr.chi * (_wr.af_on - _wr.af_off), 3)   # lam_W (1 - alpha) / n_d
for t in TOPOS:
    L_ = meta[t]["links_undirected"]
    macros_extra[f"sleepSave{t[:3]}"] = f((_pw.port_idle_w - _pw.port_sleep_w) / (_pw.port_idle_w * L_), 3)
stt = pd.read_csv(R / "E1_main" / "stats_wilcoxon_holm.csv").set_index(["topology", "scenario", "comparison"])
for sc in ("base", "highload"):
    r_ = stt.loc[("nobel", sc, "LiRA vs B6")]
    macros_extra[f"effBsix{SC_KEY[sc]}"] = f(r_.mean_daily_J_diff, 2)
    macros_extra[f"effBsixDays{SC_KEY[sc]}"] = f(r_.lira_better_days_pct, 0)
with open(G / "results_macros.tex", "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(f"\\newcommand{{\\{mname(k)}}}{{{v}}}" for k, v in macros_extra.items()) + "\n")
print("generated", sorted(p.name for p in G.iterdir()))
