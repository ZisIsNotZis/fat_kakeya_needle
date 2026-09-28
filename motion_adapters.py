"""Continuous saved pivot-slide and repaired-v2 motions for numeric integer scoring.

Integer clipping does not certify the floating poses, trigonometry or areas.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from integer_motion_area import LIMITATION, evaluate
from pivot_slide import PivotSlideModel
from smooth_pivot import SmoothProfileModel
from v2_numerical_enclosure import decode_keyframes


def _pose(center, theta):
    x, y = map(float, center)
    theta = float(theta)
    if not all(map(math.isfinite, (x, y, theta))):
        raise ValueError("nonfinite pose")
    return {"center": [x, y], "theta": theta}


def _join(actual, nominal, *, context):
    """Use the existing endpoint; reject more than floating recurrence drift."""
    a, b = actual["center"], nominal
    tolerance = 64 * (math.ulp(a[0]) + math.ulp(a[1]) + math.ulp(float(b[0]))
                      + math.ulp(float(b[1])) + math.ulp(1.0))
    if not all(math.isfinite(float(x)) for x in b) or math.hypot(a[0]-b[0], a[1]-b[1]) > tolerance:
        raise ValueError(f"discontinuous {context}")


def _reflect(pose, axis_x):
    x, y = pose["center"]
    return _pose((2 * axis_x - x, y), math.pi - pose["theta"])


def _full_halfturn(first_half):
    if not first_half:
        raise ValueError("empty halfturn")
    axis_x = first_half[-1]["end"]["center"][0]
    reversed_half = []
    previous = first_half[-1]["end"]
    for original in reversed(first_half):
        end = _reflect(original["start"], axis_x)
        kind = original["kind"]
        entry = {"kind": kind, "start": previous, "end": end}
        if kind == "slide":
            entry["length"] = -original["length"]
        else:
            entry["angle"] = original["angle"]
            if kind == "pivot_rotate":
                px, py = original["pivot"]
                entry.update(pivot=[2 * axis_x - px, py], fraction=original["fraction"])
        reversed_half.append(entry)
        previous = end
    return first_half + reversed_half


def pivot_primitives(model: PivotSlideModel, params) -> list[dict]:
    """Decode P,f,beta; preserve each whole signed slide and both continuous arcs."""
    values = np.asarray(params, dtype=float)
    if values.shape != (2 * model.K,) or not np.all(np.isfinite(values)):
        raise ValueError("pivot params must be finite and have length 2*K")
    pivots, centers, fractions, slides = model.centers_and_pivots(values)
    if not all(np.all(np.isfinite(v)) for v in (pivots, centers, fractions, slides)):
        raise ValueError("nonfinite decoded pivot motion")
    current = _pose(centers[0], model.theta[0])
    first = []
    for i in range(model.K):
        angle0, angle1 = map(float, model.theta[i:i+2])
        f = float(fractions[i])
        nominal_start = pivots[i] - .5 * f * model.u[i]
        _join(current, nominal_start, context=f"pivot {i} start")
        # Anchor the decoded pivot to the preceding exact primitive endpoint.
        # The shift must be only floating recurrence drift, never a teleport.
        pivot = [current["center"][j] + .5 * f * float(model.u[i, j]) for j in range(2)]
        end_center = [pivot[j] - .5 * f * float(model.u[i+1, j]) for j in range(2)]
        end = _pose(end_center, angle1)
        if i == model.K - 1:
            _join(end, centers[-1], context="final pivot endpoint")
        first.append({"kind": "pivot_rotate", "pivot": pivot, "fraction": f,
                      "angle": angle1-angle0, "start": current, "end": end})
        current = end
        if i < model.K - 1:
            beta = float(slides[i])
            end = _pose((current["center"][0] + beta * float(model.u[i+1, 0]),
                         current["center"][1] + beta * float(model.u[i+1, 1])), angle1)
            _join(end, centers[i+1], context=f"slide {i} endpoint")
            first.append({"kind": "slide", "length": beta, "start": current, "end": end})
            current = end
    return _full_halfturn(first)


def v2_primitives(keyframes, eps: float) -> list[dict]:
    """Decode archived logspace keyframes; linearly interpolate world centers."""
    theta, centers = decode_keyframes(keyframes, eps)
    current = _pose(centers[0], theta[0])
    first = []
    for i in range(len(theta)-1):
        end = _pose(centers[i+1], theta[i+1])
        first.append({"kind": "linear_pose", "start": current, "end": end,
                      "angle": end["theta"] - current["theta"]})
        current = end
    return _full_halfturn(first)


def evaluate_saved(source: Path, index: int, *, max_wall_s: float = 30,
                   max_polygons: int = 100000, step_fraction: float = .0001) -> dict:
    """Evaluate one archived record; malformed input and geometry fail typed."""
    start_wall, start_cpu = time.monotonic(), time.process_time()
    row = {"status": "error", "input_source": str(source), "source_record_index": index,
           "limitation": LIMITATION}
    try:
        records = json.loads(source.read_text())
        if (isinstance(index, bool) or not isinstance(index, int) or index < 0
                or not isinstance(records, list) or index >= len(records)):
            raise ValueError("invalid saved record index")
        record = records[index]
        eps, K = float(record["eps"]), record["K"]
        if not math.isfinite(eps) or not 0 < eps <= 1:
            raise ValueError("invalid eps")
        if isinstance(K, bool) or not isinstance(K, int) or K < 1:
            raise ValueError("invalid K")
        model = record.get("model")
        row.update(eps=eps, model=model, K=K, seed=record.get("seed"))
        if model == "pivot-slide":
            primitives = pivot_primitives(PivotSlideModel(eps, K), record["params"])
        elif model in ("v2-logspace-growing", "v2-logspace"):
            if len(record["keyframes"]) != K+1:
                raise ValueError("K disagrees with keyframes")
            primitives = v2_primitives(record["keyframes"], eps)
        elif model == "pivot-slide-smooth" or (model is None and
                all(field in record for field in ("Nf", "Nb", "best_params")) and
                "params" not in record and "keyframes" not in record):
            params = record["best_params"]
            if "Nf" in record or "Nb" in record:
                nf, nb = record["Nf"], record["Nb"]
                layout = "explicit-control-counts"
            else:
                if not isinstance(params, list) or (len(params)-1) % 2:
                    raise ValueError("cannot infer equal smooth controls")
                nf = nb = (len(params)-1)//2
                layout = "equal-count-inferred-from-archive-length"
            if (type(nf) is not int or type(nb) is not int or nf < 2 or nb < 2
                    or not isinstance(params, list) or len(params) != 1+nf+nb):
                raise ValueError("invalid smooth control layout")
            smooth = SmoothProfileModel(K, eps, nf, nb)
            primitives = pivot_primitives(smooth.base,
                                          smooth.to_full_params(np.asarray(params, dtype=float)))
            row.update(model="pivot-slide-smooth", Nf=nf, Nb=nb,
                       control_layout=layout)
        else:
            raise ValueError("unsupported saved motion model")
        row.update(evaluate(primitives, eps, max_wall_s=max_wall_s,
                            max_polygons=max_polygons, step_fraction=step_fraction))
        row["mirror_axis_x"] = primitives[len(primitives)//2-1]["end"]["center"][0]
    except (OSError, ValueError, KeyError, TypeError, OverflowError, IndexError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["wall_s"] = time.monotonic() - start_wall
    row["cpu_s"] = time.process_time() - start_cpu
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON file, never overwritten")
    parser.add_argument("--max-wall-s", type=float, default=30)
    parser.add_argument("--max-polygons", type=int, default=100000)
    parser.add_argument("--step-fraction", type=float, default=.0001)
    args = parser.parse_args()
    row = evaluate_saved(args.source, args.index, max_wall_s=args.max_wall_s,
                         max_polygons=args.max_polygons, step_fraction=args.step_fraction)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(row, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"status={row['status']} area={row.get('numeric_outer_area')} output={args.out}")


if __name__ == "__main__":
    main()
