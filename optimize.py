"""Optimize keyframe motions of a 1 x eps needle to minimize swept area.

Parametrization (symmetric motions; see sweeper.py):
  * keyframes (theta_i, x_i, y_i), i = 0..K, theta monotone 0 -> pi/2
  * pose at theta = pi/2 is forced to the mirror of the theta = 0 pose:
    x_K = -x_0, y_K = y_0  (the second half of the 180-deg turn is the
    x-mirror of the first half; swept set = S1 | mirror_x(S1))
  * free params: x_0, y_0, and (theta_i, x_i, y_i) for interior i
    -> 2 + 3*(K-1) parameters for K+1 keyframes.

Search: scipy differential_evolution (multimodal landscape), multiprocess
workers, then a Nelder-Mead polish at the same resolution.

Run from this directory:  python3 optimize.py --eps 0.1 --out r01.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

import numpy as np
from scipy.optimize import differential_evolution, minimize

_HERE = os.path.dirname(os.path.abspath(__file__))
def _load_sweeper():
    """Load sweeper.py by absolute path so the import works from any cwd."""
    _spec = importlib.util.spec_from_file_location(
        "sweeper", os.path.join(_HERE, "sweeper.py"))
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot load sweeper.py from {_HERE}")
    _mod = importlib.util.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_mod)
    except Exception as e:
        raise ImportError(f"error executing sweeper.py: {e}") from e
    # register so pickle resolves classes by qualified name
    sys.modules["sweeper"] = _mod
    return _mod


sweeper = _load_sweeper()
make_sweeper = sweeper.make_sweeper


def _safe_float(x, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return default if v != v else v  # NaN -> default


def _safe_int(x, default: int = 0) -> int:
    try:
        return int(x)
    except (TypeError, ValueError, OverflowError):
        return default


def unpack(u: np.ndarray, K: int):
    """u -> (thetas, xs, ys) of length K+1, theta sorted, mirror-closed."""
    x0, y0 = u[0], u[1]
    inner = u[2:].reshape(K - 1, 3)      # (theta, x, y)
    th = np.concatenate([[0.0], inner[:, 0], [np.pi / 2]])
    th = np.sort(np.clip(th, 0.0, np.pi / 2))
    xs = np.concatenate([[x0], inner[:, 1], [-x0]])
    ys = np.concatenate([[y0], inner[:, 2], [y0]])
    return th, xs, ys


class Objective:
    """Picklable objective wrapping a Sweeper for a fixed keyframe count."""

    def __init__(self, sw, K: int, bound: float):
        self.sw = sw
        self.K = K
        self.bound = bound

    def __call__(self, u):
        th, xs, ys = unpack(np.asarray(u), self.K)
        # keep needle centers inside the raster window (the window margin
        # already leaves slack for the needle's half-length)
        if np.max(np.abs(xs)) > self.bound or np.max(np.abs(ys)) > self.bound:
            return 10.0 + 10.0 * (np.max(np.abs(xs)) + np.max(np.abs(ys)))
        return self.sw.swept_area(np.column_stack([th, xs, ys]))


def optimize_one(eps: float, K: int = 6, seed: int = 0, popsize: int = 40,
                 maxiter: int = 250, grid_res: int = 420, n_theta: int = 140,
                 tol: float = 1e-6, verbose: bool = False):
    margin = max(0.9, 0.25 + 12 * eps)
    bound = margin - 0.55          # center must stay this far from window edge
    sw = make_sweeper(eps, grid_res=grid_res, n_theta=n_theta, margin=margin)
    ndim = 2 + 3 * (K - 1)
    lb = np.full(ndim, -bound)
    ub = np.full(ndim, bound)
    # interior thetas live in (0, pi/2): rows 2, 5, 8, ... are thetas
    for i in range(K - 1):
        lb[2 + 3 * i], ub[2 + 3 * i] = 0.01, np.pi / 2 - 0.01
    obj = Objective(sw, K, bound)

    rng = np.random.default_rng(seed)
    result = differential_evolution(
        obj, bounds=list(zip(lb, ub)), rng=rng, popsize=popsize,
        maxiter=maxiter, tol=tol, polish=False, workers=-1,
        updating="deferred", mutation=(0.4, 1.0), recombination=0.9,
    )
    # Nelder-Mead polish (objective is only piecewise-smooth)
    pol = minimize(obj, result.x, method="Nelder-Mead",
                   options={"maxiter": 4000, "xatol": 1e-5, "fatol": 1e-7})

    try:
        f_de = _safe_float(result.fun, default=float("inf"))
        f_nm = _safe_float(pol.fun, default=float("inf"))
    except AttributeError as e:  # malformed optimizer result
        raise RuntimeError(f"optimizer returned incomplete result: {e}") from e
    if f_nm < f_de:
        best_u, best_f = pol.x, f_nm
    else:
        best_u, best_f = np.asarray(result.x), f_de

    th, xs, ys = unpack(best_u, K)
    keyframes = np.column_stack([th, xs, ys])
    # re-evaluate at higher angular resolution for a fair number
    sw_hi = make_sweeper(eps, grid_res=grid_res, n_theta=3 * n_theta,
                         margin=margin)
    area_hi = sw_hi.swept_area(keyframes)
    out = {
        "eps": eps, "K": K, "seed": seed, "area": best_f, "area_hi": area_hi,
        "n_evals": _safe_int(getattr(result, "nfev", 0)),
        "keyframes": keyframes.tolist(),
    }
    if verbose:
        print(f"eps={eps:.4g} K={K} seed={seed}: area={best_f:.5f} "
              f"hi-res={area_hi:.5f}", flush=True)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eps", type=float, required=True)
    p.add_argument("--K", type=int, default=6)
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--popsize", type=int, default=40)
    p.add_argument("--maxiter", type=int, default=250)
    p.add_argument("--grid", type=int, default=420)
    p.add_argument("--out", type=str, default=None)
    a = p.parse_args()

    results = []
    for seed in range(a.seeds):
        r = optimize_one(a.eps, K=a.K, seed=seed, popsize=a.popsize,
                         maxiter=a.maxiter, grid_res=a.grid, verbose=True)
        results.append(r)
    best = min(results, key=lambda r: r["area_hi"])
    print("BEST:", json.dumps({k: best[k] for k in ("eps", "K", "area",
                                                    "area_hi")}))
    if a.out:
        try:
            with open(a.out, "w") as f:
                json.dump(results, f)
        except OSError as e:
            print(f"could not write {a.out}: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
