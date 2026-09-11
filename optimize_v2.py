"""v2 optimizer: DE + Nelder-Mead over log-space keyframe motions.

Usage: python3 optimize_v2.py --eps 0.05 --K 12 --out results/v2_005.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import differential_evolution, minimize

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from sweeper_v2 import make_logsweeper  # noqa: E402


class ObjectiveV2Uniform:
    """Uniform-theta variant: only log-space coords are optimized."""

    def __init__(self, sw, K: int, zmax: float):
        self.sw = sw
        self.K = K
        self.zmax = zmax
        self.th = np.linspace(0.0, np.pi / 2, K + 1)

    def __call__(self, x) -> float:
        x = np.asarray(x, dtype=float)
        if not np.all(np.isfinite(x)) or np.max(np.abs(x)) > self.zmax:
            return 1e6
        return self.sw.swept_area(np.concatenate([self.th, x]))


class ObjectiveV2:
    """Picklable objective: u -> swept area (with mirror closure)."""

    def __init__(self, sw, zmax: float):
        self.sw = sw
        self.zmax = zmax

    def __call__(self, u) -> float:
        u = np.asarray(u, dtype=float)
        if not np.all(np.isfinite(u)):
            return 1e6
        return self.sw.swept_area(u)


def grow_keyframes(u: np.ndarray, K_from: int, K_to: int) -> np.ndarray:
    """Interpolate a uniform-variant solution (zs only, length 2*(K+1))
    from K_from to K_to keyframes by inserting midpoints."""
    zs = np.asarray(u, dtype=float).reshape(K_from + 1, 2)
    t_old = np.linspace(0.0, np.pi / 2, K_from + 1)
    t_new = np.linspace(0.0, np.pi / 2, K_to + 1)
    new_zs = np.column_stack([
        np.interp(t_new, t_old, zs[:, 0]),
        np.interp(t_new, t_old, zs[:, 1]),
    ])
    return new_zs.ravel()


def optimize_growing(eps: float, K_start: int, K_end: int, seed: int,
                     popsize: int, maxiter: int, n_theta: int,
                     verbose: bool = False, workers: int = -1):
    """Optimize at K_start, then grow K by 2 at a time, warm-starting
    each stage from the interpolated previous solution."""
    best_u = None
    try:
        best_f = float("inf")
    except (TypeError, ValueError):  # pragma: no cover
        best_f = 1e9
    K_last = K_start
    for K in range(K_start, K_end + 1, 2):
        sw = make_logsweeper(eps, K=K, n_theta=n_theta)
        ndim = 2 * (K + 1)
        lb = np.full(ndim, -sw.zmax)
        ub = np.full(ndim, sw.zmax)
        obj = ObjectiveV2Uniform(sw, K, sw.zmax)
        x0 = None if best_u is None else grow_keyframes(best_u, K - 2, K)
        rng = np.random.default_rng(seed * 100 + K)
        res = differential_evolution(
            obj, bounds=list(zip(lb, ub)), rng=rng, popsize=popsize,
            maxiter=maxiter, tol=1e-8, polish=False, workers=workers,
            updating="deferred", mutation=(0.4, 1.0), recombination=0.9,
            x0=x0,
        )
        pol = minimize(obj, res.x, method="Nelder-Mead",
                       options={"maxiter": 6000, "xatol": 1e-4,
                                "fatol": 1e-8})
        try:
            f_de = float(res.fun)
            f_nm = float(pol.fun)
        except (TypeError, AttributeError) as e:
            raise RuntimeError(f"optimizer returned malformed result: {e}") from e
        best_f = min(f_de, f_nm)
        best_u = pol.x if f_nm <= f_de else res.x
        K_last = K
        if verbose:
            print(f"  eps={eps:.4g} K={K}: area={best_f:.5f}", flush=True)
    if best_u is None:
        raise RuntimeError("no stage produced a usable solution")
    return best_f, best_u, K_last


def optimize_v2(eps: float, K: int, seed: int, popsize: int, maxiter: int,
                n_theta: int, verbose: bool = False, uniform_theta: bool = True):
    sw = make_logsweeper(eps, K=K, n_theta=n_theta)
    if uniform_theta:
        # thetas fixed on a uniform grid; optimize only the 2*(K+1) zs
        ndim = 2 * (K + 1)
        lb = np.full(ndim, -sw.zmax)
        ub = np.full(ndim, sw.zmax)
        obj = ObjectiveV2Uniform(sw, K, sw.zmax)
    else:
        ndim = 3 * (K + 1)
        lb = np.full(ndim, -sw.zmax)
        ub = np.full(ndim, sw.zmax)
        lb[:K + 1] = 0.0
        ub[:K + 1] = np.pi / 2
        obj = ObjectiveV2(sw, sw.zmax)

    rng = np.random.default_rng(seed)
    t0 = time.time()
    result = differential_evolution(
        obj, bounds=list(zip(lb, ub)), rng=rng, popsize=popsize,
        maxiter=maxiter, tol=1e-8, polish=False, workers=-1,
        updating="deferred", mutation=(0.4, 1.0), recombination=0.9,
    )
    pol = minimize(obj, result.x, method="Nelder-Mead",
                   options={"maxiter": 6000, "xatol": 1e-4, "fatol": 1e-8})
    try:
        f_de = float(result.fun)
        f_nm = float(pol.fun)
    except (TypeError, AttributeError) as e:
        raise RuntimeError(f"optimizer returned malformed result: {e}") from e
    f = min(f_de, f_nm)
    best = pol.x if f_nm <= f_de else result.x
    if verbose:
        print(f"eps={eps:.4g} K={K} seed={seed}: area={f:.5f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return f, best, sw


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eps", type=float, required=True)
    p.add_argument("--K", type=int, default=12)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--popsize", type=int, default=24)
    p.add_argument("--maxiter", type=int, default=300)
    p.add_argument("--n_theta", type=int, default=40)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--K_start", type=int, default=4)
    p.add_argument("--K_end", type=int, default=12)
    p.add_argument("--workers", type=int, default=-1)
    a = p.parse_args()

    results = []
    for seed in range(a.seeds):
        try:
            f, u, K = optimize_growing(a.eps, a.K_start, a.K_end, seed,
                                       a.popsize, a.maxiter, a.n_theta,
                                       verbose=True, workers=a.workers)
        except (ValueError, RuntimeError) as e:
            print(f"seed {seed} failed: {e}", file=sys.stderr)
            continue
        K_last = K
        th = np.linspace(0.0, np.pi / 2, K_last + 1)
        zs = np.asarray(u, dtype=float).reshape(K_last + 1, 2)
        results.append({
            "eps": a.eps, "K": K_last, "seed": seed, "area": f,
            "model": "v2-logspace-growing",
            "keyframes": np.column_stack([th, zs]).tolist(),
        })
    if not results:
        return 1
    best = min(results, key=lambda r: r["area"])
    print("BEST:", json.dumps({k: best[k] for k in ("eps", "K", "area")}))
    try:
        with open(a.out, "w") as fh:
            json.dump(results, fh)
    except OSError as e:
        print(f"write failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
