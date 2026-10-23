"""Link power: P = N*chassis + sum_l [x_l (ports*idle + dyn*(u_ab+u_ba)) + (1-x_l) ports*sleep]."""
from dataclasses import dataclass

import numpy as np
import yaml

from lira import CONFIGS, DYN
from lira.models.routing import utilization


@dataclass
class PowerModel:
    chassis_w: float
    port_idle_w: float
    port_dyn_w: float
    port_sleep_w: float = 0.0
    ports_per_link: int = 2

    @classmethod
    def from_yaml(cls, path=CONFIGS / "power.yaml"):
        with open(path) as f:
            p = yaml.safe_load(f)["power"]
        dyn = float(DYN) if DYN is not None else p["port_dyn_w"]["value"]
        return cls(p["chassis_w"]["value"], p["port_idle_w"]["value"], dyn, p.get("port_sleep_w", {"value": 0.0})["value"],
                   p["ports_per_link"])

    def power(self, topo, cfg, d):
        """Watts for config cfg on demand d [T, OD] -> [T]."""
        u = utilization(topo, cfg.split, d)  # [T, A]
        # the transmitting port of each direction carries that direction's load
        u_link = u.reshape(u.shape[0], topo.L, 2).sum(axis=2)
        per_link = self.ports_per_link * self.port_idle_w + self.port_dyn_w * u_link
        sleeping = self.ports_per_link * self.port_sleep_w * (1 - cfg.x).sum()
        return self.chassis_w * topo.N + (per_link * cfg.x).sum(axis=1) + sleeping

    def max_link_power(self, topo):
        """Idle power of all links on (the normalisation unit for energy)."""
        return topo.L * self.ports_per_link * self.port_idle_w

    def link_cost(self, topo):
        """Per-link power saved by waking vs. sleeping (L,): the ILP objective coefficient."""
        return np.full(topo.L, self.ports_per_link * (self.port_idle_w - self.port_sleep_w))

    def library_power(self, topo, library, d):
        return np.stack([self.power(topo, c, d) for c in library], axis=1)  # [T, K]
