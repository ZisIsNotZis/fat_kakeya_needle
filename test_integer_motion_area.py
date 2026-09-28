"""Regressions for the non-certified integer Keich primitive evaluator."""
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from integer_motion_area import (SCALE, _grid_bound, evaluate, evaluate_keich,
                                 primitive_paths, union_area)
from keich_motion import pose, slide, turn


def rectangle(x0, y0, x1, y1):
    return [(x0*SCALE, y0*SCALE), (x1*SCALE, y0*SCALE),
            (x1*SCALE, y1*SCALE), (x0*SCALE, y1*SCALE)]


def contains(path, x, y):
    # All paths returned by the monotone hull are counterclockwise.
    return all((b[0]-a[0])*(y-a[1]) - (b[1]-a[1])*(x-a[0]) >= 0
               for a, b in zip(path, path[1:] + path[:1]))


class IntegerMotionAreaTests(unittest.TestCase):
    def test_overlapping_rectangles_and_hole_with_nested_island(self):
        self.assertEqual(union_area([rectangle(0, 0, 2, 1),
                                     rectangle(1, 0, 3, 1)]), 3)
        ring = [rectangle(0, 0, 4, 1), rectangle(0, 3, 4, 4),
                rectangle(0, 1, 1, 3), rectangle(3, 1, 4, 3)]
        self.assertEqual(union_area(ring), 12)
        self.assertEqual(union_area(ring + [rectangle(1, 1, 2, 2)]), 13)

    def test_centered_rotation_against_analytic_disk(self):
        eps = 1/256
        rotation = turn(pose([0., 0.], 0.), math.pi, 0)
        row = evaluate([rotation], eps, max_wall_s=20)
        self.assertEqual(row['status'], 'ok', row)
        expected = math.pi * (1 + eps**2) / 4
        self.assertGreaterEqual(row['numeric_outer_area'], expected - 0.0001)
        self.assertLess(row['numeric_outer_area'] - expected, 0.01)
        self.assertEqual(row['backend_version'], '1.4.0')
        self.assertIn('not rigorously', row['limitation'])

    def test_signed_far_axial_slides_enclose_intermediate_corners(self):
        eps = 2**-20
        for length in (100., -100.):
            start = pose([1000., -1000.], 0.37)
            move = slide(start, length, 0)
            path, = primitive_paths(move, eps, 0.01)
            for t in (0, .05, .25, .5, .95, 1):
                cx = start['center'][0] + t*(move['end']['center'][0]-start['center'][0])
                cy = start['center'][1] + t*(move['end']['center'][1]-start['center'][1])
                for u in (-.5, .5):
                    for v in (-eps/2, eps/2):
                        theta = start['theta']
                        x = cx + math.cos(theta)*u - math.sin(theta)*v
                        y = cy + math.sin(theta)*u + math.cos(theta)*v
                        self.assertTrue(contains(path, _grid_bound(x, False),
                                                 _grid_bound(y, False)))
            row = evaluate([move], eps)
            self.assertEqual(row['status'], 'ok', row)
            self.assertGreater(row['numeric_outer_area'], abs(length)*eps)

    def test_dense_interior_rotation_corners_both_directions(self):
        eps = 1/1024
        for angle in (.27, -.27):
            primitive = turn(pose([1000., -1000.], 1.2), angle, 0)
            paths = primitive_paths(primitive, eps, 0.02)
            self.assertGreater(len(paths), 1)
            for i, path in enumerate(paths):
                for j in range(1, 20):
                    theta = 1.2 + angle*(i+j/20)/len(paths)
                    for u in (-.5, .5):
                        for v in (-eps/2, eps/2):
                            x = 1000 + math.cos(theta)*u - math.sin(theta)*v
                            y = -1000 + math.sin(theta)*u + math.cos(theta)*v
                            self.assertTrue(contains(path, _grid_bound(x, False),
                                                     _grid_bound(y, False)))

    def test_nonfinite_overflow_and_invalid_primitive_fail_closed(self):
        self.assertEqual(_grid_bound(-.125, False), -SCALE//8)
        for coordinate in (float('nan'), float('inf'), 8192., -8192.):
            move = slide(pose([coordinate, 0.], 0.), 0., 0)
            row = evaluate([move], .01)
            self.assertEqual(row['status'], 'error', row)
            self.assertNotIn('numeric_outer_area', row)
        skew = {'kind': 'slide', 'start': pose([0, 0], 0),
                'end': pose([0, 1], 0)}
        self.assertEqual(evaluate([skew], .01)['status'], 'error')
        limited = evaluate([turn(pose([0, 0], 0), math.pi, 0)], .01,
                           max_polygons=1)
        self.assertEqual(limited['status'], 'resource_limited')
        self.assertNotIn('numeric_outer_area', limited)
        first = slide(pose([0, 0], 0), 1, 0)
        two_slides = [first, slide(first['end'], 1, 1)]
        self.assertEqual(evaluate(two_slides, .01, max_polygons=1)['status'],
                         'resource_limited')
        self.assertEqual(evaluate([], .01, max_wall_s=float('nan'))['status'],
                         'error')
        self.assertEqual(evaluate([], .01)['status'], 'error')

    def test_rejects_contradictory_primitive_and_broken_chain(self):
        rotation = turn(pose([0., 0.], 0.), math.pi, 0)
        rotation['end'] = pose([0., 0.], 0.)
        row = evaluate([rotation], .01)
        self.assertEqual(row['status'], 'error')
        self.assertIn('angle disagrees', row['error'])
        self.assertNotIn('numeric_outer_area', row)

        motion = slide(pose([0., 0.], 0.), 2., 0)
        motion['length'] = .1
        row = evaluate([motion], .01)
        self.assertEqual(row['status'], 'error')
        self.assertIn('length disagrees', row['error'])

        a = slide(pose([0., 0.], 0.), 1., 0)
        b = slide(pose([2., 0.], 0.), 1., 1)
        row = evaluate([a, b], .01)
        self.assertEqual(row['status'], 'error')
        self.assertIn('discontinuous', row['error'])
        self.assertNotIn('numeric_outer_area', row)

    def test_large_and_negative_rotations_are_subdivided(self):
        for angle in (4 * math.pi, -4 * math.pi):
            rotation = turn(pose([0., 0.], 0.), angle, 0)
            paths = primitive_paths(rotation, .01, 4 * math.pi)
            self.assertGreaterEqual(len(paths), 8)
            row = evaluate([rotation], .01, max_wall_s=30)
            self.assertEqual(row['status'], 'ok', row)
            self.assertGreaterEqual(row['numeric_outer_area'], math.pi / 4)

    def test_keich_n4_smoke(self):
        row = evaluate_keich(4, max_wall_s=70, max_polygons=50000)
        self.assertEqual(row['status'], 'ok', row)
        self.assertAlmostEqual(row['numeric_outer_area'], 1.242, delta=.08)
        self.assertLess(row['wall_s'], 120)
        self.assertEqual(row['input_source'], 'keich_motion.generate')

    def test_keich_n5_bounded_subprocess(self):
        # Native clipping cannot be interrupted in-process: enforce a hard
        # subprocess deadline, while normal budget exhaustion stays typed.
        code = ('import json; from integer_motion_area import evaluate_keich; '
                'print(json.dumps(evaluate_keich(5, max_wall_s=90, '
                'max_polygons=70000)))')
        proc = subprocess.run([sys.executable, '-c', code], capture_output=True,
                              text=True, timeout=120, check=True)
        row = json.loads(proc.stdout)
        self.assertIn(row['status'], ('ok', 'resource_limited'), row)
        if row['status'] == 'ok':
            self.assertAlmostEqual(row['numeric_outer_area'], .941, delta=.08)
            self.assertLessEqual(row['quality_check']['relative_discrepancy'], 0.02)
        else:
            self.assertNotIn('numeric_outer_area', row)

    def test_cli_writes_separate_json_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'integer_keich_n4.json'
            command = [sys.executable, str(Path(__file__).with_name('integer_motion_area.py')),
                       '--n', '4', '--out', str(target)]
            subprocess.run(command, capture_output=True, text=True, timeout=15, check=True)
            content = target.read_text()
            self.assertEqual(json.loads(content)['status'], 'ok')
            second = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(target.read_text(), content)

    def test_keich_quality_gate_never_publishes_bad_area(self):
        base = {'status': 'ok', 'numeric_outer_area': 1., 'wall_s': 1.,
                'cpu_s': 1., 'step_fraction': .1, 'max_step': .1,
                'polygon_count': 20}
        fine = dict(base, numeric_outer_area=.9, step_fraction=.05)
        with patch('integer_motion_area.evaluate', side_effect=[base.copy(), fine]):
            row = evaluate_keich(5)
        self.assertEqual(row['status'], 'quality_limited')
        self.assertNotIn('numeric_outer_area', row)
        self.assertGreater(row['quality_check']['relative_discrepancy'], 0.02)


if __name__ == '__main__':
    unittest.main()
