"""Synthetic drive-ratio algebra tests; no native arrays, analysis CLI or PDE."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np


TOOLS = Path(__file__).resolve().parents[1] / 'tools'
MODES = {'raw_declared_Vpp', 'equal_total_source_output_RMS_sum',
         'equal_total_power', 'skin_contact_only', 'legacy_composite_full_skin'}
DEGREES = {
    'surface_J_RMS_max_A_m2': 1, 'surface_J_RMS_p95_A_m2': 1,
    'contact_voltage_RMS_max_V': 1, 'SC_power_W': 2,
    'contact_power_W': 2, 'source_power_W': 2,
    'bulk_skin_J_vector_RMS_max_A_m2': 1,
    'bulk_skin_J_vector_RMS_p95_A_m2': 1,
    'skin_SC_plus_dermis_power_W': 2,
}


def coefficients():
    return {3000: np.array([.25+.01j, .04-.03j]),
            3030: np.array([.012j, .25-.02j]),
            9000: np.array([1/12-.03j, .008+.003j]),
            9090: np.array([-.003+.001j, -1/12+.002j])}


def probe_fixture():
    rows = []
    for depth in (5, 10, 15, 20):
        for name, x, y in (('center', 0, 0), ('xminus', -5, 0),
                           ('xplus', 5, 0), ('yminus', 0, -5), ('yplus', 0, 5)):
            for axis in ('x', 'y'):
                i = len(rows)+1
                rows.append(dict(id=f'{depth}-{name}-{axis}', RMS_V=i/100.,
                    Vpp_lower_V=i/80., Vpp_upper_V=i/70.,
                    fundamental_fixed_axis_envelope=dict(variation_range_V=i/120.),
                    center_xyz_mm=[x, y, depth], axis=axis, tip_spacing_mm=5,
                    spectrum=dict(scope='unloaded', sentinel=[i, .125])))
    return dict(status='complete', measurements=rows,
                coordinates='z positive depth; five centers, two axes; tip gap 5mm')


class DriveRatioAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(TOOLS))
        spec = importlib.util.spec_from_file_location('drive_ratio_audit_tested', TOOLS/'task1_drive_ratio_audit.py')
        cls.audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def test_componentwise_scaling_includes_harmonics_and_passive_output_columns(self):
        base=coefficients()
        result=self.audit.scaled_coefficients(base,[.5,2.])
        self.assertEqual(set(result),set(base))
        for frequency in base:
            np.testing.assert_array_equal(result[frequency],base[frequency]*np.array([.5,2.]))
        self.assertNotEqual(result[3000][1],0)
        self.assertNotEqual(result[3030][0],0)

    def test_coefficients_are_copies_and_never_mutate_input(self):
        base=coefficients();before={f:a.copy() for f,a in base.items()}
        result=self.audit.scaled_coefficients(base,[2.,1.])
        for f in base:
            np.testing.assert_array_equal(base[f],before[f])
            self.assertFalse(np.shares_memory(result[f],base[f]))
        result[3000][0]=99
        np.testing.assert_array_equal(base[3000],before[3000])

    def test_missing_or_extra_frequency_is_rejected(self):
        for variant in ('missing','extra'):
            base=coefficients()
            if variant=='missing':base.pop(9000)
            else:base[12000]=np.ones(2,dtype=complex)
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):
                self.audit.scaled_coefficients(base,[1.,1.])

    def test_malformed_or_nonfinite_complex_coefficient_is_rejected(self):
        for bad in (np.ones(3),np.ones((1,2)),np.array([math.nan,1.]),
                    np.array([1.,complex(0,math.inf)])):
            base=coefficients();base[3000]=bad
            with self.subTest(bad=repr(bad)),self.assertRaises((ValueError,RuntimeError)):
                self.audit.scaled_coefficients(base,[1.,1.])

    def test_source_drive_requires_two_finite_positive_amplitudes(self):
        for vector in ([1.],[1.,1.,1.],[0.,1.],[-.5,1.],[math.nan,1.],[1.,math.inf]):
            with self.subTest(vector=vector),self.assertRaises((ValueError,RuntimeError)):
                self.audit.scaled_coefficients(coefficients(),vector)

    def test_five_normalizations_keep_declared_output_vector_not_scalar_1Vpp(self):
        candidate={key:4. if degree==2 else 2. for key,degree in DEGREES.items()}
        baseline={key:1. for key in DEGREES}
        modes=self.audit.normalization_adapter(candidate,baseline,4.,2.,[2.,1.])
        self.assertEqual(set(modes),MODES)
        self.assertEqual(modes['raw_declared_Vpp']['source_Vpp_by_output'],[2.,1.])
        for mode in modes.values():
            self.assertNotIn('source_Vpp_per_output',mode)
            self.assertEqual(mode['raw_declared_source_Vpp_by_output'],[2.,1.])
            self.assertEqual(mode['source_Vpp_by_output'],[2.*mode['amplitude_scale'],mode['amplitude_scale']])
        low_burden={key:.01 if degree==2 else .1 for key,degree in DEGREES.items()}
        ceiling=self.audit.normalization_adapter(low_burden,baseline,1.,2.,[2.,1.])['legacy_composite_full_skin']
        self.assertAlmostEqual(ceiling['amplitude_scale'],.5)
        self.assertEqual(ceiling['source_Vpp_by_output'],[1.,.5])

    def test_normalized_current_is_linear_and_losses_are_quadratic(self):
        candidate={key:4. if degree==2 else 2. for key,degree in DEGREES.items()}
        baseline={key:1. for key in DEGREES}
        modes=self.audit.normalization_adapter(candidate,baseline,4.,2.,[.5,1.])
        for name in MODES-{'raw_declared_Vpp'}:
            mode=modes[name]
            self.assertAlmostEqual(mode['amplitude_scale'],.5)
            self.assertAlmostEqual(mode['sum_source_output_RMS_mA'],2.)
            for key,degree in DEGREES.items():
                self.assertAlmostEqual(mode['normalized_burdens'][key],candidate[key]*.5**degree)

    def test_normalization_adapter_leaves_burdens_and_source_vector_unchanged(self):
        candidate={key:4. if degree==2 else 2. for key,degree in DEGREES.items()}
        baseline={key:1. for key in DEGREES};source=[2.,1.]
        before=copy.deepcopy((candidate,baseline,source))
        self.audit.normalization_adapter(candidate,baseline,4.,2.,source)
        self.assertEqual((candidate,baseline,source),before)

    def test_probe_scaling_preserves_40_unique_ids_and_absolute_voltage_fields(self):
        probe=probe_fixture();result=self.audit.scaled_probe_rows(probe,2.5)
        self.assertEqual(len(result),40)
        self.assertEqual([row['id'] for row in result],[row['id'] for row in probe['measurements']])
        self.assertEqual(len({row['id'] for row in result}),40)
        for source,row in zip(probe['measurements'],result):
            for key in ('RMS_V','Vpp_lower_V','Vpp_upper_V'):
                self.assertAlmostEqual(row[key],source[key]*2.5)
            self.assertAlmostEqual(row['fundamental_envelope_variation_V'],
                source['fundamental_fixed_axis_envelope']['variation_range_V']*2.5)

    def test_unit_probe_scaling_leaves_centers_tip_spacing_and_spectrum_untouched(self):
        probe=probe_fixture();before=copy.deepcopy(probe)
        result=self.audit.scaled_probe_rows(probe,1.)
        self.assertEqual(probe,before)
        self.assertEqual(len({tuple(row['center_xyz_mm']) for row in probe['measurements']}),20)
        self.assertTrue(all(row['tip_spacing_mm']==5 for row in probe['measurements']))
        self.assertEqual(result[-1]['RMS_V'],probe['measurements'][-1]['RMS_V'])

    def test_probe_must_be_complete_with_40_distinct_measurement_ids(self):
        for variant in ('running','missing','duplicate'):
            probe=probe_fixture()
            if variant=='running':probe['status']='running'
            elif variant=='missing':probe['measurements'].pop()
            else:probe['measurements'][-1]['id']=probe['measurements'][0]['id']
            with self.subTest(variant=variant),self.assertRaises((ValueError,RuntimeError)):
                self.audit.scaled_probe_rows(probe,1.)

    def test_probe_scale_must_be_positive_and_finite(self):
        for scale in (0.,-1.,math.nan,math.inf):
            with self.subTest(scale=scale),self.assertRaises((ValueError,RuntimeError)):
                self.audit.scaled_probe_rows(probe_fixture(),scale)


if __name__=='__main__':
    unittest.main()
