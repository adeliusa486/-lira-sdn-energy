# Repository Forensic Audit: LiRA SDN energy paper

Repository: `E:\Work\SDN energy aware 1` (not under git). Audit date: 2026-10-23. Mode: Full Audit.
Scope: `lira/`, `experiments/`, `scripts/`, `tests/`, `tools/`, `paper/tools/`, `paper/results/`, `paper/generated/`, `paper/main.tex`, `data/processed/`, `configs/`, `results/`.
Not inspected byte by byte: `data/raw/` (911 MB of SNDlib downloads, checked through `data/MANIFEST.json` hashes and the parser), the 128 binary probe logs under `paper/results/E11_emulation/runs/` (checked through `emu_analyze.py` and its CSV output), and the pickled libraries in `artifacts/` (loaded and used through `build_ctx`).

---

# 🧠 OVERALL VERDICT

**Score:** 7/10
**Decision:** Minor Revision (integrity and reproducibility), with one methodological gap that needed a new experiment

The most serious flaw is methodological, not fraudulent. Every online controller, including the safety layer, decides interval t with the realized traffic matrix D_t (`lira/policy/lira_policy.py:68-72` and `lira/policy/lira_policy.py:142`), so LiRA reproduces the oracle sequence exactly in all 5 Nobel high-load seeds (0 of 2,160 intervals differ, from `E1_main/nobel_highload_seqs.npz`). Every number in the paper traces to code: 112 of 112 macros in `paper/generated/results_macros.tex` come from `paper/tools/make_paper_assets.py`, which reads only CSV and JSON files written by `experiments/*.py`. Eleven numbers are typed by hand in `paper/main.tex`, and three of them are wrong or out of scope (0.2% wear margin, "only setting" claim, unchanged static configuration under drift). The deployed LiRA policy is the round-0 behaviour-cloning model in 56 of 60 runs and a constant classifier in 30 of 60, which the paper discloses only partly. The repository has no single reproduction entry point, a stale README, and an unpinned requirements file with five unused packages.

---

# 📋 PHASE 0: REPOSITORY MAP

## File Tree

Code and documentation files are listed one by one. Result files are grouped by experiment because there are more than 400 of them, and every group was traced to its writer.

```
README.md                         project overview. STALE: says results are placeholders, points to 4 files that moved to paper/archive_placeholder_version/
IMPLEMENTATION_PLAN.md            10-phase plan (documentation)
DATASETS_AND_EXPERIMENTS.md       dataset and experiment spec E1-E14 (documentation)
LITERATURE_REVIEW.md              literature review (documentation)
PROGRESS.md                       running project log
requirements.txt                  unpinned (>=). Lists torch, optuna, pulp, stable-baselines3, gurobipy, which no file imports
configs/power.yaml                power and wear constants, read by PowerModel.from_yaml and WearModel.from_yaml
data/MANIFEST.json                SHA-256 of every raw download, written by lira/data/download.py
data/processed/{abilene,geant,nobel}/   od.npy, timestamps.npy, segment.npy, splits.json, meta.json, topology.json (lira/data/preprocess.py), features.npz (lira/data/features.py)
lira/__init__.py                  paths and scenario tags (imported everywhere)
lira/data/download.py             SNDlib download + hashes (entry point)
lira/data/parse_sndlib.py         SNDlib parser (imported by preprocess, run_extra)
lira/data/preprocess.py           cleaning, Nobel semi-synthetic series, splits, scaling (entry point)
lira/data/features.py             train-fitted PCA/scaler features (imported by common.py)
lira/models/network.py            topology, k-shortest paths, incidence matrices
lira/models/routing.py            Config, splits, MLU
lira/models/power.py              port power model
lira/models/reconfig.py           toggles, flow-mods, disruption, R normalisation
lira/models/wear.py               acceleration factor and its DP split
lira/models/cost.py               cost tables over the library
lira/library/ilp.py               energy ILP (B1) and min-MLU LP
lira/library/ga.py                NSGA-II (B3)
lira/library/build_library.py     library construction (entry point, run per scenario with LIRA_LOAD/LIRA_DYN/LIRA_THETA)
lira/oracle/dp.py                 Viterbi oracle
lira/oracle/milp_check.py         independent MILP of the library problem
lira/oracle/make_labels.py        labels + DP-vs-MILP validation (entry point)
lira/policy/expert.py             backward values for DAgger relabelling
lira/policy/models.py             XGB/LGBM/RF/MLP backends, ConstantModel
lira/policy/lira_policy.py        B4 (SnapshotML), LiRA, safety layer
lira/baselines/classical.py       B0, B1, B2, B3, B5, B6, B7
lira/baselines/runlog.py          independent per-interval evaluator, used by tests/test_baselines.py (cross-check of evaluate()). run_extra.py imported it as `_unused`
lira/drift/__init__.py            EMPTY PACKAGE. Drift code lives in experiments/run_extra.py
experiments/common.py             contexts, evaluate(), oracle, tuned baselines, statistics
experiments/run_main.py           E1, E2, E2b, E3, E4, E6, E7, E9, E12 (entry point)
experiments/run_extra.py          E1b, E5, E8, E10, E13, E14 (entry point)
experiments/run_milp.py           E15 (new in this audit)
experiments/run_stale.py          E16 (new in this audit)
experiments/run_static.py         E17 (new in this audit)
experiments/emu_export.py         E11 input export
experiments/emulate_mininet.py    E11 Mininet driver (runs in WSL as root)
experiments/run_emulation.sh      E11 runner
experiments/emu_analyze.py        E11 analysis -> emulation_summary.csv, emulation_transitions.csv
experiments/make_report.py        RESULTS.md, headline.csv, figures/*.png
scripts/pilot_experiment.py       Session-2 pilot (results/pilot/)
scripts/pilot_learned_b4.py       Session-2 pilot with learned B4
tests/test_data.py, test_models.py, test_baselines.py   18 tests, all pass (pytest, 11.5 s)
tools/verify_refs.py, search_literature.py, doi2bib.py  reference tooling
paper/main.tex                    manuscript (main_v2.tex is a byte-identical duplicate)
paper/main_conference_v1.tex/.pdf conference version (archived)
paper/archive_placeholder_version/  placeholder-era draft and its generator (archived, not built)
paper/tools/make_paper_assets.py  writes every macro, table and plot file in paper/generated/
paper/tools/fix_gen2.py, fix_gen3.py, fix_gen4.py, fix_layout.py, rename_macros.py   ONE-OFF PATCH SCRIPTS. They edited make_paper_assets.py and main_v2.tex once. Their asserts now fail, so they can never run again
paper/tools/build_check.py        draft compile with \providecommand{...}{0} stand-ins for missing macros (draft only)
paper/tools/clean_bib.py, check_paragraphs.py   bibliography and paragraph checks
paper/results/E1..E14/            per-experiment CSV/NPZ/JSON written by run_main.py and run_extra.py
paper/results/E11_emulation/      Mininet runs (5 runs, 128 binary probe logs) and analysis CSVs
paper/results/RESULTS.md, headline.csv, figures/   written by make_report.py
paper/results/FINDINGS.md, README_RESUME.md, PEER_REVIEW_main_v2.md   hand-written notes
paper/generated/                  written by make_paper_assets.py only
results/                          library reports, DP-vs-MILP validation, label summaries, run logs, pilots
artifacts/library/*.pkl, artifacts/labels/*.npz   libraries and oracle labels (138 files)
```

## Dead Code / Orphan Files

- `lira/baselines/runlog.py`: not used by any experiment, but `tests/test_baselines.py` uses it as an independent evaluator. `run_extra.py` imported it as `evaluate as _unused`, which served no purpose. (Corrected after the first draft of this report, which called the module dead.)
- `lira/drift/__init__.py`: empty package. The ADWIN and Page-Hinkley code is `Detectors` in `experiments/run_extra.py:209`.
- `paper/tools/fix_gen2.py`, `fix_gen3.py`, `fix_gen4.py`, `fix_layout.py`, `rename_macros.py`: one-off editors of `main_v2.tex` and `make_paper_assets.py`. `fix_gen4.py` wrote the `\emuTransS\\,s` typo that breaks the abstract line in the PDF.
- `paper/main_v2.tex`: duplicate of `main.tex`.
- `paper/build.log`: log of the placeholder-era build.
- No orphan result files. `figures/E3_case_study.png` and `figures/E2_pareto.png` come from `make_report.py:154,175`.

## Claim Ledger

"Verified" means the number was recomputed from the result files by `verify_claims.py` (scratchpad) or read from a generated macro whose code path was traced.

| # | Claim | Value | Source location | Verified? | Evidence or gap |
|---|-------|-------|-----------------|-----------|-----------------|
| 1 | B4 changes on Abilene | 0.019/day | abstract, macro `abiBFourchg` | Verified | `E1_main/abilene_base_runs.csv`, mean of 5 seeds |
| 2 | Savings Abilene / GÉANT | 24.0% / 29.8% | abstract, `abiSav`, `geaSav` | Verified | O* rows of E1 |
| 3 | LiRA within 0.02% of snapshot classifiers (real traces) | 0.02% | main.tex:44, 415 (typed) | Verified | spread 0.0137% Abilene, 0.0% GÉANT |
| 4 | B4 flaps on Nobel | 11.7/day | `nobBFourchg` | Verified | E1 Nobel base |
| 5 | RF B4 changes | 0.5/day | `modRfChg` | Verified | E13 seed 0 |
| 6 | Nearly every change saves < 1% of interval energy | "nearly every" | main.tex:44, 68 (typed) | Verified, understated | `gain_hist.dat`: 100% < 0.5%, 99.0% < 0.1% |
| 7 | LiRA cuts changes and transitions | 97.7% | `nobY`, `nobZ` | Verified | but the policy is a ConstantModel (config 1 in 2,159 of 2,160 intervals) |
| 8 | Hysteresis does as well, adjusted p | 0.88 | `nobPbsix` | Verified | `stats_wilcoxon_holm.csv` |
| 9 | High load: LiRA 880.9 vs B6 887.0 | 880.9 / 887.0 | `nobhlJLiRA`, `nobhlJBSix` | Verified | B2-naive reaches 882.2, not mentioned |
| 10 | Test days Nobel | 7.5 | `nobTestDays` | Verified | |
| 11 | DP equals MILP | 1e-14 | `dpMilpDiff` | Verified | `results/dp_milp_validation_*.csv` |
| 12 | Emulation transitions / duration | 18 / 1.11 s | `emuTrans`, `emuTransS` | Verified | 1.0 s of the 1.11 s is the modeled wake-up constant (`emulate_mininet.py:162`) |
| 13 | Only setting where LiRA beats tuned hysteresis is high load | "only" | main.tex:68 (typed) | **FALSE** | stress: LiRA 898.6 < B6 899.4 (`tab_scen.tex`) |
| 14 | Constant LiRA policy | 30 of 60 runs | `liraConstRuns` | Verified | `E1_main/*_info.json` |
| 15 | Wilcoxon minimum p | 0.0078 with 8 days | main.tex:426 (typed) | Verified | 2/2^8. The 8th day is a half day |
| 16 | Gain histogram | 96 changes, 100% < 1%, median 0.00% | `gainChanges` etc. | Verified | seed 0 only, not stated |
| 17 | Busiest week changes | 88 vs 2 | `caseBFourchg`, `caseLiRAchg` | Verified | seed 0 |
| 18 | Model choice | 12.8 / 10.1 / 0.5 / 44.8 changes | `mod*Chg` | Verified | seed 0, E13 |
| 19 | Ablation stress costs | 897.4, 902.0, 898.6, 899.0, 895.6, 889.9 | `ablStress*` | Verified | "removing lag features" lowers cost (895.6 < 897.4), text says it raises |
| 20 | No-safety violations | 0.17% / 0.14% | `ablStressNoSafeViol` | Verified | |
| 21 | K: B4 939.3 at K=8 to 935.7 | values | `KBFour*` | Verified | |
| 22 | B6/LiRA within 0.2% of oracle at every K | 0.2% | main.tex:525 (typed) | Verified | max 0.064% (B6), 0.132% (LiRA) |
| 23 | Library saturates because pruning stops | 51 | main.tex:525 | **Wrong mechanism** | `results/library_nobel_report.json`: only 51 candidates exist |
| 24 | θ ≥ 0.7 identical on Nobel | "identical" | main.tex:525 | Verified for B4, B6, LiRA, O* | B7 differs at θ = 0.9 (878.5 vs 885.7) |
| 25 | Every method below AF 1 for α = 0.5, χ ≤ 0.1 | max 0.945 | main.tex:547 | Verified | |
| 26 | Most-cycled links of non-B4 methods within 0.2% of one | 0.2% | main.tex:547 (typed) | **FALSE** | LiRA max AF 1.0024 (`E4_per_link_wear/nobel_base_per_link.csv`) |
| 27 | B1 matches library snapshot optimum | 0.01 pp | main.tex:565 (typed) | Verified | max |diff| 0.0066 pp |
| 28 | B1 median on GÉANT | 4.1 s | main.tex:565 (`ilpGeant`) | Inconsistent | Table X shows 3.53 s from 60 matrices, text uses a single-matrix scalability run |
| 29 | Drift: static cost change ≤ 0.74% | 0.74% | main.tex:587 (typed) | Verified | 0.743% Nobel hotspot |
| 30 | Shifts did not change the static configuration | "did not" | main.tex:587 | **FALSE for Nobel hotspot** | static switches 0.41 → 0.82 per day |
| 31 | Oracle runs in seconds | "seconds" | main.tex:630 | Unsupported where cited | not in Section res-time. `results/labels_abilene_K32.json`: 3.6 s for 48,108 intervals |
| 32 | σ of Nobel noise | 1.23 | main.tex:363 (typed) | Verified | `meta.json` 1.2313 |
| 33 | GÉANT spikes removed | eleven | main.tex:363 (typed) | Verified | `meta.json` 11 |
| 34 | Folds Nobel | 371.5, 350.1, 357.9, 350.3, 350.0 | `foldNob*` | Verified | |
| 35 | Emulation loss, link-hours | 3.7 pkt/transition, 31% | `emuLostPerTrans`, `emuLinkSave` | Verified | link-hours are computed from the replayed sequence, not measured |
| 36 | Safety check ≤ 0.36 ms on 65 nodes | 0.36 | `safetyTA` | Verified | |
| 37 | Wear: B4 0.94 vs LiRA 0.85 at χ = 0.1 | values | `wearBigChi*` | Verified | |
| 38 | Drift false alarms | 0.17, 0.00, 0.93 | `driftFa*` | Verified | |
| 39 | B4 has "the same safety layer as LiRA" | | main.tex:376 | **FALSE** | B4 falls back to the cheapest feasible energy (`safe_batch`), LiRA to Eq. (fallback) with switching and wear (`rollout`) |
| 40 | O* "is a lower bound" | | main.tex:376 | Out of scope | only over library sequences. E15 now bounds the non-library optimum |

**Fabrication threshold:** 0 of 40 claims are unverifiable (0%). Four are false or wrongly explained and one is inconsistent. No fabrication flag.

---

# 🔍 PHASE 1: FRAUD FINGERPRINT AUDIT

| # | Fingerprint | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Hardcoded metrics | ABSENT | All metrics come from `evaluate()` (`experiments/common.py:96-138`). Eleven typed numbers in `main.tex` are traceable, 3 are wrong (ledger 13, 26, 30) |
| 2 | Constant model outputs | PRESENT, disclosed | `ConstantModel` in 30 of 60 LiRA runs (`lira/policy/models.py:10`, `*_info.json`). Disclosed at main.tex:415 and 643. Not disclosed in the abstract next to the 97.7% claim |
| 3 | Reverse-engineered fixtures | ABSENT | LiRA = O* exactly in Nobel high load is explained by the safety layer seeing D_t (`lira_policy.py:142`) and a near-constant expert. Prediction never queries the expert (`rollout(beta=0)`) |
| 4 | Disconnected eval pipeline | ABSENT | train and test share `build_ctx`, tables and features |
| 5 | Unreachable training code | PRESENT, minor | `lira/drift/` empty. `runlog.py` is test-only |
| 6 | Orphan result files | ABSENT | every result group has a writer |
| 7 | Suspiciously perfect numbers | UNCERTAIN, explained | LiRA = O* to 1e-14 (Abilene) and exactly (Nobel high load). Mechanism: constant oracle, same-interval information |
| 8 | Seed sensitivity concealment | ABSENT | 5 seeds in E1 with 95% CIs. E6, E10, E13 are seed 0 and say so |
| 9 | Test set contamination | ABSENT | scaler, PCA and top-OD fit on train (`features.py:28-31`), scaling on train (`preprocess.py:164`). Spike filter uses a centered 1-day median over the whole series (cleaning only) |
| 10 | Label leakage | ABSENT | features at t use D_t, which is the decision input by design, and the label is a function of D_t. The realism problem is listed under Critical Issue 1 |
| 11 | Metric implementation bugs | PRESENT, disclosed | `evaluate()` J has no violation penalty, so "no safety layer" (889.9) scores below the oracle (894.3). The text explains it at main.tex:514 |
| 12 | Fabricated dataset | ABSENT | Nobel is semi-synthetic and labelled so in text and Table II. Generator in `preprocess.py:100` |
| 13 | Phantom ablation studies | ABSENT | `run_main.py:260` runs all six variants |
| 14 | Mock/stub inference | ABSENT | `predict_one` runs the booster or the constant |

**Flags triggered:** 3/14 (2, 5, 11), all disclosed or cosmetic
**Fraud risk level:** LOW. The constant-model and no-penalty flags are honest consequences of the data, and the paper says so in the body.

---

# 🔬 PHASE 2: PIPELINE RECONSTRUCTION

## Execution Pipeline

```
[raw data] → [preprocessing] → [splits] → [library + labels] → [training] → [evaluation] → [metrics] → [paper]
lira/data/   lira/data/        preprocess   build_library.py    common.py      common.py      common.py    make_report.py
download.py  preprocess.py     chrono_     make_labels.py      SnapshotML,    evaluate()     *_runs.csv   make_paper_assets.py
             features.py       splits      (env-var scenario)  LiRA.fit                                     -> generated/ -> main.tex
runnable     runnable          runnable    runnable, but the   runnable       runnable       runnable     runnable
                                           scenario calls are
                                           not scripted
```

## Pipeline Questions

| # | Question | Answer | Evidence |
|---|----------|--------|----------|
| Q1 | Reproducible in < 2 h? | No | Libraries for 4 scenarios × 3 topologies plus 3 θ values take hours of ILP time (`results/library_*_solver_log.csv`). The scenario and θ builds were run ad hoc with `LIRA_LOAD`, `LIRA_DYN`, `LIRA_THETA`, and no script records those calls. E1 alone took about 95 min (`results/runlogs`) |
| Q2 | Seeds fixed everywhere? | Yes | k-means `random_state`, NSGA-II `seed`, XGB `seed`, numpy `default_rng(seed)`, PCA `random_state=0`. XGB with `nthread=16` and `hist` is deterministic. `E7` seeds 0-2 reproduce `E1` seeds 0-2 exactly (897.36 both) |
| Q3 | Split before feature eng? | Yes | `Featurizer.__init__` fits on `splits.json["train"]` only |
| Q4 | Eval independent from train? | Yes, with one caveat | The library uses train + validation matrices for coverage (`build_library.py:87`). B6/B7 tuning and LiRA round selection also use validation. Test data is never used for fitting |
| Q5 | Reported metrics match code? | Yes, except 4 typed claims | ledger 13, 23, 26, 30 |

---

# 🧪 PHASE 3: STATISTICAL VALIDITY GATE

| Requirement | Present? | Evidence |
|-------------|----------|----------|
| ≥3 seeds with mean + std | Yes for E1 (5 seeds), E7 (3 seeds) | seeds vary only the learner. The traffic traces are fixed |
| Confidence intervals | Yes | `tab_main.tex` 95% t-intervals |
| Significance tests vs baselines | Partly | Wilcoxon + Holm for LiRA vs B4, B6, B7 per setting (`run_main.py:149`). No test against B2 or the static rule |
| Effect size | No | `mean_daily_J_diff` and `lira_better_days_pct` exist in `stats_wilcoxon_holm.csv` but the paper does not report them |
| Ablation with significance | No | disclosed at main.tex:514 |
| No cherry-picking | Yes | all seeds aggregated, all scenarios in Table V |
| Compute budget documented | Partly | hardware at main.tex:384. Total run time not reported |

**Verdict:** Adequate for the claims the paper makes. The power is low on Nobel (8 daily samples) and the paper says so.

---

# 🔗 PHASE 4: CROSS-FILE CONSISTENCY MATRIX

| Pair | Status | Evidence |
|------|--------|----------|
| README metrics ↔ eval script | INCONSISTENT | README says the paper holds placeholders and names `paper/EDITORIAL_REPORT.md`, `paper/data/`, `paper/results_macros.tex`, `make_placeholder_data.py`, which now live in `paper/archive_placeholder_version/` |
| Config hyperparams ↔ train script | CONSISTENT | `configs/power.yaml` read by `from_yaml`. Paper Table III matches (30/5/3 W, α 0.5, χ 0.01) |
| Architecture description ↔ model code | INCONSISTENT in two places | B4 safety layer (ledger 39). Algorithm 1 line 4 pairs s_t with c*_{t-1}, the code labels with c*_t (`lira_policy.py:196`) |
| Dataset description ↔ data loader | CONSISTENT | sizes, splits, σ, spike count, scaling all match `meta.json` |
| requirements.txt ↔ imports | INCONSISTENT | torch, optuna, pulp, stable-baselines3, gurobipy listed and never imported. pyarrow only for `runlog.save`, which no script calls. No versions pinned. river, pymoo, highspy are imported and listed |
| Baseline descriptions ↔ baseline code | CONSISTENT except B4 fallback and B0 routing | B0 uses shortest-path routing (`routing.py:41`), which causes its 0.05% violations on Nobel. The paper does not say so |
| Ablation descriptions ↔ ablation code | CONSISTENT | `ABLATIONS` in `run_main.py:260` |

---

# 🚨 CRITICAL ISSUES (rejection-level)

## Issue 1: Every controller sees the traffic of the interval it configures

- **Problem**: B4, B6, B7, B2 and LiRA all choose c_t with features of D_t and check feasibility on D_t, so the safety layer never errs and LiRA copies the oracle whenever the expert is near-constant.
- **Evidence**: `lira/policy/lira_policy.py:142` (`if self.safety and not np.isfinite(node[t, c])`, with `node` built from the realized tables), `lira/policy/lira_policy.py:71-72` (`safe_batch(ctx.tab.node(0.0)[a:b], pred)`). Disclosed in one sentence at main.tex:299.
- **Why it invalidates results**: the high-load result "LiRA reaches the oracle" (880.9) and the 0% violation rates depend on perfect same-interval knowledge. A deployed controller configures interval t from D_{t-1} or an estimate. Without a test of that protocol, the paper cannot claim that the safety layer prevents congestion (main.tex:632).
- **Exact fix**: run every online method on D_{t-1} and score on D_t (E16, `experiments/run_stale.py`), add a safety-margin variant, move the assumption into Section VI, and report violations.
  ```python
  # BEFORE (lira_policy.py, SnapshotML.predict): decide and check on D_t
  X = ctx.F[a:b, :ctx.n_snap]; node = ctx.tab.node(0.0)[a:b]
  # AFTER (run_stale.py, b4_seq): decide and check on D_{t-1}, evaluate on D_t
  pred = model.predict_many(ctx.F[a - 1:b - 1, :ctx.n_snap])
  seq = safe_batch(ctx.tab.slice(a - 1, b - 1).node(0.0), pred)[0]
  ```

## Issue 2: Three typed claims in the manuscript are false

- **Problem**: main.tex:68 says high load is "the only setting" where LiRA beats tuned hysteresis, main.tex:547 says the most-cycled links of the other methods stay within 0.2% of one, and main.tex:587 says the shifts did not change which configuration the static policy uses.
- **Evidence**: `tab_scen.tex` Nobel stress (LiRA 898.6, B6 899.4). `E4_per_link_wear/nobel_base_per_link.csv` (LiRA max AF 1.0024). `E8_drift/nobel_drift.csv` (static LiRA 0.41 → 0.82 switches per day under the hotspot).
- **Why it invalidates results**: a reviewer who checks one of these against the tables will distrust the rest.
- **Exact fix**: generate these quantities as macros in `make_paper_assets.py` and rewrite the sentences around the computed values.

---

# ⚠️ MODERATE ISSUES

## Issue 1: The deployed LiRA is rarely the DAgger policy

- **Problem**: LiRA keeps the round with the lowest validation cost, and round 0 (plain imitation of the oracle trajectory) wins in 56 of 60 E1 runs.
- **Evidence**: `E1_main/*_info.json`, field `lira_best_round`: 0 everywhere except Nobel stress seeds 0, 1, 3, 4 (rounds 3, 3, 3, 2).
- **Impact**: Section IV presents DAgger and Proposition 3 as part of the learner, yet the evaluated policy almost never contains DAgger data.
- **Fix**: generate the count as a macro and state it next to the constant-policy caveat.

## Issue 2: A non-learning rule is missing from the comparison

- **Problem**: in most settings LiRA behaves like "hold one configuration and fall back when it is infeasible". That rule is never evaluated.
- **Evidence**: LiRA is a `ConstantModel` in 30 of 60 runs. All Nobel high-load ablations that keep the safety layer score 880.9 (`tab_ablation.tex`).
- **Impact**: without it, readers attribute to learning what the safety layer does.
- **Fix**: E17 (`experiments/run_static.py`) evaluates the training oracle's most frequent configuration plus LiRA's fallback in all 12 settings and both information protocols.

## Issue 3: B2 is left out of the Nobel narrative

- **Problem**: the rolling-horizon B2 ties B6 on Nobel base (875.3) and reaches 882.2 under high load (oracle 880.9, B6 887.0), and the text compares LiRA only with B6.
- **Evidence**: `tab_main.tex`, `E1_main/nobel_highload_runs.csv`.
- **Impact**: the "LiRA is the only method that reaches the oracle" sentence hides that a forecast-free optimiser gets within 0.14%.
- **Fix**: report B2 next to B6 in the abstract, Section VII-B and the discussion.

## Issue 4: The library-loss question was unanswered

- **Problem**: the paper says B2 "is not the full multi-period mixed-integer program" and calls O* "a lower bound", but no experiment bounds what the library gives up.
- **Evidence**: main.tex:376, 639.
- **Impact**: reviewers will ask whether the library restriction hides savings.
- **Fix**: E15 (`experiments/run_milp.py --mode bound`) solves an exact single-interval MILP with free routing for every test interval. The sum is a lower bound on the cost of any controller, library or not, because switching costs are non-negative.

## Issue 5: No reproduction entry point, stale README, unpinned requirements

- **Problem**: no script rebuilds the 21 scenario and θ libraries, the README describes the placeholder era, and `requirements.txt` has no versions and five unused packages.
- **Evidence**: `README.md`, `requirements.txt`, `results/scenarios/*.log` (the only record of the env-var calls).
- **Impact**: the Data Availability statement promises scripts that "produce every table and figure", which a reader cannot follow without the project log.
- **Fix**: a `REPRODUCE.md` and a `reproduce.ps1` with the exact command order, a rewritten README, and versions pinned to `paper/results/environment.json`.

## Issue 6: Validation coverage is reported as library coverage

- **Problem**: Table VIII reports coverage on validation matrices, and the library builder solved ILPs for uncovered validation matrices.
- **Evidence**: `build_library.py:87` (`D_cov = D[train + val]`), `run_main.py:250` (`val_coverage`).
- **Impact**: the 100.0% column is optimistic by construction.
- **Fix**: report test coverage in Table VIII.

---

# 🟢 MINOR ISSUES

- `paper/main.tex:44`: `\emuTransS\\,s` puts a line break inside the abstract. Use `\emuTransS\,s`.
- `paper/main.tex:565`: uses `\ilpGeant` (one matrix, 4.1 s) where Table X has 3.53 s. Use `\geaIlpS`.
- `paper/main.tex:525`: the library stops at 51 because only 51 candidates exist (`results/library_nobel_report.json`), not because pruning stops.
- `paper/main.tex:443`: the oracle's change rate is printed with `\nobhlLiRAchg`. Add an oracle macro.
- `paper/generated/tab_scale.tex`: 6.7 pt overfull box.
- `experiments/run_main.py:137`: the E12 docstring calls B2 "the multi-period MILP-style baseline".
- `experiments/common.py:96`: J has no violation penalty. Document it in the docstring and in the paper.
- `lira/policy/models.py:89`: the MLP backend ignores sample weights. LiRA's cost-sensitive weights do not reach it.
- `lira/policy/lira_policy.py:174-176`: `states_from` sets prev = 0 at the first training interval, while the oracle trajectory starts free. One label per segment is affected.
- `paper/tools/fix_gen*.py`, `fix_layout.py`, `rename_macros.py`, `build_check.py`: move to an archive folder.
- `paper/main_v2.tex`: delete or archive the duplicate.
- `lira/drift/__init__.py`: document where the drift code lives. `experiments/run_extra.py`: drop the `_unused` import of `runlog`.

---

# 🔬 MISSING EXPERIMENTS

### Experiment 1: Stale traffic matrix (E16)

- **What**: every online method decides interval t with D_{t-1} and is scored on D_t, with and without a 0.05 MLU margin in the safety check.
- **How**: `experiments/run_stale.py`, 3 seeds, Abilene, GÉANT, Nobel × base and high load, plus Nobel stress.
- **Why**: tests whether the safety layer and the "LiRA reaches the oracle" result survive realistic information.
- **Expected outcome**: a sound result shows small violation rates on smooth traces and larger ones on Nobel, removable with a margin at some energy cost. A suspicious result would be zero violations everywhere without a margin.

### Experiment 2: Static configuration with fallback (E17)

- **What**: hold the training oracle's most frequent configuration and apply LiRA's fallback.
- **How**: `experiments/run_static.py`, all 12 settings, both protocols.
- **Why**: separates what the classifier learns from what the safety layer does.
- **Expected outcome**: equal to LiRA wherever LiRA is constant. Any gap in Nobel stress is the share learning contributes.

### Experiment 3: Lower bound that no controller can beat (E15)

- **What**: per-interval exact MILP with free routing and link states.
- **How**: `experiments/run_milp.py --mode bound`, whole test split, Abilene, GÉANT, Nobel base, Nobel high load and stress.
- **Why**: bounds what the library restriction can cost.
- **Expected outcome**: a gap close to the per-interval routing slack (well below 1%). A large gap would mean the library is too coarse.

### Not runnable here

- Deep RL baseline: `import torch` fails in this environment (`torch` has no `__version__`), and stable-baselines3 and gymnasium are not installed.
- A second noisy real trace: SNDlib offers one day for Nobel-Germany and Germany50. No other public multi-week trace is on disk.
- Hardware testbed: no sleep-capable line cards.

---

# 🛠️ ACTION PLAN (prioritized fix roadmap)

### Step 1: Run E15, E16, E17 (Est. effort: 2 h of compute)
- **Files**: `experiments/run_milp.py`, `run_stale.py`, `run_static.py`
- **Changes**: new experiments, results under `paper/results/E15_full_milp`, `E16_stale_tm`, `E17_static_fallback`
- **Validates**: Critical Issue 1, Moderate Issues 2 and 4

### Step 2: Generate every typed number (Est. effort: 1 h)
- **Files**: `paper/tools/make_paper_assets.py`, `paper/main.tex`
- **Changes**: macros for the wear margin, the drift switching change, the cost-spread of real traces, the B1 gap, the DP run time, the DAgger count, B2 costs, test coverage, the oracle change rate
- **Validates**: Critical Issue 2, Minor issues

### Step 3: Correct the manuscript (Est. effort: 2 h)
- **Files**: `paper/main.tex`
- **Changes**: B4 fallback, O* scope, Algorithm 1 label, information protocol in Section VI, B2 and static rule in the narrative, abstract under 250 words, new E15/E16/E17 subsections
- **Validates**: Moderate Issues 1-4

### Step 4: Reproducibility package (Est. effort: 1 h)
- **Files**: `README.md`, `REPRODUCE.md`, `reproduce.ps1`, `requirements.txt`
- **Changes**: exact command order including the env-var library builds, pinned versions, archive of one-off scripts
- **Validates**: Moderate Issue 5

---

# 📊 FINAL SCORECARD

| Dimension | Score | Key reason (one sentence) |
|-----------|-------|---------------------------|
| Reproducibility | 6/10 | Seeds and hashes are fixed, but the scenario library builds are unscripted and versions are unpinned |
| Experimental validity | 6/10 | Train-only fitting is clean, but all online decisions use the realized D_t |
| Model/algorithm correctness | 8/10 | DP matches an independent MILP to 1e-14 and the wear split is exact |
| System design realism | 6/10 | Mininet emulation is real, but the 1 s wake-up is a constant and the TM is known exactly |
| Baselines & comparisons | 7/10 | Seven baselines with validation tuning, but the static rule and the library-loss bound were missing |
| Code quality | 7/10 | Small, readable modules with tests, plus a few dead modules and one-off scripts |
| Logging & observability | 8/10 | Every experiment writes CSVs and run logs, and per-run info JSONs record the selected rounds |
| Robustness | 6/10 | Scenarios, θ, K, folds and drift are covered, but information delay was not |
| Claim–implementation alignment | 7/10 | 112 generated macros, 3 false typed claims |
| Statistical validity | 6/10 | Paired tests with Holm correction, no effect sizes, 8 days on Nobel |
| **Overall** | **7/10** | Honest and traceable, with one methodological gap that new experiments now address |

---

# ⚖️ FRAUD RISK ASSESSMENT

**Risk level:** LOW

Three fingerprints are triggered: a constant model in half the LiRA runs, two unused modules, and a cost J without a violation penalty. The first and third are disclosed in the body of the paper and follow from the data: the oracle is constant on the training period, and the no-safety ablation's lower cost is explained in the text. The pattern is engineering debt plus an optimistic information assumption, not result manipulation. The evaluation code never reads test labels during prediction, ablations exist as code, and every reported number has a generation path.

---

# 🐛 SILENT BUG HUNT RESULTS

| # | Anti-pattern | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Off-by-one in sequences | FOUND, minor | `states_from` (`lira_policy.py:174-176`) starts prev = 0 although the oracle trajectory starts free, and carries prev across segment boundaries where the oracle restarts. Lag features handle boundaries correctly (`features.py:49-53`) |
| 2 | sklearn fit before split | NOT FOUND | `features.py:28-31` |
| 3 | DataFrame index leakage | NOT FOUND | no row index in features |
| 4 | Train metrics labeled as test | NOT FOUND | `evaluate(ctx, "test", ...)` everywhere |
| 5 | Missing class weights | FOUND, minor | MLP backend drops `sample_weight` (`models.py:89`). XGB, LGBM, RF use it |
| 6 | Double softmax | NOT FOUND | XGB `multi:softprob`, argmax only |
| 7 | Augmentation on val/test | NOT FOUND | none |
| 8 | LR scheduler misuse | NOT FOUND | none |
| 9 | Gradient accumulation | NOT FOUND | none |
| 10 | BatchNorm mode | NOT FOUND | none |
| 11 | Detached gradients | NOT FOUND | none |
| 22 | Simulation passed as real | NOT FOUND | Nobel labelled semi-synthetic, emulation labelled as emulation |
| 23 | Unrealistic simulation parameters | FOUND | perfect same-interval TM (Critical Issue 1), modeled 1 s wake-up (`emulate_mininet.py:162`), Nobel noise without temporal correlation (disclosed) |

---

# REMEDIATION STATUS (same day, after the fixes)

| Finding | Status | What changed |
|---|---|---|
| Critical 1: controllers see D_t | Addressed | New section VI-C states the protocol. E16 (`experiments/run_stale.py`) reruns every online method with D_{t-1}: costs move by at most 0.002%, Nobel violations rise to 0.05% (base), 0.19% (high load, stress) for B2, B4, B6, and 0.05/0.14/0.17% for LiRA. Every violation of the static rule is an interval where always-on also violates, with one-interval MLU jumps of 0.66 to 1.36. A 0.05 margin does not remove them. Reported in Section VII-I, the discussion and the limitations |
| Critical 2: three false typed claims | Fixed | All three now come from macros (`maxAFlira`, `nobJLiRAst` vs `nobJBsixst`, `driftNobSwNone`/`driftNobSwHot`) and the sentences were rewritten |
| Moderate 1: DAgger round 0 in 56 of 60 runs | Fixed | Macro `daggerRoundZero`, stated in Section IV-C, the results preamble and the limitations |
| Moderate 2: no non-learning static rule | Fixed | E17 (`experiments/run_static.py`). The static rule equals LiRA in 11 of 12 settings. Only Nobel stress differs (static 902.0, LiRA 898.6, B2 895.4, O* 894.3) |
| Moderate 3: B2 left out | Fixed | B2 columns added to Table V, B2 named in every Nobel comparison |
| Moderate 4: library loss unknown | Fixed | E15 (`experiments/run_milp.py --mode bound`): 21,203 single-interval MILPs solved to optimality (max relative gap 9e-7). The library loses at most 0.045% against the bound, and the oracle is within 0.55% of it (Table XII). The first E15 design, 24-interval windows, was dropped before use: it hit the time limit with 2 to 22% gaps and used a flow-mod surrogate that is not a valid bound |
| Moderate 5: reproduction | Fixed | `README.md` rewritten, `REPRODUCE.md` and `reproduce.ps1` added (all 7 library scenarios with their environment variables), `requirements.txt` pinned to `environment.json`, unused packages removed |
| Moderate 6: validation coverage | Fixed | Table VIII now reports test coverage (0 uncovered of 2,160 intervals at every K) |
| Minor: abstract `\,s` | Fixed | The abstract was rewritten (249 words) and no longer contains the macro |
| Minor: GÉANT ILP time | Fixed | Text uses `\geaIlpS` (3.5 s, 60 matrices) |
| Minor: library saturation mechanism | Fixed | Text cites the 51-candidate pool (`nobCand`) |
| Minor: oracle change macro | Fixed | `nobhlOchg` |
| Minor: Table XI overfull | Fixed | No overfull boxes remain in `main.log` |
| Minor: E12 docstring | Fixed | `run_main.py:137` |
| Minor: J without penalty | Fixed | `evaluate()` docstring and Section VI-D |
| Minor: one-off scripts, duplicate draft | Fixed | Moved to `paper/tools/archive_oneoff/` with a README |
| Minor: `lira/drift` empty, `_unused` import | Fixed | Package docstring points to `run_extra.py`, import removed |
| Minor: MLP ignores sample weights | Not changed | LiRA is a constant policy for every backend in E13, so the weights have no effect on any reported number. The code comment documents it |
| Minor: `states_from` starts with prev = 0 | Not changed | Changing it would retrain every policy. It affects at most one label per segment (5 on Abilene, 6 on GÉANT, 1 on Nobel) |
| Missing: DRL baseline | Not possible here | `torch` is broken in this environment |
| Missing: second noisy real trace | Not possible here | No public multi-week trace on disk |

Tests: 18 of 18 pass after the changes. The paper compiles without errors, warnings or overfull boxes (14 pages).

## Scorecard after remediation

| Dimension | Before | After | Reason |
|---|---|---|---|
| Reproducibility | 6 | 8 | Scripted end-to-end order and pinned versions. Library builds still take hours |
| Experimental validity | 6 | 7 | The information assumption is now tested and reported. The main tables still use D_t |
| Baselines & comparisons | 7 | 8 | Static rule and the library-free bound added |
| Claim–implementation alignment | 7 | 9 | No typed result numbers remain except definitions and the 0.0078 Wilcoxon floor |
| Statistical validity | 6 | 6 | Effect sizes added for two comparisons, but Nobel still has 8 daily samples |
| **Overall** | **7** | **8** | |
