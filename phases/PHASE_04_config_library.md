# Phase 4 — Configuration Library Generation (ILP + GA)

**Goal:** A compact library C of K energy-efficient, feasible configurations that covers the traffic seen in training.
**Module:** `lira/library/` → `ilp.py`, `ga.py`, `cluster.py`, `build_library.py`, `coverage.py`

## Steps
1. **Representative TMs:** k-means (or k-medoids) on training TM features → M ∈ {64,128,256} centroids, plus the per-cluster 95th-percentile TM (for robustness to peaks).
2. **ILP (`ilp.py`)** per representative TM: min power s.t. flow conservation, capacity with MLU ≤ θ, link-pair sleep, connectivity. Use the path-based formulation (k=4 paths). Solver: Gurobi or HiGHS, MIP gap 1%, time limit 300 s. Log the gap and runtime for each solve. This is also baseline B1.
3. **GA (`ga.py`)**: pymoo NSGA-II, binary link-state chromosome, objectives (power, MLU), repair operator for connectivity. Run on the same TMs. This is also baseline B3, and it adds Pareto-diverse configs.
4. **Merge + dedupe:** identical `x` vectors are merged; routing is re-optimised per `x` with an LP for minimal MLU.
5. **Coverage (`coverage.py`)**: for each training/validation TM, check that at least one library config is feasible. Add configs greedily (set cover) until ≥ 99.5% coverage. The all-on config is always included as a safe fallback.
6. **Prune to K** ∈ {8,16,32,64,128,256} by greedy cost-coverage (used in E6).

## Outputs
`artifacts/library/{topo}_K{K}.pkl`, a solver log CSV, and a coverage report.

## Exit gate
Coverage ≥ 99.5% on validation; ILP gap ≤ 1% on ≥ 95% of solves; library build is reproducible from its seed.
