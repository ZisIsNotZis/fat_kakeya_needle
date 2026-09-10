"""Continuation pass: re-optimize on a fine eps grid, warm-starting each
run from the best motion of the neighboring eps.

Purpose: the coarse sweep (run_sweep.sh) samples f(eps) with independent
searches per eps; different runs may land in different keyframe-topology
basins, making the sampled curve zigzag even though the true f is
continuous.  Warm-starting along the eps axis makes the sampled curve
track one basin family, and an occasional *downward* jump to a better
basin is then real signal, not noise.

Usage:  python3 continuation.py --eps-from 0.8 --eps-to 0.03 --steps 30
Writes results/cont_<tag>.json per point and cont_summary.json at end.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import sys

import numpy as np
from scipy.optimize import differential_evolution, minimize

_HERE = os.path.dirname(os.path.abspath(__file__))

def _load_module(name: str):
    """Load a sibling module by absolute path (works from any cwd).

    Registered in sys.modules so pickle can resolve its classes when the
    objective ships to multiprocess workers.
    """
    _spec = importlib.util.spec_from_file_location(
        name, os.path.join(_HERE, f"{name}.py"))
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot load {name}.py from {_HERE}")
    _mod = importlib.util.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(_mod)
    except Exception as e:
        raise ImportError(f"error executing {name}.py: {e}") from e
    sys.modules[name] = _mod
    return _mod


optimize = _load_module("optimize")
sweeper = _load_module("sweeper")
make_sweeper = sweeper.make_sweeper


def load_best_keyframes(results_dir="results"):
    """Best motion per eps from the coarse sweep, sorted by eps."""
    pts = []
    for f in sorted(glob.glob(f"{results_dir}/eps_*.json")):
        try:
            with open(f) as fh:
                runs = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"skipping {f}: {e}", file=sys.stderr)
            continue
        best = min(runs, key=lambda r: r["area_hi"])
        pts.append((best["eps"], np.asarray(best["keyframes"])))
    pts.sort()
    return pts


def keyframes_to_u(kf: np.ndarray, K: int) -> np.ndarray:
    """Inverse of optimize.unpack: (K+1, 3) keyframes -> parameter vector."""
    # assumes kf thetas are already sorted ascending (they are, post-unpack)
    order = np.argsort(kf[:, 0])
    kf = kf[order]
    x0, y0 = kf[0, 1], kf[0, 2]
    inner = kf[1:-1, :].reshape(-1)
    return np.concatenate([[x0, y0], inner])


def continuation_point(eps: float, K: int, warm_kf: np.ndarray | None,
                       seed: int, popsize: int, maxiter: int,
                       grid_res: int, n_theta: int):
    margin = max(0.9, 0.25 + 12 * eps)
    bound = margin - 0.55
    sw = make_sweeper(eps, grid_res=grid_res, n_theta=n_theta, margin=margin)
    ndim = 2 + 3 * (K - 1)
    lb = np.full(ndim, -bound)
    ub = np.full(ndim, bound)
    for i in range(K - 1):
        lb[2 + 3 * i], ub[2 + 3 * i] = 0.01, np.pi / 2 - 0.01
    obj = optimize.Objective(sw, K, bound)

    x0 = None
    if warm_kf is not None and warm_kf.shape[0] == K + 1:
        cand = keyframes_to_u(warm_kf, K)
        if cand.shape[0] == ndim and np.all(cand >= lb) and np.all(cand <= ub):
            x0 = cand

    rng = np.random.default_rng(seed)
    result = differential_evolution(
        obj, bounds=list(zip(lb, ub)), rng=rng, popsize=popsize,
        maxiter=maxiter, tol=1e-6, polish=False, workers=-1,
        updating="deferred", mutation=(0.4, 1.0), recombination=0.9,
        x0=x0,
    )
    pol = minimize(obj, result.x, method="Nelder-Mead",
                   options={"maxiter": 4000, "xatol": 1e-5, "fatol": 1e-7})
    try:
        f_de = optimize._safe_float(result.fun, default=float("inf"))
        f_nm = optimize._safe_float(pol.fun, default=float("inf"))
    except AttributeError as e:  # malformed optimizer result
        raise RuntimeError(f"optimizer returned incomplete result: {e}") from e
    if f_nm < f_de:
        best_u, best_f = pol.x, f_nm
    else:
        best_u, best_f = np.asarray(result.x), f_de

    th, xs, ys = optimize.unpack(best_u, K)
    kf = np.column_stack([th, xs, ys])
    sw_hi = make_sweeper(eps, grid_res=grid_res, n_theta=3 * n_theta,
                         margin=margin)
    return {
        "eps": eps, "K": K, "seed": seed, "area": best_f,
        "area_hi": sw_hi.swept_area(kf), "warm": warm_kf is not None,
        "keyframes": kf.tolist(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eps-from", type=float, default=0.8)
    p.add_argument("--eps-to", type=float, default=0.03)
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--K", type=int, default=6)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--popsize", type=int, default=40)
    p.add_argument("--maxiter", type=int, default=200)
    p.add_argument("--grid", type=int, default=420)
    a = p.parse_args()

    coarse = load_best_keyframes()
    if not coarse:
        print("no coarse results to warm-start from", file=sys.stderr)
        return 1

    eps_grid = np.geomspace(a.eps_from, a.eps_to, a.steps)
    prev_kf = None
    prev_eps = None
    summary = []
    for eps in eps_grid:
        # nearest coarse result at eps' >= eps gives the warm start
        if prev_kf is None:
            cands = [kf for e, kf in coarse if e >= eps * 0.999]
            warm = cands[0] if cands else None
            wsrc = "coarse"
        else:
            warm = prev_kf
            wsrc = f"cont(eps={prev_eps:.4g})"
        best = None
        for seed in range(a.seeds):
            # seed 0: warm-started (tracks the basin family along the eps
            # axis); seeds >= 1: fresh independent starts (escape valve --
            # take the min so we never do worse than an independent search)
            w = warm if seed == 0 else None
            r = continuation_point(eps, a.K, w, seed, a.popsize,
                                   a.maxiter, a.grid, 140)
            if best is None or r["area_hi"] < best["area_hi"]:
                best = r
        if best is None:  # defensive: seeds >= 1 guarantees a result
            print(f"eps={eps:.4g}: no feasible result, skipping", file=sys.stderr)
            continue
        best["warm_source"] = wsrc
        tag = f"{eps:.4g}".replace(".", "_").replace("-", "m")
        try:
            with open(f"results/cont_{tag}.json", "w") as fh:
                json.dump([best], fh)
        except OSError as e:
            print(f"write failed for eps={eps}: {e}", file=sys.stderr)
        print(f"eps={eps:.4g} area_hi={best['area_hi']:.5f} "
              f"({wsrc}{'+' if best['warm'] else ''}"
              f"{'warm' if best['warm'] else 'fresh'} s{best['seed']})",
              flush=True)
        summary.append({k: best[k] for k in
                        ("eps", "area", "area_hi", "warm", "warm_source")})
        prev_kf = np.asarray(best["keyframes"])
        prev_eps = eps

    try:
        with open("results/cont_summary.json", "w") as fh:
            json.dump(summary, fh, indent=1)
    except OSError as e:
        print(f"summary write failed: {e}", file=sys.stderr)
        return 1
    print("CONTINUATION DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
