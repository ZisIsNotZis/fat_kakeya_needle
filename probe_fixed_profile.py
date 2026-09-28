"""Probe ONE stored smooth motion profile at different needle widths.

This is not reoptimization at each epsilon and cannot establish the optimal
fixed-K asymptote; the analytic bound pi/(8K) holds for every pivot profile.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-sub", type=int, default=320)
    parser.add_argument("--eps", type=float, nargs="+",
                        default=[0.005, 0.002, 0.001, 0.0005, 0.0002])
    args = parser.parse_args()
    rows = json.loads(args.source.read_text())
    best = min(rows, key=lambda x: x["numerical_upper"])
    params = np.asarray(best["best_params"])
    controls = (len(params) - 1) // 2
    if len(params) != 1 + 2 * controls or args.n_sub < 1:
        parser.error("unsupported parameter layout or n_sub")
    out = []
    for eps in args.eps:
        model = SmoothProfileModel(best["K"], eps, controls, controls)
        data = numerical_pivot_enclosure(model.base,
                  model.to_full_params(params), n_sub=args.n_sub)
        row = {"source": str(args.source), "eps": eps, "K": best["K"],
               "n_sub": args.n_sub, "numerical_lower": data["lower"],
               "numerical_upper": data["upper"],
               "analytic_fixed_K_floor": math.pi / (8 * best["K"]),
               "limitation": "fixed parameters; floating-point enclosure; no reoptimization"}
        out.append(row)
        print(eps, data["lower"], data["upper"], flush=True)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
