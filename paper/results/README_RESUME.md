# Results folder: status and how to resume (saved 2026-10-19)

Everything here is MEASURED by code in `experiments/`. `RESULTS.md` is regenerated from the CSVs by
`python experiments/make_report.py` (run it again after any experiment finishes).

## Done (CSV present)
E1 main comparison (scenarios base, highload, highdyn; stress for Abilene only so far), E3 case study,
E4 per-link wear, E9 wear sensitivity, E12 gap to oracle, E2 price sweep (base), E6 library size,
E8 drift (all 3 topologies), E10 theta sweep, E13 model choice, E14 rolling folds,
E1b/E5 optimisation baselines for Nobel and GEANT, E7 ablation (base + partial other scenarios),
E2b joint price sweep (partial).

## UPDATE 2026-10-23: E15 (lower bound), E16 (D_{t-1}) and E17 (static rule) added after the forensic audits. See FINDINGS.md sections 6 and 7, and REPRODUCE.md in the project root for the full command order. Everything below is historical.

## UPDATE 2026-10-19 (later): ALL runnable experiments are finished; see FINDINGS.md. The section below is historical.

## Still pending / was running when saved (all scripts skip finished outputs, so just re-run)
```
cd "E:\Work\SDN energy aware 1"
python experiments/run_main.py  --exp E1 E2 E2b E7        # remaining scenarios (stress Nobel/GEANT, highdyn/stress E2, ...)
python experiments/run_extra.py --exp E1b E5 --topos abilene --n-ga 15   # Abilene opt baselines + scalability (SNDlib germany50, ta2)
python experiments/make_report.py
```
Check logs in `results/runlogs/*.log` to see which jobs finished.

## Not run (cannot be run here)
- E11 Mininet emulation (needs a Linux VM with Mininet/OVS/Ryu).
- B8 PPO baseline (optional in the plan).
- Link-failure drift, Topology Zoo graphs (site unreachable; SNDlib germany50 and ta2 are used instead).
- B2 here is a library-restricted rolling-horizon DP, NOT a full multi-period MILP.

## Key findings so far (see RESULTS.md for numbers)
1. Base scenario, real traces (Abilene, GEANT): the oracle is one constant configuration, the exact snapshot rule
   barely switches, and LiRA equals B4/B6/B7. No advantage is measurable.
2. Nobel (semi-synthetic, very noisy): B4 flaps (about 12 changes/day); hysteresis (B6) and LiRA remove nearly all.
   In Nobel-highload LiRA (0.80 changes/day, cost 880.9) beats tuned hysteresis (1.07, 887.0) and B4 (1.76, 890.7).
3. The paper's claim must be reframed or tested on harder traffic before submission; the paper tables/figures still
   hold PLACEHOLDER numbers and must be regenerated from these CSVs.
