"""CLI runner for the smooth-profile pivot+slide model.

Same DE + Nelder-Mead machinery as optimize_pivot, over SmoothProfileModel.
Supports mixed initialization for cross-eps continuation (Phase C):
--init-json a results JSON whose best params seed 30% of the population
(pure warm-start is known to hurt; random stays dominant).
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np
from scipy.optimize import differential_evolution, minimize

from smooth_pivot import SmoothProfileModel


class SmoothObj:
    def __init__(self, model, spread):
        self.model = model
        self.spread = spread

    def __call__(self, x) -> float:
        x = np.asarray(x, dtype=float)
        if not np.all(np.isfinite(x)) or np.max(np.abs(x)) > self.spread:
            return 1e6
        return self.model.swept_area(x)


def build_init(model, ndim, seed_params, popsize, rng, frac=0.3, sigma=0.1):
    total = popsize * ndim
    if seed_params is None or len(seed_params) != ndim:
        return "latinhypercube"
    rows = []
    base = np.asarray(seed_params, dtype=float)
    n_seed = int(total * frac)
    for _ in range(n_seed):
        rows.append(np.clip(base + rng.normal(0, sigma, ndim),
                            -model.base.eps if False else -3.0, 3.0))
    while len(rows) < total:
        rows.append(rng.uniform(-3.0, 3.0, ndim))
    return np.array(rows[:total])


def run_one(eps, K, Nf, Nb, seed, popsize, maxiter, workers,
            seed_params=None, verbose=False, n_arc=120):
    model = SmoothProfileModel(K, eps, Nf=Nf, Nb=Nb, n_arc=n_arc)
    ndim = model.ndim
    obj = SmoothObj(model, 3.0)
    bounds = [(-3.0, 3.0)] * ndim
    rng = np.random.default_rng(seed)
    init = build_init(model, ndim, seed_params, popsize, rng)
    t0 = time.time()
    res = differential_evolution(obj, bounds, rng=rng, popsize=popsize,
                                 maxiter=maxiter, tol=1e-8, polish=False,
                                 workers=workers, updating="deferred",
                                 mutation=(0.4, 1.0), recombination=0.9,
                                 init=init)
    pol = minimize(obj, res.x, method="Nelder-Mead",
                   options={"maxiter": 6000, "xatol": 1e-5, "fatol": 1e-8})
    f_de, f_nm = float(res.fun), float(pol.fun)
    f = min(f_de, f_nm)
    best = pol.x if f_nm <= f_de else res.x
    if verbose:
        tag = "mixed" if seed_params is not None else "random"
        print(f"eps={eps:.4g} K={K} seed={seed} ({tag}): area={f:.5f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return f, best.tolist()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eps", type=float, required=True)
    p.add_argument("--K", type=int, default=16)
    p.add_argument("--Nf", type=int, default=6)
    p.add_argument("--Nb", type=int, default=6)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--popsize", type=int, default=20)
    p.add_argument("--maxiter", type=int, default=200)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--init-json", type=str, default=None)
    p.add_argument("--n_arc", type=int, default=120)
    p.add_argument("--out", type=str, required=True)
    a = p.parse_args()

    seed_params = None
    if a.init_json:
        try:
            with open(a.init_json) as fh:
                prior = json.load(fh)
            if isinstance(prior, list):
                prior = min(prior, key=lambda r: r["area"])
            seed_params = prior.get("best_params") or prior.get("params")
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"init-json unusable ({e}); using random", file=sys.stderr)
            seed_params = None

    results = []
    for seed in range(a.seeds):
        try:
            f, best = run_one(a.eps, a.K, a.Nf, a.Nb, seed, a.popsize,
                              a.maxiter, a.workers, seed_params=seed_params,
                              verbose=True, n_arc=a.n_arc)
        except (ValueError, RuntimeError) as e:
            print(f"seed {seed} failed: {e}", file=sys.stderr)
            continue
        results.append({"eps": a.eps, "K": a.K, "seed": seed, "area": f,
                        "model": "pivot-slide-smooth",
                        "best_params": best,
                        "init": "mixed" if seed_params is not None else "random",
                        "n_arc": a.n_arc})
        # incremental checkpoint: persist after every seed so long runs
        # never lose completed work
        try:
            with open(a.out, "w") as fh:
                json.dump(results, fh)
        except OSError as e:
            print(f"checkpoint write failed: {e}", file=sys.stderr)
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
