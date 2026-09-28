"""Cold-start DE budget experiment on repaired continuous integer-scored motions.

Preflight first; budgets are supplied by the experiment owner, not inferred here.
Run externally with one CPU affinity and nice -n 10; native Clipper union is
not preemptible, so use an external wall timeout as well. Integer geometry is
numerical, not a proof of a rigorous swept-area upper bound.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time

import numpy as np
from scipy.optimize import differential_evolution

import integer_motion_area
from hierarchical_pivot import HierModel
from motion_adapters import pivot_primitives, v2_primitives
from pivot_slide import PivotSlideModel
from smooth_pivot import SmoothProfileModel

FAMILIES = ("smooth", "hierarchical", "free_pivot", "v2_repaired")
EXCLUDED_BASELINES = ("keich_n4", "keich_n5")  # deterministic, not cold-start DE
PENALTY = 1e6
SEARCH_STEP = .1
VALIDATION_STEPS = (.0001, .00005)
VALIDATION_SCALES = (1 << 38, 1 << 40)
MAX_TRACE_ROWS = 128


class BudgetExpired(Exception):
    """Stop DE at an objective boundary, never during a native union."""


class Family:
    def __init__(self, name: str, eps: float = .005, smoke_k: int | None = None):
        if name not in FAMILIES or not math.isfinite(eps) or not 0 < eps <= 1:
            raise ValueError("invalid family or eps")
        self.name, self.eps = name, eps
        K = {"smooth": 32, "hierarchical": 32, "free_pivot": 8,
             "v2_repaired": 6}[name] if smoke_k is None else smoke_k
        if K < 2 or (name == "hierarchical" and K & (K - 1)):
            raise ValueError("K must be >=2; hierarchical K must be a power of two")
        self.K = K
        if name == "smooth":
            self.model = SmoothProfileModel(K, eps, Nf=6, Nb=6)
            self.bounds = [(-3., 3.)] + [(-1., 1.)] * 6 + [(-.5, .5)] * 6
        elif name == "hierarchical":
            self.model = HierModel(K, eps, use_f0=True)
            self.bounds = [(-3., 3.)] + [(-.5, .5)] * (self.model.ndim - 1)
        elif name == "free_pivot":
            self.model = PivotSlideModel(eps, K)
            self.bounds = [(-3., 3.)] + [(-1., 1.)] * K + [(-.5, .5)] * (K - 1)
        else:
            self.model = None
            self.bounds = [(-3., 3.)] * (2 * (K + 1))
        self.ndim = len(self.bounds)
        self.population_evals = 5 * self.ndim

    def primitives(self, params):
        x = np.asarray(params, dtype=float)
        if x.shape != (self.ndim,) or not np.all(np.isfinite(x)) or any(
                not lo <= val <= hi for val, (lo, hi) in zip(x, self.bounds)):
            raise ValueError("parameters outside registered bounds")
        if self.name == "v2_repaired":
            keyframes = np.column_stack((np.linspace(0, math.pi / 2, self.K + 1),
                                         x.reshape(self.K + 1, 2)))
            return v2_primitives(keyframes, self.eps)
        if self.name == "free_pivot":
            return pivot_primitives(self.model, x)
        return pivot_primitives(self.model.base, self.model.to_full_params(x))

    def describe(self):
        return {"family": self.name, "eps": self.eps, "K": self.K,
                "dimension": self.ndim, "bounds": [list(pair) for pair in self.bounds],
                "population_evals": self.population_evals,
                "motion": "continuous repaired pivot/linear-pose mirror about final center x",
                "step_fraction": SEARCH_STEP}


def score(family: Family, params, *, step_fraction=SEARCH_STEP, scale=None,
          max_wall_s=60, max_polygons=100000):
    """A typed failure is never a candidate; the penalty is only for DE."""
    try:
        primitives = family.primitives(params)
        if scale is None:
            row = integer_motion_area.evaluate(primitives, family.eps,
                step_fraction=step_fraction, max_wall_s=max_wall_s,
                max_polygons=max_polygons)
        else:
            with integer_scale(scale):
                row = integer_motion_area.evaluate(primitives, family.eps,
                    step_fraction=step_fraction, max_wall_s=max_wall_s,
                    max_polygons=max_polygons)
    except Exception as exc:
        row = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    area = row.get("numeric_outer_area")
    if row.get("status") == "ok" and (not isinstance(area, (int, float)) or
            not math.isfinite(area) or not 0 < area < PENALTY):
        row = {**row, "status": "error", "error": "invalid numeric_outer_area"}
        row.pop("numeric_outer_area", None)
    return row


@contextmanager
def integer_scale(scale):
    """Synchronous validation only: integer backend uses a module scale global."""
    old = integer_motion_area.SCALE
    integer_motion_area.SCALE = scale
    try:
        yield
    finally:
        integer_motion_area.SCALE = old


def atomic_update(out: Path, row: dict):
    """Only update a path exclusively created for this invocation."""
    temp = out.with_name(out.name + f".tmp.{os.getpid()}")
    try:
        with temp.open("x") as stream:
            json.dump(row, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, out)
    finally:
        temp.unlink(missing_ok=True)


def create_output(out: Path, row: dict):
    """Publish a complete initial checkpoint without replacing an existing path."""
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_name(out.name + f".init.{os.getpid()}")
    try:
        with temp.open("x") as stream:
            json.dump(row, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, out)  # exclusive, atomic appearance on the same filesystem
    finally:
        temp.unlink(missing_ok=True)


def preflight(families, seed: int, out: Path, *, max_wall_s=60):
    row = {"mode": "preflight", "seed": seed, "random_calls_per_family": 10,
           "limitation": integer_motion_area.LIMITATION,
           "excluded_nonoptimized_baselines": list(EXCLUDED_BASELINES),
           "families": [], "status": "running"}
    create_output(out, row)
    try:
        for family in families:
            row["families"].append({**family.describe(), "calls": []})
            atomic_update(out, row)
            rng = np.random.default_rng(seed)  # independent, repeatable calls per family
            calls = []
            for _ in range(10):
                x = np.array([rng.uniform(lo, hi) for lo, hi in family.bounds])
                start = time.process_time()
                result = score(family, x, max_wall_s=max_wall_s)
                calls.append({"cpu_s": time.process_time() - start,
                              "status": result["status"],
                              "numeric_outer_area": result.get("numeric_outer_area"),
                              "error": result.get("error", result.get("resource_limited")),
                              "backend_version": result.get("backend_version")})
                row["families"][-1]["calls"] = calls
                atomic_update(out, row)
            timings = [c["cpu_s"] for c in calls]
            row["families"][-1].update(cpu_median_s=statistics.median(timings),
                cpu_p95_s=float(np.percentile(timings, 95)),
                failure_count=sum(c["status"] != "ok" for c in calls),
                estimated_population_cpu_s=family.population_evals * statistics.median(timings))
            atomic_update(out, row)
        row["status"] = "complete"
    except BaseException as exc:
        row.update(status="aborted", abort_reason=f"{type(exc).__name__}: {exc}")
        atomic_update(out, row)
        raise
    atomic_update(out, row)
    return row


def validate(family: Family, params, *, max_wall_s=120, max_polygons=100000):
    start = time.process_time()
    raw = []
    for step in VALIDATION_STEPS:
        for scale in VALIDATION_SCALES:
            result = score(family, params, step_fraction=step, scale=scale,
                           max_wall_s=max_wall_s, max_polygons=max_polygons)
            raw.append({"step_fraction": step, "scale": scale, **result})
    areas = [r["numeric_outer_area"] for r in raw if r["status"] == "ok"]
    quality = (len(areas) == 4 and
               (max(areas) - min(areas)) / max(areas) <= .005)
    row = {"status": "ok" if quality else "quality_limited", "raw": raw,
           "relative_tolerance": .005, "validation_cpu_s": time.process_time() - start}
    if quality:
        row["numeric_outer_area_range"] = [min(areas), max(areas)]
        row["relative_discrepancy"] = (max(areas) - min(areas)) / max(areas)
    return row


def attach_best_validated_so_far(checkpoints: list[dict]):
    """Do not let a later coarse-objective improvement worsen known quality."""
    cumulative = None
    for item in checkpoints:
        validation = item.get("validation", {})
        if validation.get("status") == "ok":
            candidate_upper = max(validation["numeric_outer_area_range"])
            if cumulative is None or candidate_upper < cumulative["numeric_upper"]:
                cumulative = {"numeric_upper": candidate_upper,
                              "first_budget_cpu_s": item["budget_cpu_s"],
                              "params": item["best_params"]}
        item["best_validated_so_far"] = dict(cumulative) if cumulative else None


def run(family: Family, seed: int, budgets: list[float], out: Path, *,
        max_wall_s=60, validation_wall_s=120, max_polygons=100000):
    if (not budgets or any(not math.isfinite(b) or b <= 0 for b in budgets)
            or sorted(set(budgets)) != budgets):
        raise ValueError("budgets must be positive, unique and strictly increasing")
    row = {"mode": "run", **family.describe(), "seed": seed,
           "limitation": integer_motion_area.LIMITATION,
           "budgets_cpu_s": budgets, "max_objective_wall_s": max_wall_s,
           "max_validation_wall_s": validation_wall_s, "max_polygons": max_polygons,
           "de": {"popsize": 5, "workers": 1, "polish": False,
                  "updating": "immediate", "tol": 0, "maxiter": 100000},
           "status": "running", "search_started": False, "calls": 0,
           "valid_calls": 0, "failed_calls": [], "failed_count": 0,
           "failed_log_dropped": 0, "eval_log": [], "eval_log_dropped": 0,
           "checkpoints": [], "best_params": None, "best_search_area": None,
           "discovery_cpu_s": 0., "validation_cpu_s": 0.,
           "excluded_nonoptimized_baselines": list(EXCLUDED_BASELINES),
           "aggregate_ranking_authorized": False,
           "external_timeout_note": "Native pyclipper union is not preemptible; run with an external wall timeout. CPU may overshoot a budget by one evaluation. SIGINT/TERM marks aborted when Python regains control; SIGKILL leaves status running, which must not be ranked or resumed."}
    create_output(out, row)
    start_cpu, start_wall = time.process_time(), time.monotonic()
    best = None
    pending = list(budgets)

    def checkpoint(before, elapsed):
        while pending and elapsed >= pending[0]:
            budget = pending.pop(0)
            row["checkpoints"].append({"budget_cpu_s": budget, **before,
                "observed_cpu_s": elapsed,
                "observed_wall_s": time.monotonic() - start_wall,
                "boundary_note": "an evaluation crossing this CPU checkpoint is excluded",
                "status": "pending_validation" if before["best_params"] is not None
                          and before["calls"] > family.population_evals else "unranked"})

    def snapshot():
        return {"calls": row["calls"], "valid_calls": row["valid_calls"],
                "search_started": row["search_started"],
                "best_params": row["best_params"],
                "best_search_area": row["best_search_area"]}

    def objective(x):
        nonlocal best
        elapsed = time.process_time() - start_cpu
        checkpoint(snapshot(), elapsed)
        if elapsed >= budgets[-1]:
            atomic_update(out, row)
            raise BudgetExpired()
        before = snapshot()
        result = score(family, x, max_wall_s=max_wall_s, max_polygons=max_polygons)
        row["calls"] += 1
        if result["status"] == "ok":
            row["valid_calls"] += 1
            value = float(result["numeric_outer_area"])
            if best is None or value < best:
                best = value
                row["best_search_area"] = value
                row["best_params"] = np.asarray(x, dtype=float).tolist()
        else:
            value = PENALTY
            row["failed_count"] += 1
            row["failed_calls"].append({"call": row["calls"], "status": result["status"],
                "detail": result.get("error", result.get("resource_limited"))})
            if len(row["failed_calls"]) > MAX_TRACE_ROWS:
                row["failed_calls"].pop(0)
                row["failed_log_dropped"] += 1
        row["search_started"] = row["calls"] > family.population_evals
        elapsed = time.process_time() - start_cpu
        checkpoint(before, elapsed)  # crossing evaluation cannot count at earlier cutoff
        row["discovery_cpu_s"] = elapsed
        row["discovery_wall_s"] = time.monotonic() - start_wall
        row["eval_log"].append({"call": row["calls"], "cpu_s": elapsed,
            "status": result["status"], "area": result.get("numeric_outer_area"),
            "objective_value": value, "best_search_area": row["best_search_area"]})
        if len(row["eval_log"]) > MAX_TRACE_ROWS:
            row["eval_log"].pop(0)
            row["eval_log_dropped"] += 1
        if row["calls"] % 5 == 0 or (value != PENALTY and value == best):
            atomic_update(out, row)
        return value

    try:
        try:
            differential_evolution(objective, family.bounds, rng=np.random.default_rng(seed),
                popsize=5, workers=1, polish=False, updating="immediate", tol=0,
                maxiter=100000)
        except BudgetExpired:
            pass
        row["discovery_cpu_s"] = time.process_time() - start_cpu
        row["discovery_wall_s"] = time.monotonic() - start_wall
        checkpoint(snapshot(), row["discovery_cpu_s"])
        for budget in pending:
            row["checkpoints"].append({"budget_cpu_s": budget, **snapshot(),
                "observed_cpu_s": row["discovery_cpu_s"],
                "observed_wall_s": row["discovery_wall_s"],
                "status": "unranked", "reason": "optimizer_terminated_before_budget"})
        atomic_update(out, row)
        validated = {}
        for item in row["checkpoints"]:
            if item["status"] != "pending_validation":
                continue
            params = item["best_params"]
            key = tuple(params)
            if key not in validated:
                validated[key] = validate(family, params, max_wall_s=validation_wall_s,
                                          max_polygons=max_polygons)
                row["validation_cpu_s"] += validated[key]["validation_cpu_s"]
            item["validation"] = validated[key]
            item["status"] = validated[key]["status"]
            atomic_update(out, row)
        # The raw current checkpoint may validate worse than an earlier
        # coarse-objective incumbent; retain both observations separately.
        attach_best_validated_so_far(row["checkpoints"])
        row["status"] = ("complete" if all(c["status"] == "ok" for c in row["checkpoints"])
                         else "quality_limited")
    except BaseException as exc:
        row.update(status="aborted", abort_reason=f"{type(exc).__name__}: {exc}")
        atomic_update(out, row)
        raise
    atomic_update(out, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--family", choices=FAMILIES, help="required for --run")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eps", type=float, default=.005)
    parser.add_argument("--smoke-k", type=int, help="non-ranking small K; never use for formal comparison")
    parser.add_argument("--budgets", nargs="+", type=float, help="predeclared CPU checkpoints, required for --run")
    parser.add_argument("--out", type=Path, required=True, help="exclusive new output; never overwrite or resume")
    parser.add_argument("--resume", action="store_true", help="unsupported: DE RNG/population cannot be reconstructed")
    parser.add_argument("--max-wall-s", type=float, default=60)
    parser.add_argument("--validation-wall-s", type=float, default=120)
    parser.add_argument("--max-polygons", type=int, default=100000)
    args = parser.parse_args()
    if args.resume:
        parser.error("exact DE resume is unsupported; an existing output is read-only; start a new seed/output")
    if (not math.isfinite(args.max_wall_s) or args.max_wall_s <= 0 or
            not math.isfinite(args.validation_wall_s) or args.validation_wall_s <= 0 or
            args.max_polygons < 1):
        parser.error("work limits must be positive and finite")
    if args.run and (args.family is None or args.budgets is None):
        parser.error("--run requires --family and --budgets chosen after preflight")
    if args.preflight and (args.family is not None or args.budgets is not None):
        parser.error("--preflight evaluates all four families without budgets")
    # The caller sets process affinity/niceness externally; reject accidental shared-core runs.
    if len(os.sched_getaffinity(0)) != 1 or os.getpriority(os.PRIO_PROCESS, 0) < 10:
        parser.error("run externally on one core with nice -n 10 and a wall timeout")
    def stop_on_term(signum, frame):
        raise KeyboardInterrupt("SIGTERM requested; output is not resumable")

    signal.signal(signal.SIGTERM, stop_on_term)
    try:
        families = [Family(name, args.eps, args.smoke_k) for name in
                    (FAMILIES if args.preflight else (args.family,))]
        if args.preflight:
            result = preflight(families, args.seed, args.out, max_wall_s=args.max_wall_s)
        else:
            result = run(families[0], args.seed, args.budgets, args.out,
                         max_wall_s=args.max_wall_s,
                         validation_wall_s=args.validation_wall_s,
                         max_polygons=args.max_polygons)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"status={result['status']} output={args.out}", flush=True)


if __name__ == "__main__":
    main()
