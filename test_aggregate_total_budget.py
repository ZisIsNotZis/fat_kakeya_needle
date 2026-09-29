"""Regressions for the total-CPU grid aggregator (ticket 03)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import aggregate_total_budget as agg


def make_cell(fam="smooth", budget=60, seed=0, status="complete",
              area=0.4, reserve=None, *, total=None):
    cell = {
        "mode": "total_run", "protocol": "A_total_cpu", "family": fam,
        "seed": seed, "eps": 0.005,
        "requested_total_budget_cpu_s": budget,
        "reserved_validation_cpu_s": agg.FROZEN_RF[fam] if reserve is None
        else reserve,
        "status": status, "search_started": True,
        "selected_params": [0., 0.1, -0.2],
        "code_sha256": [{"file": "budget_total_integer.py", "sha256": "x"}],
        "environment": {"pyclipper": "1.4.0", "python": "3.12.3"},
        "validation": {"status": "ok",
                       "numeric_outer_area_range": [area, area * 1.001]},
        "total_cpu_s": total if total is not None else budget * 0.9,
        "numeric_outer_area": area if status == "complete" else None,
    }
    return cell


class AggregateTest(unittest.TestCase):
    def write_grid(self, tmp, mutate=None):
        for fam in agg.FAMILIES:
            for budget in agg.BUDGETS:
                for seed in agg.SEEDS:
                    cell = make_cell(fam, budget, seed,
                                     area=0.3 + 0.01 * agg.FAMILIES.index(fam))
                    if mutate:
                        cell = mutate(cell, fam, budget, seed) or cell
                    (tmp / f"{fam}_{seed}_{budget}.json").write_text(
                        json.dumps(cell))

    def test_full_valid_grid_aggregates(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d))
            result = agg.aggregate(Path(d))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cells"], 48)
        row = result["table"]["smooth"][60]
        self.assertEqual(row["valid_seeds"], [0, 1, 2])
        self.assertAlmostEqual(row["min_over_seeds"], 0.3)
        self.assertEqual(row["argmin_seed"], 0)
        self.assertGreaterEqual(row["hit_rate"], 0)

    def test_missing_cell_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d))
            (Path(d) / "smooth_0_60.json").unlink()
            result = agg.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")
        self.assertTrue(any("missing cell" in v for v in result["violations"]))

    def test_over_budget_cell_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d), mutate=lambda c, *a: c.update(
                total_cpu_s=c["requested_total_budget_cpu_s"] + 1.))
            result = agg.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")

    def test_wrong_reserve_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d), mutate=lambda c, *a: c.update(
                reserved_validation_cpu_s=1.))
            result = agg.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")

    def test_unranked_status_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d), mutate=lambda c, *a: c.update(
                status="over_budget", numeric_outer_area=None))
            result = agg.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")

    def test_duplicate_cell_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d))
            (Path(d) / "smooth_0_60_copy.json").write_text(
                (Path(d) / "smooth_0_60.json").read_text())
            result = agg.aggregate(Path(d))
        self.assertEqual(result["status"], "invalid_grid")
        self.assertTrue(any("duplicate" in v for v in result["violations"]))

    def test_hit_rate_definition(self):
        # areas by family index: smooth .30, hier .31, free .32, v2 .33;
        # global best at B60 = .30 (smooth), threshold .309 -> only smooth hits
        with tempfile.TemporaryDirectory() as d:
            self.write_grid(Path(d))
            result = agg.aggregate(Path(d))
        row = result["table"]["v2_repaired"][60]
        self.assertAlmostEqual(row["global_best_at_budget"], 0.3)
        self.assertAlmostEqual(row["hit_threshold"], 0.309)
        self.assertEqual(row["hit_rate"], 0.0)
        smooth_row = result["table"]["smooth"][60]
        self.assertEqual(smooth_row["hit_rate"], 1.0)
        hier_row = result["table"]["hierarchical"][60]
        self.assertEqual(hier_row["hit_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
