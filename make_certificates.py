"""Compute numerical enclosures for the recorded pivot-slide construction.

Usage: python3 make_certificates.py
Writes results/pivot_numerical_enclosures.json; never rewrites the legacy
results/certificates.json. Shapely floating-point areas are not mathematical
certificates. Generic v2 keyframe paths are unsupported by this evaluator.
"""
from __future__ import annotations

import json

import numpy as np

from pivot_slide import PivotSlideModel
from strict_bound import numerical_pivot_enclosure


def main() -> int:
    source = "results/pivot_005_K16_night.json"
    output = "results/pivot_numerical_enclosures.json"
    try:
        with open(source) as fh:
            runs = json.load(fh)
        best = min(runs, key=lambda r: r["area"])
        model = PivotSlideModel(best["eps"], K=best["K"])
        enclosure = numerical_pivot_enclosure(model, np.asarray(best["params"]),
                                               n_sub=300)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"pivot numerical enclosure failed: {exc}")
        return 1

    record = {"model": "pivot-slide", "eps": best["eps"], "K": best["K"],
              "optimizer_area_estimate": best["area"],
              "numerical_lower": enclosure["lower"],
              "numerical_upper": enclosure["upper"],
              "numerical_gap": enclosure["gap"], "n_sub": enclosure["n_sub"],
              "method": "endpoint-hull-corner-sagitta-and-full-slides",
              "limitation": "Shapely floating-point geometry; not a mathematical certificate"}
    try:
        with open(output, "w") as fh:
            json.dump([record], fh, indent=1)
            fh.write("\n")
        print(f"wrote {output}: lower={enclosure['lower']:.5f} "
              f"upper={enclosure['upper']:.5f} (numerical, not certified)")
    except OSError as exc:
        print(f"write failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
