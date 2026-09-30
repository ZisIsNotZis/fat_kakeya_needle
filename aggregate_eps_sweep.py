"""Aggregate the ticket-05 eps sweep (protocol A, B=480, 4 families, 3 seeds).

Reuses the ticket-03 cell validation, but the grid axis is eps instead of
budget.  Produces min-over-seeds f_hat(eps), hit-rate and a log-law shape
diagnostic.  Numerical estimates only.
"""
import json
import math
import sys
from pathlib import Path

import aggregate_total_budget as agg

EPS_GRID = (0.8, 0.4, 0.2, 0.1, 0.05, 0.02, 0.01)
SWEEP_DIR = Path("results/budget_total_sweep")
EXPECTED_BUDGET = 480


def check_sweep_cell(cell, path: Path):
    problems = agg.check_cell(cell, path, allowed_eps=None)
    eps = cell.get("eps")
    if eps not in EPS_GRID:
        problems.append(f"{path.name}: eps {eps!r} outside the sweep grid")
    if cell.get("requested_total_budget_cpu_s") != EXPECTED_BUDGET:
        problems.append(f"{path.name}: budget "
                        f"{cell.get('requested_total_budget_cpu_s')!r} != 480")
    return problems


def aggregate(sweep_dir: Path = SWEEP_DIR):
    cells = {}
    problems = []
    for path in sorted(Path(sweep_dir).glob("*.json")):
        cell = agg._load_cell(path)
        key = (cell.get("family"), cell.get("eps"), cell.get("seed"))
        if key in cells:
            problems.append(f"{path.name}: duplicate cell {key}")
        cells[key] = cell
        problems.extend(check_sweep_cell(cell, path))
    for fam in agg.FAMILIES:
        for eps in EPS_GRID:
            for seed in agg.SEEDS:
                if (fam, eps, seed) not in cells:
                    problems.append(f"missing cell ({fam}, {eps}, {seed})")
    if problems:
        return {"status": "invalid_grid", "violations": problems,
                "cells_seen": len(cells)}

    table = {}
    for fam in agg.FAMILIES:
        per_eps = {}
        for eps in EPS_GRID:
            scores = {s: cells[(fam, eps, s)].get("numeric_outer_area")
                      for s in agg.SEEDS}
            valid = {s: v for s, v in scores.items()
                     if isinstance(v, (int, float)) and math.isfinite(v)}
            best_overall = min(
                min(cells[(f2, eps, s)].get("numeric_outer_area")
                    for s in agg.SEEDS) for f2 in agg.FAMILIES)
            threshold = best_overall * agg.HIT_TOLERANCE
            hits = [s for s, v in valid.items() if v <= threshold]
            per_eps[eps] = {
                "scores_by_seed": scores,
                "min_over_seeds": min(valid.values()),
                "argmin_seed": min(valid, key=valid.get),
                "valid_seeds": sorted(valid),
                "hit_rate": len(hits) / len(agg.SEEDS),
                "global_best_at_eps": best_overall,
            }
        table[fam] = per_eps
    return {
        "status": "ok",
        "protocol": "A_total_cpu",
        "sweep_dir": str(sweep_dir),
        "cells": 84,
        "eps_grid": list(EPS_GRID),
        "budget_cpu_s": EXPECTED_BUDGET,
        "frozen_rf": agg.FROZEN_RF,
        "resolution_note": ("every cell uses the same coarse objective "
                            "step_fraction=.1 and the same four-fold "
                            "validation (2^38/2^40 x 1e-4/5e-5, spread "
                            "<=0.5%), so values are comparable across eps"),
        "table": table,
    }


def log_law_shape(result):
    """Diagnostic: f_hat(eps) * ln(1/eps) and a A/(ln(1/eps)+B) fit."""
    import numpy as np
    out = {}
    for fam, per in result["table"].items():
        eps = np.array(list(EPS_GRID))
        q = np.array([per[e]["min_over_seeds"] for e in EPS_GRID])
        x = np.log(1.0 / eps)
        scaled = q * x
        # fit q = A/(x+B) by least squares over B
        best = None
        for B in np.linspace(-1.0, 8.0, 901):
            A = float(np.sum(q * x / (x + B)) / np.sum((x / (x + B)) ** 2))
            pred = A / (x + B)
            ss = float(np.sum((q - pred) ** 2))
            if best is None or ss < best[0]:
                best = (ss, A, B)
        ss, A, B = best
        ss_tot = float(np.sum((q - q.mean()) ** 2))
        out[fam] = {
            "f_hat_eps": {str(e): per[e]["min_over_seeds"] for e in EPS_GRID},
            "f_hat_times_log": {str(e): per[e]["min_over_seeds"] * math.log(1 / e)
                                for e in EPS_GRID},
            "log_fit_A_over_ln_plus_B": {"A": A, "B": B,
                                         "r2": 1 - ss / ss_tot if ss_tot else None},
            "monotone_decreasing": bool(np.all(np.diff(q) < 0)),
        }
    return out


def main():
    sweep = Path(sys.argv[1]) if len(sys.argv) > 1 else SWEEP_DIR
    result = aggregate(sweep)
    if result["status"] != "ok":
        for p in result["violations"][:20]:
            print("VIOLATION:", p)
        sys.exit(1)
    result["log_law_shape"] = log_law_shape(result)
    out = Path(sweep).parent / (Path(sweep).name + "_aggregate.json")
    out.write_text(json.dumps(result, indent=1))
    print("wrote", out)
    for fam, shape in result["log_law_shape"].items():
        fit = shape["log_fit_A_over_ln_plus_B"]
        print(f"{fam:14s} A={fit['A']:.3f} B={fit['B']:.2f} R2={fit['r2']:.4f} "
              f"monotone={shape['monotone_decreasing']}")


if __name__ == "__main__":
    main()
