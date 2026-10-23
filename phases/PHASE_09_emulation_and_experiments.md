# Phase 9 — Emulation + Full Experiment Campaign + Statistics

**Goal:** Run E1–E14 (see `DATASETS_AND_EXPERIMENTS.md`) and write every number into `results/`.
**Module:** `lira/emu/{mininet_topo.py, ryu_app.py, replay.py}`, `experiments/{run_all.py, configs/*.yaml, stats.py, make_figures.py, make_tables.py}`

## 9.1 Mininet/Ryu emulation (E11)
- Abilene in Mininet (12 OVS switches), link bandwidth scaled ×1/100 (TCLink), delays from geographic distance.
- Traffic: D-ITG or iperf3 flows that replay a scaled 24 h Abilene TM segment, sped up (1 interval = 30 s).
- Ryu app applies each method's config log: port down/up for sleep (to emulate a sleeping link), flow-mods for routing. Make-before-break ordering when possible.
- Measure: packet loss and RTT spikes during transitions, flow-mod install time, controller CPU.
- Compare B4 vs B6 vs LiRA over the same segment, 5 repetitions.
- State the limit clearly: Mininet does not emulate real line-card wake-up times. Model the wake-up delay (published values) as an added delay before a port is usable.

## 9.2 Campaign runner
- `run_all.py --exp E1 --topo all --seeds 0-4` → `results/runs/...` (parquet logs) + `results/summary/E1.csv`.
- Fixed seeds, saved config hashes, and the git commit hash in every output file.

## 9.3 Statistics (`stats.py`)
Mean ± 95% CI (bootstrap, 10k), Wilcoxon signed-rank on daily totals, Holm-Bonferroni correction, Cliff's delta effect size.

## 9.4 Figures/tables
`make_figures.py` writes PGFPlots-ready `.dat`/`.csv` files to `paper/data/`, so the LaTeX plots read the real data (no copied numbers). `make_tables.py` writes `.tex` table bodies to `paper/tables/`.

## 9.5 Fill the abstract
`[X]` = retention (%), `[Y]` = config-change reduction (%), `[Z]` = transition reduction (%), `[T]` = median decision latency (ms). Take them from `results/summary/E1.csv` (average over the 3 topologies, or report per topology). Write them to `results/headline.json`.

## Exit gate
All experiments finished; `headline.json` exists; every figure and table is generated from scripts; a fresh-clone rerun of E1 on Abilene reproduces the numbers within the CI.
