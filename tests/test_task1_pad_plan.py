"""Contract regressions prevent pad/source confusion and fabricated comparisons."""
import copy
import importlib.util
import math
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "task1_pad_plan", Path(__file__).resolve().parents[1] / "tools/task1_pad_plan.py")
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class PadPlanContractTests(unittest.TestCase):
    def setUp(self):
        self.plan = planner.make_plan("a" * 40, "b" * 64)

    def test_sixteen_finite_cases_keep_two_outputs_and_one_ground(self):
        self.assertEqual(16, len(self.plan["cases"]))
        self.assertEqual([], planner.validate_plan(self.plan))
        for case in self.plan["cases"]:
            self.assertEqual(case["n_pads"], len(case["pads"]))
            self.assertEqual(2, len(case["sources"]))
            self.assertEqual(1, case["n_return_nodes"])
            self.assertEqual({"GND"}, set(case["pad_to_return_node"].values()))
            self.assertEqual({"OUT0", "OUT1"}, set(case["pad_to_source_node"].values()))
            self.assertFalse(case["execution_allowed"])

    def test_pad_count_does_not_silently_add_power_or_unterminate_output(self):
        for case in self.plan["cases"]:
            for source in case["sources"]:
                self.assertEqual(1.0, source["source_Vpp"])
                self.assertEqual(50.0, source["source_resistance_ohm"])
                self.assertEqual({"source_peak_V": 0.0, "resistance_ohm": 50.0},
                                 source["inactive_frequency_termination"])
            for connection in case["frequency_connections"]:
                outputs = connection["outputs"]
                self.assertEqual(1, sum(o["state"] == "driven" for o in outputs.values()))
                for output in outputs.values():
                    self.assertEqual(50.0, output["series_resistance_ohm"])
                    if output["state"] == "terminated":
                        self.assertEqual({"real": 0.0, "imag": 0.0}, output["ideal_peak_phasor_V"])

    def test_historical_square_command_normalizes_whole_waveform_to_one_vpp(self):
        square = next(c for c in self.plan["cases"] if "square_3h" in c["waveform_branch"])
        a1, a3 = square["sources"][0]["dimensionless_harmonic_coefficients"]
        # Analytic maximum at theta=pi/4; third harmonic is not an extra1Vpp source.
        peak = .5 * (a1 * math.sin(math.pi / 4) + a3 * math.sin(3 * math.pi / 4))
        self.assertAlmostEqual(.5, peak)
        self.assertGreater(.5 * a1, peak)

    def test_area_modes_are_separate_and_impossible_top_area_is_rejected(self):
        for case in self.plan["cases"]:
            area = case["area_comparison"]
            self.assertAlmostEqual(area["per_pad_area_mm2"] * case["n_pads"], area["total_contact_area_mm2"])
            if area["mode"] == "equal_total_area":
                self.assertEqual(900.0, area["total_contact_area_mm2"])
            elif case["n_pads"] >= 12:
                self.assertGreater(area["total_contact_area_mm2"], math.pi * 25**2)
                self.assertEqual("necessary_area_bound_failed", case["geometry_status"])

    def test_contract_rejects_resealed_hardware_phantom_and_result_changes(self):
        edits = [lambda p: p["cases"][0].__setitem__("n_outputs", 4),
                 lambda p: p["phantom"].__setitem__("diameter_mm", 100),
                 lambda p: p["cases"][0]["sources"][0]["inactive_frequency_termination"].__setitem__("resistance_ohm", 0),
                 lambda p: p["cases"][0]["normalizations"]["equal_surface_burden"]["metrics"].__setitem__("target_tis_mean_V_per_cm", 0),
                 lambda p: p["cases"][0].__setitem__("execution_allowed", True)]
        for edit in edits:
            changed = copy.deepcopy(self.plan)
            edit(changed)
            for case in changed["cases"]:
                planner.seal(case, "config_sha256")
            planner.seal(changed, "plan_sha256")
            self.assertTrue(planner.validate_plan(changed))

    def test_no_computed_results_or_implicit_geometry_for_expanded_pads(self):
        for case in self.plan["cases"]:
            for normalization in case["normalizations"].values():
                self.assertTrue(all(v is None for v in normalization["metrics"].values()))
                self.assertIsNone(normalization["scale"])
                self.assertIsNone(normalization["reference_limits"])
            if case["n_pads"] > 4:
                self.assertTrue(all(p["geometry"] is None for p in case["pads"]))
                self.assertEqual("grouped_pad_solver_required", case["solver_support"])

    def test_preview_keeps_reference_and_missing_absolute_burden_metrics_visible(self):
        preview = planner.render_preview(self.plan)
        self.assertEqual(4, preview.count("<th>4 패드 / 2 출력</th>"))
        self.assertIn("동일 표면 부담 ROI 절대 mean / P10 (V/cm)", preview)
        self.assertIn("—는 미계산이며 0이 아닙니다", preview)


if __name__ == "__main__":
    unittest.main()
