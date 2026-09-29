"""Protocol A total-CPU-budget runner regressions; no long optimizer runs."""
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import budget_search_integer as budget
import budget_total_integer as total_runner
import integer_motion_area


def ok_validation(range_pair, cpu_s):
    return {"status": "ok", "raw": [{"step_fraction": step, "scale": scale,
             "status": "ok", "cpu_s": cpu_s / 4}
            for step in (.0001, .00005) for scale in (1 << 38, 1 << 40)],
            "numeric_outer_area_range": list(range_pair),
            "relative_discrepancy": 0., "validation_cpu_s": cpu_s}


def fake_de(objective, bounds, **kwargs):
    assert kwargs["popsize"] == 5 and kwargs["workers"] == 1
    assert not kwargs["polish"] and kwargs["updating"] == "immediate"
    while True:
        objective([0., 0., 0.])


class BudgetTotalIntegerTests(unittest.TestCase):
    def run_mocked(self, folder, name, *, step, budget=10., reserve=3.,
                   validate_result=None, seed=3, score_status="ok",
                   validation_clock=None):
        """Mocked cell: score advances the CPU clock by `step` per call."""
        family = total_runner.Family("hierarchical", .01, smoke_k=2)
        clock = [0.]
        validation_calls = []

        def fake_score(f, x, **kwargs):
            clock[0] += step
            if score_status != "ok":
                return {"status": score_status, "error": "mock failure"}
            return {"status": "ok", "numeric_outer_area": 100. - clock[0] / step}

        def fake_validate(f, params, **kwargs):
            validation_calls.append((f.name, tuple(params)))
            if validation_clock is not None:
                clock[0] = validation_clock
            return validate_result

        out = Path(folder) / name
        with (patch.object(total_runner, "score", side_effect=fake_score),
              patch.object(total_runner.time, "process_time",
                           side_effect=lambda: clock[0]),
              patch.object(total_runner, "differential_evolution",
                           side_effect=fake_de),
              patch.object(total_runner, "validate",
                           side_effect=fake_validate)):
            row = total_runner.run(family, seed, budget, reserve, out)
        return row, out, clock, validation_calls

    def test_search_stops_at_deadline_and_publishes_within_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            # deadline 7; evals complete at .4..7.2; eval 18 crosses and is excluded
            row, out, _, validation_calls = self.run_mocked(
                folder, "eligible.json", step=.4, validation_clock=9.,
                validate_result=ok_validation((.5, .5), 2.))
            self.assertEqual(json.loads(out.read_text()), row)
            self.assertEqual(row["status"], "complete")
            self.assertEqual(row["mode"], "total_run")
            self.assertEqual(row["protocol"], "A_total_cpu")
            self.assertIn("not rigorously", row["limitation"])
            self.assertFalse(row["aggregate_ranking_authorized"])
            self.assertEqual(row["requested_total_budget_cpu_s"], 10.)
            self.assertEqual(row["reserved_validation_cpu_s"], 3.)
            self.assertEqual(row["search_deadline_cpu_s"], 7.)
            self.assertEqual(row["calls"], 18)
            self.assertEqual(row["valid_calls"], 18)
            self.assertTrue(row["search_started"])
            self.assertEqual(row["cross_cutoff_evals_excluded"], 1)
            # best completed candidate finished at cpu 6.8 (17th eval, area 83)
            self.assertEqual(row["selected_search_area"], 83.)
            self.assertEqual(row["selected_params"], [0., 0., 0.])
            self.assertGreaterEqual(row["eval_log"][-1]["cpu_s"], 7.)
            self.assertEqual(len(row["eval_log"]), 18)
            self.assertEqual(validation_calls, [("hierarchical", (0., 0., 0.))])
            self.assertAlmostEqual(row["search_cpu_s"], 7.2)
            self.assertAlmostEqual(row["validation_cpu_s"], 1.8)
            self.assertGreaterEqual(row["misc_cpu_s"], 0.)
            self.assertLessEqual(row["total_cpu_s"], 10.)
            self.assertEqual(row["overshoot_cpu_s"], 0.)
            self.assertEqual(row["numeric_outer_area"], .5)
            self.assertTrue(all(row["gates"].values()))
            self.assertIn("fresh np.random.default_rng", row["de"]["rng"])
            self.assertEqual(row["de"]["popsize"], 5)
            self.assertEqual(row["code_sha256"][0]["file"],
                             "budget_total_integer.py")
            self.assertEqual(row["environment"]["pyclipper"], "1.4.0")
            self.assertIn("timeout", row["external_timeout_note"])
            self.assertIn("SIGKILL", row["sigkill_note"])
            with self.assertRaises(FileExistsError):
                self.run_mocked(folder, "eligible.json", step=.4)

    def test_validation_cost_over_budget_is_typed_over_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            row, out, _, _ = self.run_mocked(
                folder, "over.json", step=.4, validation_clock=10.5,
                validate_result=ok_validation((.5, .5), 3.5))
            self.assertEqual(row["status"], "over_budget")
            self.assertNotIn("numeric_outer_area", row)
            self.assertFalse(row["gates"]["within_total_budget"])
            self.assertTrue(row["gates"]["population_initialized"])
            self.assertTrue(row["gates"]["validation_quality_ok"])
            self.assertAlmostEqual(row["overshoot_cpu_s"], .5)
            self.assertGreater(row["total_cpu_s"], 10.)
            self.assertIsNotNone(row["validation"]["numeric_outer_area_range"])
            self.assertEqual(json.loads(out.read_text())["status"], "over_budget")

    def test_quality_limited_validation_never_publishes_a_score(self):
        with tempfile.TemporaryDirectory() as folder:
            failed = {"status": "quality_limited",
                      "raw": [{"status": "resource_limited"}] * 3
                             + [{"status": "ok", "numeric_outer_area": 1.}],
                      "validation_cpu_s": 2.}
            row, out, _, calls = self.run_mocked(
                folder, "quality.json", step=.4, validation_clock=9.,
                validate_result=failed)
            self.assertEqual(len(calls), 1)
            self.assertEqual(row["status"], "quality_limited")
            self.assertNotIn("numeric_outer_area", row)
            self.assertFalse(row["gates"]["validation_quality_ok"])
            self.assertTrue(row["gates"]["within_total_budget"])
            self.assertTrue(row["gates"]["population_initialized"])
            self.assertEqual(json.loads(out.read_text())["status"],
                             "quality_limited")

    def test_uninitialized_population_is_unranked_and_skips_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            row, _, _, validation_calls = self.run_mocked(
                folder, "uninit.json", step=1., validation_clock=9.,
                validate_result=ok_validation((.5, .5), 2.))
            # 7 evaluations <= 15 population evals of hierarchical K2
            self.assertEqual(row["calls"], 7)
            self.assertFalse(row["search_started"])
            self.assertEqual(validation_calls, [])
            self.assertEqual(row["status"], "unranked")
            self.assertNotIn("numeric_outer_area", row)
            self.assertFalse(row["gates"]["population_initialized"])

    def test_all_failed_search_is_unranked_without_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            row, _, _, validation_calls = self.run_mocked(
                folder, "failed.json", step=.3, score_status="error")
            self.assertEqual(row["status"], "unranked")
            self.assertIsNone(row["selected_search_area"])
            self.assertIsNone(row["validation"])
            self.assertTrue(row["search_started"])
            self.assertEqual(row["failed_count"], row["calls"])
            self.assertEqual(validation_calls, [])
            self.assertNotIn("numeric_outer_area", row)

    def test_duplicate_output_path_is_rejected_without_rewriting(self):
        with tempfile.TemporaryDirectory() as folder:
            _, out, _, _ = self.run_mocked(
                folder, "dup.json", step=.4, validation_clock=9.,
                validate_result=ok_validation((.5, .5), 2.))
            before = out.read_text()
            with self.assertRaises(FileExistsError):
                self.run_mocked(folder, "dup.json", step=.4)
            self.assertEqual(out.read_text(), before)

    def test_initial_output_is_atomic_exclusive_and_logs_are_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "atomic.json"

            def fail_after_partial(row, stream, **kwargs):
                stream.write('{"status":')
                raise RuntimeError("interrupted first dump")

            with patch.object(budget.json, "dump",
                              side_effect=fail_after_partial):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    total_runner.create_output(target, {"status": "running"})
            self.assertEqual(list(Path(folder).iterdir()), [])
            total_runner.create_output(target, {"status": "running"})
            with self.assertRaises(FileExistsError):
                total_runner.create_output(target, {"status": "other"})
            self.assertEqual(json.loads(target.read_text())["status"], "running")

        def failing(clock):
            clock[0] += .04
            return {"status": "resource_limited", "resource_limited": "mock"}

        with tempfile.TemporaryDirectory() as folder:
            family = total_runner.Family("hierarchical", .01, smoke_k=2)
            clock = [0.]
            out = Path(folder) / "bounded.json"
            with (patch.object(total_runner, "score",
                               side_effect=lambda *a, **k: failing(clock)),
                  patch.object(total_runner.time, "process_time",
                               side_effect=lambda: clock[0]),
                  patch.object(total_runner, "differential_evolution",
                               side_effect=fake_de)):
                row = total_runner.run(family, 0, 10., 3., out)
            self.assertGreater(row["failed_count"], total_runner.MAX_TRACE_ROWS)
            self.assertEqual(len(row["failed_calls"]), total_runner.MAX_TRACE_ROWS)
            self.assertEqual(len(row["eval_log"]), total_runner.MAX_TRACE_ROWS)
            self.assertGreater(row["eval_log_dropped"], 0)
            self.assertEqual(row["failed_log_dropped"],
                             row["failed_count"] - total_runner.MAX_TRACE_ROWS)
            self.assertEqual(row["status"], "unranked")

    def test_v2_repaired_real_target_completes_end_to_end(self):
        family = total_runner.Family("v2_repaired", .01, smoke_k=2)
        params = [0., .1, .1, .2, .4, -.3]
        clock = [0.]

        def real_de(objective, bounds, **kwargs):
            for _ in range(family.population_evals + 1):
                objective(params)

        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "v2.json"
            with (patch.object(total_runner.time, "process_time",
                               side_effect=lambda: clock[0]),
                  patch.object(total_runner, "differential_evolution",
                               side_effect=real_de),
                  patch.object(total_runner, "validate",
                               return_value=ok_validation((.4, .40001), 2.))):
                row = total_runner.run(family, 1, 1000., 500., out)
            self.assertEqual(row["status"], "complete")
            self.assertTrue(row["search_started"])
            self.assertEqual(row["calls"], family.population_evals + 1)
            self.assertEqual(row["selected_params"], params)
            real_area = budget.score(family, params)["numeric_outer_area"]
            self.assertAlmostEqual(row["selected_search_area"], real_area)
            self.assertGreater(row["selected_search_area"], 0.)
            self.assertEqual(row["numeric_outer_area"], .40001)
            self.assertTrue(row["optimizer_terminated_before_deadline"])
            self.assertEqual(row["dimension"], 6)
            self.assertEqual(row["K"], 2)
            self.assertIn("not rigorously", row["limitation"])
            self.assertTrue(all(math.isfinite(a) for a in
                                row["validation"]["numeric_outer_area_range"]))

    def test_run_rejects_invalid_budget_arguments(self):
        family = total_runner.Family("hierarchical", .01, smoke_k=2)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "never.json"
            for total, reserve in ((0., 0.), (-1., 0.), (10., 10.),
                                   (10., 11.), (10., -1.),
                                   (math.nan, 1.), (math.inf, 1.)):
                with self.assertRaises(ValueError):
                    total_runner.run(family, 0, total, reserve, out)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_decide_outcome_gate_order_and_budget_boundary(self):
        validation = ok_validation((.4, .5), 1.)
        self.assertEqual(total_runner.decide_outcome(
            search_started=False, selected_params=None, validation=None,
            total_cpu_s=5., total_budget=10.), ("unranked", False, None))
        self.assertEqual(total_runner.decide_outcome(
            search_started=True, selected_params=None, validation=None,
            total_cpu_s=5., total_budget=10.), ("unranked", False, None))
        self.assertEqual(total_runner.decide_outcome(
            search_started=True, selected_params=[0.],
            validation={"status": "quality_limited"},
            total_cpu_s=5., total_budget=10.), ("quality_limited", False, None))
        self.assertEqual(total_runner.decide_outcome(
            search_started=True, selected_params=[0.], validation=validation,
            total_cpu_s=10.5, total_budget=10.), ("over_budget", False, None))
        self.assertEqual(total_runner.decide_outcome(
            search_started=True, selected_params=[0.], validation=validation,
            total_cpu_s=10., total_budget=10.), ("complete", True, .5))

    def publish(self, folder, name, clock_values):
        row = {"mode": "total_run", "status": "running", "gates": None}
        out = Path(folder) / name
        with patch.object(total_runner.time, "process_time",
                          side_effect=iter(clock_values)):
            total_runner.publish_result(row, out, total_budget=10.,
                search_started=True, selected_params=[0.],
                validation=ok_validation((.5, .6), 1.))
        return row, json.loads(out.read_text())

    def test_publication_rewrite_demotes_score_when_write_exceeds_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            row, stored = self.publish(folder, "demote.json", [9.9, 10.2])
            self.assertEqual(row["status"], "over_budget")
            self.assertEqual(stored["status"], "over_budget")
            self.assertNotIn("numeric_outer_area", stored)
            self.assertTrue(stored["demoted_after_publication"])
            self.assertFalse(stored["gates"]["within_total_budget"])
            self.assertEqual(stored["total_cpu_s"], 10.2)
            self.assertAlmostEqual(stored["overshoot_cpu_s"], .2)
            self.assertIn("demotes", stored["publication_note"])

    def test_publication_rewrite_keeps_score_when_still_within_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            row, stored = self.publish(folder, "keep.json", [9., 9.05])
            self.assertEqual(row["status"], "complete")
            self.assertEqual(stored["status"], "complete")
            self.assertEqual(stored["numeric_outer_area"], .6)
            self.assertNotIn("demoted_after_publication", stored)
            self.assertEqual(stored["total_cpu_s"], 9.05)
            self.assertTrue(stored["gates"]["within_total_budget"])

    def test_preflight_validation_is_deterministic_inbounds_and_unranked(self):
        families = [total_runner.Family(name, .01, smoke_k=2)
                    for name in total_runner.FAMILIES]
        seen = []

        def fake_validate(family, params, **kwargs):
            seen.append((family.name, tuple(params)))
            return ok_validation((1., 1.001), .5)

        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "preflight.json"
            with patch.object(total_runner, "validate",
                              side_effect=fake_validate):
                row = total_runner.preflight_validation(families, 7, out,
                                                        candidates=2)
                repeated = total_runner.preflight_validation(
                    families, 7, Path(folder) / "again.json", candidates=2)
            self.assertEqual(json.loads(out.read_text()), row)
            self.assertEqual(row["status"], "complete")
            self.assertFalse(row["aggregate_ranking_authorized"])
            self.assertIn("never ranked", row["no_ranking_note"])
            self.assertEqual([f["family"] for f in row["families"]],
                             list(total_runner.FAMILIES))
            for family_row in row["families"]:
                self.assertEqual(len(family_row["candidates"]), 2)
                bounds = family_row["bounds"]
                for candidate in family_row["candidates"]:
                    self.assertEqual(len(candidate["raw"]), 4)
                    self.assertEqual(candidate["status"], "ok")
                    for raw, (step, scale) in zip(
                            candidate["raw"], [(s, c) for s in (.0001, .00005)
                                               for c in (1 << 38, 1 << 40)]):
                        self.assertEqual(raw["step_fraction"], step)
                        self.assertEqual(raw["scale"], scale)
                        self.assertGreaterEqual(raw["cpu_s"], 0.)
                    self.assertTrue(all(lo <= p <= hi for p, (lo, hi)
                                        in zip(candidate["params"], bounds)))
                self.assertEqual(family_row["validation_cpu_max_s"], .5)
            self.assertEqual(seen[:8], seen[8:])
            self.assertEqual(repeated["families"][0]["candidates"][0]["params"],
                             row["families"][0]["candidates"][0]["params"])
            with self.assertRaises(FileExistsError):
                total_runner.preflight_validation(families, 7, out, candidates=1)
            with self.assertRaises(ValueError):
                total_runner.preflight_validation(families, 7,
                                                  Path(folder) / "zero.json",
                                                  candidates=0)

    def test_abort_persists_failure_and_sigkill_is_never_complete(self):
        family = total_runner.Family("hierarchical", .01, smoke_k=2)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "abort.json"
            with patch.object(total_runner, "differential_evolution",
                              side_effect=KeyboardInterrupt("requested")):
                with self.assertRaises(KeyboardInterrupt):
                    total_runner.run(family, 0, 10., 3., out)
            stored = json.loads(out.read_text())
            self.assertEqual(stored["status"], "aborted")
            self.assertEqual(stored["abort_reason"], "KeyboardInterrupt: requested")
            self.assertIn("never ranked", stored["sigkill_note"])
            self.assertIn("'running'", stored["sigkill_note"])
            with self.assertRaises(FileExistsError):
                total_runner.run(family, 0, 10., 3., out)


if __name__ == "__main__":
    unittest.main()
