"""Synthetic actual-frequency resynthesis; no native data or real CLI runs."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np


TOOLS=Path(__file__).resolve().parents[1]/'tools'


class FakeSampler:
    def __init__(self, grid, geometry):
        pass

    def stencil(self, point, gamma):
        return {'indices': np.array([0]), 'weights': np.array([1.])}


class FakePost:
    LayeredPotentialSampler=FakeSampler
    _DIRECTIONS=np.eye(3)

    @staticmethod
    def _deadline(deadline, stage):
        pass


def fixture():
    frequencies=(3000, 3030, 9000, 9090)
    contacts=np.zeros(4, dtype=[('pad', int), ('area_m2', float)])
    contacts['pad']=np.arange(4);contacts['area_m2']=1e-6
    basis={'f': {}, 'grid': np.zeros(1), 'config': {}}
    geometry={'gamma_S_m': {f: 1.+0.j for f in frequencies}}
    for f in frequencies:
        high=f>=9000;g=.002 if high else .001;h=g/5
        source=np.array([[g, -h], [-h, g]], complex)
        density=np.array([[g, -h, -(g-h)/2, -(g-h)/2],
                          [-h, g, -(g-h)/2, -(g-h)/2]], complex)/1e-6
        loss=np.zeros((6, 2, 2), complex)
        loss[5]=25*source.conj().T@source
        loss[0]=.25*source-loss[5]
        field=np.array([[[0., 3.j, 0.]], [[0., -3.j, 0.]]]) if high else \
            np.array([[[1., 0., 0.]], [[-1., 0., 0.]]], complex)
        basis['f'][f]=dict(contacts=contacts.copy(), source=source, density=density,
                          loss=loss, field=field)
        basis['config'][f'z.{f}.re']='0.002' if high else '0.001'
        basis['config'][f'z.{f}.im']='0'
    return basis, geometry


class FrequencyResynthesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(TOOLS))
        spec=importlib.util.spec_from_file_location('frequency_resynthesis_tested', TOOLS/'task1_frequency_resynthesis.py')
        cls.audit=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def electrical(self, basis, geometry, pair):
        return self.audit.electrical_for_pair(basis, self.audit.sine_coefficients(pair),
                                              geometry, pair, FakePost, math.inf)

    def test_coefficients_keep_actual_low_and_high_frequency_keys(self):
        for pair in ((3000, 3030), (9000, 9090)):
            with self.subTest(pair=pair):
                result=self.audit.sine_coefficients(pair)
                self.assertEqual(set(result), set(pair))
                np.testing.assert_array_equal(result[pair[0]], [-1.j, 0.j])
                np.testing.assert_array_equal(result[pair[1]], [0.j, -1.j])

    def test_unregistered_missing_duplicate_reversed_or_crossed_pairs_are_rejected(self):
        for pair in ((3000,), (3000, 3000), (3030, 3000), (3000, 9090),
                     (2000, 2010), (9000, 9090, 3000)):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                self.audit.sine_coefficients(pair)

    def test_coefficients_return_independent_vectors_without_mutating_pair(self):
        pair=[9000, 9090];before=pair.copy()
        result=self.audit.sine_coefficients(pair)
        result[9000][0]=99
        fresh=self.audit.sine_coefficients(pair)
        self.assertEqual(pair, before)
        np.testing.assert_array_equal(fresh[9000], [-1.j, 0.j])
        self.assertFalse(np.shares_memory(fresh[9000], fresh[9090]))

    def test_high_pair_uses_actual_9k_basis_and_never_requires_3k_aliases(self):
        basis, geometry=fixture()
        low=self.electrical(basis, geometry, (3000, 3030))
        high_only=copy.deepcopy(basis)
        high_only['f']={f: row for f, row in high_only['f'].items() if f>=9000}
        high_only['config']={key: value for key, value in high_only['config'].items()
                             if key.startswith(('z.9000.', 'z.9090.'))}
        high=self.electrical(high_only, {'gamma_S_m': {9000: 1.j, 9090: 1.j}}, (9000, 9090))
        self.assertAlmostEqual(low['target20_modulation_V_m'], 2.)
        self.assertAlmostEqual(high['target20_modulation_V_m'], 6.)
        self.assertAlmostEqual(low['target20_total_E_RMS_V_m'], 1.)
        self.assertAlmostEqual(high['target20_total_E_RMS_V_m'], 3.)
        self.assertEqual(high['actual_fundamental_Hz'], [9000, 9090])
        self.assertEqual(high['beat_frequency_Hz'], 90)
        self.assertEqual(low['beat_frequency_Hz'], 30)
        self.assertEqual({row['frequency_Hz'] for row in high['centre_field_spectrum']}, {9000, 9090})
        self.assertAlmostEqual(high['source_power_W'], 2*low['source_power_W'])

    def test_other_output_ideal_zero_retains_50ohm_passive_termination(self):
        basis, geometry=fixture()
        result=self.electrical(basis, geometry, (9000, 9090))
        currents={row['frequency_Hz']: np.array(row['real_A'])+1.j*np.array(row['imaginary_A'])
                  for row in result['source_current_spectrum']}
        loaded={row['frequency_Hz']: np.array(row['real_V'])+1.j*np.array(row['imaginary_V'])
                for row in result['loaded_metal_voltage_spectrum']}
        coefficients=self.audit.sine_coefficients((9000, 9090))
        for f, active in ((9000, 0), (9090, 1)):
            self.assertNotEqual(currents[f][1-active], 0)
            np.testing.assert_allclose(loaded[f], .5*coefficients[f]-50*currents[f], rtol=0, atol=1e-15)
            self.assertAlmostEqual(abs(loaded[f][1-active]), 50*abs(currents[f][1-active]))

    def test_current_contact_and_power_metrics_use_analytic_frequency_correct_values(self):
        basis, geometry=fixture();result=self.electrical(basis, geometry, (3000, 3030))
        g, h=.001, .0002
        expected_current=math.sqrt((g*g+h*h)/2)
        np.testing.assert_allclose(result['source_current_RMS_by_output_mA'], [expected_current*1000]*2,
                                   rtol=1e-14, atol=1e-14)
        expected_j=expected_current/1e-6
        self.assertAlmostEqual(result['surface_J_RMS_max_A_m2'], expected_j)
        self.assertAlmostEqual(result['surface_J_RMS_p95_A_m2'], expected_j)
        self.assertAlmostEqual(result['contact_voltage_RMS_max_V'], expected_j*.001)
        self.assertAlmostEqual(result['source_power_W'], .5*g)
        self.assertAlmostEqual(result['SC_power_W']+result['contact_power_W']+result['source_resistor_power_W'], .5*g)
        self.assertLessEqual(result['driven_max_current_relative_error'], 2e-6)
        self.assertLessEqual(result['driven_max_power_relative_error'], 2e-7)

    def test_current_or_power_conservation_failure_is_rejected(self):
        for variant in ('current', 'power'):
            basis, geometry=fixture()
            if variant=='current':basis['f'][9000]['density'][0, 0]*=2
            else:basis['f'][9000]['loss']*=2
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                self.electrical(basis, geometry, (9000, 9090))

    def test_true_two_fundamental_envelope_uses_30_or_90Hz_beat_without_frequency_relabelling(self):
        for pair, beat in (((3000, 3030), 30), ((9000, 9090), 90)):
            coefficients=self.audit.sine_coefficients(pair)
            amplitudes=np.array([coefficients[pair[0]][0], coefficients[pair[1]][1]])
            times=np.array([0., 1/(2*beat), 1/beat])
            # Actual carrier phases, no substitution of carrier frequency labels.
            envelope=np.abs(np.exp(2.j*np.pi*times[:, None]*np.array(pair))@amplitudes)
            np.testing.assert_allclose(envelope, [2., 0., 2.], rtol=0, atol=1e-12)
            self.assertAlmostEqual(np.ptp(envelope), 2., places=12)

    def test_electrical_resynthesis_does_not_mutate_cached_basis_or_geometry(self):
        basis, geometry=fixture();before=copy.deepcopy((basis, geometry))
        self.electrical(basis, geometry, (9000, 9090))
        self.assertEqual(basis['config'], before[0]['config'])
        self.assertEqual(geometry, before[1])
        for f in basis['f']:
            for name, array in basis['f'][f].items():
                np.testing.assert_array_equal(array, before[0]['f'][f][name])


if __name__=='__main__':
    unittest.main()
