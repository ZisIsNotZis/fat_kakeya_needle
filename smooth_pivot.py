"""Smooth-profile parameterization of the pivot+slide motion.

Evidence from free-parameter optimization (results/pivot_005_K*_night.json):
the optimal pivot-fraction f(theta) is a SMOOTH single-valued profile and
the slides beta(theta) are small smooth corrections.  This is the right
family: a few spline control points express the motion at any angle
resolution K, giving a low-dimensional search space that scales to large K.

Model: f(theta) and beta(theta) are piecewise-linear functions through a
small number of control points over theta in [0, pi/2].  They are decoded
to the pivot_slide.PivotSlideModel parameter format and evaluated exactly
by that evaluator (fully comparable with free-beta results).

Parameter layout: [y0, f_0..f_{Nf-1}, b_0..b_{Nb-1}]
  f control points at theta = j*pi/2/(Nf-1), values in [-1, 1]
  b control points at theta = j*pi/2/(Nb-1), values in [-spread, spread]
"""
from __future__ import annotations

import math

import numpy as np

from pivot_slide import PivotSlideModel


class SmoothProfileModel:
    def __init__(self, K: int, eps: float, Nf: int = 6, Nb: int = 6,
                 n_arc: int = 30):
        if K < 1:
            raise ValueError("K must be positive")
        if Nf < 2 or Nb < 2:
            raise ValueError("need at least 2 control points each")
        self.K = int(K)
        self.Nf = int(Nf)
        self.Nb = int(Nb)
        self.base = PivotSlideModel(eps, K=K, n_arc=n_arc)
        self.theta = self.base.theta          # K+1 keyframe angles
        self.f_grid = np.linspace(0.0, math.pi / 2, self.Nf)
        self.b_grid = np.linspace(0.0, math.pi / 2, self.Nb)

    @property
    def ndim(self) -> int:
        return 1 + self.Nf + self.Nb

    def to_full_params(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        y0 = x[0]
        f_ctrl = np.clip(x[1:1 + self.Nf], -1.0, 1.0)
        b_ctrl = x[1 + self.Nf:1 + self.Nf + self.Nb]
        # f at segment starts theta_0..theta_{K-1}; beta at theta_1..theta_{K-1}
        f = np.interp(self.theta[:self.K], self.f_grid, f_ctrl)
        beta = np.interp(self.theta[1:self.K], self.b_grid, b_ctrl)
        return np.concatenate([[y0], f, beta])

    def swept_area(self, x: np.ndarray) -> float:
        return self.base.swept_area(self.to_full_params(x))

    def decode(self, x: np.ndarray):
        return self.base.centers_and_pivots(self.to_full_params(x))
