"""Synthetic return-current drive contracts; no native arrays or PDE."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


class ReturnCurrentDriveScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('return_current_drive_tested',ROOT/'tools/task1_return_current_drive_scout.py')
        cls.scout=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.scout)

    def setUp(self):
        self.first=np.array([[3.,2.],[1.,4.],[-3.,-1.],[-1.,-5.]],dtype=complex)
        self.second=np.array([[4.,1.],[2.,3.],[-2.,-3.],[-4.,-1.]],dtype=complex)
        self.contacts=np.array([(pad,area)for pad in range(4)for area in(.25,.75)],
            dtype=[('pad','i4'),('area_m2','f8')])
        self.density=np.repeat(self.first.T,2,axis=1)
        self.density[0,::2]+=3j;self.density[0,1::2]-=1j
        self.density[1,::2]+=6+3j;self.density[1,1::2]-=2+1j

    def test_response_integrates_complex_patch_density_by_area_in_channel_major_order(self):
        before=self.density.copy();response,proof=self.scout.return_response(self.density,self.contacts,self.first[:2])
        self.assertEqual(response.shape,(4,2));self.assertTrue(np.iscomplexobj(response))
        np.testing.assert_allclose(response,self.first,rtol=0,atol=1e-15)
        np.testing.assert_allclose(response.sum(axis=0),np.zeros(2),rtol=0,atol=1e-15)
        np.testing.assert_array_equal(self.density,before)
        self.assertIsInstance(proof,dict)
        self.assertLessEqual(proof['source_groupwise_relative_error'],2e-6)
        self.assertLessEqual(proof['KCL_groupwise_relative_error'],2e-6)
        self.assertGreater(min(proof['return_singular_values_A']),0.)

    def test_response_keeps_complex_coherent_integration_distinct_from_integrated_magnitudes(self):
        response,_=self.scout.return_response(self.density,self.contacts,self.first[:2])
        area=self.contacts['area_m2'];pad=self.contacts['pad']
        unsigned=np.array([[np.sum(abs(self.density[channel,pad==p])*area[pad==p])for channel in range(2)]for p in range(4)])
        self.assertTrue(np.any(abs(unsigned-abs(response))>1e-3))
        np.testing.assert_allclose(response,self.first,rtol=0,atol=1e-15)

    def test_response_rejects_wrong_basis_dimensions_and_nonfinite_density(self):
        for density in (self.density.T,self.density[:,:-1],np.full(self.density.shape,np.nan+0j)):
            with self.subTest(shape=density.shape),self.assertRaises(ValueError):
                self.scout.return_response(density,self.contacts,self.first[:2])

    def test_response_rejects_invalid_contact_areas_pad_mapping_and_source_shape(self):
        for key,value in (('area_m2',0.),('area_m2',-1.),('area_m2',float('nan')),('pad',4),('pad',-1)):
            contacts=self.contacts.copy();contacts[key][0]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                self.scout.return_response(self.density,contacts,self.first[:2])
        for source in (np.zeros((1,2),complex),np.full((2,2),np.inf+0j)):
            with self.assertRaises(ValueError):self.scout.return_response(self.density,self.contacts,source)

    def test_response_rejects_failed_kcl_or_wrong_driven_source_current(self):
        density=self.density.copy();density[0,4]+=1
        with self.assertRaises(ValueError):self.scout.return_response(density,self.contacts,self.first[:2])
        source=self.first[:2].copy();source[0,1]+=.01
        with self.assertRaises(ValueError):self.scout.return_response(self.density,self.contacts,source)


    def test_exact_cosine_coefficients_and_zero_harmonics_for_three_weights(self):
        before=copy.deepcopy((self.first,self.second))
        for tau in (0.,.5,1.):
            coefficients,proof=self.scout.design_coefficients(self.first,self.second,tau)
            self.assertEqual(set(coefficients),{3000,3030,9000,9090})
            np.testing.assert_allclose(coefficients[3000],[1.,-3*tau],rtol=0,atol=1e-15)
            np.testing.assert_allclose(coefficients[3030],[-.25*tau,1.],rtol=0,atol=1e-15)
            np.testing.assert_array_equal(coefficients[9000],np.zeros(2,dtype=complex))
            np.testing.assert_array_equal(coefficients[9090],np.zeros(2,dtype=complex))
            self.assertIsInstance(proof,dict)
        np.testing.assert_array_equal(self.first,before[0]);np.testing.assert_array_equal(self.second,before[1])

    def test_tau_zero_retains_exclusive_one_carrier_per_source_output(self):
        coefficients,_=self.scout.design_coefficients(self.first,self.second,0.)
        np.testing.assert_array_equal(coefficients[3000],[1.+0j,0j])
        np.testing.assert_array_equal(coefficients[3030],[0j,1.+0j])
        self.assertEqual(np.count_nonzero(np.stack([coefficients[3000],coefficients[3030]])),2)

    def test_weighted_target_return_currents_shrink_linearly_to_complex_cancellation(self):
        for tau in (0.,.5,1.):
            coefficients,_=self.scout.design_coefficients(self.first,self.second,tau)
            self.assertAlmostEqual(abs(self.first[2]@coefficients[3000]-(1-tau)*self.first[2,0]),0.,places=13)
            self.assertAlmostEqual(abs(self.second[3]@coefficients[3030]-(1-tau)*self.second[3,1]),0.,places=13)
        coefficients,_=self.scout.design_coefficients(self.first,self.second,1.)
        self.assertGreater(abs(self.first[3]@coefficients[3000]),0.)
        self.assertGreater(abs(self.second[2]@coefficients[3030]),0.)

    def test_complex_response_ratios_keep_phase_instead_of_magnitude_only_division(self):
        first=self.first.copy();second=self.second.copy()
        first[2:]=[[-3+1j,-1-.5j],[-1+.2j,-5-.5j]]
        second[2:]=[[-2+.4j,-3-.2j],[-4-.3j,-1+.1j]]
        first[0]=-first[1]-first[2]-first[3];second[0]=-second[1]-second[2]-second[3]
        coefficients,_=self.scout.design_coefficients(first,second,1.)
        self.assertGreater(abs(coefficients[3000][1].imag),0.)
        self.assertGreater(abs(coefficients[3030][0].imag),0.)
        self.assertAlmostEqual(abs(first[2]@coefficients[3000]),0.,places=13)
        self.assertAlmostEqual(abs(second[3]@coefficients[3030]),0.,places=13)

    def test_integrated_return_cancellation_does_not_zero_local_patch_current_density(self):
        coefficients,_=self.scout.design_coefficients(self.first,self.second,1.)
        local=coefficients[3000]@self.density;mask=self.contacts['pad']==2
        self.assertAlmostEqual(abs(np.sum(local[mask]*self.contacts['area_m2'][mask])),0.,places=13)
        self.assertTrue(np.all(abs(local[mask])>1e-3))
        self.assertGreater(float(np.max(abs(local[mask]))),0.)

    def test_design_rejects_unregistered_tau_shape_and_nonfinite_response(self):
        for tau in (-.1,.25,2.,float('nan'),float('inf')):
            with self.subTest(tau=tau),self.assertRaises(ValueError):
                self.scout.design_coefficients(self.first,self.second,tau)
        for first in (self.first[:2],np.zeros((4,3),complex),np.full((4,2),np.nan+0j)):
            with self.assertRaises(ValueError):self.scout.design_coefficients(first,self.second,.5)

    def test_design_rejects_singular_and_numerically_unresolvable_return_matrices_before_tau(self):
        for returns in (np.array([[1.,2.],[2.,4.]]),np.array([[1.,1.],[1.,1.+1e-7]])):
            first=self.first.copy();first[2:]=returns;first[0]=-first[1]-first[2]-first[3]
            for tau in (0.,1.):
                with self.subTest(returns=returns,tau=tau),self.assertRaises(ValueError):
                    self.scout.design_coefficients(first,self.second,tau)

    def test_design_rejects_zero_and_threshold_small_denominators_with_full_rank(self):
        for small in (0.,4e-6):
            first=self.first.copy();first[2:]=[[1.,small],[1.,2.]];first[0]=-first[1]-first[2]-first[3]
            self.assertGreater(abs(np.linalg.det(first[2:])),1.)
            with self.subTest(denominator=small),self.assertRaises(ValueError):
                self.scout.design_coefficients(first,self.second,1.)
        second=self.second.copy();second[2:]=[[-2.,-3.],[0.,-1.]];second[0]=-second[1]-second[2]-second[3]
        with self.assertRaises(ValueError):self.scout.design_coefficients(self.first,second,1.)

    class FakeSamplingLimits:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)

    def test_global_vpp_normalization_preserves_both_column_and_cancellation_ratios(self):
        coefficients,_=self.scout.design_coefficients(self.first,self.second,1.);before=copy.deepcopy(coefficients);calls=[]
        def statistics(frequencies,phasors,fundamentals,*,sampling):
            self.assertEqual(list(frequencies),[3000,3030]);self.assertEqual(list(fundamentals),[3000,3030])
            self.assertEqual(sampling.max_statistics_samples,262144)
            output=len(calls);calls.append(np.asarray(phasors).copy());upper=(2.,4.)[output]
            return dict(Vpp_lower_V=upper*(1-5e-7),Vpp_upper_V=upper)
        normalized,proof=self.scout.normalize_source(coefficients,statistics,self.FakeSamplingLimits)
        self.assertTrue(proof['global_normalization']);self.assertFalse(proof['independent_column_normalization'])
        self.assertEqual(proof['global_scale'],.25)
        np.testing.assert_allclose(proof['source_Vpp_intervals_V'],[[.5*(1-5e-7),.5],[1-5e-7,1.]],rtol=0,atol=1e-15)
        self.assertLessEqual(proof['maximum_bracket_width_V'],1e-6)
        self.assertEqual(len(calls),2)
        for output,phasors in enumerate(calls):
            np.testing.assert_allclose(phasors,.5*np.array([coefficients[f][output]for f in(3000,3030)]),rtol=0,atol=1e-15)
        for frequency in normalized:
            np.testing.assert_allclose(normalized[frequency],coefficients[frequency]*.25,rtol=0,atol=1e-15)
            np.testing.assert_array_equal(coefficients[frequency],before[frequency])
        self.assertAlmostEqual(abs(self.first[2]@normalized[3000]),0.,places=13)
        self.assertAlmostEqual(abs(self.second[3]@normalized[3030]),0.,places=13)
        self.assertNotEqual(proof['source_Vpp_intervals_V'][0][1],1.)

    def test_global_normalization_accepts_tau_zero_cross_frequency_zeros(self):
        coefficients,_=self.scout.design_coefficients(self.first,self.second,0.)
        def statistics(*args,**kwargs):return dict(Vpp_lower_V=1.-5e-7,Vpp_upper_V=1.)
        normalized,proof=self.scout.normalize_source(coefficients,statistics,self.FakeSamplingLimits)
        self.assertEqual(proof['global_scale'],1.)
        for frequency in coefficients:np.testing.assert_array_equal(normalized[frequency],coefficients[frequency])

    def test_global_normalization_rejects_unresolved_or_invalid_source_brackets(self):
        coefficients,_=self.scout.design_coefficients(self.first,self.second,.5)
        def unresolved(*args,**kwargs):return dict(Vpp_lower_V=.99,Vpp_upper_V=1.)
        with self.assertRaisesRegex(ValueError,'1uV'):
            self.scout.normalize_source(coefficients,unresolved,self.FakeSamplingLimits)
        for lower,upper in ((-1.,1.),(1.,.5),(0.,0.),(1.,float('nan'))):
            def invalid(*args,**kwargs):return dict(Vpp_lower_V=lower,Vpp_upper_V=upper)
            with self.subTest(lower=lower,upper=upper),self.assertRaises(ValueError):
                self.scout.normalize_source(coefficients,invalid,self.FakeSamplingLimits)


    def test_tone_activity_distinguishes_tau_zero_and_mixed_frequency_outputs(self):
        zero,_=self.scout.design_coefficients(self.first,self.second,0.)
        self.assertEqual(self.scout.tone_activity(zero),{'0':[3000],'1':[3030]})
        for tau in (.5,1.):
            mixed,_=self.scout.design_coefficients(self.first,self.second,tau)
            self.assertEqual(self.scout.tone_activity(mixed),{'0':[3000,3030],'1':[3000,3030]})

    def test_design_proof_reports_return_targets_without_isolation_or_local_zero_claim(self):
        _,proof=self.scout.design_coefficients(self.first,self.second,1.)
        self.assertEqual(proof['tau'],1.)
        self.assertEqual(proof['q0'],{'real':-3.,'imaginary':0.})
        self.assertEqual(proof['q1'],{'real':-.25,'imaginary':0.})
        self.assertEqual(proof['common_GND_nodes'],1)
        self.assertFalse(proof['isolated_pairs_claimed'])
        self.assertFalse(proof['zero_net_current_implies_zero_local_J'])
        self.assertEqual([(row['frequency_Hz'],row['wrong_return_pad'])for row in proof['wrong_return_predictions']],[(3000,2),(3030,3)])
        for row in proof['wrong_return_predictions']:
            self.assertLessEqual(row['net_current_relative_error'],2e-6)
            self.assertLessEqual(row['prediction_relative_error'],2e-6)


if __name__=='__main__':unittest.main()
