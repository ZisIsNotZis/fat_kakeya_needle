"""Budgeted coarse-knot coordinate attack on a previously refined profile.

At K256 the 73-control profiles came from 37->73 knot insertion. This
searches the original 37+37 coarse knots while holding inserted knots fixed.
Incumbent discovery, other seeds and validation are not free search time.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seeds', type=int, default=3)
    parser.add_argument('--budget', type=float, default=240)
    parser.add_argument('--n-arc', type=int, default=20)
    parser.add_argument('--n-verify', type=int, default=80)
    args = parser.parse_args()
    if args.seeds < 1 or args.budget <= 0:
        parser.error('positive seeds and CPU budget required')
    record = min(json.loads(args.source.read_text()),
                 key=lambda row: row['numerical_upper'])
    if record['Nf'] != record['Nb'] or (record['Nf'] - 1) % 2:
        raise ValueError('equal odd control counts required')
    n = record['Nf']
    model = SmoothProfileModel(record['K'], record['eps'], n, n,
                               n_arc=args.n_arc)
    base = np.asarray(record['best_params'], dtype=float)
    indices = np.r_[np.arange(1, n + 1, 2), np.arange(n + 1, 2 * n + 2, 2)]
    step0 = np.r_[np.full((n + 1) // 2, .02),
                  np.full((n + 1) // 2, .002)]
    rows = []
    for seed in range(args.seeds):
        start = time.process_time()
        rng = np.random.default_rng(seed)
        x = base.copy()
        best = float(model.swept_area(x))
        baseline = best
        calls = 1
        steps = step0.copy()
        sweeps = 0
        while time.process_time() - start < args.budget:
            improved = False
            for j in rng.permutation(len(indices)):
                for direction in (1.0, -1.0):
                    if time.process_time() - start >= args.budget:
                        break
                    trial = x.copy()
                    trial[indices[j]] += direction * steps[j]
                    value = float(model.swept_area(trial))
                    calls += 1
                    if value < best:
                        best, x, improved = value, trial, True
                if time.process_time() - start >= args.budget:
                    break
            sweeps += 1
            if not improved:
                steps *= .5
        cpu_s = time.process_time() - start
        e = numerical_pivot_enclosure(model.base, model.to_full_params(x),
                                      n_sub=args.n_verify)
        row = {'source': str(args.source), 'eps': record['eps'], 'K': record['K'],
               'Nf': n, 'Nb': n, 'seed': seed, 'n_arc': args.n_arc,
               'n_verify': args.n_verify, 'cpu_budget_s': args.budget,
               'cpu_used_s': cpu_s, 'calls': calls, 'sweeps': sweeps,
               'baseline_sampled': baseline, 'best_sampled': best,
               'best_params': x.tolist(), 'numerical_lower': e['lower'],
               'numerical_upper': e['upper'],
               'limitation': 'shared inherited basin and floating-point area; no cold-start ranking'}
        rows.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + '\n')
        print(f'seed={seed} cpu={cpu_s:.1f} calls={calls} sweeps={sweeps} '
              f'base={baseline:.9f} best={best:.9f} upper={e["upper"]:.9f}',
              flush=True)


if __name__ == '__main__':
    main()
