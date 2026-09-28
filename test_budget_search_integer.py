"""Budget and repaired-motion regressions; no long optimizer is launched."""
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import budget_search_integer as budget
import integer_motion_area


class BudgetSearchIntegerTests(unittest.TestCase):
    def test_v2_repaired_end_axis_join_and_integer_objective(self):
        family = budget.Family("v2_repaired", .01, smoke_k=2)
        params = [0., .1, .1, .2, .4, -.3]
        primitives = family.primitives(params)
        axis = math.expm1(.4)
        self.assertAlmostEqual(primitives[1]["end"]["center"][0], axis)
        self.assertEqual(primitives[1]["end"], primitives[2]["start"])
        self.assertAlmostEqual(primitives[-1]["end"]["center"][0],
                               2 * axis - math.expm1(0.))
        self.assertNotAlmostEqual(axis, 0.)
        result = budget.score(family, params, max_wall_s=10)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["step_fraction"], .1)

    def test_integer_scale_restored_on_failure_and_validation_quality(self):
        family = budget.Family("hierarchical", .01, smoke_k=2)
        with patch.object(integer_motion_area, "evaluate", side_effect=ValueError("bad")):
            result = budget.score(family, [0., 0., 0.], scale=1 << 38)
        self.assertEqual(result["status"], "error")
        self.assertEqual(integer_motion_area.SCALE, 1 << 40)
        with patch.object(budget, "score", side_effect=[
                {"status": "ok", "numeric_outer_area": 1.},
                {"status": "ok", "numeric_outer_area": 1.001},
                {"status": "resource_limited", "resource_limited": "time"},
                {"status": "ok", "numeric_outer_area": 1.002}]):
            validation = budget.validate(family, [0., 0., 0.])
        self.assertEqual(validation["status"], "quality_limited")
        self.assertEqual(len(validation["raw"]), 4)
        self.assertNotIn("numeric_outer_area_range", validation)
        with patch.object(budget, "score", side_effect=[
                {"status": "ok", "numeric_outer_area": a}
                for a in (1., 1.001, 1.002, 1.004)]):
            validation = budget.validate(family, [0., 0., 0.])
        self.assertEqual(validation["status"], "ok")
        self.assertEqual(validation["numeric_outer_area_range"], [1., 1.004])

    def test_run_records_cutoff_before_crossing_eval_and_failure_penalty(self):
        family = budget.Family("hierarchical", .01, smoke_k=2)  # population: 15
        clock = [0.]
        calls = [0]

        def fake_score(*args, **kwargs):
            calls[0] += 1
            clock[0] += .6
            if calls[0] == 1:
                return {"status": "resource_limited", "resource_limited": "mock limit"}
            return {"status": "ok", "numeric_outer_area": 100. - calls[0]}

        def fake_de(objective, bounds, **kwargs):
            self.assertEqual(kwargs["popsize"], 5)
            self.assertEqual(kwargs["workers"], 1)
            self.assertFalse(kwargs["polish"])
            while True:
                objective([0., 0., 0.])

        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "run.json"
            with (patch.object(budget, "score", side_effect=fake_score),
                  patch.object(budget.time, "process_time", side_effect=lambda: clock[0]),
                  patch.object(budget, "differential_evolution", side_effect=fake_de),
                  patch.object(budget, "validate", return_value={"status": "ok",
                       "numeric_outer_area_range": [1., 1.], "validation_cpu_s": 2.})):
                row = budget.run(family, 3, [1., 3., 10.], out)
            self.assertEqual(json.loads(out.read_text()), row)
            self.assertEqual(row["status"], "quality_limited")
            self.assertFalse(row["aggregate_ranking_authorized"])
            self.assertIn('not rigorously', row['limitation'])
            self.assertEqual(row["calls"], 17)
            self.assertEqual(row["valid_calls"], 16)
            self.assertEqual(row["failed_calls"][0]["status"], "resource_limited")
            self.assertEqual(row["eval_log"][0]["objective_value"], budget.PENALTY)
            self.assertFalse(row["checkpoints"][0]["search_started"])
            self.assertEqual(row["checkpoints"][0]["calls"], 1)
            self.assertGreaterEqual(row["checkpoints"][0]["observed_cpu_s"], 1.)
            self.assertGreaterEqual(row["checkpoints"][0]["observed_wall_s"], 0.)
            self.assertIn('crossing', row["checkpoints"][0]["boundary_note"])
            self.assertFalse(row["checkpoints"][1]["search_started"])
            self.assertEqual(row["checkpoints"][1]["calls"], 4)
            self.assertTrue(row["checkpoints"][2]["search_started"])
            self.assertEqual(row["checkpoints"][2]["calls"], 16)
            self.assertEqual(row["checkpoints"][2]["best_search_area"], 84.)
            self.assertEqual(row["validation_cpu_s"], 2.)
            self.assertGreater(row["discovery_cpu_s"], 10.)
            with self.assertRaises(FileExistsError):
                budget.run(family, 3, [1.], out)

    def test_validated_best_so_far_survives_worse_later_checkpoint(self):
        rows = [
            {'budget_cpu_s': 60., 'best_params': [1],
             'validation': {'status': 'ok', 'numeric_outer_area_range': [.4, .5]}},
            {'budget_cpu_s': 120., 'best_params': [2],
             'validation': {'status': 'ok', 'numeric_outer_area_range': [.6, .7]}},
            {'budget_cpu_s': 240., 'best_params': [3],
             'validation': {'status': 'ok', 'numeric_outer_area_range': [.3, .45]}},
            {'budget_cpu_s': 480., 'best_params': [4],
             'validation': {'status': 'quality_limited'}},
        ]
        budget.attach_best_validated_so_far(rows)
        self.assertEqual([r['best_validated_so_far']['numeric_upper'] for r in rows],
                         [.5, .5, .45, .45])
        self.assertEqual([r['best_validated_so_far']['first_budget_cpu_s'] for r in rows],
                         [60., 60., 240., 240.])

    def test_failure_and_eval_histories_are_bounded(self):
        family = budget.Family('hierarchical', .01, smoke_k=2)
        clock = [0.]
        def fail(*args, **kwargs):
            clock[0] += .1
            return {'status': 'error', 'error': 'mock'}
        def de(objective, bounds, **kwargs):
            while True:
                objective([0., 0., 0.])
        with tempfile.TemporaryDirectory() as folder:
            with (patch.object(budget, 'score', side_effect=fail),
                  patch.object(budget.time, 'process_time', side_effect=lambda: clock[0]),
                  patch.object(budget, 'differential_evolution', side_effect=de)):
                row = budget.run(family, 0, [5., 15.], Path(folder)/'bounded.json')
        self.assertGreater(row['failed_count'], budget.MAX_TRACE_ROWS)
        self.assertEqual(len(row['failed_calls']), budget.MAX_TRACE_ROWS)
        self.assertEqual(len(row['eval_log']), budget.MAX_TRACE_ROWS)
        self.assertGreater(row['eval_log_dropped'], 0)
        self.assertEqual(row['failed_log_dropped'], row['failed_count']-budget.MAX_TRACE_ROWS)
        self.assertTrue(all(c['best_validated_so_far'] is None for c in row['checkpoints']))

    def test_all_failed_population_never_ranks(self):
        family = budget.Family("hierarchical", .01, smoke_k=2)
        clock = [0.]

        def fail(*args, **kwargs):
            clock[0] += .5
            return {"status": "error", "error": "mock geometry"}

        def de(objective, bounds, **kwargs):
            while True:
                objective([0., 0., 0.])

        with tempfile.TemporaryDirectory() as folder:
            with (patch.object(budget, "score", side_effect=fail),
                  patch.object(budget.time, "process_time", side_effect=lambda: clock[0]),
                  patch.object(budget, "differential_evolution", side_effect=de),
                  patch.object(budget, "validate") as validate):
                row = budget.run(family, 0, [7., 8.], Path(folder) / "failed.json")
                validate.assert_not_called()
            self.assertEqual(row["status"], "quality_limited")
            self.assertTrue(row["search_started"])
            self.assertTrue(all(c["status"] == "unranked" for c in row["checkpoints"]))
            self.assertIsNone(row["best_search_area"])

    def test_aborted_run_persists_failure_and_cannot_resume_in_place(self):
        family = budget.Family("hierarchical", .01, smoke_k=2)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "abort.json"
            with patch.object(budget, "differential_evolution",
                              side_effect=KeyboardInterrupt("requested")):
                with self.assertRaises(KeyboardInterrupt):
                    budget.run(family, 0, [1.], out)
            stored = json.loads(out.read_text())
            self.assertEqual(stored["status"], "aborted")
            self.assertEqual(stored["abort_reason"], "KeyboardInterrupt: requested")
            with self.assertRaises(FileExistsError):
                budget.run(family, 0, [1.], out)

    def test_optimizer_early_exit_does_not_fabricate_future_checkpoint(self):
        family = budget.Family("hierarchical", .01, smoke_k=2)
        clock = [0.]

        def score(*args, **kwargs):
            clock[0] += 1.
            return {"status": "ok", "numeric_outer_area": 1.}

        def early_exit(objective, bounds, **kwargs):
            objective([0., 0., 0.])

        with tempfile.TemporaryDirectory() as folder:
            with (patch.object(budget, "score", side_effect=score),
                  patch.object(budget.time, "process_time", side_effect=lambda: clock[0]),
                  patch.object(budget, "differential_evolution", side_effect=early_exit),
                  patch.object(budget, "validate") as validate):
                row = budget.run(family, 0, [2., 5.], Path(folder) / "early.json")
                validate.assert_not_called()
            self.assertEqual(row["status"], "quality_limited")
            self.assertEqual(row["checkpoints"][0]["reason"],
                             "optimizer_terminated_before_budget")
            self.assertFalse(row["checkpoints"][1]["search_started"])

    def test_initial_checkpoint_is_atomic_and_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'checkpoint.json'
            def fail_after_partial(row, stream, **kwargs):
                stream.write('{"status":')
                raise RuntimeError('interrupted first dump')
            with patch.object(budget.json, 'dump', side_effect=fail_after_partial):
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    budget.create_output(target, {'status': 'running'})
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(folder).iterdir()), [])
            budget.create_output(target, {'status': 'running'})
            self.assertEqual(json.loads(target.read_text())['status'], 'running')
            with self.assertRaises(FileExistsError):
                budget.create_output(target, {'status': 'other'})
            self.assertEqual(json.loads(target.read_text())['status'], 'running')

    def test_preflight_seeded_ten_calls_and_exclusive_output(self):
        family = budget.Family("smooth", .01, smoke_k=2)
        seen = []

        def score(f, x, **kwargs):
            seen.append(tuple(x))
            return {"status": "ok", "numeric_outer_area": 1.,
                    "backend_version": "1.4.0"}

        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "preflight.json"
            with patch.object(budget, "score", side_effect=score):
                row = budget.preflight([family], 7, out)
                repeated = budget.preflight([family], 7, Path(folder) / "again.json")
            self.assertEqual(json.loads(out.read_text()), row)
            self.assertEqual(row["status"], "complete")
            self.assertIn('not rigorously', row['limitation'])
            self.assertEqual(list(row["excluded_nonoptimized_baselines"]),
                             ["keich_n4", "keich_n5"])
            self.assertNotIn("keich_n4", budget.FAMILIES)
            self.assertNotIn("keich_n5", budget.FAMILIES)
            self.assertEqual(row["families"][0]["dimension"], 13)
            self.assertEqual(row["families"][0]["population_evals"], 65)
            self.assertEqual(len(row["families"][0]["calls"]), 10)
            self.assertEqual(seen[:10], seen[10:])
            self.assertEqual(repeated["families"][0]["failure_count"], 0)
            with self.assertRaises(FileExistsError):
                budget.preflight([family], 7, out)


if __name__ == "__main__":
    unittest.main()
