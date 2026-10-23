# Findings (written from the measured tables; numbers are in RESULTS.md and the CSVs)

Scope: all experiments in `paper/results/` finished except E11 (Mininet, needs a Linux VM) and the optional
PPO baseline. Test splits: Abilene 41.8 days, GÉANT 28.1 days, Nobel 7.5 days (semi-synthetic).

## 1. The central claim is NOT supported on the real traces
- **Abilene and GÉANT (real), all four scenarios:** the offline oracle is one constant configuration. B4, B6, B7,
  LiRA, B2 and the oracle reach the same savings (Abilene 23.97 %, GÉANT 29.85 % in the base scenario) and make
  0–0.02 configuration changes per day. LiRA retention X = 100 %. The reduction Y and Z are undefined because B4
  itself barely switches. Wilcoxon tests give p = 1.0 (Abilene vs B6/B7 identical; vs B4 p_holm = 0.54, n.s.).
- **Nobel (semi-synthetic, 7.5 test days, 8 daily samples):** B4 flaps (11.7 changes/day in the base scenario).
  LiRA cuts that by 97.7 % (X = 100 %), but a tuned hysteresis rule (B6) achieves the same (p_holm = 0.875 vs B6).
  LiRA beats B4 and B7 only (p_holm = 0.023).
- **Only case where LiRA beats tuned hysteresis:** Nobel highload (0.80 vs 1.07 changes/day; cost 880.9 vs 887.0),
  but p_holm = 0.31 (not significant with 8 days). In Nobel stress LiRA is within +0.3 % cost of the oracle.
- Caveat: Nobel noise is i.i.d. log-normal per OD pair and interval (σ = 1.23 fitted on Abilene residuals), which
  makes the series unrealistically jagged. Flapping on Nobel may be an artifact of the synthetic generator.

## 2. Why: with these power and traffic models the best link set rarely changes
Idle port power dominates (30 W idle vs 5 W dynamic), so the energy-optimal set of sleeping links depends on
connectivity and peak load, not on the instantaneous traffic. Higher load (peak 0.8) and 3× dynamic power did not
change this on Abilene/GÉANT.

## 3. What does hold
- DP oracle = independent MILP to 1e-14 (3 real-data cases per topology). DP over the full test split takes ≈ 1.5 s.
- Safety layer: 0 % MLU violations with it; without it (ablation) 0.14–0.17 % violations on Nobel highload/stress.
- Ablation (Nobel stress, λR default): removing prev-config raises cost 897.4 → 902.0, removing cost-sensitive
  loss 897.4 → 898.6, removing DAgger 897.4 → 899.0 (3 seeds, small effects, no significance test). In all other
  scenarios the expert is constant, so all variants collapse to the same constant policy.
- Decision time: LiRA median 0.01 ms when the policy is constant, 0.7–4.2 ms with a boosted-tree model; B4 about
  1–1.6 ms; per-snapshot ILP 0.4 s (Nobel) to 4.1 s (GÉANT), NSGA-II 28–42 s, ElasticTree 0.09–0.56 s.
- Scalability (E5): ILP median 1.6 s (Germany50, 50 nodes), 11.4 s (TA2, 65 nodes); safety check 0.07–0.36 ms.
- θ sweep: results for θ = 0.7, 0.8, 0.9 are identical on Nobel (coverage 100 %); θ = 0.6 forces more switching.
- Optimisation baselines (60-snapshot subsample): ILP and the library snapshot optimum agree within 0.01 pt;
  ElasticTree loses 0.3–2.7 pt; NSGA-II loses 0–0.3 pt (Abilene GA used only 15 snapshots).
- Drift (E8): shifts (growth, hotspot, 6-h phase shift) did not change cost of the static policies, and the
  detectors fired at the same times with and without a shift (false alarms 0.06, 0.00, 0.31 per 1k intervals on
  Abilene, GÉANT, Nobel in the no-shift control). So detection is NOT attributable to the injected shifts here,
  and retraining brought no cost gain for LiRA. The experiment is inconclusive, not a validation.

## 4. Consequences for the paper
- Do not claim large reductions in configuration changes on real traces: the data shows none are needed.
- Options: (a) reframe as an analysis showing when sequence awareness matters (noisy or high-variance traffic,
  large prices, learned snapshot classifiers), with Nobel as the illustrative case; (b) find real traces with
  stronger variation or a model where load-proportional power dominates; (c) shorten the claim to the oracle,
  safety layer and price analysis.
- All tables and figures in `paper/main.tex` still hold placeholder numbers and must be replaced from the CSVs.

## 5. Update after the Mininet emulation (E11) and the paper rewrite
- Mininet 2.3.0 and Open vSwitch 3.7.1 run in WSL2 Ubuntu. The most active Nobel-Germany day (B4 makes 18 changes)
  was replayed (288 intervals, 2 s each, 1 s modeled wake-up, 8 UDP probe flows at 100 packets/s).
- Each B4 transition takes about 1.11 s, of which 99 ms is rule installation (6 switches updated, 1 link woken and 1 slept).
  B4 loses 3.7 probe packets per transition (0.22% of probes inside transition windows, 0.014% over the day, 3 runs).
  LiRA and the always-on control lose none. LiRA uses 31% fewer emulated link-hours than the always-on network.
- In 30 of 60 LiRA runs the trained policy is a constant classifier (all Abilene runs, Nobel base and high-dynamic-power).
- `paper/main.tex` was rewritten around these findings; every number is generated from the CSVs by
  `paper/tools/make_paper_assets.py`. The old placeholder version is in `paper/archive_placeholder_version/`.
- Simulated reviewer notes: `paper/results/PEER_REVIEW_main_v2.md`.

## 6. Update after the forensic audits (2026-10-23)

Reports: `reports/repo_forensic_audit_2026-10-23.md` and `reports/forensic_writing_audit_2026-10-23.md`.

Corrections to this file:
- Section 1 said high load is the only case where LiRA beats tuned hysteresis. Under stress LiRA also beats B6
  (898.6 vs 899.4, five seeds). Under high dynamic power they tie (883.7).
- Section 3 said the θ = 0.7 to 0.9 results are identical on Nobel. That holds for B4, B6, LiRA and the oracle.
  B7 differs at θ = 0.9 (878.5 vs 885.7).

New mechanism facts (from saved E1 sequences and info files):
- Nobel base: LiRA holds configuration 1 in 2,159 of 2,160 test intervals. The test-period oracle uses
  configuration 2. The 97.7% change reduction is a constant policy.
- Nobel high load: LiRA's test sequence equals the oracle's in every interval and all 5 seeds. The expert is
  nearly constant and the safety layer, which sees D_t, switches exactly when the default becomes infeasible.
- The validation-selected LiRA policy is round 0 (no DAgger data) in 56 of 60 E1 runs.
- B2 (rolling horizon, persistence forecast) ties B6 on Nobel base (875.3) and beats LiRA in 3 of 4 Nobel
  scenarios (base 875.3 vs 875.9, high dynamic power 883.2 vs 883.7, stress 895.4 vs 898.6).

E17, static configuration + LiRA's fallback (`experiments/run_static.py`):
- Equals LiRA (E1, 5 seeds) in 11 of 12 settings. The exception is Nobel stress: static 902.0, LiRA 898.6,
  B6 899.4, B2 895.4, oracle 894.3. That is the only setting where LiRA's learned component matters.

E16, decisions on D_{t-1} (`experiments/run_stale.py`, 3 seeds):
- Costs and change rates move by at most 0.002% (Nobel) and less than 0.001% (Abilene, GÉANT).
- Nobel violations appear: B2, B4, B6 0.05% / 0.19% / 0.19% (base / high load / stress), the same share as
  the always-on network. LiRA 0.05% / 0.14% / 0.17%. Abilene and GÉANT at most 0.008% (B2, Abilene high load).
- Every violated interval of the static rule is a B0-violated interval, where the MLU of the installed
  configuration jumps by 0.66 to 1.36 within one interval (i.i.d. noise peaks). A 0.05 margin does not remove
  them and raises the cost (LiRA high load 886.2 vs 880.9).

E15, per-interval exact lower bound (`experiments/run_milp.py --mode bound`): see the summary in section 7.

## 7. E15: what the library gives up (per-interval exact lower bound)

`experiments/run_milp.py --mode bound` solves the single-interval MILP (free link states, free routing over
the k = 4 paths, wear credit, no switching terms) for every test interval: 21,203 intervals in five settings, all
optimal (largest relative MIP gap 9e-7, median 214 ms). The sum is a lower bound on the J of any controller,
with or without a library, including the full multi-period MILP.

| Setting | Bound | Library snapshot | O* | LiRA | Library loss | O* gap |
|---|---|---|---|---|---|---|
| Abilene base | 7226.7 | 7226.7 | 7226.7 | 7226.7 | 0.000% | 0.000% |
| GÉANT base | 603.7 | 603.7 | 603.7 | 603.7 | 0.011% | 0.011% |
| Nobel base | 874.5 | 874.5 | 874.7 | 875.9 | 0.001% | 0.024% |
| Nobel high load | 876.9 | 877.2 | 880.9 | 880.9 | 0.043% | 0.463% |
| Nobel stress | 889.3 | 889.7 | 894.3 | 898.6 | 0.045% | 0.554% |

The library restriction costs at most 0.045%. The larger Nobel gaps are the cost of holding a configuration
instead of re-optimizing every interval, which the bound ignores. A first design with 24-interval multi-period
windows was dropped: HiGHS hit the time limit with 2 to 22% gaps, and its flow-mod surrogate was not a valid bound.
