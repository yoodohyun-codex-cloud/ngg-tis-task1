"""Pure admission/scaling fixtures; no files, native arrays or numerical solves."""
import copy
import math
import unittest

from drive_contracts import (
    baseline_close,
    relative_multipliers,
    require_baseline_QA,
    validate_descriptor,
)


def descriptor():
    return dict(path="/synthetic/saved-field.npz", SHA256="a" * 64, bytes=123,
                publication_commit="b" * 40,
                publication_target="data-native/synthetic/saved-field.npz",
                readback_passed=True)


def baseline_receipt():
    return dict(status="passed", baseline_multiplier=1.,
                map_checks={name: dict(passed=True) for name in
                            ("AM_max2074", "carrier_RMS", "Jtotal_vector_RMS")},
                unavailable_saved_float_maps=["AM_x", "AM_y", "AM_z", "carrier0_RMS", "carrier1_RMS"],
                statistics_passed=True, electrical_passed=True, source_identity_passed=True)


class DriveContracts(unittest.TestCase):
    def test_relative_ratios_preserve_the_requested_ratio_with_no_gain(self):
        for ratio, expected in ((1., (1., 1.)), (.8, (.8, 1.)), (1.25, (1., .8))):
            with self.subTest(ratio=ratio):
                result = relative_multipliers(ratio)
                self.assertEqual(result, expected)
                self.assertEqual(max(result), 1.)
                self.assertAlmostEqual(result[0] / result[1], ratio, places=14)

    def test_relative_ratio_rejects_nonpositive_nonfinite_and_untyped_values(self):
        for ratio in (0., -1., math.inf, -math.inf, math.nan, True, False, "0.8", None, 1j, [1.]):
            with self.subTest(ratio=ratio):
                with self.assertRaises((TypeError, ValueError)):
                    relative_multipliers(ratio)

    def test_field_baseline_uses_both_the_fixed_absolute_and_relative_tolerance(self):
        self.assertTrue(baseline_close(.5e-10, 0.))
        self.assertFalse(baseline_close(2e-10, 0.))
        reference = 2.
        tolerance = 1e-10 + 2e-7 * abs(reference)
        self.assertTrue(baseline_close(reference + .5 * tolerance, reference))
        self.assertFalse(baseline_close(reference + 2 * tolerance, reference))
        self.assertFalse(baseline_close(reference - 2 * tolerance, reference))

    def test_electrical_baseline_has_its_own_stricter_absolute_tolerance(self):
        self.assertTrue(baseline_close(.5e-15, 0., electrical=True))
        self.assertFalse(baseline_close(2e-15, 0., electrical=True))
        self.assertTrue(baseline_close(1e-12, 0.))
        self.assertFalse(baseline_close(1e-12, 0., electrical=True))
        reference = 1e-4
        tolerance = 1e-15 + 2e-7 * abs(reference)
        self.assertTrue(baseline_close(reference + .5 * tolerance, reference, electrical=True))
        self.assertFalse(baseline_close(reference + 2 * tolerance, reference, electrical=True))

    def test_baseline_closeness_never_accepts_nonfinite_or_boolean_inputs(self):
        for invalid in (math.nan, math.inf, -math.inf, True, False, "1", None):
            with self.subTest(invalid=invalid):
                self.assertFalse(baseline_close(invalid, 1.))
                self.assertFalse(baseline_close(1., invalid, electrical=True))

    def test_descriptor_is_an_exact_readback_identity_without_io_or_rewrite(self):
        value = descriptor()
        before = copy.deepcopy(value)
        result = validate_descriptor(value, expected_commit="b" * 40,
                                     expected_target=value["publication_target"],
                                     publication_role="result", expected_role="result")
        self.assertIs(result, value)
        self.assertEqual(value, before)
        source = dict(value, publication_commit="c" * 40,
                      publication_target="tools/synthetic/model.py", path="/synthetic/model.py")
        self.assertIs(validate_descriptor(source, expected_commit="c" * 40,
                                         expected_target="tools/synthetic/model.py",
                                         publication_role="source", expected_role="source"), source)

    def test_source_result_ownership_commit_and_target_have_no_fallback(self):
        value = descriptor()
        for changes in (dict(publication_role="source"), dict(expected_role="source"),
                        dict(publication_role="unknown", expected_role="unknown"),
                        dict(expected_commit="c" * 40), dict(expected_commit="b" * 39),
                        dict(expected_target="tools/synthetic/saved-field.npz")):
            args = dict(expected_commit="b" * 40, expected_target=value["publication_target"],
                        publication_role="result", expected_role="result")
            args.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    validate_descriptor(value, **args)
        missing_commit = {k: v for k, v in value.items() if k != "publication_commit"}
        with self.assertRaises(ValueError):
            validate_descriptor(missing_commit, expected_commit="b" * 40,
                                expected_target=value["publication_target"],
                                publication_role="result", expected_role="result")

    def test_descriptor_rejects_incomplete_hash_readback_size_and_unsafe_paths(self):
        for key, bad in (("SHA256", None), ("SHA256", "a" * 63), ("SHA256", "A" * 64),
                         ("SHA256", "g" * 64), ("bytes", True), ("bytes", 0),
                         ("bytes", 80 * 1024 ** 2), ("readback_passed", False),
                         ("readback_passed", 1), ("path", "relative/file.npz"),
                         ("path", "/synthetic/../file.npz")):
            value = descriptor()
            value[key] = bad
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(ValueError):
                    validate_descriptor(value, expected_commit="b" * 40,
                                        expected_target=value["publication_target"],
                                        publication_role="result", expected_role="result")
        for target in ("/absolute/file.npz", "data-native/../file.npz"):
            value = dict(descriptor(), publication_target=target)
            with self.assertRaises(ValueError):
                validate_descriptor(value, expected_commit="b" * 40, expected_target=target,
                                    publication_role="result", expected_role="result")

    def test_complete_baseline_receipt_is_pure_and_required_before_candidates(self):
        value = baseline_receipt()
        before = copy.deepcopy(value)
        self.assertTrue(require_baseline_QA(value))
        self.assertEqual(value, before)
        for key, bad in (("status", "pending"), ("status", "failed_preserved"),
                         ("baseline_multiplier", .8), ("baseline_multiplier", None),
                         ("statistics_passed", False), ("electrical_passed", False),
                         ("source_identity_passed", False)):
            bad_receipt = baseline_receipt()
            bad_receipt[key] = bad
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(ValueError):
                    require_baseline_QA(bad_receipt)

    def test_missing_or_failed_baseline_map_blocks_instead_of_dropping_a_map(self):
        value = baseline_receipt()
        value["map_checks"].pop("AM_max2074")
        with self.assertRaises(ValueError):
            require_baseline_QA(value)
        for missing in (False, True):
            value = baseline_receipt()
            if missing:
                value["map_checks"]["carrier_RMS"] = {}
            else:
                value["map_checks"]["carrier_RMS"]["passed"] = False
            with self.assertRaises(ValueError):
                require_baseline_QA(value)

    def test_unsaved_five_maps_are_explicitly_unavailable_never_fake_native_checks(self):
        value = baseline_receipt()
        value["map_checks"]["AM_x"] = dict(passed=True)
        with self.assertRaises(ValueError):
            require_baseline_QA(value)
        for unavailable in ([], ["AM_x"], ["AM_x", "AM_y", "AM_z", "carrier0_RMS", "AM_max2074"],
                            ["AM_x", "AM_y", "AM_z", "carrier0_RMS", "carrier0_RMS"], None):
            value = baseline_receipt()
            value["unavailable_saved_float_maps"] = unavailable
            with self.subTest(unavailable=unavailable):
                with self.assertRaises(ValueError):
                    require_baseline_QA(value)


if __name__ == "__main__":
    unittest.main()
