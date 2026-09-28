"""Grow smooth control resolution by exact knot insertion, then local search.

10 -> 19 controls per f/b profile preserves the starting piecewise-linear
functions. Only the 9+9 newly inserted midpoint controls may vary. This is a
continuation from an already discovered incumbent; discovery cost is unknown.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


def insert_knots(params: np.ndarray) -> np.ndarray:
    if len(params) != 21:
        raise ValueError("expected y0 + 10 f controls + 10 b controls")
    old_grid = np.linspace(0.0, 1.0, 10)
    new_grid = np.linspace(0.0, 1.0, 19)
    f = np.interp(new_grid, old_grid, np.clip(params[1:11], -1.0, 1.0))
    b = np.interp(new_grid, old_grid, params[11:21])
    return np.r_[params[0], f, b]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--budget", type=float, default=180.0)
    parser.add_argument("--n-arc", type=int, default=80)
    parser.add_argument("--n-verify", type=int, default=320)
    args = parser.parse_args()
    if args.seeds < 1 or args.budget <= 0:
        parser.error("positive seeds and CPU budget required")
    source = min(json.loads(args.source.read_text()),
                 key=lambda row: row["numerical_upper"])
    base = insert_knots(np.asarray(source["best_params"], dtype=float))
    model = SmoothProfileModel(source["K"], source["eps"], Nf=19, Nb=19,
                               n_arc=args.n_arc)
    coordinate_indices = np.r_[np.arange(2, 20, 2), np.arange(21, 39, 2)]
    initial_steps = np.r_[np.full(9, 0.05), np.full(9, 0.005)]
    rows = []
    for seed in range(args.seeds):
        rng = np.random.default_rng(seed)
        start = time.process_time()
        calls = 0

        def objective(x):
            nonlocal calls
            calls += 1
            return float(model.swept_area(x))

        x = base.copy()
        value = objective(x)
        baseline = value
        steps = initial_steps.copy()
        sweeps = 0
        while time.process_time() - start < args.budget:
            improved = False
            for j in rng.permutation(len(coordinate_indices)):
                index = coordinate_indices[j]
                for sign in (1.0, -1.0):
                    if time.process_time() - start >= args.budget:
                        break
                    trial = x.copy()
                    trial[index] += sign * steps[j]
                    score = objective(trial)
                    if score < value:
                        x, value, improved = trial, score, True
                if time.process_time() - start >= args.budget:
                    break
            sweeps += 1
            if not improved:
                steps *= 0.5
        cpu_s = time.process_time() - start
        check = numerical_pivot_enclosure(model.base,
                  model.to_full_params(x), n_sub=args.n_verify)
        row = {"source": str(args.source), "eps": source["eps"], "K": source["K"],
               "seed": seed, "cpu_budget_s": args.budget, "cpu_used_s": cpu_s,
               "calls": calls, "sweeps": sweeps, "Nf": 19, "Nb": 19,
               "baseline_sampled": baseline, "best_sampled": value,
               "best_params": x.tolist(), "n_arc": args.n_arc,
               "n_verify": args.n_verify, "numerical_lower": check["lower"],
               "numerical_upper": check["upper"],
               "limitation": "incumbent discovery cost unknown; floating-point only"}
        rows.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + "\n")
        print(f"seed={seed} cpu={cpu_s:.1f} calls={calls} sweeps={sweeps} "
              f"base={baseline:.9f} best={value:.9f} "
              f"upper={check['upper']:.9f}", flush=True)


if __name__ == "__main__":
    main()
