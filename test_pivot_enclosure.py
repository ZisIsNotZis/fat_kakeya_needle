"""Regression tests for numerical enclosures of actual pivot-slide motions."""
import json
import math
import unittest

import numpy as np
from shapely.affinity import scale
from shapely.ops import unary_union

from pivot_slide import PivotSlideModel, needle_polygon, slide_strip
from smooth_pivot import SmoothProfileModel
from strict_bound import numerical_pivot_enclosure, strict_upper


class PivotEnclosureTests(unittest.TestCase):
    def test_centered_arc_brackets_disk(self):
        eps = 0.001
        model = PivotSlideModel(eps, K=1)
        result = numerical_pivot_enclosure(model, np.array([0.0, 0.0]), n_sub=48)
        truth = math.pi * (1 + eps * eps) / 4
        self.assertLessEqual(result["lower"], truth + 1e-10)
        self.assertGreaterEqual(result["upper"], truth - 1e-10)
        # The sparse sampled lower union is deliberately loose for a thin needle.
        self.assertGreater(result["lower"], 0.0)
        self.assertLess(result["upper"] - truth, 0.001)

    def test_off_center_arc_covers_dense_intermediate_poses(self):
        eps = 0.02
        model = PivotSlideModel(eps, K=1)
        params = np.array([0.0, 0.8])
        enclosure = numerical_pivot_enclosure(model, params, n_sub=8)
        pivot, _, fractions, _ = model.centers_and_pivots(params)
        samples = []
        for theta in np.linspace(0, math.pi / 2, 257):
            c = pivot[0] - 0.5 * fractions[0] * np.array([math.cos(theta), math.sin(theta)])
            samples.append(needle_polygon(theta, *c, eps))
        dense = unary_union(samples)
        dense_area = dense.union(scale(dense, xfact=-1, origin=(0, 0))).area
        self.assertLessEqual(dense_area, enclosure["upper"] + 1e-10)
        self.assertGreater(dense_area, enclosure["lower"])

    def test_nonzero_beta_includes_whole_slide(self):
        eps = 0.1
        model = PivotSlideModel(eps, K=2)
        n_sub = 8
        for displacement in (1.5, -1.5):
            with self.subTest(beta=displacement):
                params = np.array([0.0, 0.0, 0.0, displacement])
                result = numerical_pivot_enclosure(model, params, n_sub=n_sub)
                pivots, centers, fractions, _ = model.centers_and_pivots(params)
                polys = []
                poses_only = []
                for i in range(model.K):
                    for theta in np.linspace(model.theta[i], model.theta[i + 1], n_sub + 1):
                        u = np.array([math.cos(theta), math.sin(theta)])
                        c = pivots[i] - 0.5 * fractions[i] * u
                        pose = needle_polygon(theta, *c, eps)
                        polys.append(pose)
                        poses_only.append(pose)
                    if i < model.K - 1:
                        end = pivots[i] - 0.5 * fractions[i] * model.u[i + 1]
                        strip = slide_strip(model.theta[i + 1], end, centers[i + 1], eps)
                        polys.append(strip)
                without_slide = unary_union(poses_only)
                without_slide = without_slide.union(scale(without_slide, xfact=-1,
                                                          origin=(0, 0))).area
                first_half = unary_union(polys)
                sampled_with_slide = first_half.union(
                    scale(first_half, xfact=-1, origin=(0, 0))).area
                self.assertAlmostEqual(result["lower"], sampled_with_slide, places=9)
                self.assertGreater(sampled_with_slide - without_slide, 0.05)
                self.assertGreaterEqual(result["upper"] + 1e-10, result["lower"])

    def test_discontinuous_boundary_is_rejected(self):
        class BrokenModel(PivotSlideModel):
            def centers_and_pivots(self, params):
                pivots, centers, fractions, beta = super().centers_and_pivots(params)
                centers[1, 0] += 0.25
                return pivots, centers, fractions, beta

        with self.assertRaisesRegex(ValueError, "discontinuous"):
            numerical_pivot_enclosure(BrokenModel(0.1, K=2),
                                      np.array([0.0, 0.0, 0.0, 0.2]), n_sub=4)

    def test_arc_hulls_contain_intermediate_poses(self):
        # Geometry inclusion, not merely area comparison; buffer is polygonal.
        eps = 0.003
        model = PivotSlideModel(eps, K=2)
        params = np.array([0.0, 0.7, -0.5, 0.2])
        pivots, _, fractions, _ = model.centers_and_pivots(params)
        for i in range(model.K):
            start, end = model.theta[i:i + 2]
            radius = math.hypot((1 + abs(fractions[i])) / 2, eps / 2)
            for left, right in zip(np.linspace(start, end, 9)[:-1],
                                   np.linspace(start, end, 9)[1:]):
                rects = []
                for theta in (left, right):
                    u = np.array([math.cos(theta), math.sin(theta)])
                    c = pivots[i] - 0.5 * fractions[i] * u
                    rects.append(needle_polygon(theta, *c, eps))
                hull = unary_union(rects).convex_hull
                delta = right - left
                outer = hull.buffer(radius * (1 - math.cos(delta / 2)) /
                                    math.cos(math.pi / 64), quad_segs=16)
                for theta in np.linspace(left, right, 17)[1:-1]:
                    u = np.array([math.cos(theta), math.sin(theta)])
                    c = pivots[i] - 0.5 * fractions[i] * u
                    pose = needle_polygon(theta, *c, eps)
                    self.assertLess(pose.difference(outer).area, 1e-13)

    def test_nested_angle_mesh_does_not_lose_area(self):
        # Without precision-grid overlay GEOS dropped about 0.000374 area
        # when this same recorded solution was refined from 40 to 80.
        with open('results/smooth_hr_0005_K32.json') as fh:
            best = min(json.load(fh), key=lambda run: run['area'])
        model = SmoothProfileModel(32, 0.005, Nf=8, Nb=8, n_arc=40)
        params = np.asarray(best['best_params'])
        coarse = model.swept_area(params)
        model.base.n_arc = 80
        fine = model.swept_area(params)
        self.assertGreaterEqual(fine + 1e-7, coarse)

    def test_recorded_result_reproduces_full_precision(self):
        with open('results/pivot_005_K16_night.json') as fh:
            best = min(json.load(fh), key=lambda run: run['area'])
        with open('results/pivot_numerical_enclosures.json') as fh:
            recorded = json.load(fh)[0]
        result = numerical_pivot_enclosure(PivotSlideModel(best['eps'], best['K']),
                                           np.asarray(best['params']), n_sub=recorded['n_sub'])
        self.assertAlmostEqual(result['lower'], recorded['numerical_lower'], places=11)
        self.assertAlmostEqual(result['upper'], recorded['numerical_upper'], places=11)

    def test_generic_pose_is_not_supported(self):
        with self.assertRaises(NotImplementedError):
            strict_upper(0.001, lambda s: (s * math.pi / 2, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
