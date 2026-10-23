"""Build paper/results/RESULTS.md and figures from the saved CSV files only.

No number is typed by hand: every table cell is read from paper/results/*/*.csv|json.
Findings text is written separately (paper/results/FINDINGS.md) after reading the tables.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "paper" / "results"
FIG = R / "figures"
FIG.mkdir(exist_ok=True)
TOPOS = ("abilene", "geant", "nobel")
SCEN = ("base", "highload", "highdyn", "stress")
NAMES = {"abilene": "Abilene", "geant": "GÉANT", "nobel": "Nobel-Germany"}


def ci95(x):
    from scipy import stats
    x = np.asarray(x, float)
    return stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan


def md(df, fmt="{:.3f}"):
    df = df.copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else fmt.format(v))
    return df.to_markdown(index=False)


def pm(x, nd=2):
    x = np.asarray(x, float)
    return f"{x.mean():.{nd}f} ± {ci95(x):.{nd}f}" if len(x) > 1 else f"{x.mean():.{nd}f}"


out = []
w = out.append


def section(title, level=2):
    w("\n" + "#" * level + " " + title + "\n")


# ----------------------------------------------------------------------------- header
w("# Experimental results (measured)\n")
w("All numbers below are produced by `experiments/run_main.py` and `experiments/run_extra.py` and read "
  "from the CSV files in this folder by `experiments/make_report.py`. Nothing is typed by hand.\n")
env = json.loads((R / "environment.json").read_text())
section("Environment")
w("| item | value |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in env.items()))

section("Data (Phase 2)")
rows = []
for t in TOPOS:
    m = json.loads((ROOT / "data" / "processed" / t / "meta.json").read_text())
    rows.append({"topology": NAMES[t], "nodes": m["nodes"], "links": m["links_undirected"],
                 "OD pairs": m["od_pairs"], "interval": m["freq"], "intervals kept": m["T"],
                 "start": m["start"][:10], "end": m["end"][:10],
                 "dropped (gaps/outages)": m.get("dropped", "n/a (synthetic)"),
                 "spikes removed": m.get("volume_spikes_removed", "n/a"),
                 "scale factor": f"{m['scale_factor']:.4g}", "type": "semi-synthetic" if m.get("semi_synthetic") else "real (SNDlib)"})
w(pd.DataFrame(rows).to_markdown(index=False))

# ----------------------------------------------------------------------------- E1
section("E1 Main comparison (test split; 5 seeds; mean ± 95% CI over seeds)")
cols = [("savings_pct", "Savings S (%)", 2), ("config_changes_per_day", "Changes/day", 2),
        ("link_transitions_per_day", "Link transitions/day", 2), ("mlu_violation_pct", "MLU viol. (%)", 3),
        ("total_cost_J", "Total cost J", 1), ("mean_AF", "Mean AF", 3),
        ("latency_median_ms", "Median latency (ms)", 3)]
order = ["B0", "SNAP-exact", "B2-naive", "B2-perfect", "B4", "B6", "B7", "LiRA", "O*"]
headline = []
for t in TOPOS:
    for sc in SCEN:
        f = R / "E1_main" / f"{t}_{sc}_runs.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f)
        info = json.loads((R / "E1_main" / f"{t}_{sc}_info.json").read_text())
        section(f"{NAMES[t]} — {sc} scenario (λR={info['lam_R']:.3g}, λW={info['lam_W']:.3g}, K={info['K']})", 3)
        rows = []
        for m in order:
            g = d[d.method == m]
            if g.empty:
                continue
            row = {"method": m}
            for c, lab, nd in cols:
                if c in g and g[c].notna().any():
                    row[lab] = pm(g[c].dropna(), nd)
                else:
                    row[lab] = ""
            rows.append(row)
        w(pd.DataFrame(rows).to_markdown(index=False))
        # X, Y, Z of LiRA relative to B4 (paired by seed)
        b4, li = d[d.method == "B4"].set_index("seed"), d[d.method == "LiRA"].set_index("seed")
        X = 100 * li.savings_pct / b4.savings_pct
        has = (b4.config_changes_per_day > 0).all()
        Y = 100 * (1 - li.config_changes_per_day / b4.config_changes_per_day) if has else None
        Z = 100 * (1 - li.link_transitions_per_day / b4.link_transitions_per_day) if has else None
        w(f"\nLiRA vs B4: retention X = {pm(X)} %; change reduction Y = "
          f"{pm(Y) if has else 'undefined (B4 makes 0 configuration changes)'}; transition reduction Z = "
          f"{pm(Z) if has else 'undefined (B4 makes 0 transitions)'}.\n")
        headline.append({"topology": NAMES[t], "scenario": sc, "X retention %": X.mean(),
                         "Y change reduction %": Y.mean() if has else np.nan,
                         "Z transition reduction %": Z.mean() if has else np.nan,
                         "B4 changes/day": b4.config_changes_per_day.mean(),
                         "LiRA changes/day": li.config_changes_per_day.mean(),
                         "LiRA median latency ms": li.latency_median_ms.mean()})
section("Headline numbers (LiRA relative to B4)", 3)
if headline:
    w(md(pd.DataFrame(headline), "{:.2f}"))
    pd.DataFrame(headline).to_csv(R / "headline.csv", index=False)
f = R / "E1_main" / "stats_wilcoxon_holm.csv"
if f.exists():
    section("E1 Statistical tests (Wilcoxon signed-rank on per-day cost, Holm-corrected)", 3)
    w(md(pd.read_csv(f), "{:.4g}"))

# ----------------------------------------------------------------------------- E2
section("E2 Energy versus stability (price sweep)")
fig, axes = plt.subplots(len(TOPOS), len(SCEN), figsize=(4.2 * len(SCEN), 3.2 * len(TOPOS)), squeeze=False)
any_e2 = False
for i, t in enumerate(TOPOS):
    for j, sc in enumerate(SCEN):
        f = R / "E2_pareto" / f"{t}_{sc}_pareto.csv"
        if not f.exists():
            axes[i][j].axis("off"); continue
        any_e2 = True
        d = pd.read_csv(f)
        ax = axes[i][j]
        for m, mk in (("B6", "s-"), ("B7", "^-"), ("O*", "k*--"), ("LiRA", "ro-")):
            g = d[d.method == m]
            ax.plot(g.savings_pct, g.config_changes_per_day + 1e-3, mk, label=m, ms=4)
        g = d[d.method == "B4"]
        ax.plot(g.savings_pct, g.config_changes_per_day + 1e-3, "bD", label="B4")
        ax.set_yscale("log"); ax.set_xlabel("Energy savings (%)"); ax.set_ylabel("Changes/day (+0.001)")
        ax.set_title(f"{NAMES[t]} - {sc}", fontsize=9); ax.grid(alpha=.3)
        if i == 0 and j == 0:
            ax.legend(fontsize=7)
        w(f"\n**{NAMES[t]} / {sc}**\n")
        g = d[d.method.isin(["O*", "LiRA"])][["method", "param", "savings_pct", "config_changes_per_day",
                                               "link_transitions_per_day", "total_cost_J", "mlu_violation_pct"]]
        w(md(g.rename(columns={"param": "price×"}), "{:.3f}"))
plt.tight_layout()
if any_e2:
    plt.savefig(FIG / "E2_pareto.png", dpi=150)
    w("\n![Pareto](figures/E2_pareto.png)\n")
plt.close()

# ----------------------------------------------------------------------------- E3/E4/E9/E12
section("E3 Case-study week")
for p in sorted((R / "E3_case_study").glob("*_first_week.csv")):
    d = pd.read_csv(p)
    w(f"- `{p.name}`: first test week, {len(d)} intervals. Configuration changes in the week: " +
      ", ".join(f"{m} {int((d[f'{m}_config'].diff().fillna(0) != 0).sum())}" for m in ("B4", "B6", "B7", "LiRA", "O*")))
fig, axes = plt.subplots(len(TOPOS), 1, figsize=(9, 2.4 * len(TOPOS)), squeeze=False)
for i, t in enumerate(TOPOS):
    p = R / "E3_case_study" / f"{t}_base_busiest_week.csv"
    if not p.exists():
        continue
    d = pd.read_csv(p)
    ax = axes[i][0]
    for m, c in (("B4", "tab:blue"), ("B6", "tab:green"), ("LiRA", "tab:red")):
        ax.step(d.t, d[f"{m}_config"] + {"B4": 0, "B6": 0.15, "LiRA": 0.3}[m], c, lw=.8, label=m)
    ax.set_title(f"{NAMES[t]}: configuration index over the busiest test week (offset for visibility)", fontsize=8)
    ax.legend(fontsize=7, ncol=3)
plt.tight_layout(); plt.savefig(FIG / "E3_case_study.png", dpi=150); plt.close()
w("\n![case study](figures/E3_case_study.png)\n")

section("E4 Per-link transitions and wear")
rows = []
for t in TOPOS:
    for sc in SCEN:
        p = R / "E4_per_link_wear" / f"{t}_{sc}_per_link.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p)
        for m, g in d.groupby("method"):
            rows.append({"topology": NAMES[t], "scenario": sc, "method": m,
                         "mean transitions/link/day": g.transitions_per_day.mean(),
                         "max transitions/link/day": g.transitions_per_day.max(),
                         "mean AF": g.AF.mean(), "max AF": g.AF.max(),
                         "mean lifetime change vs always-on (%)": g.lifetime_change_pct_vs_alwayson.mean()})
w(md(pd.DataFrame(rows), "{:.3f}") if rows else "_not available_")

section("E9 Wear-model sensitivity (mean AF of the same decision sequences)")
for t in TOPOS:
    p = R / "E9_wear_sensitivity" / f"{t}_base_sensitivity.csv"
    if not p.exists():
        continue
    d = pd.read_csv(p)
    piv = d[d.af_off == 0.5].pivot_table(index="chi", columns="method", values="mean_AF")
    w(f"\n**{NAMES[t]}** (AF_off = 0.5; AF of always-on = 1)\n")
    w(piv.reset_index().to_markdown(index=False, floatfmt=".4f"))
    flip = d[(d.method == "B4")].merge(d[d.method == "LiRA"], on=["chi", "af_off", "topology", "scenario"], suffixes=("_B4", "_LiRA"))
    w(f"\nParameter combinations where B4 has a higher mean AF than LiRA: "
      f"{int((flip.mean_AF_B4 > flip.mean_AF_LiRA + 1e-9).sum())} of {len(flip)}; "
      f"combinations where LiRA's mean AF exceeds always-on (1.0): {int((d[d.method == 'LiRA'].mean_AF > 1 + 1e-9).sum())} of {len(flip)}.\n")

section("E12 Gap to the offline oracle")
rows = []
for t in TOPOS:
    p = R / "E12_gap_to_oracle" / f"{t}_base_regret.csv"
    if not p.exists():
        continue
    d = pd.read_csv(p)
    d["method"] = d.run.str.replace(r"_s\d+$", "", regex=True)
    for m, g in d.groupby("method"):
        rows.append({"topology": NAMES[t], "method": m, "mean regret vs O* (%)": g.regret_vs_oracle_pct.mean()})
w(md(pd.DataFrame(rows), "{:.3f}") if rows else "_not available_")

# ----------------------------------------------------------------------------- E5
section("E5 Decision time and optimisation baselines")
for p in sorted((R / "E5_latency_scalability").glob("*_opt_baselines.csv")):
    d = pd.read_csv(p)
    w(f"\n**{p.stem.replace('_opt_baselines', '')}** (test subsample)\n")
    w(md(d, "{:.3f}"))
p = R / "E5_latency_scalability" / "scalability.csv"
if p.exists():
    w("\n**Scalability of the optimisation step and the safety check**\n")
    w(md(pd.read_csv(p), "{:.4g}"))
else:
    w("\n_scalability study not available_\n")
rows = []
for t in TOPOS:
    f = R / "E1_main" / f"{t}_base_runs.csv"
    if f.exists():
        d = pd.read_csv(f)
        for m in ("B2-naive", "B4", "LiRA"):
            g = d[d.method == m]
            rows.append({"topology": NAMES[t], "method": m, "median ms": g.latency_median_ms.mean(),
                         "p99 ms": g.latency_p99_ms.mean()})
if rows:
    w("\n**Single-threaded decision latency of library-based methods (batch size 1)**\n")
    w(md(pd.DataFrame(rows), "{:.3f}"))

# ----------------------------------------------------------------------------- E6, E7
section("E6 Library size")
for t in TOPOS:
    p = R / "E6_library_size" / f"{t}_K.csv"
    if p.exists():
        d = pd.read_csv(p)
        w(f"\n**{NAMES[t]}**\n")
        w(md(d[["K_requested", "K_actual", "val_coverage", "method", "savings_pct", "config_changes_per_day",
                "mlu_violation_pct", "total_cost_J"]], "{:.3f}"))
section("E7 Ablation (LiRA variants; mean over 3 seeds)")
for t in TOPOS:
    for sc in SCEN:
        p = R / "E7_ablation" / f"{t}_{sc}_ablation.csv"
        if p.exists():
            d = pd.read_csv(p)
            g = d.groupby(["price_mult", "variant"], sort=False)[
                ["savings_pct", "config_changes_per_day", "link_transitions_per_day", "mlu_violation_pct", "total_cost_J"]].mean().reset_index()
            w(f"\n**{NAMES[t]} / {sc}** (price_mult scales lam_R only)\n")
            w(md(g, "{:.3f}"))

# ----------------------------------------------------------------------------- E8, E10, E13, E14
section("E8 Drift")
for t in TOPOS:
    p = R / "E8_drift" / f"{t}_drift.csv"
    if p.exists():
        d = pd.read_csv(p)
        w(f"\n**{NAMES[t]}** (Page-Hinkley threshold {d.ph_threshold.dropna().iloc[0]})\n")
        keep = ["shift", "method", "mode", "detections", "detection_delay_hours", "false_alarms_per_1k_intervals",
                "retrains", "retrain_total_s", "library_configs_added", "post_savings_pct", "post_total_cost_J",
                "post_mlu_violation_pct"]
        w(md(d[keep], "{:.3f}"))
section("E10 Utilization threshold θ")
for t in TOPOS:
    p = R / "E10_theta" / f"{t}_theta.csv"
    if p.exists():
        d = pd.read_csv(p)
        w(f"\n**{NAMES[t]}**\n")
        w(md(d[["theta", "method", "test_coverage_pct", "alwayson_violation_pct", "library_size", "savings_pct",
                "config_changes_per_day", "mlu_violation_pct", "total_cost_J"]], "{:.3f}"))
section("E13 Model choice")
for t in TOPOS:
    p = R / "E13_model_choice" / f"{t}_models.csv"
    if p.exists():
        d = pd.read_csv(p)
        cols_ = [c for c in ["price_mult", "backend", "method", "lira_model", "savings_pct", "config_changes_per_day",
                             "total_cost_J", "latency_median_ms", "error"] if c in d]
        w(f"\n**{NAMES[t]}**\n")
        w(md(d[cols_], "{:.3f}"))
section("E14 Rolling-origin folds")
for t in TOPOS:
    p = R / "E14_rolling_folds" / f"{t}_folds.csv"
    if p.exists():
        d = pd.read_csv(p)
        g = d.groupby(["price_mult", "method"])[["savings_pct", "config_changes_per_day", "total_cost_J"]].agg(["mean", "std"])
        g.columns = ["_".join(c) for c in g.columns]
        w(f"\n**{NAMES[t]}** (mean and std over 4 folds)\n")
        w(md(g.reset_index(), "{:.3f}"))

section("E11 Mininet emulation (most active Nobel-Germany day, 2 s per interval, 1 s modeled wake-up)")
_p = R / "E11_emulation" / "emulation_summary.csv"
if _p.exists():
    w(md(pd.read_csv(_p).drop(columns=["intervals", "seconds_per_interval", "wake_delay_s"]), "{:.3f}"))
else:
    w("_not available_")

(R / "RESULTS.md").write_text("\n".join(out), encoding="utf-8")
print("wrote", R / "RESULTS.md", len("\n".join(out)), "chars")
