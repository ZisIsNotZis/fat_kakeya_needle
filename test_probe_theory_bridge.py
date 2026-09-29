"""Tests for the theory-bridge probe (ticket 04). Numerical-estimate tier."""
import math
import unittest
from pathlib import Path

import numpy as np

import motion_adapters
import probe_theory_bridge as p
from motion_adapters import _full_halfturn


class ProbeTest(unittest.TestCase):
    def _setup(self):
        return p.load_carrier()

    def test_baseline_rebuild_matches_evaluate_saved(self):
        record, model, full = self._setup()
        row = motion_adapters.evaluate_saved(
            Path(p.CARRIER), 0, max_wall_s=30, max_polygons=100000,
            step_fraction=0.1)
        rebuilt = p.evaluate_primitives(p.first_half(model, full),
                                        record["eps"], step_fraction=0.1)
        self.assertEqual(rebuilt["status"], "ok")
        self.assertAlmostEqual(rebuilt["numeric_outer_area"],
                               row["numeric_outer_area"], places=12)

    def test_excursion_continuity_and_offset(self):
        record, model, full = self._setup()
        first, offset = p.excursion_first_half(model, full, 128, 4, 2.0)
        for a, b in zip(first, first[1:]):
            self.assertTrue(np.allclose(a["end"]["center"],
                                        b["start"]["center"]))
            self.assertEqual(a["end"]["theta"], b["start"]["theta"])
        u = model.base.u
        expect = sum(2.0 * (u[i] - u[i + 1]) for i in range(128, 132))
        self.assertTrue(np.allclose(offset, expect))

    def test_zero_radius_window_is_degenerate_in_place_rotation(self):
        """R=0 collapses the legs to a rotation about the needle center.

        That is a DIFFERENT primitive from the archived pivot about the
        offset pivot point (different swept area), so no area identity is
        asserted -- only structure and continuity.
        """
        record, model, full = self._setup()
        first, offset = p.excursion_first_half(model, full, 10, 3, 0.)
        self.assertTrue(np.allclose(offset, 0.))
        self.assertEqual(len(first), len(p.first_half(model, full)) + 3 * 3)
        for a, b in zip(first, first[1:]):
            self.assertTrue(np.allclose(a["end"]["center"],
                                        b["start"]["center"]))

    def test_mirror_preserves_kinds_and_angles(self):
        record, model, full = self._setup()
        first, _ = p.excursion_first_half(model, full, 128, 4, 2.0)
        full_prims = _full_halfturn(first)
        self.assertEqual(len(full_prims), 2 * len(first))
        kinds_first = [x["kind"] for x in first]
        mirrored = [x["kind"] for x in reversed(full_prims[len(first):])]
        self.assertEqual(kinds_first, mirrored)

    def test_window_outside_first_half_rejected(self):
        record, model, full = self._setup()
        with self.assertRaises(ValueError):
            p.excursion_first_half(model, full, model.K - 1, 4, 2.0)

    def test_run_writes_results(self):
        out = Path("/tmp/probe_smoke.json")
        result = p.run(out_path=out, confirm=False)
        self.assertGreater(result["baseline_area"], 0)
        self.assertEqual(len(result["variants"]), 41)
        for row in result["variants"]:
            self.assertEqual(row["tier"], "numerical_estimate")
        out.unlink()


if __name__ == "__main__":
    unittest.main()
