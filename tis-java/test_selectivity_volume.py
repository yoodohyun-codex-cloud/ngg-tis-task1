"""Analytic-only fixtures. No source cache, PDE, Java or GUI data is touched."""
import copy
import json
import math
import time
import unittest

import numpy as np

from selectivity_volume import (VolumeAnalysisError, VolumeDeadlineExceeded,
                               evaluate_volume, native_region_weights,
                               weighted_statistics)


def fixture(h=2.5, csv_rounding=False):
    faces = np.array([0, .1, 5.1, 10.1, 25.1])
    axis = -25+(np.arange(round(50/h))+.5)*h
    yy, xx = np.meshgrid(axis, axis, indexing="ij")
    mask = xx*xx+yy*yy < 25**2
    xy = np.column_stack((xx[mask], yy[mask]))
    rows = []
    for k, (lo, hi) in enumerate(zip(faces[:-1], faces[1:])):
        for x, y in xy:
            vol = h*h*(hi-lo)*1e-9
            if csv_rounding:
                vol = float(f"{vol:.11g}")
            rows.append((x, y, (lo+hi)/2, k, vol))
    grid = np.array(rows, dtype=[(key, float) for key in
                    ("x_mm", "y_mm", "z_mm", "layer", "volume_m3")])
    meta = dict(h_xy_mm=h, radius_mm=25, z_faces_mm=faces.tolist(),
                layer_counts=[1, 1, 1, 1], geometry_volume_tolerance_relative=.01,
                target_volume_tolerance_relative=.001,
                source_provenance={"fixture": "analytic constant fields only"})
    a = np.tile(np.array([1, 1, 0], complex), (len(grid), 1))
    b = 2j*a
    return grid, meta, {3000: a, 3030: b}


class SelectivityVolumeTests(unittest.TestCase):
    def setUp(self):
        self.grid, self.meta, self.spectra = fixture()

    def score(self, spectra=None, **kwargs):
        return evaluate_volume(self.spectra if spectra is None else spectra,
                               self.grid, self.meta, fundamental_frequencies_Hz=(3000, 3030),
                               fibonacci_count=16, **kwargs)

    def test_actual_geometry_and_disjoint_tissue_strata(self):
        weights, receipt = native_region_weights(self.grid, self.meta)
        self.assertLess(abs(receipt["target_relative_volume_deviation"]), .001)
        self.assertLess(abs(receipt["domain_relative_volume_deviation"]), .01)
        np.testing.assert_allclose(weights["target"]+weights["off_target"], weights["total"], rtol=0, atol=1e-22)
        np.testing.assert_allclose(weights["surface_0_5"]+weights["subsurface_5_10"]+
                                   weights["remaining"]+weights["target"], weights["total"], rtol=0, atol=1e-22)
        layer = self.grid["layer"]
        self.assertGreater(weights["surface_0_5"][layer == 0].sum(), 0)
        self.assertGreater(weights["subsurface_5_10"][layer == 1].sum(), 0)
        self.assertGreater(weights["remaining"][layer == 2].sum(), 0)
        self.assertEqual(weights["target"][layer != 3].sum(), 0)

    def test_constant_field_analytic_rms_tis_and_relative_volume(self):
        result = self.score(thresholds={"relative_example": 2.8, "above_every_cell": 3.0})
        for region in result["metrics"]["regions"].values():
            for key in ("min", "p10", "p50", "p95", "max", "mean"):
                self.assertAlmostEqual(region["statistics"]["maxTIS"][key], 2*math.sqrt(2), places=12)
                self.assertAlmostEqual(region["statistics"]["fixedTIS"][key], 2*math.sqrt(2), places=12)
                self.assertAlmostEqual(region["statistics"]["RMS"][key], math.sqrt(5), places=12)
            self.assertEqual(region["high_modulation_volume"]["relative_example"]["maxTIS"]["fraction"], 1)
            self.assertEqual(region["high_modulation_volume"]["above_every_cell"]["maxTIS"]["fraction"], 0)
        np.testing.assert_allclose(result["scalars"]["fixed_modulation_depth"], .5)
        json.dumps(result["metrics"], allow_nan=False)

    def test_default_exact_2074_legacy_directions(self):
        result = evaluate_volume(self.spectra, self.grid, self.meta,
                                 fundamental_frequencies_Hz=(3000, 3030))
        self.assertEqual(result["metrics"]["total_sampled_directions"], 2074)
        np.testing.assert_allclose(result["scalars"]["maxTIS"], 2*math.sqrt(2), rtol=1e-14)

    def test_harmonic_is_in_actual_rms_only(self):
        spectra = dict(self.spectra)
        spectra[9000] = np.tile(np.array([0, 0, 4j]), (len(self.grid), 1))
        result = self.score(spectra)
        np.testing.assert_allclose(result["scalars"]["RMS"], math.sqrt(13))
        np.testing.assert_allclose(result["scalars"]["maxTIS"], 2*math.sqrt(2))

    def test_zero_or_single_carrier_has_exact_zero_tis(self):
        spectra = {f: np.zeros_like(a) for f, a in self.spectra.items()}
        zero = self.score(spectra)
        self.assertFalse(zero["scalars"]["fixed_modulation_depth_defined"].any())
        self.assertEqual(float(zero["scalars"]["maxTIS"].sum()), 0)
        spectra[3000] = self.spectra[3000]
        single = self.score(spectra)
        self.assertEqual(float(single["scalars"]["maxTIS"].sum()), 0)
        self.assertEqual(float(single["scalars"]["fixedTIS"].sum()), 0)

    def test_amplitude_and_common_phase_scaling_input_not_mutated(self):
        original_grid = self.grid.copy()
        original_spectra = {f: a.copy() for f, a in self.spectra.items()}
        meta_before = copy.deepcopy(self.meta)
        first = self.score()
        second = self.score({f: a*3*np.exp(.73j) for f, a in self.spectra.items()})
        for key in ("maxTIS", "fixedTIS", "RMS"):
            np.testing.assert_allclose(second["scalars"][key], 3*first["scalars"][key], rtol=1e-13)
        np.testing.assert_array_equal(self.grid, original_grid)
        for f in self.spectra:
            np.testing.assert_array_equal(self.spectra[f], original_spectra[f])
        self.assertEqual(self.meta, meta_before)

    def test_fixed_orientation_can_differ_from_voxel_max(self):
        result = self.score(fixed_direction=(0, 0, 1))
        self.assertEqual(float(result["scalars"]["fixedTIS"].sum()), 0)
        self.assertGreater(float(result["scalars"]["maxTIS"].min()), 0)

    def test_inverse_volume_ecdf_and_ties(self):
        result = weighted_statistics([2, 1, 2, 3], [1, 1, 7, 1])
        self.assertEqual(result["p10"], 1)
        self.assertEqual(result["p50"], 2)
        self.assertEqual(result["p95"], 3)
        self.assertAlmostEqual(result["mean"], 2)

    def test_incomplete_mask_wrong_layer_and_wrong_volume_rejected(self):
        for kind in ("missing", "layer", "volume", "coordinate"):
            grid = self.grid.copy()
            if kind == "missing":
                grid = grid[:-1]
            elif kind == "layer":
                grid["layer"][0] = 1
            elif kind == "volume":
                grid["volume_m3"][0] *= 2
            else:
                grid["x_mm"][0] += .01
            with self.subTest(kind=kind), self.assertRaises(VolumeAnalysisError):
                native_region_weights(grid, self.meta)

    def test_actual_metadata_not_inferred_and_geometry_gate_not_renormalized(self):
        for kind in ("faces", "counts", "tolerance", "radius"):
            meta = copy.deepcopy(self.meta)
            if kind == "faces":
                meta.pop("z_faces_mm")
            elif kind == "counts":
                meta["layer_counts"][0] = 2
            elif kind == "tolerance":
                meta["geometry_volume_tolerance_relative"] = .0001
            else:
                meta["radius_mm"] = 20
            with self.subTest(kind=kind), self.assertRaises(VolumeAnalysisError):
                native_region_weights(self.grid, meta)

    def test_nonfinite_missing_frequency_or_wrong_shape_rejected(self):
        for kind in ("nan", "missing", "shape"):
            spectra = {f: a.copy() for f, a in self.spectra.items()}
            if kind == "nan":
                spectra[3000][0, 0] = np.nan
            elif kind == "missing":
                del spectra[3030]
            else:
                spectra[3000] = spectra[3000][:-1]
            with self.subTest(kind=kind), self.assertRaises(VolumeAnalysisError):
                self.score(spectra)

    def test_cached_weights_strict_identity(self):
        weights, _ = native_region_weights(self.grid, self.meta)
        self.score(region_weights=weights)
        weights["target"] = weights["target"].copy()
        weights["target"][0] = 1e-12
        with self.assertRaises(VolumeAnalysisError):
            self.score(region_weights=weights)

    def test_invalid_threshold_does_not_create_zero_threshold_success(self):
        for threshold in (0, -1, float("nan")):
            with self.subTest(threshold=threshold), self.assertRaises(VolumeAnalysisError):
                self.score(thresholds={"bad": threshold})

    def test_expired_deadline_preserved(self):
        with self.assertRaises(VolumeDeadlineExceeded):
            self.score(deadline_monotonic=time.monotonic()-1)

    def test_csv_volume_printing_roundoff_does_not_break_partition(self):
        grid, meta, _ = fixture(csv_rounding=True)
        weights, receipt = native_region_weights(grid, meta)
        self.assertLess(receipt["max_relative_partition_roundoff"], 1e-13)
        self.assertLess(abs(receipt["source_csv_volume_relative_rounding"]), 2e-10)
        self.assertTrue(np.all(weights["remaining"] >= 0))


if __name__ == "__main__":
    unittest.main()
