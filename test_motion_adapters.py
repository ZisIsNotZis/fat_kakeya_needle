"""Regressions for continuous pivot and repaired-v2 numeric integer scoring."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from integer_motion_area import SCALE, _grid_bound, evaluate, primitive_paths
from motion_adapters import evaluate_saved, pivot_primitives, v2_primitives
from pivot_slide import PivotSlideModel
from v2_numerical_enclosure import decode_keyframes


def contains(path, x, y, grid_tolerance=0):
    return all((b[0]-a[0])*(y-a[1]) - (b[1]-a[1])*(x-a[0]) >=
               -grid_tolerance * max(abs(b[0]-a[0]), abs(b[1]-a[1]))
               for a, b in zip(path, path[1:] + path[:1]))


def corners(x, y, theta, eps):
    c, s = math.cos(theta), math.sin(theta)
    for u in (-.5, .5):
        for v in (-eps/2, eps/2):
            yield x+c*u-s*v, y+s*u+c*v


class MotionAdapterTests(unittest.TestCase):
    def test_k1_center_circle_and_mirrored_seam(self):
        eps = .005
        primitives = pivot_primitives(PivotSlideModel(eps, 1), [0., 0.])
        self.assertEqual(len(primitives), 2)
        self.assertEqual(primitives[0]['end'], primitives[1]['start'])
        row = evaluate(primitives, eps, step_fraction=.0001, max_wall_s=15)
        self.assertEqual(row['status'], 'ok', row)
        self.assertAlmostEqual(row['numeric_outer_area'], math.pi*(1+eps**2)/4,
                               delta=.00005)
        self.assertIn('not rigorously', row['limitation'])

    def test_pivot_resolution_meets_declared_sagitta_fraction(self):
        eps = .003
        primitives = pivot_primitives(PivotSlideModel(eps, 1), [0., .8])
        row = evaluate(primitives, eps, step_fraction=.001, max_wall_s=20)
        self.assertEqual(row['status'], 'ok', row)
        self.assertAlmostEqual(row['max_corner_radius'],
                               math.hypot(.9, eps/2), places=12)
        sagitta = row['max_corner_radius'] * 2 * math.sin(row['max_step']/4)**2
        self.assertLessEqual(sagitta, .001 * eps * (1 + 1e-12))

    def test_off_center_pivot_dense_interior_corners(self):
        eps = .003
        model = PivotSlideModel(eps, 1)
        first = pivot_primitives(model, [0., .8])[0]
        paths = primitive_paths(first, eps, .04)
        self.assertGreater(len(paths), 1)
        px, py = first['pivot']
        for i, path in enumerate(paths):
            for j in range(1, 30):
                theta = first['start']['theta'] + (i+j/30)*first['angle']/len(paths)
                x, y = px-.4*math.cos(theta), py-.4*math.sin(theta)
                for cx, cy in corners(x, y, theta, eps):
                    self.assertTrue(contains(path, _grid_bound(cx, False),
                                             _grid_bound(cy, False)))
        self.assertEqual(first['fraction'], .8)
        second = pivot_primitives(model, [0., .8])[1]
        paths = primitive_paths(second, eps, .04)
        px, py = second['pivot']
        for i, path in enumerate(paths):
            theta = second['start']['theta'] + (i+.5)*second['angle']/len(paths)
            x, y = px-.4*math.cos(theta), py-.4*math.sin(theta)
            for cx, cy in corners(x, y, theta, eps):
                self.assertTrue(contains(path, _grid_bound(cx, False),
                                         _grid_bound(cy, False)))

    def test_signed_full_slides_and_mirrored_sign(self):
        for length in (1.5, -1.5):
            with self.subTest(length=length):
                primitives = pivot_primitives(PivotSlideModel(.01, 2),
                                               [0., .2, -.4, length])
                slide, reversed_slide = primitives[1], primitives[-2]
                self.assertEqual(slide['length'], length)
                self.assertEqual(reversed_slide['length'], -length)
                for item in (slide, reversed_slide):
                    path, = primitive_paths(item, .01, .05)
                    start, end = item['start']['center'], item['end']['center']
                    for t in (0, .1, .5, .9, 1):
                        x, y = (start[0]+t*(end[0]-start[0]),
                                start[1]+t*(end[1]-start[1]))
                        for cx, cy in corners(x, y, item['start']['theta'], .01):
                            # Floor of the separately recomputed float corner may
                            # differ by one grid cell along an exact hull edge.
                            self.assertTrue(contains(path, _grid_bound(cx, False),
                                                     _grid_bound(cy, False), 2))
                self.assertEqual(evaluate(primitives, .01)['status'], 'ok')

    def test_v2_zero_angle_full_translation_and_off_axis_mirror(self):
        eps = .01
        keyframes = [[0, -.2, .4], [0, .5, .2], [math.pi/2, .7, -.4]]
        theta, centers = decode_keyframes(keyframes, eps)
        primitives = v2_primitives(keyframes, eps)
        axis = centers[-1, 0]
        self.assertNotEqual(axis, 0.)
        self.assertEqual(primitives[2]['end'], primitives[3]['start'])
        self.assertEqual(primitives[1]['end'], primitives[2]['start'])
        self.assertEqual(primitives[-1]['end']['center'][0], 2*axis-centers[0, 0])
        self.assertEqual(primitives[-1]['end']['theta'], math.pi)
        self.assertNotEqual(primitives[-1]['end']['center'][0], -centers[0, 0])
        self.assertEqual(primitives[0]['angle'], 0)
        path, = primitive_paths(primitives[0], eps, .01)
        for t in np.linspace(0, 1, 31):
            x, y = centers[0] + t*(centers[1]-centers[0])
            for cx, cy in corners(x, y, theta[0], eps):
                self.assertTrue(contains(path, _grid_bound(cx, False),
                                         _grid_bound(cy, False), 2))
        translated = primitives[1]
        paths = primitive_paths(translated, eps, .025)
        for i, path in enumerate(paths):
            for j in range(1, 12):
                t = (i+j/12)/len(paths)
                x, y = centers[1]+t*(centers[2]-centers[1])
                angle = theta[1]+t*(theta[2]-theta[1])
                for cx, cy in corners(x, y, angle, eps):
                    self.assertTrue(contains(path, _grid_bound(cx, False),
                                             _grid_bound(cy, False)))
        self.assertEqual(evaluate(primitives, eps)['status'], 'ok')

    def test_invalid_endpoint_angle_fraction_chain_and_discontinuity(self):
        pivot = pivot_primitives(PivotSlideModel(.01, 1), [0., .5])[0]
        for change in ({'fraction': 1.1}, {'pivot': [float('inf'), 0]},
                       {'angle': 0}, {'end': {'theta': pivot['end']['theta'],
                                             'center': [2, 2]}}):
            item = {**pivot, **change}
            self.assertEqual(evaluate([item], .01)['status'], 'error')
        line = v2_primitives([[0, 0, 0], [math.pi/2, 0, 0]], .01)[0]
        self.assertEqual(evaluate([{**line, 'angle': 0}], .01)['status'], 'error')
        self.assertEqual(evaluate([line, {**line, 'start': line['start']}], .01)['status'],
                         'error')

        class BrokenModel(PivotSlideModel):
            def centers_and_pivots(self, params):
                pivots, centers, fractions, beta = super().centers_and_pivots(params)
                centers[1, 0] += .25
                return pivots, centers, fractions, beta

        with self.assertRaisesRegex(ValueError, 'discontinuous'):
            pivot_primitives(BrokenModel(.01, 2), [0., 0., 0., .2])

    def test_saved_candidates_near_independent_numeric_enclosures(self):
        for source, enclosure, tolerance in (
            ('results/v2_0005.json', 'results/v2_0005_repaired_dense.json', .003),
            ('results/pivot_005_K16_night.json', 'results/pivot_numerical_enclosures.json', .005),
        ):
            with self.subTest(source=source):
                records = json.loads(Path(source).read_text())
                index = min(range(len(records)), key=lambda i: records[i]['area'])
                row = evaluate_saved(Path(source), index, max_wall_s=20)
                self.assertEqual(row['status'], 'ok', row)
                archived = json.loads(Path(enclosure).read_text())[0]['numerical_upper']
                self.assertGreaterEqual(row['numeric_outer_area'] + .00001, archived)
                self.assertLess(row['numeric_outer_area'] - archived, tolerance)
                self.assertEqual(row['scale'], SCALE)
                self.assertEqual(row['source_record_index'], index)
                self.assertEqual(row['backend_version'], '1.4.0')
                self.assertGreater(row['wall_s'], 0)
                limited = evaluate_saved(Path(source), index, max_polygons=1)
                self.assertEqual(limited['status'], 'resource_limited', limited)
                self.assertNotIn('numeric_outer_area', limited)

    def test_smooth_archive_and_explicit_control_layouts(self):
        source = Path('results/smooth_0005_K32_v3.json')
        records = json.loads(source.read_text())
        index = min(range(len(records)), key=lambda i: records[i]['area'])
        row = evaluate_saved(source, index, max_wall_s=30)
        self.assertEqual(row['status'], 'ok', row)
        self.assertEqual((row['Nf'], row['Nb']), (10, 10))
        self.assertEqual(row['control_layout'],
                         'equal-count-inferred-from-archive-length')
        old = json.loads(Path('results/smooth_revaluation_0005_0002.json').read_text())
        expected = next(item['numerical_upper'] for item in old
                        if item['source'] == str(source))
        self.assertLess(abs(row['numeric_outer_area'] - expected), .005)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smooth.json'
            base = {'eps': .01, 'K': 4, 'seed': 0, 'Nf': 2, 'Nb': 2,
                    'best_params': [0., 0., 0., 0., 0.]}
            path.write_text(json.dumps([base]))
            result = evaluate_saved(path, 0, max_wall_s=15)
            self.assertEqual(result['status'], 'ok', result)
            self.assertEqual(result['control_layout'], 'explicit-control-counts')
            path.write_text(json.dumps([{**base, 'Nf': True}]))
            invalid = evaluate_saved(path, 0)
            self.assertEqual(invalid['status'], 'error')
            self.assertNotIn('numeric_outer_area', invalid)
            path.write_text(json.dumps([{**base, 'best_params': [0., 0.]}]))
            self.assertEqual(evaluate_saved(path, 0)['status'], 'error')

    def test_cli_typed_failure_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'source.json', Path(directory)/'scored.json'
            source.write_text(json.dumps([{'model': 'other', 'eps': .01, 'K': 1}]))
            command = [sys.executable, str(Path(__file__).with_name('motion_adapters.py')),
                       str(source), '--index', '0', '--out', str(target)]
            subprocess.run(command, timeout=10, check=True, capture_output=True, text=True)
            scored = target.read_text()
            self.assertEqual(json.loads(scored)['status'], 'error')
            self.assertNotIn('numeric_outer_area', json.loads(scored))
            second = subprocess.run(command, timeout=10, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(target.read_text(), scored)
            source.write_text(json.dumps([{'model': 'pivot-slide', 'eps': float('nan'),
                                           'K': 1, 'params': [0., 0.]}]))
            target.unlink()
            subprocess.run(command, timeout=10, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(target.read_text())['status'], 'error')


if __name__ == '__main__':
    unittest.main()
