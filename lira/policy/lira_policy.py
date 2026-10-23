"""Phase 6 (snapshot ML, B4) and Phase 7 (LiRA) policies over a configuration library.

B4  : maps the current traffic features to the energy-optimal feasible config (no history).
LiRA: maps (traffic features, lag deltas, previous config, dwell time) to the config chosen
      by the exact sequence-optimal expert. Trained by imitation + DAgger with a
      cost-sensitive weight (the cost gap between the best and second-best action),
      followed by a feasibility safety layer. The DAgger round with the lowest validation
      sequence cost is kept (no test data is touched).
"""
import time
from dataclasses import dataclass, field

import numpy as np

from lira.oracle.dp import viterbi
from lira.policy.expert import backward_values, expert_actions
from lira.policy.models import fit_classifier

DWELL_CAP = 288


@dataclass
class Ctx:
    """Everything a policy needs for one topology/scenario."""
    tab: object            # CostTables over the whole series
    F: np.ndarray          # [T, nF] features (snapshot columns first)
    n_snap: int            # number of snapshot (non-lag) feature columns
    seg: np.ndarray
    split: dict            # train/val/test index lists
    per_day: int
    K: int

    def rng_idx(self, name):
        i = np.asarray(self.split[name])
        return int(i[0]), int(i[-1]) + 1


def snapshot_labels(tab, sl):
    """Energy-optimal feasible config per interval (what a perfect snapshot classifier outputs)."""
    node = tab.node(0.0)[sl]
    return node.argmin(axis=1).astype(np.int32)


def safe_batch(node, pred):
    """Replace infeasible predictions by the cheapest feasible config. Returns (seq, rate)."""
    bad = ~np.isfinite(node[np.arange(len(pred)), pred])
    out = pred.copy()
    out[bad] = node[bad].argmin(axis=1)
    return out.astype(np.int32), float(bad.mean())


class SnapshotML:
    """B4 reproduction: snapshot classifier + feasibility safety layer."""

    def __init__(self, backend="xgb", seed=0):
        self.backend, self.seed = backend, seed

    def fit(self, ctx):
        a, b = ctx.rng_idx("train")
        va0, va1 = ctx.rng_idx("val")
        y = snapshot_labels(ctx.tab, slice(0, None))
        X = ctx.F[:, :ctx.n_snap]
        self.model = fit_classifier(X[a:b], y[a:b], Xv=X[va0:va1], yv=y[va0:va1],
                                    backend=self.backend, seed=self.seed)
        return self

    def predict(self, ctx, name):
        a, b = ctx.rng_idx(name)
        X = ctx.F[a:b, :ctx.n_snap]
        pred = self.model.predict_many(X).astype(np.int32)
        node = ctx.tab.node(0.0)[a:b]
        seq, fb = safe_batch(node, pred)
        return seq, fb

    def latency(self, ctx, name="test", n=2000):
        a, b = ctx.rng_idx(name)
        X = ctx.F[a:b, :ctx.n_snap].astype(np.float32)
        node = ctx.tab.node(0.0)[a:b]
        lat = []
        for i in np.linspace(0, len(X) - 1, min(n, len(X))).astype(int):
            t0 = time.perf_counter()
            c = self.model.predict_one(X[i])
            if not np.isfinite(node[i, c]):
                c = int(node[i].argmin())
            lat.append(time.perf_counter() - t0)
        return np.array(lat)


@dataclass
class LiRA:
    rounds: int = 3                 # DAgger rounds after the initial imitation round
    beta0: float = 0.5              # expert mixing in the first rollout, halved each round
    cost_sensitive: bool = True
    use_lags: bool = True           # lag-delta features ("recent history of traffic")
    use_prev: bool = True           # previous config + dwell time
    safety: bool = True
    backend: str = "xgb"
    seed: int = 0
    log: list = field(default_factory=list)

    # ------------------------------------------------------------ features
    def _cols(self, ctx):
        return slice(None) if self.use_lags else slice(0, ctx.n_snap)

    def _build(self, Fs, prev, dwell, K):
        n = len(Fs)
        parts = [Fs]
        if self.use_prev:
            oh = np.zeros((n, K), dtype=np.float32)
            oh[np.arange(n), prev] = 1
            parts += [oh, (np.minimum(dwell, DWELL_CAP) / DWELL_CAP).astype(np.float32)[:, None]]
        return np.hstack(parts)

    # ------------------------------------------------------------- rollout
    def rollout(self, tab, Fs, seg, model, beta=0.0, Vb=None, edge=None, rng=None,
                lam_W=0.0, record=False, state=None):
        """Run the policy sequentially on a slice. Returns seq, latencies, fallback rate, states."""
        T, K = tab.E.shape[0], tab.E.shape[1]
        node = tab.node(lam_W)
        F32 = Fs.astype(np.float32)
        nF = F32.shape[1]
        width = nF + (K + 1 if self.use_prev else 0)
        buf = np.zeros(width, dtype=np.float32)
        seq = np.empty(T, dtype=np.int32)
        lat = np.empty(T)
        prev, dwell = (0, 1) if state is None else state
        fb = 0
        st_t, st_p, st_d = [], [], []
        for t in range(T):
            t0 = time.perf_counter()
            buf[:nF] = F32[t]
            if self.use_prev:
                buf[nF:nF + K] = 0
                buf[nF + prev] = 1
                buf[-1] = min(dwell, DWELL_CAP) / DWELL_CAP
            if record:
                st_t.append(t); st_p.append(prev); st_d.append(dwell)
            if beta > 0 and rng.random() < beta:
                c = int(expert_actions(Vb, edge, np.array([t]), np.array([prev]))[0][0])
            else:
                c = model.predict_one(buf)
            if self.safety and not np.isfinite(node[t, c]):
                c = int((edge[prev] + node[t]).argmin())
                fb += 1
            lat[t] = time.perf_counter() - t0
            dwell = dwell + 1 if c == prev else 1
            seq[t], prev = c, c
        self.last_state = (prev, dwell)
        return seq, lat, fb / T, (np.array(st_t), np.array(st_p), np.array(st_d))

    # ----------------------------------------------------------------- fit
    def fit(self, ctx, lam_R, lam_W):
        self.K, self.lam_R, self.lam_W = ctx.K, lam_R, lam_W
        cols = self._cols(ctx)
        a, b = ctx.rng_idx("train")
        v0, v1 = ctx.rng_idx("val")
        rng = np.random.default_rng(self.seed)
        tr, va = ctx.tab.slice(a, b), ctx.tab.slice(v0, v1)
        seg_tr, seg_va = ctx.seg[a:b], ctx.seg[v0:v1]
        F_tr, F_va = ctx.F[a:b][:, cols], ctx.F[v0:v1][:, cols]
        edge = tr.edge(lam_R, lam_W)
        node_tr = tr.node(lam_W)
        Vb_tr = backward_values(node_tr, edge, seg_tr)
        node_va, edge_va = va.node(lam_W), va.edge(lam_R, lam_W)
        Vb_va = backward_values(node_va, edge_va, seg_va)

        def expert_traj(node, edge, seg):
            seq = np.empty(len(node), dtype=np.int32)
            for s in np.unique(seg):
                idx = np.flatnonzero(seg == s)
                seq[idx] = viterbi(node[idx], edge)[0]
            return seq

        def states_from(seq):
            """(t, prev, dwell-before-acting) along a trajectory; mirrors rollout() exactly."""
            prev = np.concatenate([[0], seq[:-1]]).astype(np.int32)
            dwell = np.empty(len(seq), dtype=np.int32)
            cur = 1
            for t in range(len(seq)):
                dwell[t] = cur
                cur = cur + 1 if seq[t] == prev[t] else 1
            return np.arange(len(seq)), prev, dwell

        def labelled(Vb, t, p):
            y, gap = expert_actions(Vb, edge, t, p)
            if self.cost_sensitive:
                g = np.where(np.isnan(gap), np.nanmax(gap) if np.isfinite(gap).any() else 1.0, gap)
                w = np.clip(g / max(np.nanmean(g), 1e-12), 0.2, 5.0)
            else:
                w = None
            return y.astype(np.int32), w

        opt_seq = expert_traj(node_tr, edge, seg_tr)
        t, p, d = states_from(opt_seq)
        Xs, ys, ws = [], [], []
        y0, w0 = labelled(Vb_tr, t, p)
        Xs.append(self._build(F_tr[t], p, d, ctx.K)); ys.append(y0)
        if w0 is not None:
            ws.append(w0)
        # validation expert labels along the expert val trajectory (for early stopping)
        vseq = expert_traj(node_va, edge_va, seg_va)
        tv, pv, dv = states_from(vseq)
        yv = expert_actions(Vb_va, edge_va, tv, pv)[0]
        Xv = self._build(F_va[tv], pv, dv, ctx.K)

        best = None
        for r in range(self.rounds + 1):
            X = np.vstack(Xs)
            y = np.concatenate(ys)
            w = np.concatenate(ws) if ws else None
            t0 = time.perf_counter()
            model = fit_classifier(X, y, w, Xv, yv, backend=self.backend, seed=self.seed + r)
            fit_s = time.perf_counter() - t0
            seq_v, _, fbv, _ = self.rollout(va, F_va, seg_va, model, edge=edge_va, lam_W=lam_W)
            Jv = self._cost(va, seq_v, seg_va, lam_R, lam_W)
            self.log.append({"round": r, "samples": len(y), "fit_s": fit_s, "val_J": Jv,
                             "val_fallback": fbv})
            if best is None or Jv < best[0]:
                best = (Jv, model, r)
            if r == self.rounds:
                break
            beta = self.beta0 * (0.5 ** r)
            seq_t, _, _, (st, sp, sd) = self.rollout(tr, F_tr, seg_tr, model, beta=beta,
                                                      Vb=Vb_tr, edge=edge, rng=rng,
                                                      lam_W=lam_W, record=True)
            yn, wn = labelled(Vb_tr, st, sp)
            Xs.append(self._build(F_tr[st], sp, sd, ctx.K)); ys.append(yn)
            if wn is not None:
                ws.append(wn)
        self.val_J, self.model, self.best_round = best
        return self

    @staticmethod
    def _cost(tab, seq, seg, lam_R, lam_W):
        """Selection cost: energy + wear + switching (segment breaks free) + 1e3 per violation."""
        t = np.arange(len(seq))
        n = (tab.E[t, seq] + lam_W * tab.Wn[seq]).sum() + 1e3 * (~tab.feas[t, seq]).sum()
        same = seg[1:] == seg[:-1]
        return float(n + tab.edge(lam_R, lam_W)[seq[:-1], seq[1:]][same].sum())

    # ------------------------------------------------------------- predict
    def predict(self, ctx, name, tab=None, F=None, seg=None):
        a, b = ctx.rng_idx(name)
        cols = self._cols(ctx)
        tab = ctx.tab.slice(a, b) if tab is None else tab
        Fs = (ctx.F[a:b] if F is None else F)[:, cols]
        sg = ctx.seg[a:b] if seg is None else seg
        edge = tab.edge(self.lam_R, self.lam_W)
        seq, lat, fb, _ = self.rollout(tab, Fs, sg, self.model, edge=edge, lam_W=self.lam_W)
        return seq, lat, fb
