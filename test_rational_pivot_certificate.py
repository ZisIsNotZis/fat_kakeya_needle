"""Exact, independent small-grid checks for rational pivot certificate."""
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

from rational_pivot_certificate import (
    D, cell_intervals, certificate, count_cells, full_parameters, hull,
    pi_interval, polygons, series_interval, source_record, trig_grid,
)


def brute_intersects(poly, i, j, q):
    """Independent closed half-plane clipping (retains point/edge touches)."""
    vertices = [(F(x, D), F(y, D)) for x, y in poly]
    for axis, boundary, side in ((0, F(i, q), 1), (0, F(i+1, q), -1),
                                  (1, F(j, q), 1), (1, F(j+1, q), -1)):
        def inside(p):
            return side*(p[axis]-boundary) >= 0
        def intersection(a, b):
            t = (boundary-a[axis])/(b[axis]-a[axis])
            return tuple(a[k]+t*(b[k]-a[k]) for k in range(2))
        clipped = []
        for a, b in zip(vertices, vertices[1:]+vertices[:1]):
            ia, ib = inside(a), inside(b)
            if ia != ib:
                clipped.append(intersection(a, b))
            if ib:
                clipped.append(b)
        vertices = clipped
        if not vertices:
            return False
    return True


class RationalPivotTests(unittest.TestCase):
    def test_pi_enclosure_and_trig_endpoints(self):
        lo, hi = pi_interval()
        self.assertTrue(F(314159265358979323846, 10**20) < lo < hi < F(314159265358979323847, 10**20))
        self.assertEqual(trig_grid(1), [((D, D), (0, 0)), ((0, 0), (D, D))])

    def test_high_angle_and_zero_taylor_bounds(self):
        self.assertEqual(series_interval(F(0), True), (F(0), F(0)))
        self.assertEqual(series_interval(F(0), False), (F(1), F(1)))
        # Near pi/2, exact rational Taylor bounds must enclose known
        # alternating-series partial sums of the same argument.
        for x in (F(1, 1000000), F(3, 2), F(11, 7)):
            for sine in (True, False):
                lo, hi = series_interval(x, sine)
                self.assertLessEqual(lo, hi)
                term, total = (x if sine else F(1)), F(0)
                for k in range(40):
                    total += term
                    if k >= 18:
                        self.assertLessEqual(lo, total)
                        self.assertLessEqual(total, hi)
                    power = 2*k+1 if sine else 2*k
                    term *= -x*x/F((power+1)*(power+2))

    def test_centered_K1_disk(self):
        record = {'K': 1, 'eps': F(1, 100), 'model': 'pivot-slide', 'params': [F(0), F(0)]}
        n = count_cells(polygons(record), 32)
        self.assertGreater(F(n, 32*32), F(3, 4))
        self.assertLess(F(n, 32*32), 5)

    def test_positive_negative_slides_and_mirror_join(self):
        for beta in (F(2, 5), -F(2, 5)):
            record = {'K': 2, 'eps': F(1, 10), 'model': 'pivot-slide',
                      'params': [F(0), F(1, 3), -F(1, 4), beta]}
            polys = list(polygons(record))
            self.assertEqual(len(polys), 3)
            self.assertGreater(count_cells(polys, 8), 0)
            u = trig_grid(2)[1]
            ux, uy = (F(sum(component), 2*D) for component in u)
            gamma = beta+(-F(1, 4)-F(1, 3))/2
            p0x = -gamma*ux
            # Pick an exact rational direction inside the certified trig
            # box. The midpoint of the signed slide is inside its hull.
            for t in (-F(1, 2), F(1, 2)):
                for v in (-F(1, 20), F(1, 20)):
                    point = (D*(p0x+(beta/2+t-F(1, 6))*ux-v*uy),
                             D*((beta/2+t-F(1, 6))*uy+v*ux))
                    cross = [(b[0]-a[0])*(point[1]-a[1])-
                             (b[1]-a[1])*(point[0]-a[0])
                             for a, b in zip(polys[1], polys[1][1:]+polys[1][:1])]
                    self.assertTrue(all(c >= 0 for c in cross))
            # Algebraically P1.x=(-gamma*u1.x)+gamma*u1.x=0;
            # reflection of the terminal vertical rectangle is the same pose.
            self.assertTrue(any(x < 0 for x, _ in polys[-1]))
            self.assertTrue(any(x > 0 for x, _ in polys[-1]))
            self.assertEqual(count_cells([polys[-1]], 8),
                             count_cells([[(-x, y) for x, y in polys[-1]]], 8))

    def test_gridline_dual_coverage(self):
        poly = hull([(0, 0), (D, 0), (D, D), (0, D)])
        self.assertEqual(dict(cell_intervals(poly, 1)), {-1: (-1, 1), 0: (-1, 1), 1: (-1, 1)})
        self.assertEqual(count_cells([poly], 1), 12)  # Includes x-mirror.

    def test_independent_brute_closed_cell_intersection(self):
        shapes = [hull([(0, 0), (3*D//5, D//7), (D//4, D), (-D//5, D//3)]),
                  hull([(-D, -D), (D//3, -D//2), (D, D//3), (-D//2, D)])]
        q = 4
        for poly in shapes:
            rows = {(i, j) for j, (lo, hi) in cell_intervals(poly, q)
                    for i in range(lo, hi+1)}
            brute = {(i, j) for i in range(-8, 9) for j in range(-8, 9)
                     if brute_intersects(poly, i, j, q)}
            self.assertEqual(rows, brute)
            mirrored = [(-x, y) for x, y in poly]
            expected = sum(brute_intersects(shape, i, j, q)
                           or brute_intersects(other, i, j, q)
                           for i in range(-8, 9) for j in range(-8, 9)
                           for shape, other in [(poly, mirrored)])
            self.assertEqual(count_cells([poly], q), expected)

    def test_decimal_source_and_checker(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source.json'
            source.write_text('[{"seed":0,"K":1,"eps":0.05,"model":"pivot-slide","params":[0.1,0]}]')
            sha, rec = source_record(source, 0)
            self.assertEqual(rec['eps'], F(1, 20))
            result = certificate(source, 0, 8)
            self.assertEqual(result['input_sha256'], sha)
            self.assertEqual(result, certificate(source, 0, 8))
            self.assertEqual(F(result['upper']), F(result['N'], 64))
            saved = Path(temp)/'certificate.json'
            saved.write_text(json.dumps(result))
            command = [sys.executable, 'rational_pivot_certificate.py', str(source),
                       '--seed', '0', '--q', '8', '--verify', str(saved)]
            self.assertEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
            saved.write_text(json.dumps({**result, 'N': float(result['N'])}))
            self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
            # Duplicate key before the genuine one must not be silently
            # ignored by json.loads' default last-value-wins behavior.
            valid = json.dumps(result)
            saved.write_text(valid.replace('"upper":', '"upper": "0", "upper":', 1))
            self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
            saved.write_text(json.dumps({**result, 'N': result['N']-1}))
            self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=15).returncode, 0)
            source.write_text(source.read_text()+' ')
            self.assertNotEqual(result['input_sha256'], certificate(source, 0, 8)['input_sha256'])
            source.write_text('[{"seed":0,"K":1,"eps":0.05,"model":"v2-logspace-growing",'
                              '"model":"pivot-slide","params":[0.1,0]}]')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
                certificate(source, 0, 8)
            source.write_text('[{"seed":true,"K":1,"eps":0.05,'
                              '"model":"pivot-slide","params":[0.1,0]}]')
            with self.assertRaisesRegex(ValueError, 'seed must match'):
                certificate(source, 1, 8)
            source.write_text('[{"seed":1,"K":1,"eps":0.05,'
                              '"model":"pivot-slide","params":[0.1,0]}]')
            with self.assertRaisesRegex(ValueError, 'seed must be an integer'):
                certificate(source, True, 8)
            for field, bad in (("eps", 'true'), ("eps", '"0.05"'),
                               ("params", '[true,0]'),
                               ("params", '["0.1",0]')):
                source.write_text('[{"seed":0,"K":1,"eps":0.05,'
                                  '"model":"pivot-slide","params":[0.1,0]}]'
                                  .replace('"'+field+'":'+('0.05' if field == 'eps' else '[0.1,0]'),
                                           '"'+field+'":'+bad))
                with self.subTest(field=field, bad=bad), self.assertRaisesRegex(
                        ValueError, 'motion value must be a JSON number'):
                    certificate(source, 0, 8)

    def test_rejects_unrelated_explicit_model(self):
        record = {'K': 2, 'eps': F(1, 20), 'seed': 0,
                  'model': 'v2-logspace-growing', 'Nf': 2, 'Nb': 2,
                  'best_params': [F(0)] * 5, 'keyframes': []}
        with self.assertRaisesRegex(ValueError, 'unsupported motion model'):
            list(polygons(record))
        record.pop('keyframes')
        with self.assertRaisesRegex(ValueError, 'unsupported motion model'):
            list(polygons(record))

    def test_rejects_non_numeric_smooth_controls(self):
        base = {'K': 2, 'Nf': 2, 'Nb': 2,
                'best_params': [F(0), F(-1), F(1), F(0), F(1)]}
        for value in (True, '0.5'):
            record = {**base, 'best_params': [F(0), value, F(1), F(0), F(1)]}
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, 'motion value must be a JSON number'):
                full_parameters(record)

    def test_smooth_rational_interpolation(self):
        record = {'K': 4, 'Nf': 2, 'Nb': 2,
                  'best_params': [F(0), F(-1), F(1), F(0), F(1)]}
        _, f, beta = full_parameters(record)
        self.assertEqual(f, [F(-1), F(-1, 2), F(0), F(1, 2)])
        self.assertEqual(beta, [F(1, 4), F(1, 2), F(3, 4)])


if __name__ == '__main__':
    unittest.main()
