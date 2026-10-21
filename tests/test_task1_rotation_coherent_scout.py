"""Synthetic rotated-geometry coherent scout contracts; no native inputs or PDE."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
LINEAR=('target20_modulation_V_m','target20_total_E_RMS_V_m','surface_J_RMS_max_A_m2',
    'surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V','max_source_current_RMS_mA')
QUADRATIC=('SC_power_W','contact_power_W','skin_power_W','tissue_contact_power_W',
    'source_power_W','source_resistor_power_W')


def metrics_fixture():
    result={key:float(index+1)*.3 for index,key in enumerate(LINEAR)}
    result.update({key:float(index+1)*.01 for index,key in enumerate(QUADRATIC)})
    result['sampled_direction_count']=2074
    result['source_current_RMS_by_output_mA']=[1.,2.]
    for key,unit,size in (('source_current_spectrum','A',2),('loaded_metal_voltage_spectrum','V',2),
                          ('centre_field_spectrum','V_m',3)):
        result[key]=[dict(frequency_Hz=f,**{'real_'+unit:[.1*(column+1)*(row+1)if f in(3000,3030)else 0. for column in range(size)],
            'imaginary_'+unit:[-.05*(column+1)*(row+1)if f in(3000,3030)else 0. for column in range(size)]})
            for row,f in enumerate((3000,3030,9000,9090))]
    return result


def scaled_metrics(source,scale):
    result=copy.deepcopy(source)
    for key in LINEAR:result[key]*=scale
    for key in QUADRATIC:result[key]*=scale**2
    result['source_current_RMS_by_output_mA']=[value*scale for value in source['source_current_RMS_by_output_mA']]
    for key in ('source_current_spectrum','loaded_metal_voltage_spectrum','centre_field_spectrum'):
        for row in result[key]:
            for field in row:
                if field!='frequency_Hz':row[field]=[value*scale for value in row[field]]
    return result


class RotationCoherentScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rotation_coherent_scout_tested',ROOT/'tools/task1_rotation_coherent_scout.py')
        cls.scout=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.scout)

    def test_exact_five_condition_identities(self):
        self.assertEqual([row['id']for row in self.scout.CONDITIONS],['rotation-sine-control',
            'rotation-coherent-r0p5-p090','rotation-coherent-r0p5-p270','rotation-coherent-r1-p090','rotation-coherent-r1-p270'])

    def test_control_has_exact_exclusive_unit_sine_coefficients_and_zero_thirds(self):
        coefficients=self.scout.control_coefficients()
        self.assertEqual(set(coefficients),{3000,3030,9000,9090})
        np.testing.assert_array_equal(coefficients[3000],[-1j,0j])
        np.testing.assert_array_equal(coefficients[3030],[0j,-1j])
        np.testing.assert_array_equal(coefficients[9000],[0j,0j])
        np.testing.assert_array_equal(coefficients[9090],[0j,0j])
        second=self.scout.control_coefficients();coefficients[3000][0]=88j
        np.testing.assert_array_equal(second[3000],[-1j,0j])

    def test_four_coherent_seeds_preserve_actual_complex_quadrature_and_unitarity(self):
        for ratio in (.5,1.):
            for phase in(90,270):
                coefficients=self.scout.seed_coefficients(ratio,phase)
                angle=np.deg2rad(phase)
                expected=-1j/np.sqrt(1+ratio**2)*np.array([[1,-ratio*np.exp(-1j*angle)],[ratio*np.exp(1j*angle),1]])
                actual=np.stack([coefficients[3000],coefficients[3030]])
                np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-15)
                np.testing.assert_allclose(actual.conj().T@actual,np.eye(2),rtol=0,atol=6e-16)
                np.testing.assert_array_equal(coefficients[9000],np.zeros(2,dtype=complex))
                np.testing.assert_array_equal(coefficients[9090],np.zeros(2,dtype=complex))

    class FakeSamplingLimits:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)

    def test_condition_control_is_analytic_unit_vpp_and_not_two_tone_normalized(self):
        declared=self.scout.CONDITIONS[0]
        calls=[]
        def statistics(frequencies,phasors,fundamentals,*,sampling):
            carrier=(3000,3030)[len(calls)];calls.append(carrier)
            self.assertEqual(list(frequencies),[carrier]);self.assertEqual(list(fundamentals),[carrier])
            np.testing.assert_array_equal(phasors,[-.5j])
            return dict(Vpp_lower_V=.99999,Vpp_upper_V=1.00001)
        coefficients,proof=self.scout.condition_coefficients(declared,statistics,self.FakeSamplingLimits)
        self.assertEqual(calls,[3000,3030]);self.assertFalse(proof['normalization_performed'])
        for f,expected in self.scout.control_coefficients().items():np.testing.assert_array_equal(coefficients[f],expected)
        self.assertEqual(proof['source_Vpp_intervals_V'],[[1.,1.],[1.,1.]])

    def test_condition_coherent_uses_full_actual_waveform_brackets_per_output(self):
        for declared in self.scout.CONDITIONS[1:]:
            calls=[]
            def statistics(frequencies,phasors,fundamentals,*,sampling):
                self.assertEqual(list(frequencies),[3000,3030]);self.assertEqual(list(fundamentals),[3000,3030])
                self.assertEqual(sampling.max_statistics_samples,262144)
                upper=(2.,4.)[len(calls)];calls.append(np.asarray(phasors).copy())
                return dict(Vpp_lower_V=upper*(1-5e-7),Vpp_upper_V=upper)
            coefficients,proof=self.scout.condition_coefficients(declared,statistics,self.FakeSamplingLimits)
            seed=self.scout.seed_coefficients(declared['mix_ratio'],declared['phase_deg'])
            self.assertEqual(len(calls),2)
            for output,phasors in enumerate(calls):
                np.testing.assert_allclose(phasors,.5*np.array([seed[f][output]for f in(3000,3030)]),rtol=0,atol=1e-15)
            for f in seed:np.testing.assert_allclose(coefficients[f],seed[f]*[.5,.25],rtol=0,atol=1e-15)
            self.assertLessEqual(proof['maximum_bracket_width_V'],1e-6)
            np.testing.assert_allclose(proof['source_Vpp_intervals_V'],[[1-5e-7,1.],[1-5e-7,1.]],rtol=0,atol=1e-15)

    def test_equal_sine_cached_regression_needs_no_square_fundamental_rescaling(self):
        cached=metrics_fixture();before=copy.deepcopy(cached)
        proof=self.scout.validate_cached_sine(copy.deepcopy(cached),cached)
        self.assertTrue(proof['passed']);self.assertEqual(proof['amplitude_scale'],1.)
        self.assertEqual(proof['maximum_absolute_error'],0.)
        self.assertEqual(set(proof['linear_metric_fields']),set(LINEAR))
        self.assertEqual(set(proof['quadratic_metric_fields']),set(QUADRATIC))
        self.assertEqual(cached,before)

    def test_cached_sine_regression_scales_current_field_linearly_and_power_quadratically(self):
        cached=metrics_fixture();actual=scaled_metrics(cached,.5)
        proof=self.scout.validate_cached_sine(actual,cached,amplitude_scale=.5)
        self.assertTrue(proof['passed']);self.assertEqual(proof['amplitude_scale'],.5)
        self.assertEqual(proof['maximum_absolute_error'],0.)
        self.assertNotEqual(actual['source_power_W'],cached['source_power_W']*.5)

    def test_cached_sine_regression_rejects_scalar_error_or_wrong_complex_phase(self):
        cached=metrics_fixture()
        for mutation in ('linear','power','current','phase','third'):
            actual=copy.deepcopy(cached)
            if mutation=='linear':actual['target20_modulation_V_m']+=1e-6
            elif mutation=='power':actual['SC_power_W']+=1e-6
            elif mutation=='current':actual['source_current_RMS_by_output_mA'][0]+=1e-6
            elif mutation=='phase':actual['centre_field_spectrum'][0]['imaginary_V_m'][1]*=-1
            else:actual['centre_field_spectrum'][2]['real_V_m'][0]=.1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.scout.validate_cached_sine(actual,cached)

    def test_cached_sine_regression_rejects_spectrum_frequency_dimension_and_nonfinite_abi(self):
        cached=metrics_fixture()
        for mutation in ('missing_frequency','duplicate_frequency','source_dimension','field_dimension','nonfinite','directions'):
            actual=copy.deepcopy(cached)
            if mutation=='missing_frequency':actual['centre_field_spectrum'].pop()
            elif mutation=='duplicate_frequency':actual['source_current_spectrum'][1]['frequency_Hz']=3000
            elif mutation=='source_dimension':actual['loaded_metal_voltage_spectrum'][0]['real_V']=[1.,2.,3.]
            elif mutation=='field_dimension':actual['centre_field_spectrum'][0]['imaginary_V_m']=[1.,2.]
            elif mutation=='nonfinite':actual['source_current_spectrum'][0]['real_A'][0]=float('nan')
            else:actual['sampled_direction_count']=26
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.scout.validate_cached_sine(actual,cached)
        for scale in(0.,-1.,float('nan'),float('inf')):
            with self.subTest(scale=scale),self.assertRaises(ValueError):self.scout.validate_cached_sine(copy.deepcopy(cached),cached,amplitude_scale=scale)


    def test_rotation_source_geometry_is_distinct_from_canonical_square_caps_reference(self):
        self.assertEqual(self.scout.SOURCE_ID,'asym-return2-rot90-xy80')
        self.assertEqual(self.scout.SOURCE_RUN,'cloud-one-return-rotation-20261021T174000Z')
        self.assertEqual(self.scout.SOURCE_SUMMARY.parent.name,self.scout.SOURCE_ID)
        self.assertEqual(self.scout.BASELINE_SUMMARY.parent.name,'baseline-square15-xy80')
        self.assertNotEqual(self.scout.SOURCE_SUMMARY,self.scout.BASELINE_SUMMARY)
        self.assertIs(self.scout.seed_coefficients,self.scout.strong.seed_coefficients)
        self.assertIs(self.scout.normalize_source,self.scout.strong.normalize_source)
        self.assertIs(self.scout.physical_pad_currents,self.scout.strong.physical_pad_currents)
        self.assertIs(self.scout.source_metadata,self.scout.rotation.source_metadata)

    def test_physical_pad_rms_uses_two_active_carriers_and_coherent_returns(self):
        contacts=np.array([(pad,1.)for pad in range(4)],dtype=[('pad','i4'),('area_m2','f8')])
        density=np.array([[1.,-.1,-.3,-.6],[-.1,1.5,-.5,-.9]],dtype=complex)
        basis={'f':{f:dict(contacts=contacts,density=density*factor,source=density[:,:2].T*factor)
            for f,factor in((3000,1+.1j),(3030,.8-.2j))}}
        basis['f'][9000]={'forbidden_inactive_harmonic':True};basis['f'][9090]={'forbidden_inactive_harmonic':True}
        coefficients=self.scout.seed_coefficients(.5,90)
        proof=self.scout.physical_pad_currents(basis,coefficients)
        expected=np.stack([coefficients[f]@basis['f'][f]['density']for f in(3000,3030)])
        np.testing.assert_allclose(proof['physical_pad_current_RMS_mA'],np.sqrt(np.sum(abs(expected)**2,axis=0)/2)*1000,
            rtol=1e-14,atol=1e-12)
        self.assertEqual([row['frequency_Hz']for row in proof['spectrum']],[3000,3030])
        self.assertLessEqual(proof['maximum_groupwise_relative_error'],2e-6)
        basis['f'][3030]['source']=np.zeros((2,2),complex)
        with self.assertRaisesRegex(ValueError,'KCL'):self.scout.physical_pad_currents(basis,coefficients)

    def test_unregistered_condition_or_unresolved_coherent_source_bracket_is_held(self):
        declared=copy.deepcopy(self.scout.CONDITIONS[1]);declared['mix_ratio']=.1
        def unresolved(*args,**kwargs):return dict(Vpp_lower_V=.99,Vpp_upper_V=1.)
        with self.assertRaises(ValueError):self.scout.condition_coefficients(declared,unresolved,self.FakeSamplingLimits)
        with self.assertRaisesRegex(ValueError,'1uV'):
            self.scout.condition_coefficients(self.scout.CONDITIONS[1],unresolved,self.FakeSamplingLimits)


if __name__=='__main__':unittest.main()
