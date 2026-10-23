"""Drift detection (Phase 8).

The detectors (ADWIN on the regret proxy, Page-Hinkley on the deseasonalised log volume), the
retraining schedule and the library refresh are implemented next to the drift experiment E8 in
`experiments/run_extra.py` (`Detectors`, `stream`, `refresh_library`, `calibrate_ph`), because
they are only used there. This package is kept so that imports of `lira.drift` keep working.
"""
