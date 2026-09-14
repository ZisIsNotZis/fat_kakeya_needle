"""Hierarchical (self-similar) slide parameterization for the fat Kakeya
pivot+slide motion model.

Motivation
----------
Perron-tree constructions are self-similar: split into halves, then
halves of halves...  Instead of K-1 independent slide magnitudes
(beta_j), the slide hierarchy is generated from m = log2(K) scale
parameters s_1..s_m via the dyadic ruler sequence:

    r(j) = 1 + v2(j)            # 2-adic level of keyframe j (1..m)
    k(j) = j >> r(j)            # block index at level r
    sign(j) = (-1) ** k(j)      # alternates along each level's blocks
    beta_{j-1} = sign(j) * s_{r(j)-1},   j = 1..K-1

Parameter vector: [y0, s_1..s_m] (dimension m+1 = log2(K)+1), plus an
optional alternating pivot-fraction f0 ([y0, f0, s_1..s_m], f_i = f0*(-1)^i).

Area evaluation reuses pivot_slide.PivotSlideModel exactly; this module
only does the parameter mapping (so areas are fully comparable).
"""
from __future__ import annotations

import math

import numpy as np

from pivot_slide import PivotSlideModel


def v2(j: int) -> int:
    """2-adic valuation of positive integer j."""
    k = 0
    while j % 2 == 0:
        k += 1
        j //= 2
    return k


def ruler_betas(s: np.ndarray, sign_mode: str = "alternating") -> np.ndarray:
    """Generate K-1 slides from m scale parameters, K = 2**m."""
    m = len(s)
    K = 1 << m
    betas = np.zeros(K - 1)
    for j in range(1, K):
        r = 1 + v2(j)               # level in 1..m
        if sign_mode == "alternating":
            k = j >> r              # block index at level r
            sign = 1.0 if k % 2 == 0 else -1.0
        elif sign_mode == "constant":
            sign = 1.0
        else:
            raise ValueError(f"unknown sign_mode {sign_mode}")
        betas[j - 1] = sign * s[r - 1]
    return betas


class HierModel:
    def __init__(self, K: int, eps: float, sign_mode: str = "alternating",
                 use_f0: bool = False, n_arc: int = 30):
        if K < 1 or (K & (K - 1)) != 0:
            raise ValueError("K must be a power of 2")
        self.K = int(K)
        self.m = int(math.log2(K))
        self.sign_mode = sign_mode
        self.use_f0 = bool(use_f0)
        self.base = PivotSlideModel(eps, K=K, n_arc=n_arc)

    @property
    def ndim(self) -> int:
        return 1 + self.m + (1 if self.use_f0 else 0)

    def to_full_params(self, x: np.ndarray) -> np.ndarray:
        """[y0, (f0), s_1..s_m] -> pivot_slide params [y0, f(K), beta(K-1)]."""
        x = np.asarray(x, dtype=float)
        y0 = x[0]
        if self.use_f0:
            f0 = float(np.clip(x[1], -0.5, 0.5))
            s = x[2:2 + self.m]
            f = f0 * np.array([(-1.0) ** i for i in range(self.K)])
        else:
            s = x[1:1 + self.m]
            f = np.zeros(self.K)
        betas = ruler_betas(s, self.sign_mode)
        return np.concatenate([[y0], f, betas])

    def swept_area(self, x: np.ndarray) -> float:
        return self.base.swept_area(self.to_full_params(x))

    def decode(self, x: np.ndarray):
        """Return (P, centers, f, beta) from low-dim parameters."""
        return self.base.centers_and_pivots(self.to_full_params(x))
