"""Numerical area enclosures for continuous pivot-slide motions.

For each arc subinterval, the endpoint rectangle hull is enlarged by the
maximum corner arc sagitta. Slides are represented by their entire swept
strip. The mirrored half joins at x=0. Shapely uses floating-point polygon
operations (including polygonal buffers): these are NOT rigorous mathematical
certificates, and neither the reported lower nor upper has outward rounding.
"""
from __future__ import annotations

import math

import numpy as np
from shapely import set_precision, union
from shapely.affinity import scale
from shapely.ops import unary_union

from pivot_slide import PivotSlideModel, needle_polygon, slide_strip


def strict_upper(*args, **kwargs):
    """Reject legacy generic poses: endpoint displacements do not bound speed."""
    raise NotImplementedError(
        "Generic pose enclosures are unsupported; use numerical_pivot_enclosure "
        "with a PivotSlideModel instead. Floating-point areas are not certificates."
    )


def numerical_pivot_enclosure(model: PivotSlideModel, params: np.ndarray,
                              n_sub: int = 300) -> dict:
    """Sampled lower and conservative numerical upper for a pivot-slide path.

    Every pivot arc is divided into n_sub angle steps. For a corner at radius
    r from its pivot, the circular arc stays within r*(1-cos(delta/2)) of
    the chord between its endpoint positions (delta <= pi/2). Since the
    needle is the convex hull of its corners, buffering the endpoint needle
    hull by the largest corner sagitta covers all intermediate poses in
    exact arithmetic. Shapely's finite polygonal buffer is expanded by its
    chord inradius factor, but floating-point operations are not certified.
    """
    if not isinstance(model, PivotSlideModel):
        raise TypeError("model must be a PivotSlideModel")
    if isinstance(n_sub, bool) or not isinstance(n_sub, int) or n_sub < 1:
        raise ValueError("n_sub must be a positive integer")
    params = np.asarray(params, dtype=float)
    if not np.all(np.isfinite(params)):
        raise ValueError("params must be finite")
    pivots, centers, fractions, beta = model.centers_and_pivots(params)
    if not all(np.all(np.isfinite(a)) for a in (pivots, centers, fractions, beta)):
        raise ValueError("decoded motion must be finite")

    lower_polys = []
    upper_polys = []
    # A round Shapely buffer uses 4*quad_segs chords per circle; growing
    # the radius by sec(pi/(4*quad_segs)) covers each circular chord gap.
    quad_segs = 16
    buffer_factor = 1.0 / math.cos(math.pi / (4 * quad_segs))
    for i in range(model.K):
        theta0, theta1 = model.theta[i:i + 2]
        if theta1 <= theta0 or theta1 - theta0 > math.pi / 2:
            raise ValueError("unsupported pivot arc angle interval")
        r_corner = math.hypot((1 + abs(fractions[i])) / 2, model.eps / 2)
        last_rect = None
        last_center = None
        for j, theta in enumerate(np.linspace(theta0, theta1, n_sub + 1)):
            direction = np.array([math.cos(theta), math.sin(theta)])
            center = pivots[i] - 0.5 * fractions[i] * direction
            if j == 0 and not np.allclose(center, centers[i], rtol=1e-12, atol=1e-12):
                raise ValueError(f"discontinuous arc start at boundary {i}")
            rect = needle_polygon(theta, center[0], center[1], model.eps)
            lower_polys.append(rect)
            if last_rect is not None:
                hull = unary_union([last_rect, rect]).convex_hull
                delta = theta - last_theta
                sagitta = r_corner * (1 - math.cos(delta / 2))
                upper_polys.append(hull.buffer(sagitta * buffer_factor,
                                               quad_segs=quad_segs))
            last_rect, last_center, last_theta = rect, center, theta

        if i < model.K - 1:
            slide_end = last_center + beta[i] * model.u[i + 1]
            if not np.allclose(slide_end, centers[i + 1], rtol=1e-12, atol=1e-12):
                raise ValueError(f"discontinuous slide at boundary {i + 1}")
            # Pure axial translation sweeps a complete strip, including both
            # endpoints. The next arc must start at its end.
            strip = slide_strip(theta1, last_center, slide_end, model.eps)
            lower_polys.append(strip)
            upper_polys.append(strip)
        elif not np.allclose(last_center, centers[-1], rtol=1e-12, atol=1e-12):
            raise ValueError("discontinuous final arc")

    if not math.isclose(centers[-1, 0], 0.0, abs_tol=1e-10):
        raise ValueError("final pose does not join its x-mirror")
    # Same fixed-grid overlay as the optimizer; the grid perturbation is
    # numerical, not a certified inward/outward rounding direction.
    grid = min(1e-10, model.eps * 1e-8)
    lower = unary_union([set_precision(poly, grid) for poly in lower_polys])
    upper = unary_union([set_precision(poly, grid) for poly in upper_polys])
    lo_mirror = set_precision(scale(lower, xfact=-1, origin=(0, 0)), grid)
    up_mirror = set_precision(scale(upper, xfact=-1, origin=(0, 0)), grid)
    lo = float(union(lower, lo_mirror, grid_size=grid).area)
    up = float(union(upper, up_mirror, grid_size=grid).area)
    return {"lower": lo, "upper": up, "gap": up - lo, "n_sub": n_sub}
