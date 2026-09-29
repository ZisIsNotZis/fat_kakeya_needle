"""Protocol A total-CPU-budget runner: one family x seed x total-budget cell.

Ticket 03 protocol A. Every cell is an independent cold start charged the
whole process CPU: imports/startup, the DE search, checkpoint I/O, the four
independent high-density validation calls and the final publication write.
``time.process_time()`` is cumulative since process start, so the recorded
total always covers all of these phases. Search stops at the first
completed-evaluation boundary at or after ``B - R_f`` total process CPU;
only evaluations completed strictly before that deadline are eligible for
selection. A numeric score is published only when the DE population was
initialized, all four validation areas agree within 0.5%, and the total
process CPU at the last publication is still <= B; otherwise the cell is
typed ``over_budget`` / ``quality_limited`` / ``unranked`` with no rankable
numeric result. Family construction, coarse scoring and four-fold validation
are imported unchanged from ``budget_search_integer``; old exploratory
results are never reused and exact resume is impossible. Integer geometry
stays numerical, never a rigorous certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import signal
import sys
import time

import numpy as np
import scipy
from scipy.optimize import differential_evolution

import integer_motion_area
from budget_search_integer import (
    EXCLUDED_BASELINES, FAMILIES, MAX_TRACE_ROWS, PENALTY,
    BudgetExpired, Family, atomic_update, create_output, score, validate,
)

CODE_FILES = (
    "budget_total_integer.py", "budget_search_integer.py",
    "integer_motion_area.py", "motion_adapters.py", "smooth_pivot.py",
    "hierarchical_pivot.py", "pivot_slide.py", "v2_numerical_enclosure.py",
    "keich_motion.py",
)
DE_SETTINGS = {"popsize": 5, "workers": 1, "polish": False,
               "updating": "immediate", "tol": 0, "maxiter": 100000}
CPU_ACCOUNTING_NOTE = (
    "time.process_time() is cumulative since process start, so total_cpu_s "
    "includes imports/startup, the DE search, checkpoint I/O, validation and "
    "the final publication write; search_cpu_s is measured from just before "
    "differential_evolution, and misc_cpu_s is the remainder.")
SELECTION_NOTE = (
    "selected_params is the best completed coarse candidate whose evaluation "
    "finished strictly before search_deadline_cpu_s; an evaluation that "
    "crosses the deadline is counted but never eligible.")
SCORE_SOURCE_NOTE = (
    "numeric_outer_area is the maximum of the four independent validation "
    "areas: a conservative numerical observation, not a rigorous bound.")
PUBLICATION_NOTE = (
    "total_cpu_s is re-measured after the first publication write; a single "
    "bounded rewrite keeps the record honest and demotes a score to "
    "over_budget when that measurement exceeds B. The residual CPU of the "
    "very last rewrite itself is below the gate granularity.")
EXTERNAL_TIMEOUT_NOTE = (
    "Native pyclipper union is not preemptible; run under an external wall "
    "timeout (e.g. timeout --kill-after=10s). CPU may overshoot the search "
    "deadline by one evaluation; validation always runs to completion even "
    "when it exceeds the reserved R_f.")
SIGKILL_NOTE = (
    "If status is still 'running' the process was SIGKILLed before publishing "
    "a terminal state; such a record is never ranked, scored, resumed or "
    "aggregated.")


def code_hashes():
    """SHA-256 of every source file that can change a published number."""
    root = Path(__file__).resolve().parent
    return [{"file": name,
             "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
            for name in CODE_FILES]


def environment_record():
    try:
        import pyclipper
        pyclipper_version = pyclipper.__version__
    except Exception:
        pyclipper_version = None  # recorded, not silently assumed
    return {"python": sys.version.split()[0], "scipy": scipy.__version__,
            "numpy": np.__version__, "pyclipper": pyclipper_version,
            "affinity_core_count": len(os.sched_getaffinity(0)),
            "nice": os.getpriority(os.PRIO_PROCESS, 0)}


def decide_outcome(*, search_started, selected_params, validation,
                   total_cpu_s, total_budget):
    """Pre-registered gate order names the single typed status.

    Gates in ticket order: population initialized, four-fold quality within
    0.5%, total process CPU at publication <= B. The first failed gate names
    the status; only a cell passing all three yields a numeric score.
    """
    if not search_started or selected_params is None:
        return "unranked", False, None
    if validation is None or validation.get("status") != "ok":
        return "quality_limited", False, None
    areas = validation.get("numeric_outer_area_range")
    if not areas or len(areas) != 2:
        return "quality_limited", False, None
    if not math.isfinite(total_cpu_s) or total_cpu_s > total_budget:
        return "over_budget", False, None
    return "complete", True, float(max(areas))


def publish_result(row, out, *, total_budget, search_started, selected_params,
                   validation):
    """Gate, publish, then re-measure so the final write is inside the total."""
    total = time.process_time()
    status, publish_score, area = decide_outcome(
        search_started=search_started, selected_params=selected_params,
        validation=validation, total_cpu_s=total, total_budget=total_budget)
    row["gates"] = {
        "population_initialized": bool(search_started),
        "validation_quality_ok": None if validation is None
                                 else validation.get("status") == "ok",
        "within_total_budget": bool(total <= total_budget),
    }
    row["status"] = status
    row["total_cpu_s"] = total
    row["overshoot_cpu_s"] = max(0., total - total_budget)
    row["publication_note"] = PUBLICATION_NOTE
    if publish_score:
        row["numeric_outer_area"] = area
    atomic_update(out, row)
    after = time.process_time()  # covers the publication write itself
    if after != total:
        row["total_cpu_s"] = after
        row["overshoot_cpu_s"] = max(0., after - total_budget)
        row["gates"]["within_total_budget"] = bool(after <= total_budget)
        if after > total_budget and publish_score:
            row["status"] = "over_budget"
            row["demoted_after_publication"] = True
            row.pop("numeric_outer_area", None)
        atomic_update(out, row)
    return row


def run(family: Family, seed: int, total_budget: float, reserve: float,
        out: Path, *, max_wall_s=60, validation_wall_s=120, max_polygons=100000):
    """One cold-start cell: search to B - R_f, validate, gate, publish."""
    if not math.isfinite(total_budget) or total_budget <= 0:
        raise ValueError("total_budget must be finite and positive")
    if not math.isfinite(reserve) or not 0 <= reserve < total_budget:
        raise ValueError("reserve must be finite with 0 <= R_f < total_budget")
    deadline = total_budget - reserve
    row = {"mode": "total_run", "protocol": "A_total_cpu", **family.describe(),
           "seed": seed,
           "requested_total_budget_cpu_s": total_budget,
           "reserved_validation_cpu_s": reserve,
           "search_deadline_cpu_s": deadline,
           "de": {**DE_SETTINGS,
                  "rng": "fresh np.random.default_rng(seed) per invocation"},
           "limitation": integer_motion_area.LIMITATION,
           "cpu_accounting_note": CPU_ACCOUNTING_NOTE,
           "selection_note": SELECTION_NOTE,
           "score_source_note": SCORE_SOURCE_NOTE,
           "environment": environment_record(),
           "code_sha256": code_hashes(),
           "excluded_nonoptimized_baselines": list(EXCLUDED_BASELINES),
           "aggregate_ranking_authorized": False,
           "resume_policy": ("unsupported; every cell is an independent cold "
                             "start and never reuses prior results"),
           "external_timeout_note": EXTERNAL_TIMEOUT_NOTE,
           "sigkill_note": SIGKILL_NOTE,
           "status": "running", "search_started": False,
           "calls": 0, "valid_calls": 0,
           "failed_calls": [], "failed_count": 0, "failed_log_dropped": 0,
           "eval_log": [], "eval_log_dropped": 0,
           "cross_cutoff_evals_excluded": 0,
           "selected_params": None, "selected_search_area": None,
           "optimizer_terminated_before_deadline": False,
           "validation": None, "validation_cpu_s": 0., "validation_wall_s": 0.,
           "search_cpu_s": None, "search_wall_s": None,
           "total_cpu_s": None, "misc_cpu_s": None, "wall_s": None,
           "overshoot_cpu_s": None, "gates": None, "publication_note": None}
    create_output(out, row)
    start_wall = time.monotonic()
    selected_area = None
    selected_params = None

    def objective(x):
        nonlocal selected_area, selected_params
        if time.process_time() >= deadline:
            raise BudgetExpired()  # stop between evaluations, never mid-union
        result = score(family, x, max_wall_s=max_wall_s,
                       max_polygons=max_polygons)
        row["calls"] += 1
        completed = time.process_time()
        value = PENALTY
        improved = False
        if result["status"] == "ok":
            row["valid_calls"] += 1
            value = float(result["numeric_outer_area"])
            if completed < deadline:  # a cross-cutoff eval is never eligible
                if selected_area is None or value < selected_area:
                    selected_area = value
                    selected_params = np.asarray(x, dtype=float).tolist()
                    improved = True
            else:
                row["cross_cutoff_evals_excluded"] += 1
        else:
            row["failed_count"] += 1
            row["failed_calls"].append(
                {"call": row["calls"], "status": result["status"],
                 "detail": result.get("error", result.get("resource_limited"))})
            if len(row["failed_calls"]) > MAX_TRACE_ROWS:
                row["failed_calls"].pop(0)
                row["failed_log_dropped"] += 1
        row["search_started"] = row["calls"] > family.population_evals
        row["eval_log"].append({"call": row["calls"], "cpu_s": completed,
            "status": result["status"],
            "area": result.get("numeric_outer_area"),
            "objective_value": value, "min_area_so_far": selected_area})
        if len(row["eval_log"]) > MAX_TRACE_ROWS:
            row["eval_log"].pop(0)
            row["eval_log_dropped"] += 1
        if row["calls"] % 5 == 0 or improved:
            atomic_update(out, row)
        return value

    try:
        start_cpu = time.process_time()
        try:
            differential_evolution(objective, family.bounds,
                rng=np.random.default_rng(seed), **DE_SETTINGS)
        except BudgetExpired:
            pass
        before_validation = time.process_time()
        row["search_cpu_s"] = before_validation - start_cpu
        row["search_wall_s"] = time.monotonic() - start_wall
        row["search_started"] = row["calls"] > family.population_evals
        row["selected_params"] = selected_params
        row["selected_search_area"] = selected_area
        row["optimizer_terminated_before_deadline"] = before_validation < deadline
        atomic_update(out, row)
        if row["search_started"] and selected_params is not None:
            # validation starts immediately after the completed-eval stop
            wall0 = time.monotonic()
            validation = validate(family, selected_params,
                max_wall_s=validation_wall_s, max_polygons=max_polygons)
            row["validation"] = validation
            row["validation_wall_s"] = time.monotonic() - wall0
            row["validation_cpu_s"] = time.process_time() - before_validation
        total_probe = time.process_time()
        row["misc_cpu_s"] = max(0., total_probe - (row["search_cpu_s"] or 0.)
                                - row["validation_cpu_s"])
        row["wall_s"] = time.monotonic() - start_wall
        publish_result(row, out, total_budget=total_budget,
                       search_started=row["search_started"],
                       selected_params=selected_params,
                       validation=row["validation"])
    except BaseException as exc:
        row.update(status="aborted", abort_reason=f"{type(exc).__name__}: {exc}")
        atomic_update(out, row)
        raise
    return row


def preflight_validation(families, seed: int, out: Path, *, candidates=1,
                         validation_wall_s=120, max_polygons=100000):
    """Per-family deterministic validation-cost probe; never ranked."""
    if candidates < 1:
        raise ValueError("candidates must be >= 1")
    row = {"mode": "preflight_validation", "protocol": "A_total_cpu",
           "seed": seed, "candidates_per_family": candidates,
           "no_ranking_note": ("cost probe only: per-family raw four-fold "
                               "validation calls; families are never ranked"),
           "limitation": integer_motion_area.LIMITATION,
           "environment": environment_record(),
           "code_sha256": code_hashes(),
           "excluded_nonoptimized_baselines": list(EXCLUDED_BASELINES),
           "aggregate_ranking_authorized": False,
           "families": [], "status": "running"}
    create_output(out, row)
    try:
        for family in families:
            entry = {**family.describe(), "candidates": []}
            row["families"].append(entry)
            atomic_update(out, row)
            rng = np.random.default_rng(seed)  # deterministic, repeatable
            for _ in range(candidates):
                x = np.array([rng.uniform(lo, hi) for lo, hi in family.bounds])
                validation = validate(family, x,
                    max_wall_s=validation_wall_s, max_polygons=max_polygons)
                entry["candidates"].append({
                    "params": x.tolist(), "raw": validation["raw"],
                    "validation_cpu_s": validation.get("validation_cpu_s", 0.),
                    "status": validation["status"]})
                atomic_update(out, row)
            entry["validation_cpu_max_s"] = max(
                c["validation_cpu_s"] for c in entry["candidates"])
            atomic_update(out, row)
        row["status"] = "complete"
    except BaseException as exc:
        row.update(status="aborted", abort_reason=f"{type(exc).__name__}: {exc}")
        atomic_update(out, row)
        raise
    atomic_update(out, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-validation", dest="preflight_validation",
                      action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--family", choices=FAMILIES, help="required for --run")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eps", type=float, default=.005)
    parser.add_argument("--smoke-k", type=int,
                        help="non-ranking small K; never use for formal comparison")
    parser.add_argument("--total-budget", type=float, dest="total_budget",
                        help="requested total process CPU budget B, required for --run")
    parser.add_argument("--reserve", type=float,
                        help="frozen family validation reserve R_f (process CPU s), required for --run")
    parser.add_argument("--candidates", type=int, default=1,
                        help="deterministic random candidates per family for --preflight-validation")
    parser.add_argument("--out", type=Path, required=True,
                        help="exclusive new output; never overwrite or resume")
    parser.add_argument("--resume", action="store_true",
                        help="unsupported: DE RNG/population cannot be reconstructed")
    parser.add_argument("--max-wall-s", type=float, default=60)
    parser.add_argument("--validation-wall-s", type=float, default=120)
    parser.add_argument("--max-polygons", type=int, default=100000)
    args = parser.parse_args()
    if args.resume:
        parser.error("resume is unsupported; every cell is a fresh cold start; use a new output")
    if (not math.isfinite(args.max_wall_s) or args.max_wall_s <= 0 or
            not math.isfinite(args.validation_wall_s) or args.validation_wall_s <= 0 or
            args.max_polygons < 1):
        parser.error("work limits must be positive and finite")
    if args.run:
        if args.family is None or args.total_budget is None or args.reserve is None:
            parser.error("--run requires exactly one --family, --total-budget B and frozen --reserve R_f")
    else:
        if (args.family is not None or args.total_budget is not None
                or args.reserve is not None):
            parser.error("--preflight-validation evaluates all four families and takes no budget")
        if args.candidates < 1:
            parser.error("--candidates must be >= 1")
    # The caller sets process affinity/niceness externally; reject accidental shared-core runs.
    if len(os.sched_getaffinity(0)) != 1 or os.getpriority(os.PRIO_PROCESS, 0) < 10:
        parser.error("run externally on one core with nice -n 10 and a wall timeout")
    def stop_on_term(signum, frame):
        raise KeyboardInterrupt("SIGTERM requested; output is not resumable")

    signal.signal(signal.SIGTERM, stop_on_term)
    try:
        if args.preflight_validation:
            families = [Family(name, args.eps, args.smoke_k) for name in FAMILIES]
            result = preflight_validation(families, args.seed, args.out,
                candidates=args.candidates,
                validation_wall_s=args.validation_wall_s,
                max_polygons=args.max_polygons)
        else:
            family = Family(args.family, args.eps, args.smoke_k)
            result = run(family, args.seed, args.total_budget, args.reserve,
                         args.out, max_wall_s=args.max_wall_s,
                         validation_wall_s=args.validation_wall_s,
                         max_polygons=args.max_polygons)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"status={result['status']} output={args.out}", flush=True)


if __name__ == "__main__":
    main()
