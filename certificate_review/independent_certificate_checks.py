"""Read-only independent certificate checks. Run with Python from any cwd."""
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from rational_pivot_certificate import D, F, cell_intervals, hull, polygons, source_record, trig_grid
from test_rational_pivot_certificate import brute_intersects


def inside(poly, point):
    return all((b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]) >= 0
               for a, b in zip(poly, poly[1:]+poly[:1]))


def inner_rows(poly, q):
    """Closed cells wholly inside one CCW convex polygon, using integers only."""
    for row in range(min(y for x, y in poly)*q//D, max(y for x, y in poly)*q//D+1):
        lo = min(x for x, y in poly)*q//D
        hi = max(x for x, y in poly)*q//D
        for a, b in zip(poly, poly[1:]+poly[:1]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            # Minimum of the edge cross product over the four cell corners,
            # multiplied by q: A*column + B >= 0.
            A = -dy*D
            B = dx*row*D + q*(dy*a[0]-dx*a[1]) + min(0, -dy*D) + min(0, dx*D)
            if A > 0:
                lo = max(lo, -(B//A))
            elif A < 0:
                hi = min(hi, B//(-A))
            elif B < 0:
                hi = lo-1
                break
        if hi >= lo:
            yield row, (lo, hi)


def random_cells():
    rng = random.Random(20261112)
    for case in range(100):
        poly = hull([(rng.randrange(-D, D+1), rng.randrange(-D, D+1))
                     for _ in range(rng.randrange(3, 10))])
        q = rng.randrange(1, 7)
        outer = {(i, j) for j, (lo, hi) in cell_intervals(poly, q) for i in range(lo, hi+1)}
        brute = {(i, j) for i in range(-q-1, q+1) for j in range(-q-1, q+1)
                 if brute_intersects(poly, i, j, q)}
        assert outer == brute, case
        inner = {(i, j) for j, (lo, hi) in inner_rows(poly, q) for i in range(lo, hi+1)}
        brute_inner = {(i, j) for i, j in outer
                       if all(inside(poly, (F((i+di)*D, q), F((j+dj)*D, q)))
                              for di in (0, 1) for dj in (0, 1))}
        assert inner == brute_inner, case
    print('100 random exact outer/inner cell comparisons passed')


def rational_circle():
    count = 0
    for eps in (F(1, 1000), F(1, 5), F(1)):
        for f in (-F(1), F(0), F(1)):
            record = {'K': 1, 'eps': eps, 'model': 'pivot-slide', 'params': [F(2, 7), f]}
            for m in (1, 2, 3, 4, 8):
                ps = list(polygons(record, m))
                for a in range(21):
                    z = F(a, 20)
                    ux, uy = (1-z*z)/(1+z*z), 2*z/(1+z*z)
                    for t in (-F(1, 2), F(1, 2)):
                        for v in (-eps/2, eps/2):
                            point = (D*((t-f/2)*ux-v*uy), D*(F(2, 7)+(t-f/2)*uy+v*ux))
                            assert any(inside(poly, point) for poly in ps)
                            count += 1
    for K in (1, 2, 3, 7, 16, 32):
        for m in (1, 2, 3, 4, 8):
            assert trig_grid(K) == trig_grid(K*m)[::m]
    print('exact rational circle corner checks:', count, '; coarse trig invariance: 30 cases')


def envelope_lower_bound():
    _, record = source_record('results/cert_source_grid_smooth_B480.json', 0)
    q, rows = 2048, {}
    for poly in polygons(record, 1):
        for p in (poly, list(reversed([(-x, y) for x, y in poly]))):
            for row, interval in inner_rows(p, q):
                rows.setdefault(row, []).append(interval)
    n = 0
    for intervals in rows.values():
        end = None
        for lo, hi in sorted(intervals):
            if end is None or lo > end+1:
                n += hi-lo+1
                end = hi
            elif hi > end:
                n += hi-end
                end = hi
    print('original ENVELOPE lower bound, NOT motion lower bound:', n, '/', q*q, '=', F(n, q*q))
    assert n == 1587216


if __name__ == '__main__':
    random_cells()
    rational_circle()
    envelope_lower_bound()
