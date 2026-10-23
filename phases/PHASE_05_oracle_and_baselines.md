# Phase 5 — Offline Oracle & Classical Baselines

**Goal:** Exact sequence-optimal labels, plus all non-learning baselines.
**Module:** `lira/oracle/dp.py`, `lira/baselines/{always_on, snapshot_ilp, multiperiod_milp, ga_snapshot, elastictree, hysteresis, min_dwell}.py`

## 5.1 DP oracle (`dp.py`)
- Trellis: states = K configs, stages = T intervals. Node cost = E(c,D_t) if feasible, else ∞. Edge cost = λ_R R + λ_W W.
- Viterbi recursion: `V_t(c) = E(c,D_t) + min_{c'} [V_{t−1}(c') + λ_R R(c',c) + λ_W W(c',c)]`.
- Pre-compute the K×K switching matrix once, which makes it `O(T·K²)`. Vectorise over c.
- The wear term depends on history through τ_off and f_tr. Use the per-transition linearisation (each transition adds a fixed wear increment, each sleeping interval adds a fixed benefit) so the problem stays Markov. Evaluate the full non-linear AF afterwards.
- Outputs: labels `c*_t` per (topology, λ_R, λ_W) and the oracle cost (lower bound).

## 5.2 Validation
On 3 small cases (T=48, K=8), solve the same problem as a MILP and check the DP cost matches to within 1e−6.

## 5.3 Baselines
- **B0 always-on**, **B1 per-snapshot ILP** (uses ILP solves on *each* test TM, run in parallel, with the runtime recorded), **B3 GA snapshot**.
- **B2 multi-period MILP** with rolling horizon H=12, perfect-forecast and naive-forecast variants. Report runtime per decision.
- **B5 ElasticTree-style greedy**: switch off least-used links while still feasible.
- **B6 hysteresis** and **B7 min-dwell** applied on top of B4 (built in Phase 6). Tune δ and dwell on validation only.

## Exit gate
DP = MILP on small cases; all baselines output a per-interval config log in the common format `results/runs/{method}/{topo}/seed{s}.parquet`.
