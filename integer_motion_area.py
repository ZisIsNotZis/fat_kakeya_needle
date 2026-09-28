"""Non-certified integer-polygon numerical area for Keich slide/center_rotate motions.

Requires optional pyclipper==1.4.0 (Clipper 6.4.2). Integer clipping is exact
for its integer inputs, NOT for the floating-point poses or trigonometry that
produce those inputs. No failed evaluation is replaced by a sampled area.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import time

from keich_motion import generate


SCALE = 1 << 40
# Clipper 6.4.2's hiRange; the stricter 2^53 scaled-coordinate gate is also
# required, even though Python ints themselves have arbitrary precision.
HI_RANGE = (1 << 62) - 1
MAX_SCALED = 1 << 53
LIMITATION = ("Floating poses, trigonometry and heuristic roundoff padding are "
              "not rigorously outward certified; numeric_outer_area is a "
              "numerical outer approximation, not a strict area bound.")


class ResourceLimited(Exception):
    """The requested geometry exceeds the explicitly bounded work budget."""


def _finite(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("nonfinite pose or geometry coordinate")
    return value


def _grid_bound(value: float, upper: bool) -> int:
    """Exact floor/ceil of the binary float times SCALE, without float scaling."""
    value = _finite(value)
    numerator, denominator = value.as_integer_ratio()
    scaled = numerator * SCALE
    result = -(-scaled // denominator) if upper else scaled // denominator
    if abs(value) >= MAX_SCALED / SCALE or abs(result) >= MAX_SCALED:
        raise ValueError("coordinate times scale reaches 2^53")
    if abs(result) > HI_RANGE:
        raise ValueError("coordinate exceeds Clipper hiRange")
    return result


def _box(x: float, y: float, pad: float) -> list[tuple[int, int]]:
    pad = _finite(pad)
    if pad < 0:
        raise ValueError("negative padding")
    x, y = _finite(x), _finite(y)
    lo_x, hi_x = _grid_bound(x - pad, False), _grid_bound(x + pad, True)
    lo_y, hi_y = _grid_bound(y - pad, False), _grid_bound(y + pad, True)
    return [(lo_x, lo_y), (lo_x, hi_y), (hi_x, lo_y), (hi_x, hi_y)]


def _hull(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Monotone integer convex hull, retaining the true extrema of all boxes."""
    ordered = sorted(set(points))
    if len(ordered) < 3:
        raise ValueError("degenerate integer polygon")

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower, upper = [], []
    for part, sequence in ((lower, ordered), (upper, reversed(ordered))):
        for p in sequence:
            while len(part) >= 2 and cross(part[-2], part[-1], p) <= 0:
                part.pop()
            part.append(p)
    return lower[:-1] + upper[:-1]


def _pose(pose: dict) -> tuple[float, float, float]:
    x, y = pose["center"]
    return _finite(x), _finite(y), _finite(pose["theta"])


def _corners(x: float, y: float, theta: float, eps: float):
    c, s = math.cos(theta), math.sin(theta)
    for u in (-0.5, 0.5):
        for v in (-eps / 2, eps / 2):
            yield x + c * u - s * v, y + s * u + c * v


def _roundoff_pad(x: float, y: float, theta: float, eps: float) -> float:
    """Heuristic float pad (not a proven error bound for libm or upstream poses).

    Includes cancellation in distant centers and angular error. 64 ulps of
    the component magnitudes dominate ordinary double arithmetic roundoff;
    do not confuse this with a certified directed rounding of sin/cos.
    """
    r = math.hypot(0.5, eps / 2)
    return 64 * (math.ulp(x) + math.ulp(y) + math.ulp(theta) * r
                 + math.ulp(r) + math.ulp(1.0))


def primitive_paths(primitive: dict, eps: float, max_step: float, *,
                    max_paths: int = 100000, deadline: float = math.inf
                    ) -> list[list[tuple[int, int]]]:
    """Conservatively model linear slide or fixed-center rotation numerically.

    Every path is a monotone integer hull of endpoint rectangle corner boxes;
    rotation intervals also get an L-infinity sagitta pad. For each corner
    trajectory the deviation from its chord is <= r*2*sin(step/4)^2.
    """
    eps, max_step = _finite(eps), _finite(max_step)
    if eps <= 0 or max_step <= 0:
        raise ValueError("eps and max_step must be positive")
    x0, y0, a0 = _pose(primitive["start"])
    x1, y1, a1 = _pose(primitive["end"])
    kind = primitive["kind"]
    if kind == "slide":
        if max_paths < 1:
            raise ResourceLimited("polygon budget exhausted")
        if a0 != a1:
            raise ValueError("slide changes angle")
        dx, dy = x1 - x0, y1 - y0
        length = _finite(primitive['length'])
        axial = dx * math.cos(a0) + dy * math.sin(a0)
        length_tol = 64 * (math.ulp(x0) + math.ulp(y0) + math.ulp(x1)
                           + math.ulp(y1) + math.ulp(length)
                           + abs(length) * math.ulp(a0))
        if abs(axial - length) > length_tol:
            raise ValueError('slide length disagrees with endpoint displacement')
        drift = abs(dx * math.sin(a0) - dy * math.cos(a0))
        tolerance = 64 * (math.ulp(x0) + math.ulp(y0) + math.ulp(x1)
                          + math.ulp(y1) + math.hypot(dx, dy) * math.ulp(a0))
        if drift > tolerance:
            raise ValueError("slide is not axial")
        pad = max(_roundoff_pad(x, y, a0, eps) for x, y in ((x0, y0), (x1, y1)))
        points = [p for x, y in ((x0, y0), (x1, y1))
                  for cx, cy in _corners(x, y, a0, eps) for p in _box(cx, cy, pad)]
        return [_hull(points)]
    if kind != "center_rotate":
        raise ValueError(f"unsupported primitive kind: {kind}")
    if (x0, y0) != (x1, y1):
        raise ValueError("center_rotate changes center")
    angle = _finite(primitive['angle'])
    angle_tol = 64 * (math.ulp(a0) + math.ulp(a1) + math.ulp(angle))
    if abs((a1 - a0) - angle) > angle_tol:
        raise ValueError('center_rotate angle disagrees with endpoint orientation')
    # The circular sagitta formula is valid for each short arc, not for an
    # endpoint-coincident complete revolution with zero computed sagitta.
    max_step = min(max_step, math.pi / 2)
    count = max(1, math.ceil(abs(a1 - a0) / max_step))
    if count > min(100000, max_paths):
        raise ResourceLimited("rotation exceeds remaining polygon budget")
    step = (a1 - a0) / count
    radius = math.hypot(0.5, eps / 2)
    sagitta = radius * 2 * math.sin(abs(step) / 4) ** 2
    paths = []
    for i in range(count):
        if i % 64 == 0 and time.monotonic() > deadline:
            raise ResourceLimited("wall budget exhausted during rotation")
        left, right = a0 + i * step, a0 + (i + 1) * step
        pad = sagitta + max(_roundoff_pad(x0, y0, a, eps) for a in (left, right))
        points = [p for angle in (left, right)
                  for cx, cy in _corners(x0, y0, angle, eps)
                  for p in _box(cx, cy, pad)]
        paths.append(_hull(points))
    return paths


def _twice_area(path: list[tuple[int, int]]) -> int:
    return abs(sum(x * path[(i + 1) % len(path)][1] - y * path[(i + 1) % len(path)][0]
                   for i, (x, y) in enumerate(path)))


def union_area(paths: list[list[tuple[int, int]]]) -> float:
    """Union with PolyTree hole signs (including islands nested in holes)."""
    import pyclipper  # optional dependency, only needed during evaluation

    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO,
                            pyclipper.PFT_NONZERO)

    def signed_area(node):
        total = -_twice_area(node.Contour) if node.IsHole else _twice_area(node.Contour)
        return total + sum(signed_area(child) for child in node.Childs)

    twice = sum(signed_area(child) for child in tree.Childs)
    if twice < 0:
        raise ValueError("invalid signed polygon union area")
    return twice / (2 * SCALE * SCALE)


def evaluate(primitives: list[dict], eps: float, *, max_wall_s: float = 100,
             max_polygons: int = 100000, step_fraction: float = 0.1) -> dict:
    """Return typed failure instead of low fallback area; time checked per primitive.

    A single native Clipper union cannot be preempted inside this process;
    callers needing a hard deadline must run the CLI in a timed subprocess.
    """
    start_wall, start_cpu = time.monotonic(), time.process_time()
    safe_step_fraction = (step_fraction if isinstance(step_fraction, (int, float))
                          and math.isfinite(step_fraction) else None)
    row = {"status": "error", "eps": eps, "scale": SCALE,
           "geometry_backend": "pyclipper", "backend_version": None,
           "max_step": None, "step_fraction": safe_step_fraction,
           "polygon_count": 0, "primitive_count": len(primitives),
           "limitation": LIMITATION}
    try:
        import pyclipper
        row["backend_version"] = pyclipper.__version__
        if row["backend_version"] != "1.4.0":
            raise ValueError("requires pyclipper==1.4.0")
        eps, step_fraction = _finite(eps), _finite(step_fraction)
        row["step_fraction"] = step_fraction
        if eps <= 0 or not 0 < step_fraction <= 0.1:
            raise ValueError("eps must be positive and step_fraction in (0, 0.1]")
        if not primitives:
            raise ValueError("motion has no primitives")
        if not math.isfinite(max_wall_s) or max_wall_s <= 0 or max_polygons < 1:
            raise ValueError("invalid work budget")
        radius = math.hypot(0.5, eps / 2)
        # Exact inverse of r*2*sin(step/4)^2 <= step_fraction*eps.
        ratio = min(1.0, step_fraction * eps / (2 * radius))
        max_step = 4 * math.asin(math.sqrt(ratio))
        if max_step == 0:
            raise ResourceLimited("angle step underflow")
        row["max_step"] = max_step
        paths = []
        previous_end = None
        for primitive in primitives:
            if previous_end is not None and _pose(primitive['start']) != previous_end:
                raise ValueError('discontinuous primitive chain')
            if time.monotonic() - start_wall > max_wall_s:
                raise ResourceLimited("wall budget exhausted before polygon union")
            new_paths = primitive_paths(primitive, eps, max_step,
                                        max_paths=max_polygons - len(paths),
                                        deadline=start_wall + max_wall_s)
            paths.extend(new_paths)
            previous_end = _pose(primitive['end'])
            row["polygon_count"] = len(paths)
        if time.monotonic() - start_wall > max_wall_s:
            raise ResourceLimited("wall budget exhausted before polygon union")
        row["numeric_outer_area"] = union_area(paths)
        row["status"] = "ok"
    except ResourceLimited as exc:
        row.update(status="resource_limited", resource_limited=str(exc))
    except Exception as exc:
        # Includes ClipperException from the optional native backend. Never
        # publish a partial or sampled area when a backend operation fails.
        row.update(status="error", error=f"{type(exc).__name__}: {exc}")
    row["wall_s"] = time.monotonic() - start_wall
    row["cpu_s"] = time.process_time() - start_cpu
    return row


def evaluate_keich(n: int, **kwargs) -> dict:
    if n not in (4, 5):
        raise ValueError("this CLI evaluates Keich n=4 or n=5 only")
    eps = Fraction(1, 1 << (4 * n))
    motion = generate(eps)
    row = evaluate(motion["primitives"], float(eps), **kwargs)
    if n == 5 and row["status"] == "ok":
        # Empirical resolution check only, not a certified enclosure test.
        remaining = kwargs.get("max_wall_s", 100) - row["wall_s"]
        if remaining <= 0:
            row.pop("numeric_outer_area")
            row.update(status="resource_limited",
                       resource_limited="wall budget exhausted before resolution check")
            row.update(n=n, input_source="keich_motion.generate",
                       K_stations=len(motion["stations"]))
            return row
        finer = evaluate(motion["primitives"], float(eps),
                         max_wall_s=remaining,
                         max_polygons=kwargs.get("max_polygons", 100000),
                         step_fraction=kwargs.get("step_fraction", 0.1) / 2)
        row["wall_s"] += finer["wall_s"]
        row["cpu_s"] += finer["cpu_s"]
        row["quality_check"] = {"finer_step_fraction": finer["step_fraction"],
                                "finer_max_step": finer["max_step"],
                                "finer_polygon_count": finer["polygon_count"],
                                "finer_status": finer["status"],
                                "relative_tolerance": 0.02}
        if finer["status"] != "ok":
            row.pop("numeric_outer_area")
            row["status"] = finer["status"]
            row[finer["status"]] = finer.get(finer["status"], "finer resolution failed")
        else:
            coarse_area = row["numeric_outer_area"]
            fine_area = finer["numeric_outer_area"]
            discrepancy = abs(coarse_area - fine_area) / max(coarse_area, fine_area)
            row["quality_check"].update(finer_numeric_outer_area=fine_area,
                                        relative_discrepancy=discrepancy)
            if discrepancy > 0.02:
                row.pop("numeric_outer_area")
                row.update(status="quality_limited",
                           quality_limited="two angular resolutions differ by more than 2%")
    row.update(n=n, input_source="keich_motion.generate", K_stations=len(motion["stations"]))
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, choices=(4, 5), required=True)
    parser.add_argument("--out", type=Path, help="new JSON path; never overwritten")
    parser.add_argument("--max-wall-s", type=float, default=100)
    parser.add_argument("--max-polygons", type=int, default=100000)
    parser.add_argument("--step-fraction", type=float, default=0.1)
    args = parser.parse_args()
    out = args.out or Path(f"results/integer_keich_n{args.n}.json")
    row = evaluate_keich(args.n, max_wall_s=args.max_wall_s,
                         max_polygons=args.max_polygons, step_fraction=args.step_fraction)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x") as file:
        json.dump(row, file, indent=2, allow_nan=False)
        file.write("\n")
    print(f"n={args.n} status={row['status']} area={row.get('numeric_outer_area')} "
          f"wall={row['wall_s']:.2f}s output={out}", flush=True)


if __name__ == "__main__":
    main()
