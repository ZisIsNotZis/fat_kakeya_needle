"""Summarize finite staged continuation at epsilon=0.002.

Best-lineage CPU counts only selected seed paths; total-search CPU counts all
seeds/budgets. Neither includes historical incumbent discovery or validation.
"""
from __future__ import annotations

import json
from pathlib import Path


STAGES = [
    ("K64-local", "results/incumbent_refine_0002_K64.json",
     "results/refined_0002_K64_dense.json"),
    ("K64-19ctrl", "results/midpoint_refine_0002_K64.json",
     "results/midpoint_refine_0002_K64_dense.json"),
    ("K128-37ctrl", "results/midpoint_refine_0002_K128.json",
     "results/midpoint_refine_0002_K128_dense.json"),
    ("K256-73ctrl", "results/midpoint_refine_0002_K256.json",
     "results/midpoint_refine_0002_K256_dense.json"),
    ("K256-coarse-knots", "results/coarse_refine_0002_K256.json",
     "results/coarse_refine_0002_K256_dense.json"),
]


def main() -> None:
    cumulative_best = 0.0
    cumulative_search = 0.0
    summary = []
    for name, source, verified in STAGES:
        runs = json.loads(Path(source).read_text())
        areas = json.loads(Path(verified).read_text())
        best = min(areas, key=lambda row: row["numerical_upper"])
        match = [run for run in runs if run["seed"] == best.get("seed")]
        selected = (min(match, key=lambda run: run["numerical_upper"])
                    if match else min(runs, key=lambda run: run["numerical_upper"]))
        stage_search = sum(run["cpu_used_s"] for run in runs)
        cumulative_best += selected["cpu_used_s"]
        cumulative_search += stage_search
        summary.append({"stage": name, "K": best["K"], "seed": selected["seed"],
                        "numerical_lower": best["numerical_lower"],
                        "numerical_upper": best["numerical_upper"],
                        "selected_run_cpu_s": selected["cpu_used_s"],
                        "stage_all_runs_cpu_s": stage_search,
                        "cumulative_best_lineage_cpu_s": cumulative_best,
                        "cumulative_all_runs_cpu_s": cumulative_search,
                        "unaccounted": "source discovery and all validation CPU"})
    out = Path("results/refinement_scaling_0002.json")
    out.write_text(json.dumps(summary, indent=2) + "\n")
    for row in summary:
        print(row["stage"], f"upper={row['numerical_upper']:.9f}",
              f"lineage={row['cumulative_best_lineage_cpu_s']:.1f}s",
              f"all={row['cumulative_all_runs_cpu_s']:.1f}s")


if __name__ == "__main__":
    main()
