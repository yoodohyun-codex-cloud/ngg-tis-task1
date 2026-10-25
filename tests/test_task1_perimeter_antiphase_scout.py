"""Synthetic fixed-perimeter negative-cross scout contracts; no native inputs or PDE."""
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


class PerimeterAntiphaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('perimeter_antiphase_tested',ROOT/'tools/task1_perimeter_antiphase_scout.py')
        cls.scout=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.scout)

    class FakeSamplingLimits:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)

    def test_exact_six_source_bound_conditions_and_canonical_reference(self):
        self.assertEqual([c['id']for c in self.scout.CONDITIONS],['perimeter-sine-control',
            'perimeter-antiphase-r0p05','perimeter-antiphase-r0p1','perimeter-antiphase-r0p2',
            'perimeter-antiphase-r0p5','perimeter-antiphase-r1'])
        self.assertEqual(self.scout.SOURCE_ID,'perimeter-shell225-notch-xy80')
        self.assertEqual(self.scout.SOURCE_RUN,'cloud-perimeter-shell-20261021T185000Z')
        self.assertEqual(self.scout.BASELINE_SUMMARY.parent.name,'baseline-square15-xy80')
        self.assertIs(self.scout.normalize_source,self.scout.routing.normalize_source)
        self.assertIsNot(self.scout.normalize_source,self.scout.strong.normalize_source)

    def test_negative_cross_seeds_have_positive_K_and_common_differential_mode_weights(self):
        for declared in self.scout.CONDITIONS[1:]:
            r=declared['mix_ratio'];c=self.scout.seed_coefficients(r)
            np.testing.assert_array_equal(c[3000],-1j*np.array([1,-r]))
            np.testing.assert_array_equal(c[3030],-1j*np.array([-r,1]))
            np.testing.assert_array_equal(c[9000],np.zeros(2,complex));np.testing.assert_array_equal(c[9090],np.zeros(2,complex))
            proof=self.scout.coefficient_family_evidence(c,r)
            self.assertAlmostEqual(proof['ratio_product_K_real'],r*r)
            self.assertEqual(proof['pure_differential_command'],r==1)
            self.assertEqual(proof['command_matrix_rank'],1 if r==1 else 2)
            self.assertEqual(proof['independent_physical_outputs'],2)
            a=np.stack([c[3000],c[3030]])/(-1j)
            np.testing.assert_allclose(a@np.array([1.,1.]),(1-r)*np.array([1.,1.]))
            np.testing.assert_allclose(a@np.array([1.,-1.]),(1+r)*np.array([1.,-1.]))
            self.assertFalse(proof['net_GND_zero_claimed']);self.assertFalse(proof['local_GND_J_zero_claimed'])

    def test_K_distinguishes_prior_unitary_family_under_carrier_phases_and_column_scaling(self):
        for ratio in(.5,1.):
            for phase in(0,90,180,270):
                prior=self.scout.strong.seed_coefficients(ratio,phase)
                a=prior[3000]*np.exp(.37j)*np.array([.7,1.3])
                b=prior[3030]*np.exp(-.19j)*np.array([.7,1.3])
                product=(a[1]/a[0])*(b[0]/b[1])
                self.assertAlmostEqual(product.real,-ratio*ratio);self.assertAlmostEqual(product.imag,0.)
                with self.assertRaises(ValueError):self.scout.coefficient_family_evidence(prior,ratio)

    def test_one_global_normalization_preserves_family_when_output_Vpp_brackets_differ(self):
        for declared in self.scout.CONDITIONS[1:]:
            calls=[]
            def statistics(frequencies,phasors,fundamentals,*,sampling):
                self.assertEqual(list(frequencies),[3000,3030]);self.assertEqual(sampling.max_statistics_samples,262144)
                upper=(2.,4.)[len(calls)];calls.append(np.asarray(phasors).copy())
                return dict(Vpp_lower_V=upper*(1-5e-7),Vpp_upper_V=upper)
            c,proof=self.scout.condition_coefficients(declared,statistics,self.FakeSamplingLimits)
            seed=self.scout.seed_coefficients(declared['mix_ratio'])
            for f in self.scout.FREQUENCIES:np.testing.assert_array_equal(c[f],seed[f]*.25)
            self.assertTrue(proof['global_normalization']);self.assertFalse(proof['independent_column_normalization'])
            self.assertEqual(proof['source_Vpp_upper_by_output_V'],[.5,1.])
            self.assertLessEqual(proof['maximum_bracket_width_V'],1e-6)
            self.scout.coefficient_family_evidence(c,declared['mix_ratio'])
            changed={f:v*np.array([1.,.9])for f,v in c.items()}
            with self.assertRaisesRegex(ValueError,'global'):self.scout.coefficient_family_evidence(changed,declared['mix_ratio'])

    def test_analytic_sine_control_retains_scale_one_and_needs_no_sine_archive(self):
        calls=[]
        def statistics(frequencies,phasors,fundamentals,*,sampling):
            calls.append(list(frequencies));np.testing.assert_array_equal(phasors,[-.5j])
            return dict(Vpp_lower_V=.99999,Vpp_upper_V=1.00001)
        c,proof=self.scout.condition_coefficients(self.scout.CONDITIONS[0],statistics,self.FakeSamplingLimits)
        np.testing.assert_array_equal(c[3000],[-1j,0j]);np.testing.assert_array_equal(c[3030],[0j,-1j])
        self.assertEqual(calls,[[3000],[3030]])
        self.assertEqual(proof['source_Vpp_intervals_V'],[[1.,1.],[1.,1.]])
        self.assertFalse(proof['normalization_performed']);self.assertIsNone(proof['seed_unitary'])

    def test_directional_difference_gain_can_cancel_at_fixed_actual_whole_source_amplitude(self):
        base=np.array([1+.2j,-.5j,0.])
        for r in(.05,.1,.2,.5,1.):
            field0=base;field1=-base;scale=1/(1+r)
            a=scale*(field0-r*field1);b=scale*(-r*field0+field1)
            np.testing.assert_allclose(a,base,rtol=1e-15,atol=1e-15)
            np.testing.assert_allclose(b,-base,rtol=1e-15,atol=1e-15)
        # This algebraic example makes no claim about actual Vpp bound or native ROI fields.

    def test_complex_net_ground_zero_does_not_remove_local_patch_current(self):
        contacts=np.array([(p,.5)for p in range(4)for _ in range(2)],dtype=[('pad','i4'),('area_m2','f8')])
        density=np.array([[1,1,0,0,.2,-1.2,.4,-1.4],[0,0,1,1,-1.2,.2,-1.4,.4]],complex)
        basis={'f':{f:dict(contacts=contacts,density=density*factor,source=np.eye(2,dtype=complex)*factor)
            for f,factor in((3000,1.),(3030,1+.1j))}}
        basis['f'][9000]={'inactive_harmonic_must_not_be_read':True};basis['f'][9090]={'inactive_harmonic_must_not_be_read':True}
        coeff=self.scout.seed_coefficients(1.);local=self.scout.return_local_current_evidence(basis,coeff)
        physical=self.scout.physical_pad_currents(basis,coeff)
        self.assertEqual(4,len(local['frequencies_and_pads']))
        for row in local['frequencies_and_pads']:
            self.assertLess(row['net_current_over_max_source_current'],1e-14)
            self.assertGreater(row['local_J_peak_max_A_m2'],1.)
            self.assertGreater(row['absolute_patch_current_integral_A'],1.)
        self.assertFalse(local['zero_net_implies_zero_local_J']);self.assertFalse(local['isolated_pairs'])
        self.assertLess(physical['maximum_groupwise_relative_error'],2e-6)
        changed=self.scout.scaled_return_local_evidence(local,.3)
        self.assertAlmostEqual(changed['frequencies_and_pads'][0]['local_J_peak_max_A_m2'],local['frequencies_and_pads'][0]['local_J_peak_max_A_m2']*.3)
        self.assertEqual(changed['frequencies_and_pads'][0]['net_current_over_max_source_current'],local['frequencies_and_pads'][0]['net_current_over_max_source_current'])

    def test_signed_powers_preserve_absorption_per_frequency_even_when_totals_positive(self):
        metrics=dict(source_current_spectrum=[dict(frequency_Hz=f,real_A=[.01,.01],imaginary_A=[0.,0.])for f in(3000,3030)],
            loaded_metal_voltage_spectrum=[dict(frequency_Hz=3000,real_V=[1.,-.8],imaginary_V=[0.,0.]),
                dict(frequency_Hz=3030,real_V=[-.8,1.],imaginary_V=[0.,0.])],
            source_power_W=.012,source_resistor_power_W=.01,source_current_RMS_by_output_mA=[10.,10.])
        result=self.scout.signed_output_powers(metrics,scale=.5)
        self.assertTrue(result['requires_source_power_absorption']);self.assertTrue(result['requires_output_power_absorption'])
        self.assertLess(result['outputs'][0]['spectrum'][1]['ideal_source_power_W'],0.)
        self.assertAlmostEqual(result['totals']['ideal_source_power_W'],.012*.25)
        self.assertFalse(result['hardware_absorption_and_compliance_validated'])

    def test_five_modes_keep_actual_interval_scaling_and_separate_skin_caps_from_power(self):
        degree={'surface_J_RMS_max_A_m2':1,'surface_J_RMS_p95_A_m2':1,'contact_voltage_RMS_max_V':1,
            'SC_power_W':2,'contact_power_W':2,'source_power_W':2,'bulk_skin_J_vector_RMS_max_A_m2':1,
            'bulk_skin_J_vector_RMS_p95_A_m2':1,'skin_SC_plus_dermis_power_W':2}
        candidate={key:.5**d for key,d in degree.items()};baseline={key:1. for key in degree}
        intervals=[[.5-1e-7,.5],[1-1e-7,1.]]
        modes=self.scout.normalization_modes(candidate,baseline,.5,1.,intervals)
        self.assertEqual(5,len(modes));self.assertEqual(2.,modes['skin_contact_only']['amplitude_scale'])
        self.assertFalse(modes['skin_contact_only']['includes_source_power_cap'])
        self.assertFalse(modes['skin_contact_only']['includes_1Vpp_ceiling'])
        self.assertEqual([1.,2.],modes['skin_contact_only']['source_Vpp_upper_by_output_V'])
        self.assertEqual(1.,modes['legacy_composite_full_skin']['amplitude_scale'])

    def test_unregistered_coefficients_and_unresolved_actual_source_bounds_are_rejected(self):
        for r in(0.,-.1,.3,float('nan'),True):
            with self.assertRaises(ValueError):self.scout.seed_coefficients(r)
        c=self.scout.seed_coefficients(.5);c[9000][0]=1j
        with self.assertRaises(ValueError):self.scout.coefficient_family_evidence(c,.5)
        declared=copy.deepcopy(self.scout.CONDITIONS[1]);declared['mix_ratio']=.3
        def unresolved(*args,**kwargs):return dict(Vpp_lower_V=.99,Vpp_upper_V=1.)
        with self.assertRaises(ValueError):self.scout.condition_coefficients(declared,unresolved,self.FakeSamplingLimits)
        with self.assertRaisesRegex(ValueError,'1uV'):
            self.scout.condition_coefficients(self.scout.CONDITIONS[1],unresolved,self.FakeSamplingLimits)

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



if __name__=='__main__':unittest.main()
