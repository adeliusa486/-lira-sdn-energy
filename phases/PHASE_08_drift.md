# Phase 8 — Drift Detection & Retraining

**Goal:** Detect traffic regime shifts and recover performance cheaply.
**Module:** `lira/drift/{detectors.py, inject.py, retrain.py}`

## Steps
1. **Signals:**
   - (a) online regret proxy: `E(c_t,D_t) − min_c E(c,D_t)` plus the fallback indicator (needs no labels);
   - (b) feature drift: KS test on the top-5 PCA components over a sliding window, or Page–Hinkley on total volume.
2. **Detectors:** ADWIN (δ=0.002), Page–Hinkley, KS-window. Choose on validation by detection delay vs false alarms.
3. **Drift injection (`inject.py`)** on the test periods of D1/D2, giving dataset D4:
   - sudden volume step +40%; gradual growth ramp of +60% over 7 days; diurnal phase shift of 6 h; hotspot (top OD × 3); permanent link failure (remove a link, rerouted traffic).
   - Also look for *natural* drift in the real traces (e.g., known Abilene upgrade periods) and report it if present.
4. **Retraining (`retrain.py`):** on detection, retrain on the sliding window of the last W days (W ∈ {3,7,14}). DP labels on that window plus a warm-started model. Optionally refresh the library with new ILP solves for TMs that are not covered.
5. **Compare:** no retraining, periodic retraining (daily or weekly), drift-triggered retraining. Report cost, number of retrains and compute.

## Metrics
Detection delay (intervals), false alarms per 1k intervals, cumulative cost after drift, time to recover to 95% of the pre-drift retention.

## Exit gate
Triggered retraining matches periodic retraining within a few percent of cost, using clearly fewer retrains.
