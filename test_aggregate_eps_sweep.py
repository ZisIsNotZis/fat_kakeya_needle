"""Regressions for the eps-sweep aggregator (ticket 05)."""
import json
import tempfile
import unittest
from pathlib import Path

import aggregate_eps_sweep as sweep
import aggregate_total_budget as agg


def make_cell(fam="smooth", eps=0.05, seed=0, area=0.4, budget=480,
              status="complete"):
    return {
        "mode": "total_run", "protocol": "A_total_cpu", "family": fam,
        "seed": seed, "eps": eps,
        "requested_total_budget_cpu_s": budget,
        "reserved_validation_cpu_s": agg.FROZEN_RF[fam],
        "status": status, "search_started": True,
        "selected_params": [0., 0.1],
        "code_sha256": [{"file": "budget_total_integer.py", "sha256": "x"}],
        "environment": {"pyclipper": "1.4.0"},
        "validation": {"status": "ok",
                       "numeric_outer_area_range": [area, area * 1.001]},
        "total_cpu_s": budget * 0.9,
        "numeric_outer_area": area if status == "complete" else None,
        "aggregate_ranking_authorized": False,
    }


class SweepTest(unittest.TestCase):
    def write(self, tmp, mutate=None):
        for fam in agg.FAMILIES:
            for eps in sweep.EPS_GRID:
                for seed in agg.SEEDS:
                    cell = make_cell(fam, eps, seed,
                                     area=0.5 * eps + 0.01 * agg.FAMILIES.index(fam))
                    if mutate:
                        cell = mutate(cell, fam, eps, seed) or cell
                    (tmp / f"{fam}_{eps}_{seed}.json").write_text(
                        json.dumps(cell))

    def test_full_grid_ok(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(Path(d))
            result = sweep.aggregate(Path(d))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cells"], 84)
        self.assertEqual(sorted(result["table"]), sorted(agg.FAMILIES))

    def test_missing_cell_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(Path(d))
            (Path(d) / "smooth_0.05_0.json").unlink()
            result = sweep.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")

    def test_wrong_budget_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(Path(d), mutate=lambda c, *a: c.update(
                requested_total_budget_cpu_s=240))
            result = sweep.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")

    def test_out_of_grid_eps_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(Path(d), mutate=lambda c, *a: c.update(eps=0.3))
            result = sweep.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")

    def test_non_eps_checks_still_enforced(self):
        """allowed_eps=None must not disable the ticket-03 checks."""
        with tempfile.TemporaryDirectory() as d:
            def mutate(cell, fam, eps, seed):
                if seed == 0:
                    cell["protocol"] = "search_cpu"
                    cell["environment"]["pyclipper"] = "1.3.0"
                    cell["reserved_validation_cpu_s"] = 1.0
                return cell
            self.write(Path(d), mutate=mutate)
            result = sweep.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")
        joined = " ".join(result["violations"])
        for needle in ("protocol", "pyclipper", "R_f"):
            self.assertIn(needle, joined)

    def test_log_law_shape_monotone(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(Path(d))
            result = sweep.aggregate(Path(d))
        shape = sweep.log_law_shape(result)
        self.assertTrue(shape["smooth"]["monotone_decreasing"])
        self.assertIn("r2", shape["smooth"]["log_fit_A_over_ln_plus_B"])


if __name__ == "__main__":
    unittest.main()
