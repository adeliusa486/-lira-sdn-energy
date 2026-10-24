# LiRA: Sequence-Aware Learning for Energy-Efficient SDN

Code, data and results for a study of learned link sleeping in software-defined networks. LiRA stands for Lifetime- and Reconfiguration-Aware learning.

Energy-aware SDN controllers put idle links to sleep. Most learned controllers pick a configuration for each traffic matrix on its own and ignore what a change costs: link wake-ups, flow-rule updates and device wear. This repository solves the sequential problem exactly, trains a policy to imitate the solution, and measures when that history-awareness helps.

## What the study finds

All numbers are measured and stored in `results/`.

| Setting | Result |
|---|---|
| Abilene and GÉANT (real traces) | The optimal configuration sequence is constant. LiRA, a snapshot classifier, hysteresis and the oracle agree within 0.014%, with 24.0% and 29.8% energy savings |
| Nobel-Germany (semi-synthetic, noisy) | A gradient-boosted snapshot classifier changes configuration 11.7 times per day and costs 6.5% more than the oracle. Holding a configuration removes 97.7% of the changes at no energy cost |
| Non-learning rules | Hysteresis, a rolling-horizon optimizer and a static configuration with LiRA's fallback match LiRA. The static rule equals LiRA in 11 of 12 settings |
| Noise structure | With AR(1) noise (ρ = 0.5) the snapshot classifier costs 32.5% more than the oracle. With half the noise it does not flap |
| Library restriction | A per-interval exact integer program shows the configuration library loses at most 0.045% |
| One-interval-old traffic | Costs barely change, but up to 0.19% of Nobel-Germany intervals exceed the utilization bound |

`results/FINDINGS.md` discusses each experiment and `results/RESULTS.md` lists every table.

## Method

1. **Configuration library.** k-means on training traffic, an energy integer program per cluster, NSGA-II for diversity, and a set cover over training and validation traffic (`lira/library/`).
2. **Exact oracle.** Energy, reconfiguration cost and wear form one objective over the library. Dynamic programming (Viterbi) solves it in O(TK²) and matches an independent MILP to 1e-14 (`lira/oracle/`).
3. **LiRA policy.** An XGBoost classifier conditioned on traffic features, the installed configuration and its dwell time, trained by cost-sensitive imitation with DAgger and wrapped in a utilization safety layer (`lira/policy/`).
4. **Baselines.** Always-on, snapshot classifier, hysteresis, minimum dwell, rolling horizon, static configuration, per-snapshot ILP, NSGA-II and an ElasticTree-style greedy rule (`lira/baselines/`, `experiments/`).

## Installation

Python 3.11. All solvers are open source (HiGHS through `highspy` and SciPy).

```bash
git clone https://github.com/adeliusa486/-lira-sdn-energy.git lira-sdn
cd lira-sdn
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Quick start

The repository ships the processed traffic, the configuration libraries, the oracle labels and all result files. Only the feature matrices are left out because of their size. Build them first (about two minutes):

```bash
python -m lira.data.features abilene geant nobel nobel_ar05 nobel_ar09 nobel_s06
python -m pytest -q tests                 # 18 unit tests
python tools/make_paper_assets.py         # LaTeX macros, tables and plot data from results/
python experiments/run_static.py --force  # rerun one experiment group (about 5 minutes)
```

A rerun overwrites the CSV files in `results/`, so `git diff results/` shows whether you reproduced the shipped numbers.

## Full reproduction

`REPRODUCE.md` lists every step and `reproduce.ps1` runs them in order on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File reproduce.ps1                     # from the raw SNDlib downloads
powershell -ExecutionPolicy Bypass -File reproduce.ps1 -From experiments   # reuse the shipped libraries
```

Expect 4 to 6 hours of ILP time for the libraries and 6 to 8 hours for the experiments on a 14-core laptop. The raw SNDlib files (about 900 MB) are not in the repository. `python -m lira.data.download` fetches them and checks their SHA-256 hashes against `data/MANIFEST.json`.

## Repository layout

| Path | Content |
|---|---|
| `lira/` | Data pipeline, network, power, wear and reconfiguration models, library builder, oracle, baselines, policies |
| `experiments/` | One script per experiment group, the Mininet emulation, the report builder |
| `results/` | Outputs of experiments E1 to E19, library reports, DP-versus-MILP checks, run logs |
| `artifacts/` | Configuration libraries and oracle labels per topology and scenario |
| `data/` | `MANIFEST.json` and processed traffic, splits and metadata |
| `configs/power.yaml` | Power and wear constants with their sources |
| `tests/` | Unit tests for data, models, oracle and baselines |
| `tools/` | Table generator, reference verification and BibTeX helpers |

## Experiments

| Script | Experiments |
|---|---|
| `experiments/run_main.py` | E1 main comparison (5 seeds), E2 price sweeps, E3 case study, E4 per-link wear, E6 library size, E7 ablation, E9 wear sensitivity, E12 gap to oracle |
| `experiments/run_extra.py` | E1b and E5 optimization baselines and scalability, E8 drift, E10 threshold sweep, E13 model choice, E14 rolling folds |
| `experiments/run_milp.py` | E15 per-interval lower bound |
| `experiments/run_stale.py` | E16 decisions on the previous interval's traffic |
| `experiments/run_static.py` | E17 static configuration with LiRA's fallback |
| `experiments/run_variant.py` | E18 no wear price, E19 noise variants of Nobel-Germany |
| `experiments/emulate_mininet.py` | E11 Mininet and Open vSwitch emulation (Linux or WSL2, root) |

Scenarios are selected with the environment variables `LIRA_LOAD`, `LIRA_DYN` and `LIRA_THETA` (values in `REPRODUCE.md`).

## Limitations

- Nobel-Germany is semi-synthetic. Its per-interval noise has no temporal correlation.
- Port power and wear parameters are representative assumptions, not measurements of a device.
- The main results let the controller see the traffic of the interval it configures. E16 measures the effect of one-interval-old traffic.
- The emulation uses a modeled 1 s wake-up delay and no real line cards.
- No deep reinforcement learning baseline is included.

## Citation

The manuscript is under review. Until it is published, please cite this repository.
