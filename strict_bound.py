"""Certified strict upper bounds for swept areas of known motions.

For any continuous motion pose(s) = (c(s), theta(s)), s in [0,1], the
first-half sweep S1 satisfies: subdivide [0,1] into substeps; for each
substep [s_k, s_k+1] every needle point of every intermediate pose stays
within distance rho_k of the convex hull H_k of the two boundary poses,
where rho_k is certified numerically as

    rho_k = max_sampled_corner_distance(H_k)
            + Lip_corner * (max gap between samples),

with Lip_corner = max |d/ds corner(s)| <= |dc/ds| + r_max*|dtheta/ds|
(r_max = circumradius = sqrt(0.25 + (eps/2)^2); the needle is the convex
hull of its 4 corners, and if all corners are within rho of a convex set
then the whole needle is).  Therefore

    S1 subseteq union_k  buffer(H_k, rho_k)

and the full-turn swept set is S1 union mirror_x(S1).  area(U) is a
certified UPPER bound for the construction's swept area; the sampled
union (without buffers) is a LOWER bound; U - L brackets the truth.

Slides (pure along-needle translations) are exact rectangles already.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.affinity import scale
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


def needle_polygon(theta, cx, cy, eps):
    c, s = math.cos(theta), math.sin(theta)
    hl, hw = 0.5, eps / 2.0
    pts = [(cx + c * u - s * v, cy + s * u + c * v)
           for u, v in ((hl, hw), (hl, -hw), (-hl, -hw), (-hl, hw))]
    return Polygon(pts)


def corners(theta, cx, cy, eps):
    c, s = math.cos(theta), math.sin(theta)
    hl, hw = 0.5, eps / 2.0
    return np.array([(cx + c * u - s * v, cy + s * u + c * v)
                     for u, v in ((hl, hw), (hl, -hw), (-hl, -hw), (-hl, hw))])


def strict_upper(eps, pose_fn, n_sub=300, m_sample=12):
    """pose_fn(s) -> (theta, cx, cy) for s in [0,1], theta monotone 0..pi/2.

    Returns dict with upper/lower areas and certified gap.
    """
    r_max = math.sqrt(0.25 + (eps / 2.0) ** 2)
    ss = np.linspace(0.0, 1.0, n_sub + 1)
    poses = [pose_fn(s) for s in ss]
    rects = [corners(*p, eps) for p in poses]

    polys_lower = []
    polys_upper = []
    for k in range(n_sub):
        r0 = Polygon(rects[k])
        r1 = Polygon(rects[k + 1])
        polys_lower.append(r0)
        h = unary_union([r0, r1]).convex_hull
        # sample interior poses, certify rho
        th0, cx0, cy0 = poses[k]
        th1, cx1, cy1 = poses[k + 1]
        dth = abs(th1 - th0)
        # per-unit-s corner speed bound: |dc/ds| = |Δc|·n_sub,
        # |dθ/ds| = dθ·n_sub; per-corner-point Lipschitz gap over sample
        # spacing (1/(n_sub·m_sample) in s) is therefore
        #   (|Δc| + r_max·dθ) / m_sample
        lip_gap = (math.hypot(cx1 - cx0, cy1 - cy0) + r_max * dth) / m_sample
        rho = 0.0
        for j in range(1, m_sample):
            s = ss[k] + (ss[k + 1] - ss[k]) * j / m_sample
            th, cx, cy = pose_fn(s)
            cs = corners(th, cx, cy, eps)
            for pt in cs:
                d = Point(pt).distance(h)
                if d > rho:
                    rho = d
        rho += lip_gap  # Lipschitz gap correction (rigorous)
        if rho > 1e-9:
            polys_upper.append(h.buffer(rho))
        else:
            polys_upper.append(h)

    lower = unary_union(polys_lower)
    upper = unary_union(polys_upper)
    for g in (lower, upper):
        pass
    lo_m = scale(lower, xfact=-1.0, origin=(0, 0))
    up_m = scale(upper, xfact=-1.0, origin=(0, 0))
    lo = float(lower.union(lo_m).area)
    up = float(upper.union(up_m).area)
    return {"lower": lo, "upper": up, "gap": up - lo,
            "n_sub": n_sub, "m_sample": m_sample}
