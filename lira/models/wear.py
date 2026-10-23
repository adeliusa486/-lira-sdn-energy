"""Device-wear model after Chiaraviglio et al. (sleep vs. power cycling).

Full model per link e over a horizon:
    AF_e = (1 - tau_off) * AF_on + tau_off * AF_off + chi * f_tr
tau_off = fraction of intervals asleep, f_tr = transitions per day.

For the DP oracle the model is split into per-step terms (Markov):
    node(c)      = (AF_off - AF_on) / n_day * #links asleep in c
    edge(c1, c2) = chi * #links toggled
Summed over one day of decisions this equals sum_e (AF_e - AF_on) exactly,
so the linearisation is exact for the link-summed AF (not for max_e AF_e).
"""
from dataclasses import dataclass

import numpy as np
import yaml

from lira import CONFIGS


@dataclass
class WearModel:
    af_on: float = 1.0
    af_off: float = 0.6
    chi: float = 0.01

    @classmethod
    def from_yaml(cls, path=CONFIGS / "power.yaml"):
        with open(path) as f:
            w = yaml.safe_load(f)["wear"]
        return cls(w["af_on"]["value"], w["af_off"]["value"], w["chi"]["value"])

    def acceleration(self, X, intervals_per_day):
        """X: [T, L] link states over time -> AF per link [L]."""
        X = np.asarray(X, dtype=float)
        tau_off = 1 - X.mean(axis=0)
        days = X.shape[0] / intervals_per_day
        f_tr = np.abs(np.diff(X, axis=0)).sum(axis=0) / max(days, 1e-12)
        return (1 - tau_off) * self.af_on + tau_off * self.af_off + self.chi * f_tr

    def node_vector(self, library, intervals_per_day):
        X = np.stack([c.x for c in library])
        return (self.af_off - self.af_on) / intervals_per_day * (1 - X).sum(axis=1)

    def edge_matrix(self, library):
        X = np.stack([c.x for c in library])
        return self.chi * np.abs(X[:, None, :] - X[None, :, :]).sum(axis=2)
