"""Numerically compare archived and continued smooth motions at common density.

These Shapely floating-point enclosures are not mathematical certificates.
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
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--continued", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-sub", type=int, default=2048)
    args = parser.parse_args()
    archive = min(json.loads(args.archive.read_text()), key=lambda row: row["area"])
    continued = min(json.loads(args.continued.read_text()),
                    key=lambda row: row["numerical_upper"])
    if (archive["eps"], archive["K"]) != (continued["eps"], continued["K"]):
        raise ValueError("candidate epsilon/K mismatch")
    controls = (len(archive["best_params"]) - 1) // 2
    if len(archive["best_params"]) != len(continued["best_params"]) or \
            1 + 2 * controls != len(archive["best_params"]):
        raise ValueError("parameter layout mismatch")
    model = SmoothProfileModel(archive["K"], archive["eps"], controls, controls)
    rows = []
    for label, source, params in (("archive", args.archive, archive["best_params"]),
                                  ("continued", args.continued, continued["best_params"])):
        start = time.monotonic()
        e = numerical_pivot_enclosure(model.base,
                  model.to_full_params(np.asarray(params)), n_sub=args.n_sub)
        rows.append({"label": label, "source": str(source), "n_sub": args.n_sub,
                     "eps": archive["eps"], "K": archive["K"],
                     "numerical_lower": e["lower"], "numerical_upper": e["upper"],
                     "wall_s": time.monotonic() - start,
                     "limitation": "floating-point geometry, not a mathematical certificate"})
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + "\n")
        print(f"{label}: [{e['lower']:.10f}, {e['upper']:.10f}]", flush=True)
    print("numerical separation (archive lower - continued upper):",
          rows[0]["numerical_lower"] - rows[1]["numerical_upper"])


if __name__ == "__main__":
    main()
