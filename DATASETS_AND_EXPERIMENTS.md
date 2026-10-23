# Datasets, Simulations and Experiments

## 1. Datasets

| ID | Topology | Nodes / links* | Traffic | Granularity | Span | Source |
|---|---|---|---|---|---|---|
| D1 | Abilene | 12 / 15 (30 directed) | Real TMs (Zhang et al., tomogravity-estimated from Abilene netflow) | 5 min | 24 weeks, Mar–Sep 2004 (~48k TMs) | Y. Zhang Abilene TM page; also in SNDlib `abilene` |
| D2 | GÉANT | 22 / 36 (72 directed) | Real TMs (Uhlig et al. 2006) | 15 min | ~4 months, 2005 (~10.7k TMs) | TOTEM project / SNDlib `geant` |
| D3 | Nobel-Germany | 17 / 26 (52 directed) | SNDlib dynamic demands if available, else synthetic series | 5 min | verify in Phase 2 | SNDlib `nobel-germany` |
| D4 (stress) | Synthetic drift sets from D1/D2 | same | Injected shifts: growth ramp, diurnal phase shift, hotspot, link-failure reroute | same | built in Phase 8 | generated |
| D5 (scale) | Topology Zoo (e.g., Cogent ~197 nodes, GtsCe ~149) | large | Gravity model + diurnal profile | 5 min | 7 days | Topology Zoo |

\*Counts must be checked against the files downloaded in Phase 2 and the checked values written in `PROGRESS.md`. Published papers differ on link counts depending on parallel links.

**Splits (chronological, no shuffling):** 60% train / 15% validation / 25% test per topology. Rolling-origin evaluation (4 folds) for robustness.

**Preprocessing:** units to Mbps; drop or interpolate missing intervals (log the count); scale TMs so peak MLU on the full-power shortest-path routing is ≈ 0.5 (standard practice; report the scaling factor); features = flattened TM, total volume, top-k OD pairs, PCA (95% variance), time-of-day sin/cos, day-of-week, deltas over the last h intervals.

## 2. Simulation / emulation stack

| Layer | Tool | Use |
|---|---|---|
| Flow-level simulator | Own Python (NetworkX + NumPy), vectorised path-flow | All large-scale experiments (millions of decisions) |
| Optimisation | Gurobi 11 (academic) or HiGHS (open), PuLP/Pyomo | ILP config generation, multi-period MILP baseline |
| GA | pymoo NSGA-II | GA baseline and library diversity |
| ML | scikit-learn, XGBoost/LightGBM, PyTorch | Snapshot and LiRA policies |
| Drift | river (ADWIN, Page-Hinkley), SciPy KS | Phase 8 |
| Packet-level emulation | Mininet 2.3 + Open vSwitch + Ryu (or ONOS) controller | Transition disruption, rule-update latency, loss |
| DRL (optional) | Stable-Baselines3 PPO | Extra baseline |

**Hardware to report:** CPU model, cores, RAM, GPU (if used for MLP/PPO), OS, Python version, solver version. Inference latency measured single-threaded with batch size 1, median and p99 over 10k decisions.

## 3. Methods compared

| ID | Method | Notes |
|---|---|---|
| B0 | Always-on, OSPF/shortest path | Energy reference (savings = 0) |
| B1 | Per-snapshot ILP (optimal energy per TM) | Upper bound on savings, no switching awareness |
| B2 | Multi-period MILP with switching + wear cost (rolling horizon H=12) | Strong optimisation baseline, slow |
| B3 | GA / NSGA-II per snapshot | Metaheuristic baseline |
| B4 | Snapshot-ML classifier (reproduction of prior frameworks) | Main competitor |
| B5 | ElasticTree-style greedy | Classic heuristic |
| B6 | Snapshot-ML + hysteresis (switch only if gain > δ) | Simple fix, must beat it |
| B7 | Snapshot-ML + minimum dwell time | Simple fix |
| B8 | PPO (DRL) with the same reward | Optional |
| O* | Offline DP oracle (full knowledge) | Lower bound on sequence cost |
| **LiRA** | Proposed | |

## 4. Metrics

- **Energy savings** S (%) vs B0. **Retention X** = S_LiRA / S_B4 × 100.
- **Config changes** per day, **Y** = reduction vs B4 (%).
- **Link power-state transitions** per day, **Z** = reduction vs B4 (%).
- **Rule updates** (flow-mods) per day.
- **Lifetime**: mean/max link AF from the wear model; implied lifetime change (%).
- **QoS**: MLU distribution, % of intervals with MLU > θ (SLA violations), traffic on disrupted paths.
- **Emulation**: packet loss and latency spikes during transitions, rule-install time.
- **Decision latency T** (ms): median, p99; plus training time.
- **Total sequence cost** and **regret vs oracle** O*.
- **Classification metrics** (accuracy, macro-F1, top-3 accuracy) for B4/LiRA. These are secondary, since cost matters more than accuracy.
- **Drift**: detection delay, false alarms per 1k intervals, cost recovery after retraining.

## 5. Experiment list

| ID | Experiment | Data | Output (figure/table) |
|---|---|---|---|
| E1 | Main comparison, all methods, 3 topologies | D1–D3 test | Main results table (S, X, Y, Z, MLU viol., T) |
| E2 | Energy-vs-stability Pareto front (sweep λ_R, λ_W) | D1–D3 | Pareto plot |
| E3 | Time-series case study (one week) | D1 | Configs/power/transitions over time |
| E4 | Per-link transition histogram and wear AF | D1, D2 | CDF plot + lifetime table |
| E5 | Decision latency and scalability (K, |E|) | D1–D3, D5 | Latency vs topology size plot |
| E6 | Library size K sensitivity (8→256) | D1, D2 | Savings and coverage vs K |
| E7 | Ablation: −history, −prev-config, −cost-sensitive loss, −DAgger, −safety, −drift | D1–D3 | Ablation table |
| E8 | Drift: injected shifts, detection delay, recovery | D4 | Drift timeline plot + table |
| E9 | Wear-model sensitivity (χ, AF params) | D1, D2 | Sensitivity plot |
| E10 | MLU threshold θ sweep | D1–D3 | Trade-off curve |
| E11 | Mininet emulation of transitions (loss, latency, rule-install time) | D1 (Abilene in Mininet) | Emulation table + CDF |
| E12 | Gap to oracle O* and to MILP B2 | D1–D3 | Regret table |
| E13 | Model choice (XGB vs LightGBM vs MLP vs LSTM vs RF) | D1–D3 | Small table |
| E14 | Generalisation across time (rolling folds) and cross-season | D1 | Robustness table |

**Statistics:** 5 seeds for each stochastic component (GA, NN init, DAgger); 4 rolling folds; report mean ± 95% CI; Wilcoxon signed-rank on daily costs (LiRA vs B4, B6, B7), Holm correction. Make figures from CSV with one script (`experiments/make_figures.py`), so every plot is reproducible.
