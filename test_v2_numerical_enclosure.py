"""Tests for the saved-v2 linear-keyframe numerical enclosure."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
from shapely.affinity import scale
from shapely.ops import unary_union

from sweeper_v2 import needle_polygon
from v2_numerical_enclosure import (archived_sources, decode_keyframes, evaluate_source,
                                    mirror_pose, numerical_v2_enclosure, segment_polygons)


class V2NumericalEnclosureTests(unittest.TestCase):
    def test_fixed_center_disk_at_thin_width(self):
        eps = 0.001
        keyframes = [[0, 0, 0], [math.pi / 2, 0, 0]]
        result = numerical_v2_enclosure(keyframes, eps, n_sub=48)
        disk_area = math.pi * (1 + eps * eps) / 4
        self.assertLessEqual(result["numerical_lower"], disk_area + 1e-10)
        self.assertGreaterEqual(result["numerical_upper"] + 1e-10, disk_area)
        self.assertLess(result["numerical_upper"] - disk_area, 0.001)
        self.assertEqual(result["mirror_axis_x"], 0)

    def test_off_axis_mirror_joins_end_without_start_end_equality(self):
        eps = 0.03
        keyframes = [[0, -0.2, 0.4], [math.pi / 2, 0.4, -0.5]]
        theta, centers = decode_keyframes(keyframes, eps)
        axis = centers[-1, 0]
        self.assertNotAlmostEqual(centers[0, 0], axis)
        np.testing.assert_allclose(mirror_pose(theta[-1], centers[-1], axis),
                                   (math.pi / 2, *centers[-1]), atol=1e-14)
        np.testing.assert_allclose(mirror_pose(theta[0], centers[0], axis),
                                   (math.pi, 2 * axis - centers[0, 0], centers[0, 1]),
                                   atol=1e-14)
        result = numerical_v2_enclosure(keyframes, eps, n_sub=8)
        self.assertAlmostEqual(result["mirror_axis_x"], axis)
        rect = needle_polygon(theta[0], *centers[0], eps)
        reflected = scale(rect, xfact=-1, origin=(axis, 0))
        self.assertGreater(reflected.difference(rect).area, 0.001)
        self.assertGreater(result["numerical_upper"], result["numerical_lower"])
        # A fixed but off-origin center must reflect onto itself, not onto
        # a disjoint copy across the global x=0 axis.
        shifted = [[0, .7, -.4], [math.pi / 2, .7, -.4]]
        shifted_result = numerical_v2_enclosure(shifted, eps, n_sub=8)
        centered_result = numerical_v2_enclosure([[0, 0, 0], [math.pi / 2, 0, 0]],
                                                  eps, n_sub=8)
        self.assertAlmostEqual(shifted_result["numerical_lower"],
                               centered_result["numerical_lower"], places=8)
        self.assertAlmostEqual(shifted_result["numerical_upper"],
                               centered_result["numerical_upper"], places=8)

    def test_translated_linear_segment_contains_dense_poses(self):
        eps = .005
        theta, centers = decode_keyframes([[0, 0, 0], [math.pi / 2, .7, -.8]], eps)
        lower, upper = segment_polygons(theta[0], theta[1], centers[0], centers[1], eps, 8)
        upper_union = unary_union(upper)
        for fraction in np.linspace(0, 1, 129):
            center = centers[0] + fraction * (centers[1] - centers[0])
            rect = needle_polygon(theta[0] + fraction * (theta[1] - theta[0]),
                                  *center, eps)
            self.assertLess(rect.difference(upper_union).area, 1e-11)
        self.assertEqual(len(lower), 9)
        coarse = numerical_v2_enclosure([[0, 0, 0], [math.pi / 2, .7, -.8]], eps, 8)
        fine = numerical_v2_enclosure([[0, 0, 0], [math.pi / 2, .7, -.8]], eps, 32)
        self.assertGreaterEqual(fine["numerical_lower"] + 1e-8, coarse["numerical_lower"])
        self.assertLess(fine["numerical_upper"] - fine["numerical_lower"],
                        coarse["numerical_upper"] - coarse["numerical_lower"])

    def test_zero_angle_segment_contains_full_translation(self):
        eps = 0.01
        theta, centers = decode_keyframes([[0, 0, 0], [0, .5, .2],
                                           [math.pi / 2, .5, .2]], eps)
        _, upper = segment_polygons(theta[0], theta[1], centers[0], centers[1], eps, 1)
        for fraction in np.linspace(0, 1, 21):
            c = centers[0] + fraction * (centers[1] - centers[0])
            self.assertLess(needle_polygon(0, *c, eps).difference(upper[0]).area, 1e-12)
        result = numerical_v2_enclosure([[0, 0, 0], [0, .5, .2],
                                         [math.pi / 2, .5, .2]], eps, 4)
        self.assertGreaterEqual(result["numerical_upper"] + 1e-9,
                                result["numerical_lower"])

    def test_best_new_is_selected_after_repair_and_layout_rejection(self):
        base = {"eps": .001, "K": 1, "model": "v2-logspace-growing",
                "keyframes": [[0, 0, 0], [math.pi / 2, 0, 0]]}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "v2.json"
            source.write_text(json.dumps([{**base, "seed": 0, "area": 1.0},
                                          {**base, "seed": 1, "area": .8}]))
            self.assertEqual([r["seed"] for r in evaluate_source(source, 4)], [0, 1])
            self.assertEqual([r["seed"] for r in evaluate_source(source, 4, True)], [0])
            source.write_text(json.dumps([{**base, "seed": 0, "area": 1.0,
                                           "keyframes": [[0, 0], [math.pi / 2, 0]]}]))
            with self.assertRaisesRegex(ValueError, "keyframes"):
                evaluate_source(source, 4)

    def test_old_area_order_reverses_after_mirror_repair(self):
        # Recorded counterexample: old area uses global mirror, new motion
        # reflects around its endpoint and changes the candidate ordering.
        source = Path('results/v2_005_K6_multiseed.json')
        rows = evaluate_source(source, 12)
        old_best = min(rows, key=lambda row: row['original_sampled_area'])
        new_best = min(rows, key=lambda row: row['numerical_upper'])
        self.assertNotEqual(old_best['source_record_index'], new_best['source_record_index'])
        self.assertEqual(evaluate_source(source, 12, best_new=True)[0]['source_record_index'],
                         new_best['source_record_index'])

    def test_default_discovery_excludes_generated_enclosures(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            archive = {"eps": .001, "K": 1, "model": "v2-logspace-growing",
                       "seed": 0, "area": .8,
                       "keyframes": [[0, 0, 0], [math.pi / 2, 0, 0]]}
            (path / 'v2_original.json').write_text(json.dumps([archive]))
            (path / 'v2_derived_dense.json').write_text(json.dumps([
                {"eps": .001, "K": 1, "numerical_upper": .9}]))
            self.assertEqual(archived_sources(path), [path / 'v2_original.json'])
        paths = archived_sources(Path('results'))
        self.assertEqual(len(paths), 16)
        self.assertNotIn(Path('results/v2_0005_repaired_dense.json'), paths)

    def test_rejects_degenerate_large_coordinate_poses(self):
        with self.assertRaisesRegex(ValueError, 'degenerate'):
            numerical_v2_enclosure([[0, 40, 0], [math.pi / 2, 40, 0]], .05, 2)

    def test_rejects_wrong_parameter_layout_and_invalid_motion(self):
        for keyframes in ([0, 0, 0, math.pi / 2, 0, 0],
                          [[0, 0], [math.pi / 2, 0]],
                          [[0, 0, 0], [math.pi / 2, 0, float("nan")]],
                          [[0, 0, 0], [math.pi / 3, 0, 0]],
                          [[0, 0, 0], [math.pi / 2, 0, 0], [.2, 0, 0]]):
            with self.subTest(keyframes=keyframes), self.assertRaises(ValueError):
                numerical_v2_enclosure(keyframes, .001, 8)
        with self.assertRaises(ValueError):
            numerical_v2_enclosure([[0, 0, 0], [math.pi / 2, 0, 0]], float("inf"), 8)
        with self.assertRaises(ValueError):
            numerical_v2_enclosure([[0, 0, 0], [math.pi / 2, 0, 0]], .001, 0)


if __name__ == "__main__":
    unittest.main()
