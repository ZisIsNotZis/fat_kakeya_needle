"""Physically valid pivot+slide motion model.

The first half-turn is split into K uniform angle segments theta=0..pi/2.
Segment i rotates the 1 x eps rectangle about a fixed point on the needle:

    pivot P_i = center + 0.5*f_i*u(theta),  f_i in [-1,1].

At the boundary theta_i, the needle slides along its own axis by beta_i
before the next segment starts.  This is a valid continuous motion: the
end center of segment i is c_end = P_i - .5*f_i*u(theta_{i+1}); the next
center is c_next = c_end + beta_i*u(theta_{i+1}).

The last first-half pose is constrained to lie on the mirror axis x=0,
so the mirrored second half joins continuously.  P_0.x is solved
analytically from the other parameters to enforce this constraint.

Parameters are [P0_y, f_0..f_{K-1}, beta_0..beta_{K-2}].  The swept area
is the union of actual rectangle polygons sampled along every pivot arc
and every slide, then unioned with its x-mirror.  It is an approximation
to the continuous sweep whose error decreases with n_arc; unlike the
previous sector implementation it does not replace a rectangle sweep by
an outer circular-sector bound.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.affinity import scale
from shapely.geometry import Polygon
from shapely.ops import unary_union


def needle_polygon(theta: float, cx: float, cy: float, eps: float) -> Polygon:
    c, s = math.cos(theta), math.sin(theta)
    hl, hw = 0.5, eps / 2.0
    pts = [(cx + c * u - s * v, cy + s * u + c * v)
           for u, v in ((hl, hw), (hl, -hw), (-hl, -hw), (-hl, hw))]
    return Polygon(pts)


def slide_strip(theta: float, c0: np.ndarray, c1: np.ndarray,
                eps: float) -> Polygon:
    """Exact union of a rectangle translated along its own axis."""
    delta = c1 - c0
    length = float(np.linalg.norm(delta))
    mid = (c0 + c1) / 2.0
    c, s = math.cos(theta), math.sin(theta)
    half = (1.0 + length) / 2.0
    hw = eps / 2.0
    pts = [(mid[0] + c * u - s * v, mid[1] + s * u + c * v)
           for u, v in ((half, hw), (half, -hw), (-half, -hw), (-half, hw))]
    return Polygon(pts)


class PivotSlideModel:
    def __init__(self, eps: float, K: int = 8, n_arc: int = 30):
        if eps <= 0 or eps > 1:
            raise ValueError("eps must lie in (0, 1]")
        if K < 1:
            raise ValueError("K must be positive")
        self.eps = float(eps)
        self.K = int(K)
        self.n_arc = int(n_arc)
        self.theta = np.linspace(0.0, math.pi / 2, self.K + 1)
        self.u = np.column_stack([np.cos(self.theta), np.sin(self.theta)])

    def centers_and_pivots(self, params: np.ndarray):
        """Decode params and solve P0.x from the continuous mirror join."""
        x = np.asarray(params, dtype=float)
        K = self.K
        if x.size != 1 + K + max(0, K - 1):
            raise ValueError("wrong pivot-slide parameter count")
        y0 = x[0]
        f = np.clip(x[1:1 + K], -1.0, 1.0)
        beta = x[1 + K:]

        # P_i = P_0 + sum_j gamma_j*u(theta_{j+1}), where
        # gamma_j = beta_j + .5*(f_{j+1}-f_j).
        gamma = beta + 0.5 * (f[1:] - f[:-1])
        end_without_x0 = np.sum(gamma[:, None] * self.u[1:K], axis=0)
        end_without_x0[1] += y0
        # c_end = P0 + sum gamma*u - .5*f_last*u_K; enforce c_end.x=0.
        p0x = 0.5 * f[-1] * self.u[K, 0] - end_without_x0[0]
        P = np.empty((K, 2))
        P[0] = (p0x, y0)
        for i in range(K - 1):
            P[i + 1] = P[i] + gamma[i] * self.u[i + 1]

        centers = np.empty((K + 1, 2))
        centers[0] = P[0] - 0.5 * f[0] * self.u[0]
        for i in range(K):
            centers[i + 1] = P[i] - 0.5 * f[i] * self.u[i + 1]
            if i < K - 1:
                centers[i + 1] += beta[i] * self.u[i + 1]
        return P, centers, f, beta

    def swept_area(self, params: np.ndarray) -> float:
        P, centers, f, beta = self.centers_and_pivots(params)
        polys = []
        for i in range(self.K):
            t0, t1 = self.theta[i], self.theta[i + 1]
            n = max(3, int(math.ceil(self.n_arc)))
            for t in np.linspace(t0, t1, n, endpoint=False):
                u = np.array([math.cos(t), math.sin(t)])
                c = P[i] - 0.5 * f[i] * u
                polys.append(needle_polygon(t, c[0], c[1], self.eps))
            # Add the boundary pose once; it is also the start of the slide.
            c_end = P[i] - 0.5 * f[i] * self.u[i + 1]
            polys.append(needle_polygon(t1, c_end[0], c_end[1], self.eps))
            if i < self.K - 1 and abs(beta[i]) > 1e-12:
                # Exact continuous slide, not just endpoint samples.
                c_next = c_end + beta[i] * self.u[i + 1]
                polys.append(slide_strip(t1, c_end, c_next, self.eps))

        swept = unary_union(polys)
        mirrored = scale(swept, xfact=-1.0, origin=(0, 0))
        return float(swept.union(mirrored).area)
