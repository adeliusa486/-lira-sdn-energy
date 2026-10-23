# Phase 3 — Network, Power, Reconfiguration & Wear Models

**Goal:** Turn the cost terms E, R, W and the MLU check into tested code.
**Module:** `lira/models/` → `network.py`, `routing.py`, `power.py`, `reconfig.py`, `wear.py`, `cost.py`

## 3.1 Routing / utilisation (`routing.py`)
- Pre-compute k=4 shortest paths per OD on the full graph.
- A config sets path split ratios; links that are off remove the paths that use them.
- `link_load(c, D)` uses a sparse path-link incidence matrix: `u = A · (split ⊙ d) / cap`. This must be vectorised, because it runs millions of times.

## 3.2 Power (`power.py`)
`P(c,D) = Σ_v P_chassis + Σ_e x_e (P_port_idle + P_dyn · u_e)`
- Use measured values from cited sources (e.g., Mahadevan et al. 2009 line-card/port power; Chiaraviglio et al. 2012 ISP model). Keep them in `configs/power.yaml` with a citation for each number.
- Sensitivity: load-proportional share 0–30%.
- Both link ends must sleep for a link to save energy. Model the port pair.

## 3.3 Reconfiguration (`reconfig.py`)
`R(c,c') = α·#link toggles + β·#flow-mods + γ·bytes on changed paths`
- #flow-mods: compare per-switch rule sets produced by `routing.py`.
- α, β, γ are normalised so that each term equals 1 at its 95th percentile on the training data. Report this. Then λ_R scales R against energy.

## 3.4 Wear (`wear.py`)
- Use the lifetime model of Chiaraviglio et al. (sleep-mode lifetime papers): acceleration factor from temperature (Arrhenius, sleep lowers it) and thermal cycling (Coffin–Manson, transitions raise it).
- `AF_e = (1−τ_off)·AF_on + τ_off·AF_off + χ·f_tr`, with parameters from the paper; χ swept in E9.
- Report both AF and the raw transition count, so the results do not depend only on the model.

## 3.5 Total cost (`cost.py`)
`J(c_{1:T}) = Σ_t E(c_t,D_t) + λ_R R(c_{t−1},c_t) + λ_W W(c_{t−1},c_t)` plus a feasibility mask.

## Tests (`tests/test_models.py`)
- All-on config: power equals the analytic sum; MLU matches a NetworkX max-flow sanity check.
- R(c,c)=0, R symmetric where expected; W ≥ 0.
- A hand-made 4-node example with known answers.

## Exit gate
All tests pass; every constant in `configs/*.yaml` has a citation; a 10k-evaluation benchmark runs in < 2 s on GÉANT.
