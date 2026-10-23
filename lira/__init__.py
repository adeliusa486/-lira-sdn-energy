"""LiRA: Lifetime- and Reconfiguration-Aware sequential learning for energy-efficient SDNs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"
RESULTS = ROOT / "results"
CONFIGS = ROOT / "configs"
TOPOLOGIES = ("abilene", "geant", "nobel")

# Scenario knobs for sensitivity runs (default = base scenario, empty tag).
# LIRA_LOAD multiplies all demands after scaling (1.6 -> robust peak MLU 0.8).
# LIRA_DYN overrides the per-port dynamic power in W (base 5 W).
import os as _os
LOAD = float(_os.environ.get("LIRA_LOAD", "1"))
DYN = _os.environ.get("LIRA_DYN")
THETA_ENV = float(_os.environ.get("LIRA_THETA", "0.8"))


def scenario_tag(load=1.0, dyn=None, theta=0.8):
    """Suffix of artifact names for non-base scenarios (base scenario = empty)."""
    tag = "" if load == 1 and dyn is None else f"_L{load:g}" + ("" if dyn is None else f"_D{dyn}")
    return tag + ("" if theta == 0.8 else f"_T{theta:g}")


TAG = scenario_tag(LOAD, DYN, THETA_ENV)
