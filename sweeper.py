"""Parametrized motion of a 1 x eps rectangle; swept-area objective.

Model
-----
* Needle: 1 x eps rectangle (eps <= 1), pose (theta, cx, cy) with theta
  the angle of the long axis.
* Motion: keyframes (theta_i, x_i, y_i), theta in [0, pi/2]; the second
  half of the 180-degree turn is the mirror image of the first half
  across the vertical axis x = 0.  A mirror maps pose (theta, x, y) to
  (pi - theta, -x, y), so the full motion's swept set is
  S1 UNION mirror_x(S1) where S1 is the swept set of the first half.
  We rasterize S1 and OR it with its x-flip: exact for cell-center
  sampling, and cheap.
* Swept set: union over poses sampled along the (piecewise-linear)
  keyframe interpolation of the cells whose center lies inside the
  needle.  Cell-center sampling converges to true area as grid -> 0.
* Per pose only the needle's bounding box is touched (O(bbox) not
  O(grid)), so an evaluation is a few milliseconds.
"""
from __future__ import annotations

import numpy as np


def _int(x) -> int:
    """Safe int cast: clamps NaN to 0, absorbs cast errors."""
    try:
        if x != x:  # NaN
            return 0
        return int(x)
    except (TypeError, ValueError, OverflowError):
        return 0


class Sweeper:
    def __init__(self, eps: float, n_theta: int = 180, margin: float = 1.6,
                 grid_res: int = 400):
        if eps <= 0 or eps > 1:
            raise ValueError("eps must lie in (0, 1]")
        self.eps: float = eps
        self.n_theta: int = n_theta      # poses per 90 deg of rotation
        self.margin: float = margin
        self.res: int = grid_res
        self.x0 = self.y0 = -margin
        self.x1 = self.y1 = margin
        self.dx = (self.x1 - self.x0) / self.res
        self.cell_area = self.dx * self.dx
        xs = self.x0 + (np.arange(self.res) + 0.5) * self.dx
        # X[i, j] = xs[j], Y[i, j] = xs[i]  (both increase with index)
        self.X = np.tile(xs, (self.res, 1))
        self.Y = np.tile(xs[:, None], (1, self.res))

    def _cover_into(self, covered: np.ndarray, theta: float,
                    cx: float, cy: float) -> None:
        """OR the needle's coverage at one pose into `covered`."""
        c, s = np.cos(theta), np.sin(theta)
        e2 = self.eps / 2.0
        hx = 0.5 * abs(c) + e2 * abs(s)
        hy = 0.5 * abs(s) + e2 * abs(c)
        # grid index window covering the bounding box
        j0 = max(0, _int(np.floor((cx - hx - self.x0) / self.dx)))
        j1 = min(self.res, _int(np.ceil((cx + hx - self.x0) / self.dx)))
        i0 = max(0, _int(np.floor((cy - hy - self.y0) / self.dx)))
        i1 = min(self.res, _int(np.ceil((cy + hy - self.y0) / self.dx)))
        if j0 >= j1 or i0 >= i1:
            return  # needle outside the raster window: caller must ensure not
        Xb = self.X[i0:i1, j0:j1] - cx
        Yb = self.Y[i0:i1, j0:j1] - cy
        u = c * Xb + s * Yb           # along the needle
        v = -s * Xb + c * Yb          # across the needle
        covered[i0:i1, j0:j1] |= (np.abs(u) <= 0.5) & (np.abs(v) <= e2)

    def first_half_cover(self, keyframes) -> np.ndarray:
        """Raster of the first half of the motion (theta in [0, pi/2])."""
        keyframes = np.asarray(keyframes, dtype=float).reshape(-1, 3)
        if keyframes.shape[0] < 2:
            raise ValueError("need at least 2 keyframes")
        thetas = keyframes[:, 0]
        if thetas[0] > 1e-9 or abs(thetas[-1] - np.pi / 2) > 1e-9:
            raise ValueError("keyframes must span theta in [0, pi/2]")
        covered = np.zeros((self.res, self.res), dtype=bool)
        for i in range(len(keyframes) - 1):
            t0, t1 = thetas[i], thetas[i + 1]
            if not t1 > t0:
                continue  # duplicate keyframe: nothing to sweep
            x0, x1 = keyframes[i, 1], keyframes[i + 1, 1]
            y0, y1 = keyframes[i, 2], keyframes[i + 1, 2]
            n_sub = 2 + _int(self.n_theta * (t1 - t0) * 2 // 3)
            for t in np.linspace(t0, t1, n_sub, endpoint=False):
                frac = (t - t0) / (t1 - t0)
                self._cover_into(covered, t,
                                 x0 + (x1 - x0) * frac,
                                 y0 + (y1 - y0) * frac)
        # final pose (theta = pi/2) itself; shared with the mirrored half
        self._cover_into(covered, keyframes[-1, 0],
                         keyframes[-1, 1], keyframes[-1, 2])
        return covered

    def swept_area(self, keyframes) -> float:
        """Area of the full 180-degree motion's swept set (with mirror)."""
        cov = self.first_half_cover(keyframes)
        full = cov | cov[:, ::-1]      # union with the x-mirror
        return _int(full.sum()) * self.cell_area

    def swept_mask(self, keyframes) -> np.ndarray:
        cov = self.first_half_cover(keyframes)
        return cov | cov[:, ::-1]


def make_sweeper(eps: float, grid_res: int = 400, n_theta: int = 180,
                 margin: float = 1.6) -> Sweeper:
    return Sweeper(eps, n_theta=n_theta, grid_res=grid_res, margin=margin)
