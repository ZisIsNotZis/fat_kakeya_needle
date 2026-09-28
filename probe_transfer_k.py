"""Transfer saved smooth control points to different K without reoptimizing.

Fixed beta controls are a naive doubling; scaled beta controls use
beta_new = beta_old * K_source/K and approximately preserve total slide.
Neither transfer is the best achievable construction at each K.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-sub", type=int, default=80)
    parser.add_argument("--eps", type=float, default=None,
                        help="target width; default is the source width")
    parser.add_argument("--K", type=int, nargs="+", default=[8, 16, 32, 64, 128])
    parser.add_argument("--mode", choices=["fixed", "scaled"], default="fixed")
    args = parser.parse_args()
    source = min(json.loads(args.source.read_text()), key=lambda row: row["numerical_upper"])
    x = np.asarray(source["best_params"])
    controls = (len(x) - 1) // 2
    if len(x) != 1 + 2 * controls:
        parser.error("unsupported parameter layout")
    eps = source["eps"] if args.eps is None else args.eps
    rows = []
    for K in args.K:
        transferred = x.copy()
        if args.mode == "scaled":
            transferred[1 + controls:] *= source["K"] / K
        model = SmoothProfileModel(K, eps, controls, controls)
        data = numerical_pivot_enclosure(model.base, model.to_full_params(transferred),
                                        n_sub=args.n_sub)
        row = {"source": str(args.source), "eps": eps, "K": K,
               "mode": args.mode, "source_K": source["K"],
               "n_sub": args.n_sub, "numerical_lower": data["lower"],
               "numerical_upper": data["upper"],
               "limitation": "deterministic control transfer, not reoptimization; floating-point only"}
        rows.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + "\n")
        print(K, data["lower"], data["upper"], flush=True)


if __name__ == "__main__":
    main()
