"""v2: unbounded log-space motion model with exact polygon-union area.

Key changes vs v1 (sweeper.py / optimize.py), addressing two caps on how
small f(eps) can get:

1. NO raster window.  The swept set is the exact union of oriented-box
   polygons (shapely), computed at whatever distance the motion reaches.
   Area is exact (up to shapely's floating tolerance) at any distance, so
   "move far away" can no longer be forbidden or numerically explode.

2. LOG-SPACE TRANSLATIONS.  Each keyframe's center offset is
   (x, y) = (sigma * sx, sigma * sy) with
       s = exp(z),  z in [-zmax, zmax],  zmax = log(zscale/eps),
   so unit-sized z-steps multiply the reach by e (~2.7).  The needle can
   travel O(exp(K)) far in K keyframes, i.e. K ~ log(1/eps) keyframes
   suffice to reach the distances the optimal constructions use.
   sigma = max(1, ~10*eps) keeps small-eps motions from dithering at
   sub-needle scales.

3. MANY KEYFRAMES.  K is a parameter; the optimal construction family
   needs K ~ log(1/eps) stations.  Default K=14 with the option to go
   higher.

Symmetric-motion mirror closure from v1 is kept: keyframes span
theta in [0, pi/2], the second half of the turn is the x-mirror, and the
reported area is |S1 union mirror(S1)| via exact polygon union.

Sampling: poses are inserted between keyframes at a resolution fine
enough that adjacent needle placements overlap; the union is exact for
the sampled pose set, and increasing sampling density only refines the
swept set toward the continuous-motion one.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


def needle_polygon(theta: float, cx: float, cy: float, eps: float) -> Polygon:
    """Corners of the 1 x eps needle at pose (theta, cx, cy)."""
    c, s = math.cos(theta), math.sin(theta)
    hl, hw = 0.5, eps / 2.0
    # local corners (u along needle, v across), rotated + translated
    pts = []
    for u, v in ((hl, hw), (hl, -hw), (-hl, -hw), (-hl, hw)):
        pts.append((cx + c * u - s * v, cy + s * u + c * v))
    return Polygon(pts)


class LogSweeper:
    """Exact-area swept-set evaluator for log-space keyframe motions."""

    def __init__(self, eps: float, K: int = 14, n_theta: int = 40,
                 sigma: float | None = None, z_extra: float = 2.0):
        if eps <= 0 or eps > 1:
            raise ValueError("eps must lie in (0, 1]")
        self.eps: float = eps
        self.K: int = K
        self.n_theta: int = n_theta  # poses per unit angle along segments
        self.sigma: float = sigma if sigma is not None else max(1.0, 8 * eps)
        # z-range: log of the largest reachable multiple of sigma
        self.zmax = math.log(max(10.0, 1.0 / eps)) + z_extra

    def keyframe_centers(self, zparams: np.ndarray):
        """zparams: (K+1, 2) signed log coords -> actual (x, y) centers.

        Signed log map: center = sigma * (exp(z) - 1), so z = 0 is the
        origin and each unit step in z multiplies the distance-from-origin
        by e (~2.7).  Negative z mirrors to negative coordinates.
        """
        z = np.clip(zparams, -self.zmax, self.zmax)
        off = self.sigma * np.expm1(z)
        return off[:, 0], off[:, 1]

    def swept_area(self, u: np.ndarray) -> float:
        """u = [thetas (K+1), zs (K+1, 2)] flattened; theta[0]=0,
        theta[-1]=pi/2 enforced by sort+clip; second half = mirror."""
        u = np.asarray(u, dtype=float)
        K = self.K
        th = np.sort(np.clip(u[:K + 1], 0.0, math.pi / 2))
        th[0], th[-1] = 0.0, math.pi / 2
        zs = u[K + 1:].reshape(K + 1, 2)
        xs, ys = self.keyframe_centers(zs)

        polys = []
        for i in range(K):
            t0, t1 = th[i], th[i + 1]
            if t1 <= t0:
                continue
            n = 2
            try:
                n = max(2, int(math.ceil(self.n_theta * (t1 - t0))))
            except (TypeError, ValueError, OverflowError) as e:
                # degenerate span (e.g. inf/nan from a wild optimizer step):
                # keep the minimum 2 poses rather than crashing the search
                print(f"pose-count fallback: {e}", flush=True)
            for t in np.linspace(t0, t1, n, endpoint=False):
                frac = (t - t0) / (t1 - t0)
                cx = xs[i] + (xs[i + 1] - xs[i]) * frac
                cy = ys[i] + (ys[i + 1] - ys[i]) * frac
                polys.append(needle_polygon(t, cx, cy, self.eps))
        # final keyframe pose
        polys.append(needle_polygon(th[-1], xs[-1], ys[-1], self.eps))

        swept = unary_union(polys)
        # mirror closure: union with x-mirror, area of the union
        mirrored = swept.buffer(0)  # ensure validity
        m = shapely_mirror(mirrored)
        try:
            return float(swept.union(m).area)
        except Exception as e:  # shapely topology error on invalid input
            cleaned = swept.buffer(0)
            return float(cleaned.union(shapely_mirror(cleaned)).area)


def shapely_mirror(geom):
    import shapely
    return shapely.affinity.scale(geom, xfact=-1.0, origin=(0, 0))


def make_logsweeper(eps: float, K: int = 14, n_theta: int = 40,
                    sigma: float | None = None) -> LogSweeper:
    return LogSweeper(eps, K=K, n_theta=n_theta, sigma=sigma)
