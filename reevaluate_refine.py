"""Checkpointed dense numerical re-evaluation of local-search records.

Source rows must contain eps, K, best_params, seed, Nf, Nb. Float geometry
is not a mathematical area certificate.
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
    parser.add_argument("--n-sub", type=int, default=640)
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    rows = json.loads(args.out.read_text()) if args.out.exists() else []
    if any(row["source"] != str(args.source) or row["n_sub"] != args.n_sub
           for row in rows):
        raise ValueError("output contains a different source or resolution")
    completed = {row["seed"] for row in rows}
    for record in source:
        if record["seed"] in completed:
            continue
        model = SmoothProfileModel(record["K"], record["eps"],
                                   record["Nf"], record["Nb"])
        x = np.asarray(record["best_params"])
        e = numerical_pivot_enclosure(model.base,
                  model.to_full_params(x), n_sub=args.n_sub)
        row = {"source": str(args.source), "seed": record["seed"],
               "eps": record["eps"], "K": record["K"],
               "Nf": record["Nf"], "Nb": record["Nb"], "n_sub": args.n_sub,
               "numerical_lower": e["lower"], "numerical_upper": e["upper"],
               "limitation": "floating-point geometry; continuation discovery cost unknown"}
        rows.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + "\n")
        print(f"seed={record['seed']} [{e['lower']:.9f}, {e['upper']:.9f}]",
              flush=True)


if __name__ == "__main__":
    main()
