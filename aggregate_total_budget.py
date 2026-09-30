"""Aggregate the formal 48-cell total-CPU budget grid (ticket 03, protocol A).

Reads ONLY cells produced by budget_total_integer.py --run under the frozen
R_f policy.  Produces min-over-seeds and hit-rate per (family, budget), or a
typed refusal.  The aggregator never ranks on a single seed and never mixes
in exploratory/retrospective data.
"""
import json
import math
import sys
from pathlib import Path

FAMILIES = ("smooth", "hierarchical", "free_pivot", "v2_repaired")
BUDGETS = (60, 120, 240, 480)
SEEDS = (0, 1, 2)
FROZEN_RF = {"smooth": 39, "hierarchical": 23, "free_pivot": 36,
             "v2_repaired": 17}
HIT_TOLERANCE = 1.03
GRID_DIR = Path("results/budget_total_grid_0005")


def _load_cell(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # unreadable cell is an infrastructure failure
        return {"status": "unreadable", "error": str(exc)}


def check_cell(cell, path: Path, *, allowed_eps=(0.005, 5e-3)):
    """Return a list of violation strings for one cell record.

    allowed_eps restricts the eps values; pass None for grids whose eps axis
    is validated separately (e.g. the ticket-05 sweep).
    """
    problems = []
    fam = cell.get("family")
    budget = cell.get("requested_total_budget_cpu_s")
    seed = cell.get("seed")
    if fam not in FAMILIES:
        problems.append(f"{path.name}: unknown family {fam!r}")
    if budget not in BUDGETS:
        problems.append(f"{path.name}: budget {budget!r} outside frozen grid")
    if seed not in SEEDS:
        problems.append(f"{path.name}: seed {seed!r} outside frozen grid")
    if cell.get("protocol") != "A_total_cpu":
        problems.append(f"{path.name}: wrong protocol")
    if cell.get("reserved_validation_cpu_s") != FROZEN_RF.get(fam):
        problems.append(f"{path.name}: reserve "
                        f"{cell.get('reserved_validation_cpu_s')!r} != frozen "
                        f"R_f {FROZEN_RF.get(fam)}")
    if allowed_eps is not None and cell.get("eps") not in allowed_eps:
        problems.append(f"{path.name}: eps {cell.get('eps')!r} not in "
                        f"{allowed_eps}")
    if not cell.get("code_sha256"):
        problems.append(f"{path.name}: missing code_sha256 provenance")
    env = cell.get("environment") or {}
    if env.get("pyclipper") != "1.4.0":
        problems.append(f"{path.name}: pyclipper {env.get('pyclipper')!r} "
                        "is not the pinned 1.4.0")
    if cell.get("status") != "complete":
        problems.append(f"{path.name}: terminal status "
                        f"{cell.get('status')!r} is not rankable")
        return problems
    if not cell.get("search_started"):
        problems.append(f"{path.name}: DE never crossed initialization")
    validation = cell.get("validation") or {}
    if validation.get("status") != "ok":
        problems.append(f"{path.name}: validation {validation.get('status')!r}")
    total = cell.get("total_cpu_s")
    if not isinstance(total, (int, float)) or not math.isfinite(total):
        problems.append(f"{path.name}: nonfinite total_cpu_s")
    elif isinstance(budget, (int, float)) and total > budget:
        problems.append(f"{path.name}: total_cpu_s {total} exceeds budget")
    if cell.get("selected_params") is None:
        problems.append(f"{path.name}: no selected params (provenance)")
    score = cell.get("numeric_outer_area")
    if not isinstance(score, (int, float)) or not math.isfinite(score):
        problems.append(f"{path.name}: complete cell lacks a finite "
                        "numeric_outer_area")
    if cell.get("aggregate_ranking_authorized") is not False:
        problems.append(f"{path.name}: cell must not self-authorize ranking")
    return problems


def aggregate(grid_dir: Path = GRID_DIR):
    cells = {}
    problems = []
    for path in sorted(Path(grid_dir).glob("*.json")):
        cell = _load_cell(path)
        key = (cell.get("family"), cell.get("requested_total_budget_cpu_s"),
               cell.get("seed"))
        if key in cells:
            problems.append(f"{path.name}: duplicate cell {key}")
        cells[key] = cell
        problems.extend(check_cell(cell, path))
    for fam in FAMILIES:
        for budget in BUDGETS:
            for seed in SEEDS:
                if (fam, budget, seed) not in cells:
                    problems.append(f"missing cell ({fam}, {budget}, {seed})")
    if problems:
        return {"status": "invalid_grid", "violations": problems,
                "cells_seen": len(cells)}

    table = {}
    for fam in FAMILIES:
        per_budget = {}
        for budget in BUDGETS:
            scores = {seed: cells[(fam, budget, seed)].get("numeric_outer_area")
                      for seed in SEEDS}
            valid = {s: v for s, v in scores.items()
                     if isinstance(v, (int, float)) and math.isfinite(v)}
            best_overall = min(
                min(cells[(f2, budget, s)].get("numeric_outer_area")
                    for s in SEEDS)
                for f2 in FAMILIES)
            threshold = best_overall * HIT_TOLERANCE
            hits = [s for s, v in valid.items() if v <= threshold]
            per_budget[budget] = {
                "scores_by_seed": scores,
                "min_over_seeds": min(valid.values()),
                "argmin_seed": min(valid, key=valid.get),
                "valid_seeds": sorted(valid),
                "hit_rate": len(hits) / len(SEEDS),
                "hit_seeds": hits,
                "global_best_at_budget": best_overall,
                "hit_threshold": threshold,
            }
        table[fam] = per_budget
    return {
        "status": "ok",
        "protocol": "A_total_cpu",
        "grid_dir": str(grid_dir),
        "cells": 48,
        "frozen_rf": FROZEN_RF,
        "hit_rate_definition": ("fraction of the 3 frozen seeds whose "
                                "validated score <= global best across "
                                "families at the same budget x 1.03"),
        "ranking_note": ("min-over-seeds of validated four-fold conservative "
                         "scores; numerical estimates, NOT strict bounds"),
        "table": table,
    }


def main():
    grid = Path(sys.argv[1]) if len(sys.argv) > 1 else GRID_DIR
    result = aggregate(grid)
    out = Path(grid).parent / (Path(grid).name + "_aggregate.json")
    out.write_text(json.dumps(result, indent=1))
    print(json.dumps({"status": result["status"], "out": str(out)}))
    if result["status"] != "ok":
        for p in result["violations"][:20]:
            print("VIOLATION:", p)
        sys.exit(1)
    for fam, per in result["table"].items():
        line = f"{fam:14s}"
        for budget in BUDGETS:
            entry = per[budget]
            line += f"  B{budget}:{entry['min_over_seeds']:.4f}(hr {entry['hit_rate']:.2f})"
        print(line)


if __name__ == "__main__":
    main()
