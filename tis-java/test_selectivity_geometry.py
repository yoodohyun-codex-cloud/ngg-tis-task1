"""Small analytic geometry tests; no solver, Java, field or source-file writes."""

import copy
import math
import unittest

import numpy as np

import selectivity_geometry as g


class GeometryTests(unittest.TestCase):
    def test_all_candidates_and_preserved_rejections(self):
        candidates = g.designs()
        self.assertEqual(len(candidates), 10)
        self.assertEqual(len({d["id"] for d in candidates}), 10)
        for design in candidates:
            before = copy.deepcopy(design)
            report = g.validate_design(design)
            self.assertEqual(report["status"], "valid_geometry", (design["id"], report))
            self.assertEqual(design, before)
            self.assertGreaterEqual(report["minimum_gap_lower_mm"], 1-1e-10)
            self.assertLessEqual(report["rmax_upper_mm"], 25+1e-10)
        old = g.proposed_rejections()
        self.assertEqual(len(old), 3)
        for design in old:
            before = copy.deepcopy(design)
            report = g.mask(design, 1.25)
            self.assertEqual(report["status"], "rejected_geometry")
            self.assertEqual(report["contacts"], [])
            self.assertEqual(design, before)

    def test_analytic_area_curve_bound_and_original_square(self):
        for design in g.designs()[:5]:
            for pad in design["pads"]:
                self.assertAlmostEqual(pad["analytic_area_mm2"], 225, places=11)
                self.assertGreater(g.polygon_area(pad["polygon_mm"]), 0)
                self.assertLess(pad["curve_area_relative_error"], 1e-6)
                if pad["shape"] != "rectangle":
                    self.assertEqual(len(pad["polygon_mm"]), 4096)
        baseline = g.validate_design(g.designs()[0])
        self.assertAlmostEqual(baseline["rmax_upper_mm"], math.hypot(17.5, 17.5), places=12)
        self.assertAlmostEqual(baseline["minimum_gap_lower_mm"], 5, places=12)
        original = g.designs()[0]
        adjacent = g.designs()[-1]
        self.assertEqual([p["center_mm"] for p in original["pads"]],
                         [[-10, -10], [10, 10], [10, -10], [-10, 10]])
        self.assertEqual([p["center_mm"] for p in adjacent["pads"]],
                         [[-10, -10], [10, -10], [10, 10], [-10, 10]])
        self.assertEqual(original["return_connection"], "all_return_pads_ideal_common_GND")

    def test_exact_cell_intersections_and_fan(self):
        triangle = np.array([[0, 0], [2, 0], [0, 2]], float)
        clipped = g.clip_polygon_to_cell(triangle, 0, 1, 0, 1)
        self.assertAlmostEqual(g.polygon_area(clipped), 1, places=14)
        self.assertAlmostEqual(g.polygon_area(g.clip_polygon_to_cell(triangle, 1, 2, 0, 1)), .5, places=14)
        self.assertEqual(len(g.clip_polygon_to_cell(triangle, 3, 4, 0, 1)), 0)
        self.assertEqual(g._points_in_convex(triangle, np.array([[.2, .2], [1.5, 1.5], [0, 0]])).tolist(),
                         [True, False, True])
        # A pad wholly contained inside one face, with no cell corner in pad.
        tiny = np.array([[.2, .2], [.4, .2], [.4, .4], [.2, .4]])
        self.assertAlmostEqual(g.polygon_area(g.clip_polygon_to_cell(tiny, 0, 1, 0, 1)), .04, places=14)

    def test_minkowski_distance_and_ideal_curve_lower_bound(self):
        square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
        self.assertAlmostEqual(g.polygon_gap_mm(square, square+[3, 0]), 2, places=12)
        self.assertAlmostEqual(g.polygon_gap_mm(square, square+[2, 2]), math.sqrt(2), places=12)
        self.assertEqual(g.polygon_gap_mm(square, square+[.5, 0]), 0)
        self.assertEqual(g.polygon_gap_mm(square, square+[1, 0]), 0)
        a = g._pad("circle", (0, 0), 2, 2)
        b = g._pad("circle", (4, 0), 2, 2)
        gap = g.polygon_gap_mm(a["polygon_mm"], b["polygon_mm"])
        lower = gap-a["curve_hausdorff_upper_mm"]-b["curve_hausdorff_upper_mm"]
        self.assertLessEqual(lower, 2)
        self.assertGreaterEqual(gap, 2-1e-12)

    def test_partial_contact_mask_area_no_renormalization(self):
        for design in (g.designs()[0], g.designs()[1], g.designs()[2], g.designs()[4]):
            before = copy.deepcopy(design)
            for h in (1.25, .625):
                result = g.mask(design, h)
                self.assertEqual(result["status"], "valid_contact_mask", (design["id"], h, result["rejection_reasons"]))
                for row in result["areas"]:
                    self.assertLessEqual(row["relative_error_to_polygon"], 1e-10)
                    self.assertLess(row["relative_error_to_analytic"], 1e-6)
                self.assertAlmostEqual(sum(c["area_m2"] for c in result["contacts"]),
                                       sum(p["polygon_area_mm2"] for p in design["pads"])*1e-6, places=14)
                self.assertTrue(all(0 < c["area_m2"] <= h*h*1e-6*(1+1e-12) for c in result["contacts"]))
            self.assertEqual(design, before)
        baseline = g.mask(g.designs()[0], 1.25)
        self.assertEqual(len(baseline["contacts"]), 4*12*12)
        self.assertTrue(all(c["area_m2"] == 1.25**2*1e-6 for c in baseline["contacts"]))
        # Keep geometry valid but move an outer disk toward the voxelized edge:
        # unsupported patch area must reject, with actual area retained.
        edge = g._design("edge-test", "synthetic", "circle", 4, 4, radius=22)
        result = g.mask(edge, 10)
        self.assertEqual(result["status"], "rejected_geometry")
        self.assertTrue(any(a["unsupported_area_mm2"] > 0 for a in result["areas"]))

    def test_invalid_geometry_and_grid_inputs(self):
        for h in (0, -1, math.nan, .7, .001):
            with self.assertRaises(ValueError):
                g.mask(g.designs()[0], h)
        bad = g.designs()[0]
        bad["pads"][0]["polygon_mm"].reverse()
        with self.assertRaisesRegex(ValueError, "CCW"):
            g.validate_design(bad)
        with self.assertRaises(ValueError):
            g.clip_polygon_to_cell([[0, 0], [1, 0], [0, 1]], 1, 0, 0, 1)

    def test_exact_two_pad_C1_subset_and_metadata_guards(self):
        original = g.designs()[2]  # curved fractional contacts in both pairs
        original_before = copy.deepcopy(original)
        original_mask = g.mask(original, 1.25)
        for pair in (0, 1):
            control = copy.deepcopy(original)
            control["pads"] = [control["pads"][pair], control["pads"][pair+2]]
            for k, pad in enumerate(control["pads"]):
                pad.update(pad=k, role="signal" if k == 0 else "common_gnd_return",
                           original_source_pad=pair if k == 0 else pair+2,
                           original_source_output=pair if k == 0 else None,
                           source_output=0 if k == 0 else None)
            control.update(source_outputs=1, channels=1, total_pads=2,
                           control_for_design=original["id"], indexed_pair=pair,
                           id=original["id"]+f"-C1pair{pair}")
            before = copy.deepcopy(control)
            result = g.mask(control, 1.25)
            self.assertEqual(result["status"], "valid_contact_mask")
            self.assertEqual(result["physical_control_scope"], "actual_two_pad_single_output")
            self.assertEqual(result["original_pad_indices"], [pair, pair+2])
            expected = [dict(row, pad=0 if row["pad"] == pair else 1)
                        for row in original_mask["contacts"] if row["pad"] in (pair, pair+2)]
            self.assertEqual(result["contacts"], expected)
            self.assertEqual(len(result["expected_pad_areas_m2"]), 2)
            self.assertEqual(control, before)
            changed = copy.deepcopy(control)
            changed["pads"][0]["polygon_mm"][0][0] += 1e-9
            with self.assertRaisesRegex(ValueError, "exact indexed"):
                g.validate_design(changed)
            for key, value in (("indexed_pair", 2), ("control_for_design", "unknown"),
                               ("channels", 2), ("total_pads", 4)):
                changed = copy.deepcopy(control)
                changed[key] = value
                with self.assertRaises(ValueError):
                    g.validate_design(changed)
        self.assertEqual(original, original_before)


if __name__ == "__main__":
    unittest.main()
