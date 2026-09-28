"""Non-certified sampled area diagnostics for the finite Keich demo motion.

This is deliberately separate from rational_pivot_certificate.py. Long
excursions can make GEOS polygon overlay fail; a failure is saved, never
silently replaced by a low area value.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import time

import numpy as np
import shapely
from shapely import set_precision, union_all
from shapely.errors import GEOSException

from keich_motion import generate
from pivot_slide import needle_polygon, slide_strip


def probe(n: int, poses_per_radian: int) -> dict:
    eps = 2.0 ** (-4 * n)
    motion = generate(Fraction(1, 2 ** (4 * n)))
    grid = min(1e-10, eps * 1e-8)
    polygons = []
    outer_polygons = []
    begin = time.monotonic()
    for primitive in motion['primitives']:
        first, last = primitive['start'], primitive['end']
        center = np.asarray(first['center'])
        if primitive['kind'] == 'slide':
            strip = slide_strip(first['theta'], center, np.asarray(last['center']), eps)
            polygons.append(strip)
            outer_polygons.append(strip)
        else:
            count = max(3, math.ceil(abs(last['theta'] - first['theta']) * poses_per_radian))
            theta_grid = np.linspace(first['theta'], last['theta'], count)
            poses = [needle_polygon(theta, *center, eps) for theta in theta_grid]
            polygons.extend(poses)
            radius = math.hypot(.5, eps / 2)
            for a, b, left, right in zip(poses, poses[1:], theta_grid, theta_grid[1:]):
                sagitta = radius * 2 * math.sin(abs(right - left) / 4) ** 2
                outer_polygons.append(a.union(b).convex_hull.buffer(
                    sagitta / math.cos(math.pi / 64), quad_segs=16))
    row = {'n': n, 'eps': eps, 'K_stations': len(motion['stations']),
           'primitive_count': len(motion['primitives']), 'polygon_count': len(polygons),
           'poses_per_radian': poses_per_radian, 'grid': grid,
           'shapely_version': shapely.__version__,
           'fixed_center_reference': math.pi * (1 + eps * eps) / 4,
           'limitation': 'sampled floating-point polygon area; not a rigorous upper or lower bound'}
    try:
        snapped = [set_precision(poly, grid) for poly in polygons]
        row.update(status='ok', sampled_area=float(union_all(snapped, grid_size=grid).area))
        outer = [set_precision(poly, grid) for poly in outer_polygons]
        row['numerical_outer_area'] = float(union_all(outer, grid_size=grid).area)
    except (GEOSException, ValueError, OverflowError) as exc:
        row.update(status='geometry_failed', error=f'{type(exc).__name__}: {exc}')
    row['wall_s'] = time.monotonic() - begin
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--n-min', type=int, default=1)
    parser.add_argument('--n-max', type=int, default=5)
    parser.add_argument('--poses-per-radian', type=int, default=128)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.n_min <= args.n_max <= 8 or args.poses_per_radian < 1:
        parser.error('require 1 <= n-min <= n-max <= 8 and positive density')
    rows = []
    for n in range(args.n_min, args.n_max + 1):
        row = probe(n, args.poses_per_radian)
        rows.append(row)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + '\n')
        print(f'n={n} status={row["status"]} sampled={row.get("sampled_area")} '
              f'wall={row["wall_s"]:.2f}s', flush=True)


if __name__ == '__main__':
    main()
