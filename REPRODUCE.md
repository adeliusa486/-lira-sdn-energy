# Reproducing the results

All commands run from the project root. `reproduce.ps1` runs them in this order. Every experiment script skips outputs that already exist, so delete a CSV to recompute it, or pass `--force`.

## 0. Environment

Python 3.11.9 and the pinned versions in `requirements.txt`. The versions used for the results are recorded in `results/environment.json`. HiGHS (through `highspy` and `scipy.optimize.milp`) solves every integer and linear program, so no commercial solver is needed.

## 1. Data (about 10 minutes)

```powershell
python -m lira.data.download                 # SNDlib topologies and dynamic traffic, hashes in data/MANIFEST.json
python -m lira.data.preprocess abilene geant  # cleaning, splits, scaling
python -m lira.data.preprocess nobel          # needs processed Abilene (weekly profile and noise scale)
python -m lira.data.features abilene geant nobel
python -m pytest -q tests                      # 18 tests
```

## 2. Configuration libraries (4 to 6 hours of ILP time)

The scenario is selected with environment variables, which set the artifact suffix (`lira.scenario_tag`):

| Scenario | `LIRA_LOAD` | `LIRA_DYN` | `LIRA_THETA` | Suffix |
|---|---|---|---|---|
| base | 1 | unset | 0.8 | none |
| high load | 1.6 | unset | 0.8 | `_L1.6` |
| high dynamic power | 1 | 15 | 0.8 | `_L1_D15` |
| stress | 1.6 | 15 | 0.8 | `_L1.6_D15` |
| θ sweep | 1 | unset | 0.6, 0.7, 0.9 | `_T0.6`, `_T0.7`, `_T0.9` |

For each scenario and each topology: `python -m lira.library.build_library <topology>` (defaults: 64 clusters, K = 8, 16, 32, 64, 128, NSGA-II on, 300 s ILP limit). Outputs: `artifacts/library/*.pkl`, `results/library_*_report.json`, `results/library_*_solver_log.csv`.

## 3. Oracle labels and DP-versus-MILP check

For the four θ = 0.8 scenarios and each topology: `python -m lira.oracle.make_labels <topology> --K 32`. Outputs: `artifacts/labels/*.npz`, `results/dp_milp_validation_*.csv`, `results/labels_*.json`.

## 4. Experiments (6 to 8 hours)

| Command | Experiments | Output folder in `results/` |
|---|---|---|
| `python experiments/run_main.py --exp E1 E2 E2b E6 E7` | main comparison (5 seeds), derived E3, E4, E9, E12, Wilcoxon-Holm tests, price sweeps, library size, ablation | `E1_main`, `E2_pareto`, `E3_case_study`, `E4_per_link_wear`, `E6_library_size`, `E7_ablation`, `E9_wear_sensitivity`, `E12_gap_to_oracle` |
| `python experiments/run_extra.py --exp E1b E5 E8 E10 E13 E14` | per-snapshot ILP, NSGA-II, greedy, scalability (downloads Germany50 and TA2), drift, θ sweep, model choice, rolling folds | `E5_latency_scalability`, `E8_drift`, `E10_theta`, `E13_model_choice`, `E14_rolling_folds` |
| `python experiments/run_milp.py` | E15: per-interval exact MILP lower bound | `E15_full_milp` |
| `python experiments/run_stale.py` | E16: decisions on the previous interval's traffic matrix (3 seeds) | `E16_stale_tm` |
| `python experiments/run_static.py` | E17: static configuration with LiRA's safety fallback | `E17_static_fallback` |
| `python experiments/run_variant.py --exp E18` | E18: main study without a wear price (lambda_W = 0, all methods retrained) | `E18_no_wear` |
| `python experiments/make_nobel_variants.py`, then `python -m lira.library.build_library <v> --K 32` for v in nobel_ar05 nobel_ar09 nobel_s06, then `python experiments/run_variant.py --exp E19 --topos nobel_ar05 nobel_ar09 nobel_s06` | E19: Nobel-Germany with AR(1)-correlated and weaker noise | `E19_noise` |

## 5. Emulation (E11, WSL2 Ubuntu, root)

```powershell
python experiments/emu_export.py                      # busiest B4 day of Nobel-Germany -> input.json
wsl -u root bash experiments/run_emulation.sh          # 5 runs: B4 x3, LiRA, B0
python experiments/emu_analyze.py                      # emulation_summary.csv, emulation_transitions.csv
```

## 6. Report and tables

```powershell
python experiments/make_report.py                     # results/RESULTS.md, headline.csv, figures
python tools/make_paper_assets.py                     # macros, tables and plot data -> submission/generated/
```

The manuscript is kept outside this repository. It reads every number from `submission/generated/`.

## Determinism

Seeds are fixed in k-means, NSGA-II, XGBoost, LightGBM, the random forest, the MLP and the DAgger rollouts. Seeds 0 to 2 of E7 reproduce seeds 0 to 2 of E1 exactly. Time-limited solves (library building, E1b) can differ across machines if a limit is reached, which the solver logs record.
