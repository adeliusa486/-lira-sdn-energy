# Phase 6 — Snapshot-ML Baseline (Reproduce Prior Work)

**Goal:** A fair, strong copy of the "TM → precomputed config" classifier approach (B4), following Gómez-delaHiz et al. (NOMS 2025, doi 10.1109/NOMS57970.2025.11073657) and their TGCN 2026 follow-up (doi 10.1109/TGCN.2026.3724271). Copy their label definition, features, model and configuration-generation method as closely as the papers allow, and document every place where you had to guess.
**Module:** `lira/snapshot/{labels.py, train.py, infer.py}`

## Steps
1. **Labels:** `y_t = argmin_{c∈C feasible} E(c,D_t)` (snapshot-optimal over the same library, so the comparison is fair).
2. **Models:** XGBoost, LightGBM, RandomForest, MLP (2×256, ReLU, dropout 0.2), and the model used by the direct competitor paper.
3. **Hyperparameter search** (Optuna, 50 trials, validation macro-F1). Record the search spaces in `configs/hparams_snapshot.yaml`:
   - XGB: depth 4–10, eta 0.02–0.3, n_estimators 200–1500, subsample 0.6–1.0
   - MLP: Adam, lr 1e−4–3e−3, batch 128–1024, epochs ≤ 200 with early stopping (patience 15)
4. **Inference** goes through the same safety fallback as LiRA, so both are fair on feasibility.
5. **Sanity check against the literature:** accuracy, F1 and energy savings should be in the range reported by the competitor. If they are far off, find the reason before going on.

## Outputs
Trained models, config logs on test, classification report (accuracy, macro-F1, top-3).

## Exit gate
B4 matches the published numbers of prior frameworks within a reasonable margin, or the reason for the difference is documented.
