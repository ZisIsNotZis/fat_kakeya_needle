"""Probe a concrete dyadic ruler-slide recurrence, without asymptotic claims.

At level m: K=2**m, eps=1/K, f_i=0, s_r=2**(-r).  The actual
motion is the continuous pivot arc + full axial slide + mirrored half-turn
implemented by HierModel/PivotSlideModel. Numeric areas are not certificates.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from hierarchical_pivot import HierModel
from strict_bound import numerical_pivot_enclosure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m-min", type=int, default=2)
    parser.add_argument("--m-max", type=int, default=7)
    parser.add_argument("--n-sub", type=int, default=8)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.m_min < 1 or args.m_max < args.m_min or args.m_max > 12:
        parser.error("require 1 <= m-min <= m-max <= 12")
    out = []
    for m in range(args.m_min, args.m_max + 1):
        K = 1 << m
        eps = 1.0 / K
        model = HierModel(K, eps)
        scales = 2.0 ** -np.arange(1, m + 1)
        params = model.to_full_params(np.r_[0.0, scales])
        _, centers, _, beta = model.base.centers_and_pivots(params)
        if abs(centers[-1, 0]) > 1e-10:
            raise RuntimeError("mirror closure failed")
        area = numerical_pivot_enclosure(model.base, params, n_sub=args.n_sub)
        row = {"m": m, "eps": eps, "K": K, "scales": scales.tolist(),
               "sum_abs_slides": float(np.sum(np.abs(beta))),
               "mirror_join_x": float(centers[-1, 0]), "n_sub": args.n_sub,
               "numerical_lower": area["lower"], "numerical_upper": area["upper"],
               "m_times_lower": m * area["lower"],
               "analytic_single_arc_floor": math.pi / (8 * K),
               "limitation": "finite scales; floating-point geometry; no asymptotic proof"}
        out.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2) + "\n")
        print(f"m={m} K={K} eps={eps:.6g} area~[{area['lower']:.6f},"
              f"{area['upper']:.6f}] m*lower={row['m_times_lower']:.4f}",
              flush=True)


if __name__ == "__main__":
    main()
