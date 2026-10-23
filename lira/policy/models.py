"""Classifier backends with a fast single-row predict (used inside sequential rollouts).

Backends: xgb (default), lgbm, rf, mlp. Every backend is fitted on a fixed class list and
returns an index into `classes` (library configuration ids).
"""
import numpy as np
import xgboost as xgb


class ConstantModel:
    def __init__(self, cls):
        self.cls = int(cls)

    def predict_one(self, row):
        return self.cls

    def predict_many(self, X):
        return np.full(len(X), self.cls)


class XGBModel:
    def __init__(self, classes, booster, best_it):
        self.classes, self.booster, self.best_it = classes, booster, best_it

    def predict_one(self, row):
        p = self.booster.inplace_predict(row[None, :], iteration_range=(0, self.best_it))
        return int(self.classes[int(np.argmax(p[0]))])

    def predict_many(self, X):
        p = self.booster.inplace_predict(X, iteration_range=(0, self.best_it))
        return self.classes[np.argmax(p, axis=1)]


class SklearnModel:
    def __init__(self, est):
        self.est = est

    def predict_one(self, row):
        return int(self.est.predict(row[None, :])[0])

    def predict_many(self, X):
        return self.est.predict(X)


def fit_classifier(X, y, w=None, Xv=None, yv=None, backend="xgb", seed=0, n_jobs=16,
                   rounds=150, depth=6):
    """y holds library config ids. Returns a model object with predict_one/predict_many."""
    classes = np.unique(y)
    if len(classes) == 1:
        return ConstantModel(classes[0])
    enc = {c: i for i, c in enumerate(classes)}
    ye = np.array([enc[c] for c in y])
    if backend == "xgb":
        dtr = xgb.DMatrix(X, label=ye, weight=w)
        evals, kw = [], {}
        if Xv is not None:
            m = np.isin(yv, classes)
            if m.sum() > 0:
                dv = xgb.DMatrix(Xv[m], label=np.array([enc[c] for c in yv[m]]))
                evals, kw = [(dv, "val")], {"early_stopping_rounds": 15}
        params = {"objective": "multi:softprob", "num_class": len(classes), "max_depth": depth,
                  "eta": 0.1, "subsample": 0.8, "colsample_bytree": 0.8, "tree_method": "hist",
                  "nthread": n_jobs, "seed": seed, "eval_metric": "mlogloss"}
        bst = xgb.train(params, dtr, rounds, evals=evals, verbose_eval=False, **kw)
        best = getattr(bst, "best_iteration", None)
        best_it = (best + 1) if best is not None and evals else bst.num_boosted_rounds()
        return XGBModel(classes, bst, best_it)
    if backend == "lgbm":
        import lightgbm as lgb
        est = lgb.LGBMClassifier(n_estimators=rounds, learning_rate=0.1, num_leaves=63,
                                 subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                                 random_state=seed, n_jobs=n_jobs, verbose=-1)
        est.fit(X, y, sample_weight=w)
        return SklearnModel(est)
    if backend == "rf":
        from sklearn.ensemble import RandomForestClassifier
        est = RandomForestClassifier(n_estimators=100, min_samples_leaf=2, n_jobs=n_jobs,
                                     random_state=seed)
        est.fit(X, y, sample_weight=w)
        est.set_params(n_jobs=1)   # single-row inference: no thread pool (it fails under joblib)
        return SklearnModel(est)
    if backend == "mlp":
        from sklearn.neural_network import MLPClassifier
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        est = make_pipeline(StandardScaler(), MLPClassifier(
            hidden_layer_sizes=(256, 256), batch_size=512, learning_rate_init=1e-3,
            max_iter=40, early_stopping=True, random_state=seed))
        est.fit(X, y)  # MLPClassifier has no sample_weight
        return SklearnModel(est)
    raise ValueError(backend)
