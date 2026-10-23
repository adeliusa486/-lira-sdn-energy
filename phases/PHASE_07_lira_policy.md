# Phase 7 — LiRA: Sequential Learner + Safety Layer

**Goal:** The proposed history-aware policy that imitates the DP oracle.
**Module:** `lira/policy/{features_seq.py, model.py, dagger.py, cost_sensitive.py, safety.py, controller.py}`

## 7.1 Inputs to the policy
`s_t = [φ(D_t), φ(D_{t−1}), …, φ(D_{t−h}), onehot/embed(c_{t−1}), dwell_{t−1}, Δvolume, time features]`, h ∈ {0,1,3,6} (swept).

## 7.2 Models
- **Main:** LightGBM/XGBoost multiclass over K configs (fast, strong on tabular data).
- **Alternatives (E13):** MLP; small GRU/LSTM over the last h TMs; RF.

## 7.3 Training
1. **Behaviour cloning** on DP labels `c*_t` with the *oracle* previous config.
2. **Cost-sensitive loss:** sample weight or label smoothing based on the regret matrix `Q_t(c) − Q_t(c*)`, where Q is the DP cost-to-go. A cheaper option is to train a regressor for Q per config and take the argmin. Try both and keep the better one on validation.
3. **DAgger** (3–5 rounds): run the policy on the training sequence, collect the states it visits (its own c_{t−1}), relabel with the DP *conditioned on that state* (DP from (t, c_{t−1}) forward, cheap with the cost-to-go table), aggregate, retrain.
4. Hyperparameters: same Optuna setup as Phase 6, but the objective is **validation sequence cost J**, not accuracy.

## 7.4 Safety layer (`safety.py`)
At run time, given the measured `D_t` (or the last one seen):
- If the predicted c breaks MLU ≤ θ, pick `argmin_{c feasible} [E + λ_R R(c_{t−1},c)]` (vectorised over K).
- Log every fallback. The fallback rate is a reported metric.

## 7.5 Controller (`controller.py`)
Decision loop: get TM → features → predict → safety → emit diff (link toggles, flow-mods) → log. Measure end-to-end latency with `time.perf_counter_ns`.

## Exit gate
On validation, LiRA's sequence cost J < B4, B6 and B7 on all three topologies for the default λ, and the median decision latency is under 10 ms.
