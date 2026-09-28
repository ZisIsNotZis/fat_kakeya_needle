"""CPU-budgeted local continuation of a recorded smooth-profile incumbent.

The discovery cost of the incumbent is unknown and EXCLUDED; never compare this
continuation directly with cold-start method quality as if budgets were equal.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


class BudgetExpired(Exception):
    pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--budgets", type=float, nargs="+", default=[60, 120])
    parser.add_argument("--n-arc", type=int, default=80)
    parser.add_argument("--n-verify", type=int, default=160)
    parser.add_argument("--sigma", type=float, default=0.03)
    args = parser.parse_args()
    if args.seeds < 1 or args.sigma < 0 or any(b <= 0 for b in args.budgets):
        parser.error("seeds, sigma, and budgets must be nonnegative/positive")
    records = json.loads(args.source.read_text())
    incumbent = min(records, key=lambda record: record["area"])
    x0 = np.asarray(incumbent["best_params"], dtype=float)
    if (len(x0) - 1) % 2:
        parser.error("archive does not have equal control counts")
    controls = (len(x0) - 1) // 2
    model = SmoothProfileModel(incumbent["K"], incumbent["eps"],
                               controls, controls, n_arc=args.n_arc)
    rows = []
    for budget in args.budgets:
        for seed in range(args.seeds):
            rng = np.random.default_rng(seed)
            start = time.process_time()
            best = [float("inf"), None]
            calls = 0

            def objective(x):
                nonlocal calls
                if calls and time.process_time() - start >= budget:
                    raise BudgetExpired()
                calls += 1
                if not np.all(np.isfinite(x)) or np.max(np.abs(x)) > 3.0:
                    return 1e6
                value = float(model.swept_area(x))
                if value < best[0]:
                    best[:] = [value, np.asarray(x).tolist()]
                return value

            baseline = objective(x0)
            perturbation = np.zeros_like(x0) if seed == 0 else rng.normal(0, args.sigma, len(x0))
            try:
                minimize(objective, x0 + perturbation, method="Nelder-Mead",
                         options={"maxiter": 100000, "xatol": 1e-8, "fatol": 1e-9})
            except BudgetExpired:
                pass
            used_cpu = time.process_time() - start
            check = numerical_pivot_enclosure(model.base,
                      model.to_full_params(np.asarray(best[1])), n_sub=args.n_verify)
            row = {"family": "smooth-incumbent-continuation", "eps": incumbent["eps"],
                   "K": incumbent["K"], "source": str(args.source),
                   "source_seed": incumbent["seed"], "seed": seed, "sigma": args.sigma,
                   "incumbent_discovery_cpu_s": None,
                   "baseline_sampled": baseline, "cpu_budget_s": budget,
                   "cpu_used_s": used_cpu, "calls": calls, "n_arc": args.n_arc,
                   "n_verify": args.n_verify, "best_params": best[1],
                   "best_sampled": best[0], "numerical_lower": check["lower"],
                   "numerical_upper": check["upper"],
                   "limitation": "prior discovery cost unknown; floating-point numerical enclosure only"}
            rows.append(row)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(rows, indent=2) + "\n")
            print(f"budget={budget:g} seed={seed} cpu={used_cpu:.1f}s "
                  f"calls={calls} base={baseline:.8f} "
                  f"best={best[0]:.8f} upper={check['upper']:.8f}", flush=True)


if __name__ == "__main__":
    main()
