"""Single-core equal-process-CPU-time DE pilot; not a global method ranking.

Each cell uses independent seeds and the same corrected sampled-area evaluator.
A per-objective CPU deadline interrupts DE at the next evaluation boundary.
Results are checkpointed after each seed for safe restart/inspection.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

from hierarchical_pivot import HierModel
from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


class BudgetExpired(Exception):
    pass


def run_cell(family: str, eps: float, K: int, seed: int,
             budget_cpu_s: float, n_arc: int, n_verify: int) -> dict:
    model = (SmoothProfileModel(K, eps, Nf=6, Nb=6, n_arc=n_arc)
             if family == "smooth" else
             HierModel(K, eps, use_f0=True, n_arc=n_arc))
    bounds = [(-3.0, 3.0)] * model.ndim
    start_cpu, start_wall = time.process_time(), time.monotonic()
    best = [float("inf"), None]
    calls = 0
    population_evals = 5 * model.ndim

    def objective(x):
        nonlocal calls
        if time.process_time() - start_cpu >= budget_cpu_s and calls > 0:
            raise BudgetExpired()
        value = float(model.swept_area(x))
        calls += 1
        if value < best[0]:
            best[:] = [value, np.asarray(x).tolist()]
        return value

    try:
        differential_evolution(objective, bounds, seed=seed, popsize=5,
                               maxiter=100000, polish=False, tol=0.0,
                               workers=1, updating="immediate")
    except BudgetExpired:
        pass
    cpu_s = time.process_time() - start_cpu
    wall_s = time.monotonic() - start_wall
    if best[1] is None:
        raise RuntimeError("no objective evaluation completed")
    # Validation occurs outside the budget, identical for both families.
    result = numerical_pivot_enclosure(model.base,
              model.to_full_params(np.asarray(best[1])), n_sub=n_verify)
    return {"family": family, "eps": eps, "K": K, "seed": seed,
            "cpu_budget_s": budget_cpu_s, "cpu_used_s": cpu_s,
            "wall_used_s": wall_s, "calls": calls,
            "population_evals": population_evals,
            "search_started": calls > population_evals,
            "n_arc": n_arc,
            "n_verify": n_verify, "best_params": best[1],
            "objective_sampled": best[0],
            "validation_numerical_lower": result["lower"],
            "validation_numerical_upper": result["upper"],
            "limitation": "floating-point geometry; pilot uses DE only, not an all-method search"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eps", type=float, default=0.005)
    parser.add_argument("--K", type=int, default=32)
    parser.add_argument("--n-arc", type=int, default=80)
    parser.add_argument("--n-verify", type=int, default=160)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--budgets", nargs="+", type=float, default=[30, 60])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1 or min(args.budgets) <= 0:
        parser.error("positive seeds and budgets required")
    if args.K < 2 or args.K & (args.K - 1):
        parser.error("K must be a power of two >= 2")
    rows = []
    for family in ("hierarchical", "smooth"):
        for budget in args.budgets:
            for seed in range(args.seeds):
                row = run_cell(family, args.eps, args.K, seed,
                               budget, args.n_arc, args.n_verify)
                rows.append(row)
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(rows, indent=2) + "\n")
                print(f"{family} budget={budget:g} seed={seed} "
                      f"cpu={row['cpu_used_s']:.1f}s calls={row['calls']} "
                      f"sampled={row['objective_sampled']:.6f} "
                      f"valid_num_upper={row['validation_numerical_upper']:.6f}",
                      flush=True)


if __name__ == "__main__":
    main()
