"""Phase 2 features. Every fitted transform (scaler, PCA, top-OD choice) uses the training split only.

Per interval t: PCA of log1p(OD) (95 % variance), total volume, top-10 OD shares,
time-of-day sin/cos, day-of-week one-hot, and deltas of (volume, PCA) over h in {1,3,6}.
Lags never cross a segment boundary (an unfilled gap); such rows are flagged invalid.
`Featurizer.transform` applies the train-fitted transforms to any traffic (e.g. shifted
traffic in the drift experiments).
"""
import json

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from lira import DATA_PROC

LAGS = (1, 3, 6)


class Featurizer:
    def __init__(self, topo_name, load=1.0):
        p = DATA_PROC / topo_name
        self.p = p
        od = np.load(p / "od.npy").astype(np.float64) * load
        self.train = json.loads((p / "splits.json").read_text())["train"]
        logd = np.log1p(od[self.train])
        self.scaler = StandardScaler().fit(logd)
        self.pca = PCA(n_components=0.95, svd_solver="full", random_state=0).fit(
            self.scaler.transform(logd))
        self.top_idx = np.argsort(od[self.train].mean(axis=0))[::-1][:10]
        self.vol_mean = od[self.train].sum(axis=1).mean()
        k = self.pca.n_components_
        self.names = ([f"pca{i}" for i in range(k)] + ["volume"] + [f"top{i}" for i in range(10)]
                      + ["tod_sin", "tod_cos"] + [f"dow{i}" for i in range(7)]
                      + [f"d{h}_{n}" for h in LAGS for n in [f"pca{i}" for i in range(k)] + ["volume"]])
        self.n_snapshot = k + 1 + 10 + 2 + 7  # columns before the lag deltas

    def transform(self, od, ts, seg):
        od = np.asarray(od, dtype=np.float64)
        Z = self.pca.transform(self.scaler.transform(np.log1p(od)))
        vol = od.sum(axis=1, keepdims=True)
        top = od[:, self.top_idx] / np.maximum(vol, 1e-12)
        minutes = (ts.hour * 60 + ts.minute).to_numpy()
        tod = np.stack([np.sin(2 * np.pi * minutes / 1440), np.cos(2 * np.pi * minutes / 1440)], 1)
        dow = np.eye(7)[ts.dayofweek.to_numpy()]
        base = np.hstack([Z, vol / self.vol_mean])
        lagged, valid = [], np.ones(len(od), dtype=bool)
        for h in LAGS:
            prev = np.roll(base, h, axis=0)
            ok = np.zeros(len(od), dtype=bool)
            ok[h:] = seg[h:] == seg[:-h]
            valid &= ok
            lagged.append(np.where(ok[:, None], base - prev, 0.0))
        X = np.hstack([base, top, tod, dow] + lagged).astype(np.float32)
        return X, valid


def build(topo_name):
    p = DATA_PROC / topo_name
    od = np.load(p / "od.npy")
    ts = pd.DatetimeIndex(np.load(p / "timestamps.npy"))
    seg = np.load(p / "segment.npy")
    fz = Featurizer(topo_name)
    X, valid = fz.transform(od, ts, seg)
    np.savez_compressed(p / "features.npz", X=X, valid_lags=valid, names=np.array(fz.names),
                        top_idx=fz.top_idx, pca_components=fz.pca.n_components_,
                        n_snapshot=fz.n_snapshot)
    print(f"[{topo_name}] features {X.shape}, PCA comps {fz.pca.n_components_}, "
          f"rows without full lags {int((~valid).sum())}")
    return X


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:]:
        build(t)
