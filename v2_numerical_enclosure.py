"""Floating-point numerical enclosures of saved v2 linear-keyframe motions.

Endpoint poses give a sampled numerical lower area. On each angular step,
the hull of endpoint rectangles buffered by the maximum corner sagitta covers
the linear-center/linear-angle interpolation in exact geometry. The polygonal
buffer radius has a secant correction. GEOS union, buffer, and precision-grid
rounding are floating point: neither reported area is a rigorous certificate.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from shapely import set_precision, union, union_all
from shapely.affinity import scale

from sweeper_v2 import needle_polygon


DEFAULT_OUT = Path("results/v2_numerical_enclosures.json")
QUAD_SEGS = 16


def decode_keyframes(keyframes, eps: float) -> tuple[np.ndarray, np.ndarray]:
    """Decode saved rows [theta, zx, zy] without the optimizer's clipping."""
    if not math.isfinite(eps) or not 0 < eps <= 1:
        raise ValueError("eps must be finite and in (0, 1]")
    try:
        rows = np.asarray(keyframes, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("keyframes must be numeric [theta, zx, zy] rows") from exc
    if rows.ndim != 2 or rows.shape[1] != 3 or rows.shape[0] < 2:
        raise ValueError("keyframes must be (K+1, 3) [theta, zx, zy] rows")
    if not np.all(np.isfinite(rows)):
        raise ValueError("keyframes must be finite")
    theta = rows[:, 0]
    if (theta[0] != 0 or theta[-1] != math.pi / 2
            or np.any(np.diff(theta) < 0) or np.any(theta < 0)
            or np.any(theta > math.pi / 2)):
        raise ValueError("theta must be monotone from 0 to pi/2")
    sigma = max(1.0, 8 * eps)
    with np.errstate(over="ignore", invalid="ignore"):
        centers = sigma * np.expm1(rows[:, 1:])
    if not np.all(np.isfinite(centers)):
        raise ValueError("decoded centers must be finite")
    return theta, centers


def mirror_pose(theta: float, center: np.ndarray, axis_x: float) -> tuple[float, float, float]:
    """Time-reversed second-half pose reflected about the final center's x-axis."""
    return math.pi - theta, 2 * axis_x - center[0], center[1]


def segment_polygons(theta0: float, theta1: float, center0: np.ndarray,
                     center1: np.ndarray, eps: float, n_sub: int) -> tuple[list, list]:
    """Return sampled rectangles and angular-step hulls for one linear segment.

    A corner's position is center(t) + R(theta(t))*corner. Since center(t)
    interpolates linearly, compare its offset with the *same-t* chord between
    corner offsets: the maximum deviation on an arc of angle h <= pi/2 is
    r*(1-cos(h/2)). The convex hull contains these same-t endpoint points.
    For h=0 the endpoint hull is the entire translation sweep, not a single
    orientation sample. A 4*QUAD_SEGS-gon buffer gets a sec(pi/(4*QUAD_SEGS))
    expansion to compensate for circular chord gaps in exact arithmetic.
    """
    lower = []
    upper = []
    radius = math.hypot(0.5, eps / 2)
    for j in range(n_sub + 1):
        t = j / n_sub
        theta = theta0 + t * (theta1 - theta0)
        center = center0 + t * (center1 - center0)
        rect = needle_polygon(theta, *center, eps)
        if not rect.is_valid or not math.isfinite(rect.area) or abs(rect.area - eps) > eps * 1e-5:
            raise ValueError("pose polygon is degenerate at this coordinate scale")
        lower.append(rect)
        if j:
            hull = lower[-2].union(rect).convex_hull
            h = (theta1 - theta0) / n_sub
            sagitta = radius * 2 * math.sin(h / 4) ** 2
            if sagitta:
                hull = hull.buffer(sagitta / math.cos(math.pi / (4 * QUAD_SEGS)),
                                   quad_segs=QUAD_SEGS)
            upper.append(hull)
    return lower, upper


def numerical_v2_enclosure(keyframes, eps: float, n_sub: int = 80) -> dict:
    """Enclose the full continuously joined halfturn, numerically (not strictly)."""
    if isinstance(n_sub, bool) or not isinstance(n_sub, int) or n_sub < 1:
        raise ValueError("n_sub must be a positive integer")
    theta, centers = decode_keyframes(keyframes, eps)
    lower_polys = []
    upper_polys = []
    for i in range(len(theta) - 1):
        sampled, hulls = segment_polygons(theta[i], theta[i + 1], centers[i],
                                          centers[i + 1], eps, n_sub)
        lower_polys.extend(sampled)
        upper_polys.extend(hulls)
    grid = min(1e-10, eps * 1e-8)
    axis_x = float(centers[-1, 0])
    # Snap operands before their union AND snap the reflected operand before
    # the final union. This reduces overlay instability, not roundoff error.
    lower = union_all([set_precision(poly, grid) for poly in lower_polys], grid_size=grid)
    upper = union_all([set_precision(poly, grid) for poly in upper_polys], grid_size=grid)
    reflected_lower = set_precision(scale(lower, xfact=-1, origin=(axis_x, 0)), grid)
    reflected_upper = set_precision(scale(upper, xfact=-1, origin=(axis_x, 0)), grid)
    lo = float(union(lower, reflected_lower, grid_size=grid).area)
    hi = float(union(upper, reflected_upper, grid_size=grid).area)
    return {"numerical_lower": lo, "numerical_upper": hi,
            "mirror_axis_x": axis_x, "grid": grid, "n_sub": n_sub}


def evaluate_source(path: Path, n_sub: int, best_new: bool = False) -> list[dict]:
    records = json.loads(path.read_text())
    if not isinstance(records, list) or not records:
        raise ValueError(f"{path}: expected nonempty saved record list")
    evaluated = []
    for index, record in enumerate(records):
        eps, K = record["eps"], record["K"]
        if isinstance(K, bool) or not isinstance(K, int) or K < 1:
            raise ValueError(f"{path}[{index}]: invalid K")
        if len(record["keyframes"]) != K + 1:
            raise ValueError(f"{path}[{index}]: K does not match keyframes")
        if not math.isfinite(record["area"]):
            raise ValueError(f"{path}[{index}]: original sampled area must be finite")
        if record.get("model") not in ("v2-logspace-growing", "v2-logspace"):
            raise ValueError(f"{path}[{index}]: not a saved v2 linear-keyframe motion")
        enclosure = numerical_v2_enclosure(record["keyframes"], eps, n_sub)
        evaluated.append({"source": str(path), "source_record_index": index,
                          "seed": record["seed"], "eps": eps, "K": K,
                          "model": record["model"],
                          "original_sampled_area": record["area"], **enclosure,
                          "original_area_model": "sampled poses mirrored about global x=0",
                          "geometry_revision": "linear-keyframe-fixed-grid-v1",
                          "motion": "linear centers and theta; reflected reverse second half",
                          "limitation": "GEOS floating-point area, buffer and overlay; not a strict certificate"})
    if best_new:
        return [min(evaluated, key=lambda row: row["numerical_upper"])]
    return evaluated


def archived_sources(directory: Path) -> list[Path]:
    """Discover original v2 records, excluding generated enclosure artifacts."""
    sources = []
    for path in sorted(directory.glob("v2_*.json")):
        try:
            rows = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if (isinstance(rows, list) and rows and isinstance(rows[0], dict)
                and "keyframes" in rows[0] and rows[0].get("model") in
                ("v2-logspace-growing", "v2-logspace")):
            sources.append(path)
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path,
                        help="saved v2 JSON files (default: results/v2_*.json)")
    parser.add_argument("--best-new", action="store_true",
                        help="evaluate all records, then retain the lowest new numerical upper per source")
    parser.add_argument("--n-sub", type=int, default=80, help="angular steps per keyframe segment")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    sources = args.sources or archived_sources(Path("results"))
    if not sources:
        parser.error("no saved v2 sources found")
    if args.out.resolve() in {source.resolve() for source in sources}:
        parser.error("output must differ from each saved source")
    evaluated = [row for source in sources for row in evaluate_source(source, args.n_sub, args.best_new)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evaluated, indent=2) + "\n")
    for row in evaluated:
        print(f"{row['source']} seed={row['seed']}: "
              f"original={row['original_sampled_area']:.9f}, "
              f"numerical=[{row['numerical_lower']:.9f}, {row['numerical_upper']:.9f}]")


if __name__ == "__main__":
    main()
