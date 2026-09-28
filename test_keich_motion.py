"""Small exact triangle checks and numerical continuity checks for keich_motion."""

from fractions import Fraction as F
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

from keich_motion import MAX_N, connector, generate, level, pose, triangle


SCRIPT = Path(__file__).with_name("keich_motion.py")


class KeichMotionTests(unittest.TestCase):
    def test_exact_bits_and_triangles_n1_n2(self):
        expected = {
            1: [("0", F(0), F(0), F(-1)),
                ("1", F(1, 2), F(0), F(-1, 2))],
            2: [("00", F(0), F(0), F(-1, 2)),
                ("01", F(1, 4), F(-1, 8), F(-1)),
                ("10", F(1, 2), F(0), F(0)),
                ("11", F(3, 4), F(-1, 8), F(-1, 2))],
        }
        for n, values in expected.items():
            h = F(1, 1 << n)
            for q, (bits, a, b, c) in enumerate(values):
                tri = triangle(n, q)
                self.assertEqual((tri["bits"], tri["a"], tri["b"], tri["c"]),
                                 (bits, a, b, c))
                self.assertEqual(tri["vertices"], ((F(0), c), (F(0), c - h),
                                                   (F(1), c + a)))
                top, bottom, tip = tri["vertices"]
                self.assertEqual((tip[1] - top[1]) / (tip[0] - top[0]), a)
                self.assertEqual((tip[1] - bottom[1]) / (tip[0] - bottom[0]), a + h)
            self.assertEqual(triangle(n, (1 << n) - 1)["a"] + h, 1)

    def test_segment_endpoints_on_triangle_edges(self):
        for n in (1, 2):
            record = generate(F(1, 1 << (4*n)))
            for item in record["stations"]:
                tri = triangle(n, item["q"])
                start = tri["vertices"][1 if item["edge"] == "lower" else 0]
                end = tri["vertices"][2]
                angle = item["block"] * math.pi / 4
                ca, sa = math.cos(angle), math.sin(angle)
                (x0, y0), (x1, y1) = item["unit_segment"]
                self.assertAlmostEqual(math.hypot(x1 - x0, y1 - y0), 1, places=13)
                local_points = [(ca*x + sa*y, -sa*x + ca*y)
                                for x, y in item["unit_segment"]]
                for x, y in local_points:
                    self.assertGreaterEqual(x, -1e-14)
                    self.assertLessEqual(x, 1 + 1e-14)
                    self.assertAlmostEqual(y, float(start[1] + (end[1] - start[1]) * x),
                                           places=13)
                self.assertEqual(item["edge_midpoint_local"],
                                 [str((start[i] + end[i]) / 2) for i in range(2)])

    def test_station_order_theta_bound_and_centers(self):
        for n in (1, 2):
            record = generate(F(1, 1 << (4*n)))
            M = 1 << n
            stations = record["stations"]
            self.assertEqual(len(stations), 4*M+1)
            self.assertEqual([(s["block"], s["q"], s["edge"]) for s in stations],
                             [(k, j, "upper") for k in range(4) for j in range(M)]
                             + [(3, M-1, "lower")])
            self.assertEqual(stations[0]["theta"], 0)
            self.assertEqual(stations[-1]["theta"], math.pi)
            self.assertTrue(all(0 < b["theta"] - a["theta"] <= float(F(1, M))
                                for a, b in zip(stations, stations[1:])))
            for a in stations:
                self.assertLessEqual(math.hypot(*a["center"]), math.sqrt(37) + 1e-13)
                for b in stations:
                    self.assertLessEqual(math.dist(a["center"], b["center"]), 14)

    def test_primitive_order_count_continuity_and_final_pose(self):
        for n in (1, 2):
            record = generate(F(1, 1 << (4*n)))
            stations, primitives = record["stations"], record["primitives"]
            self.assertEqual(len(primitives), 6*4*(1 << n))
            self.assertEqual(primitives[0]["start"], record["initial_pose"])
            self.assertEqual(primitives[-1]["end"], record["final_pose"])
            for i in range(4*(1 << n)):
                operations = primitives[6*i:6*i+6]
                self.assertEqual([p["kind"] for p in operations],
                                 ["center_rotate", "slide", "center_rotate",
                                  "slide", "center_rotate", "slide"])
                self.assertEqual([p["station_transition"] for p in operations], [i]*6)
                self.assertAlmostEqual(operations[0]["end"]["theta"],
                                       stations[i+1]["theta"], places=14)
                self.assertLess(math.dist(operations[-1]["end"]["center"],
                                          stations[i+1]["center"]), 1e-10)
                self.assertAlmostEqual(operations[-1]["end"]["theta"],
                                       stations[i+1]["theta"], places=14)
            for previous, following in zip(primitives, primitives[1:]):
                self.assertEqual(previous["end"], following["start"])
            for p in primitives:
                if p["kind"] == "slide":
                    self.assertAlmostEqual(math.dist(p["start"]["center"], p["end"]["center"]),
                                           abs(p["length"]), delta=1e-11)
                    self.assertEqual(p["start"]["theta"], p["end"]["theta"])
                else:
                    self.assertEqual(p["start"]["center"], p["end"]["center"])
                    self.assertAlmostEqual(p["end"]["theta"] - p["start"]["theta"],
                                           p["angle"], places=14)
            self.assertAlmostEqual(record["final_pose"]["theta"], math.pi, places=14)

    def test_connector_positive_negative_transverse_near_angle_ends(self):
        for theta in (0, 1e-8, math.pi-1e-8, math.pi):
            for B in (-1.0, 1.0):
                A = 0.3
                target = [A*math.cos(theta)-B*math.sin(theta),
                          A*math.sin(theta)+B*math.cos(theta)]
                steps = connector(pose([0, 0], theta), target, 28)
                self.assertEqual([s["kind"] for s in steps],
                                 ["slide", "center_rotate", "slide",
                                  "center_rotate", "slide"])
                self.assertGreaterEqual(theta + steps[1]["angle"], 0)
                self.assertLessEqual(theta + steps[1]["angle"], math.pi)
                self.assertTrue(all(a["end"] == b["start"]
                                    for a, b in zip(steps, steps[1:])))
                self.assertLess(math.dist(steps[-1]["end"]["center"], target), 1e-12)
                self.assertAlmostEqual(steps[-1]["end"]["theta"], theta, places=14)
        direct = connector(pose([0, 0], 0), [F(3, 4), 0], 28)
        self.assertEqual(len(direct), 1)
        self.assertEqual(direct[0]["length"], F(3, 4))

    def test_max_level_finiteness_and_continuity(self):
        eps = F(1, 1 << (4 * MAX_N))
        record = generate(eps)
        self.assertEqual(record['n'], MAX_N)
        self.assertEqual(len(record['stations']), 4 * (1 << MAX_N) + 1)
        self.assertAlmostEqual(record['final_pose']['theta'], math.pi, places=13)
        self.assertLess(math.dist(record['final_pose']['center'],
                                  record['stations'][-1]['center']), 1e-8)
        for item in record['primitives']:
            for endpoint in (item['start'], item['end']):
                self.assertTrue(all(math.isfinite(v) for v in
                                    (*endpoint['center'], endpoint['theta'])))
        for a, b in zip(record['primitives'], record['primitives'][1:]):
            self.assertEqual(a['end'], b['start'])
        with self.assertRaises(ValueError):
            generate(eps / 16)

    def test_direct_coincident_center_branch(self):
        record = generate(F(1, 1 << 16))  # n=4; some adjacent centers coincide.
        centers = [item['center'] for item in record['stations']]
        self.assertTrue(any(a == b for a, b in zip(centers, centers[1:])))
        direct = connector(pose(centers[0], 0.0), centers[0], 28)
        self.assertEqual(len(direct), 1)
        self.assertEqual(direct[0]['kind'], 'slide')
        self.assertEqual(direct[0]['length'], 0)
        self.assertEqual(direct[0]['start'], direct[0]['end'])

    def test_exact_level_boundaries_and_bad_inputs(self):
        self.assertEqual(level(F(1, 16)), 1)
        self.assertEqual(level(F(1, 256)), 2)
        self.assertEqual(level(F(1, 256) + F(1, 100000)), 1)
        self.assertEqual(level(F(1, 1 << (4*MAX_N))), MAX_N)
        for eps in (F(0), -F(1, 16), F(1, 10), F(1, 1 << (4*(MAX_N+1)))):
            with self.assertRaises(ValueError):
                generate(eps)
        for n, q in ((0, 0), (2, -1), (2, 4)):
            with self.assertRaises(ValueError):
                triangle(n, q)
        for text in ("0", "-0.1", "banana", "1/0", "1/10", "1e-100"):
            process = subprocess.run([sys.executable, str(SCRIPT), text],
                                     capture_output=True, text=True, timeout=10)
            self.assertNotEqual(process.returncode, 0, text)
            self.assertEqual(process.stdout, "")
        result = subprocess.run([sys.executable, str(SCRIPT), "0.0625"],
                                capture_output=True, text=True, timeout=10, check=True)
        record = json.loads(result.stdout)
        self.assertEqual((record["eps"], record["n"], record["M"], record["R"]),
                         ("1/16", 1, 2, 28))
        self.assertIn("not this float output", record["limitations"][1])
        self.assertEqual(record["triangles"][1]["vertices"],
                         [["0", "-1/2"], ["0", "-1"], ["1", "0"]])
        rational = subprocess.run([sys.executable, str(SCRIPT), "1/256"],
                                  capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual((json.loads(rational.stdout)["eps"],
                          json.loads(rational.stdout)["n"]), ("1/256", 2))


if __name__ == "__main__":
    unittest.main()
