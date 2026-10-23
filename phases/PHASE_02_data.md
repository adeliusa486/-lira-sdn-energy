# Phase 2 — Data Acquisition & Preprocessing

**Goal:** Load clean, checked topology + TM time series for Abilene, GÉANT, Nobel-Germany (+ synthetic sets).
**Module:** `lira/data/` → `download.py`, `parse_sndlib.py`, `parse_abilene.py`, `parse_totem.py`, `preprocess.py`, `features.py`, `splits.py`

## Steps
1. **Download** (script, never by hand; save SHA-256 hashes in `data/MANIFEST.json`):
   - SNDlib native/XML for `abilene`, `geant`, `nobel-germany` (topology + static and dynamic demands).
   - Abilene 5-min TMs (Y. Zhang's dataset, 2004).
   - GÉANT 15-min TMs (TOTEM, Uhlig et al. 2006).
   - Topology Zoo GraphML for the scale topologies.
2. **Parse** into a common format: `topology.json` (nodes, directed links, capacity, length) and `tm.npy` of shape `[T, N, N]` plus `timestamps.npy`.
3. **Check:** node/link counts, missing intervals, negative or NaN entries, unit consistency. Record each value in `PROGRESS.md`.
4. **Nobel-Germany decision:** if the SNDlib dynamic series is shorter than 7 days, generate a 30-day series: gravity model fitted to the SNDlib demands × the diurnal/weekly profile taken from Abilene + log-normal noise (σ fitted to Abilene residuals). State this in the paper as *semi-synthetic*.
5. **Scaling:** scale each topology so that peak MLU on full-power shortest-path routing = 0.5. Save the factor.
6. **Features** (`features.py`): flattened OD vector (log1p), total volume, top-10 OD shares, PCA (fit on train only), time encodings, lags/deltas over h ∈ {1,3,6}.
7. **Splits** (`splits.py`): chronological 60/15/25 and 4 rolling-origin folds. Save the index files.

## Outputs
`data/processed/{abilene,geant,nobel}/{topology.json, tm.npy, timestamps.npy, features.npz, splits.json}`

## Exit gate
- Loader unit tests pass; counts match the published topology descriptions (or the difference is explained)
- No information from the test period is used in scaling, PCA or normalisation
