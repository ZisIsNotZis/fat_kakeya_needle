"""Optimize the pivot+slide motion model (pivot_slide.PivotSlideModel).

Free params: P0 (2) + beta_1..beta_K (K) = K+2 scalars.  Same DE +
Nelder-Mead machinery as the keyframe model, but the objective is the
exact pivot+slide swept area.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np
from scipy.optimize import differential_evolution, minimize

from pivot_slide import PivotSlideModel


class PSObj:
    def __init__(self, model: PivotSlideModel, spread: float):
        self.model = model
        self.spread = spread

    def __call__(self, x) -> float:
        x = np.asarray(x, dtype=float)
        if not np.all(np.isfinite(x)):
            return 1e6
        if np.max(np.abs(x)) > self.spread:
            return 1e6
        return self.model.swept_area(x)


def optimize(eps: float, K: int, seed: int, popsize: int, maxiter: int,
             spread: float = 3.0, workers: int = 3,
             verbose: bool = False):
    model = PivotSlideModel(eps, K=K)
    # params = y0, K pivot fractions, K-1 along-needle slides
    ndim = 1 + K + max(0, K - 1)
    obj = PSObj(model, spread)
    bounds = [(-spread, spread)]
    bounds += [(-1.0, 1.0)] * K
    bounds += [(-spread, spread)] * max(0, K - 1)
    rng = np.random.default_rng(seed)
    t0 = time.time()
    res = differential_evolution(obj, bounds, rng=rng, popsize=popsize,
                                 maxiter=maxiter, tol=1e-8, polish=False,
                                 workers=workers, updating="deferred",
                                 mutation=(0.4, 1.0), recombination=0.9)
    pol = minimize(obj, res.x, method="Nelder-Mead",
                   options={"maxiter": 6000, "xatol": 1e-5, "fatol": 1e-8})
    try:
        f_de, f_nm = float(res.fun), float(pol.fun)
    except (TypeError, AttributeError) as e:
        raise RuntimeError(f"optimizer returned malformed result: {e}") from e
    f = min(f_de, f_nm)
    best = pol.x if f_nm <= f_de else res.x
    if verbose:
        print(f"eps={eps:.4g} K={K} seed={seed}: area={f:.5f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return f, best


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eps", type=float, required=True)
    p.add_argument("--K", type=int, default=8)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--popsize", type=int, default=24)
    p.add_argument("--maxiter", type=int, default=150)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--workers", type=int, default=3)
    a = p.parse_args()

    results = []
    for seed in range(a.seeds):
        try:
            f, best = optimize(a.eps, a.K, seed, a.popsize, a.maxiter,
                               workers=a.workers, verbose=True)
        except (ValueError, RuntimeError) as e:
            print(f"seed {seed} failed: {e}", file=sys.stderr)
            continue
        results.append({"eps": a.eps, "K": a.K, "seed": seed, "area": f,
                        "model": "pivot-slide", "params": best.tolist()})
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