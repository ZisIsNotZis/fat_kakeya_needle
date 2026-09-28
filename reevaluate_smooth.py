"""Re-evaluate archived smooth-profile candidates with one numerical geometry path.

This compares saved constructions, not equal-budget optimizer searches. Output
is a floating-point numerical enclosure, never a mathematical certificate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure


def evaluate(path: Path, n_sub: int) -> dict:
    runs = json.loads(path.read_text())
    best = min(runs, key=lambda record: record["area"])
    params = np.asarray(best["best_params"], dtype=float)
    if (len(params) - 1) % 2 or len(params) < 5:
        raise ValueError(f"cannot infer equal Nf/Nb from {path}")
    # Archive omits Nf/Nb; all selected runs used equal control counts.
    # This is an explicit reconstruction assumption, not saved metadata.
    controls = (len(params) - 1) // 2
    model = SmoothProfileModel(best["K"], best["eps"], controls, controls)
    enclosure = numerical_pivot_enclosure(model.base, model.to_full_params(params),
                                            n_sub=n_sub)
    return {"source": str(path), "source_seed": best["seed"],
            "source_area": best["area"], "source_n_arc": best.get("n_arc"),
            "eps": best["eps"], "K": best["K"], "Nf": controls,
            "Nb": controls, "control_layout": "equal-count inferred from archive length",
            "geometry_revision": "precision-grid-v1",
            "grid": min(1e-10, best["eps"] * 1e-8),
            "numerical_lower": enclosure["lower"],
            "numerical_upper": enclosure["upper"],
            "n_sub": n_sub,
            "limitation": "Shapely floating-point geometry; not a rigorous certificate"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-sub", type=int, default=160)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()
    records = [evaluate(path, args.n_sub) for path in args.sources]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2) + "\n")
    for row in records:
        print(f"{row['source']}: old={row['source_area']:.9f} "
              f"numerical=[{row['numerical_lower']:.9f},{row['numerical_upper']:.9f}]")


if __name__ == "__main__":
    main()
