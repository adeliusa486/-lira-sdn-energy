# LiRA: Sequence-Aware Learning for Energy-Efficient SDN

Code, data pipeline, experiments and manuscript for *Sequence-Aware Learning for Energy-Efficient Software-Defined Networks: An Exact Oracle and an Empirical Study of When History Matters*. LiRA stands for Lifetime- and Reconfiguration-Aware learning.

Energy-aware SDN controllers put idle links to sleep. Most learned controllers pick a configuration for each traffic matrix on its own and ignore what a change costs: link wake-ups, flow-rule updates and device wear. This repository formulates the choice as a sequential problem, solves it exactly, trains a policy to imitate the solution, and measures when that history-awareness helps.

## Contents

- [What the study finds](#what-the-study-finds)
- [Method](#method)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Full reproduction](#full-reproduction)
- [Repository layout](#repository-layout)
- [Experiments](#experiments)
- [Testing](#testing)
- [Limitations](#limitations)
- [Citation](#citation)

## What the study finds

All numbers below are measured. They come from `paper/results/`, and the paper reads them through generated macros only.

| Setting | Result |
|---|---|
| Abilene and GÉANT (real traces) | The optimal configuration sequence is constant. LiRA, a snapshot classifier, hysteresis and the oracle agree within 0.014%, with 24.0% and 29.8% energy savings |
| Nobel-Germany (semi-synthetic, noisy) | A gradient-boosted snapshot classifier changes configuration 11.7 times per day. Holding a configuration removes 97.7% of the changes at no energy cost |
| Non-learning rules | Hysteresis, a rolling-horizon optimizer and a static configuration with LiRA's fallback match LiRA. The static rule equals LiRA in 11 of 12 settings |
| Library restriction | A per-interval exact integer program shows the configuration library loses at most 0.045% |
| One-interval-old traffic | Costs barely change, but up to 0.19% of Nobel-Germany intervals exceed the utilization bound |

The full discussion is in `paper/main.pdf` and `paper/results/FINDINGS.md`.

## Method

1. **Configuration library.** k-means on training traffic, an energy integer program per cluster, NSGA-II for diversity, and a set cover over training and validation traffic (`lira/library/`).
2. **Exact oracle.** Energy, reconfiguration cost and wear form one objective over the library. Dynamic programming (Viterbi) solves it in O(TK²) and matches an independent MILP to 1e-14 (`lira/oracle/`).
3. **LiRA policy.** An XGBoost classifier conditioned on traffic features, the installed configuration and its dwell time. It is trained by cost-sensitive imitation with DAgger and wrapped in a utilization safety layer (`lira/policy/`).
4. **Baselines.** Always-on, snapshot classifier, hysteresis, minimum dwell, rolling horizon, static configuration, per-snapshot ILP, NSGA-II and an ElasticTree-style greedy rule (`lira/baselines/`, `experiments/`).

## Installation

Requires Python 3.11. All solvers are open source (HiGHS through `highspy` and SciPy).

**Linux or macOS**

```bash
git clone <repository-url> lira-sdn
cd lira-sdn
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
git clone <repository-url> lira-sdn
cd lira-sdn
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Replace `<repository-url>` with the URL of this repository. The versions used for the paper are pinned in `requirements.txt` and recorded in `paper/results/environment.json`.

## Quick start

The repository ships processed traffic, configuration libraries and all result files, so you can check the setup and rebuild the paper's tables without rerunning experiments.

```bash
python -m pytest -q tests                  # 18 tests
python paper/tools/make_paper_assets.py    # macros and tables from paper/results/
cd paper && latexmk -pdf main.tex          # needs a LaTeX distribution
```

To rerun one experiment group, delete its output or pass `--force`:

```bash
python experiments/run_static.py --force   # static rule, a few minutes
```

## Full reproduction

`REPRODUCE.md` lists every step. `reproduce.ps1` runs them in order on Windows, and each stage can be started on its own:

```powershell
powershell -ExecutionPolicy Bypass -File reproduce.ps1                     # from the raw SNDlib downloads
powershell -ExecutionPolicy Bypass -File reproduce.ps1 -From experiments   # reuse shipped libraries
```

Expect about 4 to 6 hours of ILP time for the libraries and 6 to 8 hours for the experiments on a 14-core laptop. The raw SNDlib files (about 900 MB) are not in the repository. `python -m lira.data.download` fetches them and checks their SHA-256 hashes against `data/MANIFEST.json`.

## Repository layout

| Path | Content |
|---|---|
| `lira/` | Package: data pipeline, network, power, wear and reconfiguration models, library builder, oracle, baselines, policies |
| `experiments/` | One script per experiment group, the Mininet emulation, the report builder |
| `tests/` | Unit tests for data, models and baselines |
| `configs/power.yaml` | Power and wear constants with their sources |
| `data/` | `MANIFEST.json` and processed traffic, splits and metadata |
| `artifacts/` | Configuration libraries and oracle labels per topology and scenario |
| `paper/` | Manuscript (`main.tex`), generated assets, results of E1 to E17 |
| `reports/` | Forensic audits of the code and of the manuscript |
| `results/` | Library reports, DP-versus-MILP checks, run logs |
| `tools/` | Reference verification and BibTeX helpers |

## Experiments

| Script | Experiments |
|---|---|
| `experiments/run_main.py` | E1 main comparison (5 seeds), E2 price sweeps, E3 case study, E4 per-link wear, E6 library size, E7 ablation, E9 wear sensitivity, E12 gap to oracle |
| `experiments/run_extra.py` | E1b and E5 optimization baselines and scalability, E8 drift, E10 threshold sweep, E13 model choice, E14 rolling folds |
| `experiments/run_milp.py` | E15 per-interval lower bound |
| `experiments/run_stale.py` | E16 decisions on the previous interval's traffic |
| `experiments/run_static.py` | E17 static configuration with LiRA's fallback |
| `experiments/emulate_mininet.py` | E11 Mininet and Open vSwitch emulation (Linux or WSL2, root) |

Scenarios are selected with the environment variables `LIRA_LOAD`, `LIRA_DYN` and `LIRA_THETA`. `REPRODUCE.md` lists the values.

## Testing

```bash
python -m pytest -q tests
```

The tests cover the SNDlib parser and processed data, paths, power, MLU, the ILP, the reconfiguration and wear models, the DP oracle against an independent MILP, and the baselines.

## Limitations

- Nobel-Germany is semi-synthetic. Its per-interval noise has no temporal correlation.
- Port power and wear parameters are representative assumptions, not measurements of a device.
- The main results let the controller see the traffic of the interval it configures. E16 measures the effect of one-interval-old traffic.
- The emulation uses a modeled 1 s wake-up delay and no real line cards.
- No deep reinforcement learning baseline is included.

## Citation

The manuscript is under preparation. Until it is published, please cite this repository.
