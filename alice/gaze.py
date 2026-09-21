"""Mapping from landmark features to on-screen gaze position.

Model: standardise -> polynomial expansion -> ridge regression, fitted
separately per calibration session. Polynomial degree and ridge strength are
chosen by leave-one-POINT-out cross-validation: every frame from a given
calibration point is held out together. (Leaving out single frames would leak
near-identical frames of the same point into training and make the model look
far more accurate than it is.)
"""
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler


class GazeModel:
    def __init__(self, degrees=(1, 2), alphas=(0.01, 0.1, 1, 10, 100)):
        self.degrees = list(degrees)
        self.alphas = list(alphas)
        self.model = None
        self.degree = None
        self.alpha = None
        self.cv_error_px = None

    @staticmethod
    def _make(degree, alpha):
        return make_pipeline(StandardScaler(),
                             PolynomialFeatures(degree, include_bias=False),
                             Ridge(alpha=alpha))

    def fit(self, X, Y, groups):
        X, Y, groups = np.asarray(X, float), np.asarray(Y, float), np.asarray(groups)
        uniq = np.unique(groups)
        best = None
        for deg in self.degrees:
            for a in self.alphas:
                errs = []
                for g in uniq:
                    tr, te = groups != g, groups == g
                    m = self._make(deg, a).fit(X[tr], Y[tr])
                    errs.append(np.mean(np.linalg.norm(m.predict(X[te]) - Y[te], axis=1)))
                e = float(np.mean(errs))
                if best is None or e < best[0]:
                    best = (e, deg, a)
        self.cv_error_px, self.degree, self.alpha = best
        self.model = self._make(self.degree, self.alpha).fit(X, Y)
        return self

    def predict(self, X):
        return self.model.predict(np.atleast_2d(np.asarray(X, float)))

    def describe(self):
        return {"degree": self.degree, "alpha": self.alpha,
                "cv_error_px": round(self.cv_error_px, 2) if self.cv_error_px is not None else None}
