"""Perron/Pal-join style structured seeds for the uniform-theta keyframe model.

Construction: split [0, pi/2] into K segments (uniform theta grid).  Each
segment i pivots the needle about a fixed point q_i located at needle
fraction t_i in [-1, 1] from the center (t=-1 tail endpoint, +1 head,
0 center).  Continuity of the needle pose between segments fixes

    c(theta_i)   = q_{i-1} - 0.5 * t_{i-1} * u(theta_i)   (end of seg i-1)
                 = q_i     - 0.5 * t_i     * u(theta_i)   (start of seg i)

so choosing q_0 and the pattern t_0..t_{K-1} determines every keyframe
center; consecutive pivots connect by an along-needle slide (the cheap
move Besicovitch's construction exploits).

Patterns: 'alternating' (Pal join), 'ramp', 'center' (reference disk),
'random'.  Centers are converted to the signed-log z-parametrization of
sweeper_v2.LogSweeper (c = sigma*(exp(z)-1)).
"""
from __future__ import annotations

import math

import numpy as np


def _inv_log(c: np.ndarray, sigma: float) -> np.ndarray:
    """Signed log map inverse: c -> z with c = sigma*(e^z - 1)."""
    r = c / sigma + 1.0
    # clamp: r <= 0 means the center is at/beyond -sigma (unreachable);
    # clamp to a tiny positive value (near-sigma negative center)
    eps_r = 1e-6
    r = np.clip(r, eps_r, None)
    return np.log(r)


def pal_seed(K: int, eps: float, pattern: str = "alternating",
             sigma: float | None = None, rng: np.random.Generator | None = None,
             q0: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    """Return z-vector of shape (2*(K+1),) for optimize_v2's uniform model."""
    if rng is None:
        rng = np.random.default_rng(0)
    sig = sigma if sigma is not None else max(1.0, 8 * eps)

    if pattern == "alternating":
        t = np.array([(-1.0) ** i for i in range(K)])
    elif pattern == "ramp":
        t = np.linspace(-1.0, 1.0, K)
    elif pattern == "center":
        t = np.zeros(K)
    elif pattern == "random":
        t = rng.uniform(-1.0, 1.0, K)
    else:
        raise ValueError(f"unknown pattern {pattern}")

    th = np.linspace(0.0, math.pi / 2, K + 1)
    u = np.column_stack([np.cos(th), np.sin(th)])

    # Exact mirror closure: the pose at theta=pi/2 must be the mirror of
    # the pose at theta=0.  Pose P(theta) = center + 0.5*t_seg*u(theta)
    # spans the needle.  Build the first half freely (pivot chain on the
    # chosen pattern), then FORCE the endpoint: shift the whole chain so
    # that c[K] equals the mirror of c[0].  With c[0]=q0-0.5*t0*u0 fixed
    # by the first pivot, mirror closure requires c[K] = (-c[0].x, c[0].y).
    # We translate all centers uniformly by delta = (-c0x, c0y) - c[K],
    # which preserves the geometry of every segment (slides stay
    # along-needle only if delta is along-needle, but a small uniform
    # shift only adds bounded translation cost and keeps the structure).
    c = np.zeros((K + 1, 2))
    q = np.asarray(q0, dtype=float)
    for i in range(K):
        c_start = q - 0.5 * t[i] * u[i]
        c_end = q - 0.5 * t[i] * u[i + 1]
        if i == 0:
            c[0] = c_start
        c[i + 1] = c_end
        if i + 1 < K:
            q = c_end + 0.5 * t[i + 1] * u[i + 1]
    # Mirror-fold: the evaluator folds x -> -x, so the chain must satisfy
    # c[K] = mirror(c[0]) and, for the mirror to overlap the first half,
    # the chain should straddle x = 0.  Recenter the chain midpoint on
    # x = 0, then distribute the endpoint mismatch linearly along the
    # chain (small bend; preserves the alternating-pivot structure).
    mid = 0.5 * (c[0, 0] + (-c[K, 0]))
    c[:, 0] -= mid
    mis = np.array([-c[K, 0] - c[0, 0], 0.0])
    for i in range(K + 1):
        c[i] += mis * (1.0 - i / K)

    # convert to z-space; keyframe centers may repeat q-pivots (slides)
    z = _inv_log(c, sig)
    return z.ravel()


def seed_population(K: int, eps: float, patterns: list[str],
                    popsize: int, n_theta: int = 40,
                    rng: np.random.Generator | None = None,
                    perturb: float = 0.35) -> tuple[np.ndarray, list[float]]:
    """Build a DE init matrix (popsize*ndim, ndim): structured seeds,
    perturbed copies, and random rows to fill.

    Returns (init_matrix, seed_areas) with seed areas evaluated for
    reporting.  Rows are clipped to the z-bounds used by the sweeper.
    """
    from sweeper_v2 import make_logsweeper, LogSweeper

    if rng is None:
        rng = np.random.default_rng(0)
    sw: LogSweeper = make_logsweeper(eps, K=K, n_theta=n_theta)
    ndim = 2 * (K + 1)
    total = popsize * ndim

    rows: list[np.ndarray] = []
    areas: list[float] = []
    base_seeds = []
    for pat in patterns:
        z = pal_seed(K, eps, pat, sigma=sw.sigma, rng=rng)
        z = np.clip(z, -sw.zmax, sw.zmax)
        base_seeds.append(z)
        a = sw.swept_area(z)
        areas.append(a)

    while len(rows) < total:
        for z in base_seeds:
            if len(rows) >= total:
                break
            rows.append(np.clip(z + rng.normal(0, perturb, ndim),
                                -sw.zmax, sw.zmax))
        if len(rows) < total:
            rows.append(np.clip(rng.normal(0, 1.0, ndim),
                                -sw.zmax, sw.zmax))
    return np.array(rows[:total]), areas
