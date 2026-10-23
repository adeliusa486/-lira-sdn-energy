"""NSGA-II over binary link states (power vs. MLU), also baseline B3.

Routing for a chromosome = ECMP over the shortest alive of the k paths.
Repair: if an OD is cut, switch on the links of its shortest candidate path.
"""
import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.repair import Repair
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.operators.sampling.rnd import BinaryRandomSampling
from pymoo.optimize import minimize

from lira.models.routing import ecmp_split, mlu


class ConnectivityRepair(Repair):
    def __init__(self, topo):
        super().__init__()
        self.topo = topo

    def _do(self, problem, X, **kwargs):
        t = self.topo
        for i in range(len(X)):
            x = X[i].astype(float)
            alive = t.alive_paths(x)
            for lo, hi in t.od_slices:
                if not alive[lo:hi].any():
                    x[t.path_link[lo].indices] = 1
                    alive = t.alive_paths(x)
            X[i] = x.astype(bool)
        return X


class LinkSleepProblem(ElementwiseProblem):
    def __init__(self, topo, d, theta):
        super().__init__(n_var=topo.L, n_obj=2, n_ieq_constr=1, xl=0, xu=1, vtype=bool)
        self.topo, self.d, self.theta = topo, d, theta

    def _evaluate(self, x, out, *args, **kwargs):
        split = ecmp_split(self.topo, x.astype(float))
        m = 10.0 if split is None else float(mlu(self.topo, split, self.d)[0])
        out["F"] = [x.sum(), m]
        out["G"] = [m - self.theta]


def run_nsga2(topo, d, theta=0.8, pop=40, gens=60, seed=0):
    """Return the feasible Pareto set of link-state vectors (n, L)."""
    algo = NSGA2(pop_size=pop, sampling=BinaryRandomSampling(), crossover=TwoPointCrossover(),
                 mutation=BitflipMutation(), repair=ConnectivityRepair(topo),
                 eliminate_duplicates=True)
    res = minimize(LinkSleepProblem(topo, d, theta), algo, ("n_gen", gens), seed=seed,
                   verbose=False)
    if res.X is None:
        return np.zeros((0, topo.L))
    return np.atleast_2d(res.X).astype(float)
