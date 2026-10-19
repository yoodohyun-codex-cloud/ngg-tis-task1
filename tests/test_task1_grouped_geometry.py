import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "task1_grouped_geometry", Path(__file__).resolve().parents[1] / "tools/task1_grouped_geometry.py")
geometry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(geometry)


class GroupedGeometryTests(unittest.TestCase):
    def test_literal_legacy_centers_and_height_cannot_fit_gap_family(self):
        geometry.geometry_receipt(geometry.rectangles(4, center_x_mm=10, center_y_mm=10, height_mm=15))
        for count in (8, 12, 16):
            with self.assertRaisesRegex(ValueError, "outside D50"):
                geometry.geometry_receipt(geometry.rectangles(count, center_x_mm=10,
                                                              center_y_mm=10, height_mm=15))

    def test_explicit_position_shape_control_makes_all_four_counts_feasible(self):
        for count in (4, 8, 12, 16):
            pads = geometry.rectangles(count)
            receipt = geometry.geometry_receipt(pads)
            self.assertAlmostEqual(900, receipt["analytic_total_area_mm2"])
            self.assertLess(receipt["farthest_corner_radius_mm"], 25)
            self.assertGreaterEqual(receipt["minimum_pad_gap_mm"] + 1e-10, 1)
            for node, expected in ((0, 225), (1, 225), (-1, 450)):
                self.assertAlmostEqual(expected, sum(p["area_mm2"] for p in pads if p["node"] == node))

    def test_fractional_mask_areas_survive_coarse_and_reference_xy(self):
        for count in (4, 8, 12, 16):
            for spacing in (1.25, .625):
                pads = geometry.rectangles(count)
                rows, areas = geometry.mask_rows(pads, spacing)
                self.assertEqual(set(range(count)), {r[0] for r in rows})
                self.assertAlmostEqual(.0009, sum(areas))
                self.assertTrue(all(abs(a / (.0009 / count) - 1) < 1e-10 for a in areas))

    def test_clipped_staircase_candidates_are_rejected_without_renormalization(self):
        rejected = geometry.rectangles(16, center_x_mm=10.4, center_y_mm=7.3, height_mm=13.5)
        geometry.geometry_receipt(rejected)
        with self.assertRaisesRegex(ValueError, "56.180000000mm2 expected=56.250000000mm2"):
            geometry.mask_rows(rejected, 1.25)
        with self.assertRaisesRegex(ValueError, "staircase mesh clipped"):
            geometry.mask_rows(geometry.rectangles(16), 50 / 120)

    def test_generation_keeps_five_controls_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-run"
            manifest = geometry.generate_family(output)
            self.assertEqual([4, 4, 8, 12, 16], [c["n_pads"] for c in manifest["cases"]])
            self.assertFalse(manifest["execution_allowed"])
            self.assertEqual(0, manifest["pde_jobs"])
            for case in manifest["cases"]:
                properties = geometry.read_properties(case["config_file"])
                self.assertEqual("2", properties["n_outputs"])
                self.assertEqual(case["n_pads"], len(case["pad_node_ids"]))
                self.assertEqual(case["config_sha256"], geometry.sha(case["config_file"]))
            with self.assertRaises(FileExistsError):
                geometry.generate_family(output)


if __name__ == "__main__":
    unittest.main()
