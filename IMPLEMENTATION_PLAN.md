# Master Implementation Plan

## 0. Integrity rule (read first)

The abstract contains placeholders `[X]`, `[Y]`, `[Z]`, `[T]`. For an A* venue these **must come from experiments run in this project**. The generic paper prompt asks for "realistic" made-up results. We do not do that here, because invented numbers are research misconduct and reviewers or artifact evaluators can catch them. The prompt is kept (see `paper/PAPER_GENERATION_PROMPT.md`) but changed so it reads every number from `results/*.csv|json`. Expected *ranges* below are planning targets only, never paper content.

## 1. Problem statement

Current ML-for-green-SDN frameworks map each traffic matrix (TM) `D_t` to the cheapest precomputed configuration on its own ("snapshot" decisions). Consecutive decisions flip links between sleep and active, rewrite flow tables, and cause transient disruption. Thermal and power cycling also speeds up hardware ageing. Snapshot methods ignore all three costs.

**Claim to prove:** treating configuration as a *sequential decision problem* keeps most of the energy savings while cutting reconfigurations, link power-state transitions and wear-induced lifetime loss by a large margin, with decision latency in milliseconds.

## 2. Formal model (fixes the notation used everywhere)

- Network `G=(V,E)`, directed link set `E`, demand sequence `D_1..D_T` (TM per interval Δ = 5 or 15 min).
- Configuration library `C={c_1..c_K}`. Each `c_k=(x^k, r^k)`, where `x^k ∈ {0,1}^{|E|}` is link power state and `r^k` is the routing (split ratios over k-shortest paths on active links).
- **Energy** for an interval:
  `P(c,D) = Σ_v P_chassis(v) + Σ_e x_e (P_idle,e + P_dyn,e · u_e(c,D))`, with `E_t = P · Δ`.
  Constants come from published measurements (Mahadevan 2009, Restrepo 2009, Chiaraviglio 2012). Table in Phase 3.
- **Feasibility:** `MLU(c,D) = max_e u_e ≤ θ` (θ = 0.8 default; sweep 0.6–0.9).
- **Reconfiguration cost:**
  `R(c,c') = α·Σ_e |x_e − x'_e| + β·ΔRules(c,c') + γ·Disrupt(c,c')`
  where ΔRules counts flow-mod messages and Disrupt is traffic (bytes) on paths that change.
- **Wear (lifetime) cost:** based on the Chiaraviglio et al. lifetime model (Arrhenius for temperature + Coffin–Manson for thermal cycling). Per-link acceleration factor:
  `AF_e = (1 − τ_e^off)·AF_on + τ_e^off·AF_off + χ · f_e^tr`
  where τ^off is the fraction of time asleep, f^tr is the transition frequency, and χ is the cycling weight. Per-interval wear: `W(c,c') = Σ_e w_e · |x_e − x'_e| − (sleep benefit term)`.
- **Sequential objective:**
  `min_{c_1..c_T} Σ_t [ E(c_t,D_t) + λ_R R(c_{t−1},c_t) + λ_W W(c_{t−1},c_t) ]  s.t. MLU(c_t,D_t) ≤ θ ∀t`
- **Snapshot objective (the baseline):** `c_t = argmin_c E(c,D_t)`, feasible.

Over a finite library this is a shortest-path problem through a trellis (states = configs, stages = time). It is solved exactly offline by **dynamic programming (Viterbi)** in `O(T·K²)`. This exact *offline oracle* is both the label source and the upper bound for the learner. This is a key technical lever and an easy, solid contribution.

## 3. Proposed method — **LiRA** (Lifetime- and Reconfiguration-Aware learner)

1. **Config library** (Phase 4): K ≈ 32–128 energy-efficient configs from per-TM ILP solves on clustered representative TMs, plus GA (NSGA-II) for diversity, then deduplication.
2. **Offline oracle labels** (Phase 5): DP over training sequences gives `c*_t`, the sequence-optimal config.
3. **Policy** (Phase 7): `π(c_t | φ(D_t), φ(D_{t−1..t−h}), c_{t−1}, dwell_{t−1})`.
   - Main model: gradient-boosted trees (XGBoost/LightGBM) or a small MLP, with the previous config one-hot or embedded as input. Trained by imitation of DP labels, with **DAgger** to fix compounding errors (states the policy itself visits).
   - Cost-sensitive loss: weight each mistake by the true sequence-cost regret, not 0/1.
   - **Safety layer:** if the predicted config breaks MLU ≤ θ on the measured TM, fall back to the cheapest feasible config with the smallest R from `c_{t−1}` (a vectorised check, under 1 ms).
   - **Minimum-dwell guard** (optional, ablated): a switch is allowed only if the predicted gain exceeds the switching cost.
4. **Drift detector** (Phase 8): ADWIN on the online regret proxy plus Page–Hinkley on the TM feature distribution (or a KS test on PCA components). A detection triggers (a) retraining on a sliding window and (b) an optional library refresh.
5. **Optional DRL comparison** (PPO) to show that imitating an exact oracle beats model-free RL in sample efficiency and stability. This pre-empts a likely reviewer question.

## 4. Contributions (target list for the Introduction)

1. First formulation of energy-aware SDN configuration that jointly includes energy, reconfiguration cost and device wear as a *sequential* problem, with an exact DP oracle over a configuration library.
2. LiRA: an imitation-learned, history-conditioned policy with a feasibility safety layer and millisecond inference.
3. A lightweight drift detector that triggers retraining under traffic shifts.
4. Evaluation on Abilene, GÉANT and Nobel-Germany real or realistic TM traces, against snapshot-ML, ILP (per-snapshot and multi-period), GA and heuristics, plus Mininet emulation of transition disruption.
5. Open artifact (code, configs, scripts) for reproducibility (ACM badges).

## 5. Ten-phase overview

| # | Phase | Module (code) | Exit gate |
|---|---|---|---|
| 1 | Literature review & reference verification | `tools/verify_refs.py` | ≥35 verified refs, gap matrix done |
| 2 | Data acquisition & preprocessing | `lira/data/` | 3 topologies + TM series loaded, cleaned, split |
| 3 | Network, power & wear models | `lira/models/` | Unit tests pass; power numbers cited |
| 4 | Configuration library generation (ILP + GA) | `lira/library/` | K configs, ≥99% TMs covered feasibly |
| 5 | Offline oracle & classical baselines | `lira/oracle/`, `lira/baselines/` | DP optimal, matches MILP on small cases |
| 6 | Snapshot-ML baseline (reproduce prior work) | `lira/snapshot/` | Accuracy and savings similar to prior papers |
| 7 | LiRA sequential learner + safety layer | `lira/policy/` | Beats snapshot on total sequence cost |
| 8 | Drift detection & retraining | `lira/drift/` | Detection delay and false-alarm rate measured |
| 9 | Emulation + full experiment campaign + statistics | `lira/emu/`, `experiments/` | All E1–E14 done, CIs, significance |
| 10 | Paper writing, figures, artifact | `paper/` | Compiles, every number traced to results |

Details: `phases/PHASE_XX_*.md`.

## 6. Timeline (one researcher, full time)

| Weeks | Phases |
|---|---|
| 1–2 | 1, 2 |
| 3 | 3 |
| 4–5 | 4 |
| 6 | 5, 6 |
| 7–8 | 7 |
| 9 | 8 |
| 10–12 | 9 |
| 13–14 | 10 + internal review (peer-review skill) |

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Nobel-Germany has no long real TM trace | Use the SNDlib dynamic TMs if present; otherwise make a gravity-model series fitted to SNDlib static demands and state this clearly. Abilene and GÉANT remain the real-trace evaluations |
| Wear model criticised as speculative | Use the published Chiaraviglio model and parameters, report a sensitivity sweep over χ, and report raw transition counts (model-free) alongside |
| "Just add hysteresis" reviewer objection | Hysteresis and min-dwell heuristics are explicit baselines (B6/B7). Show the Pareto front |
| ILP too slow on GÉANT | Use path-based formulation, k-shortest paths (k=4), Gurobi academic or HiGHS, MIP gap 1% |
| Results don't support claims | Report honestly. Reframe as Pareto analysis. Never tune on the test split |
| Leakage across time | Chronological splits only, no shuffling, drift experiments use future data only |

## 8. Expected result ranges (planning only — NOT for the paper)

From prior literature, snapshot ML gives about 20–45% link-energy savings versus always-on. A credible target for LiRA is 90–97% retention of those savings, with 50–80% fewer config changes and transitions, and inference under 5 ms. If measured results differ, the paper reports the measured results.
