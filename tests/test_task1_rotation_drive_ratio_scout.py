"""Synthetic rotation-drive contracts; no native data, PDE or preparation."""
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
DEGREES={'surface_J_RMS_max_A_m2':1,'surface_J_RMS_p95_A_m2':1,'contact_voltage_RMS_max_V':1,
    'SC_power_W':2,'contact_power_W':2,'source_power_W':2,'bulk_skin_J_vector_RMS_max_A_m2':1,
    'bulk_skin_J_vector_RMS_p95_A_m2':1,'skin_SC_plus_dermis_power_W':2}


def square_coefficients():
    first=3/(2*math.sqrt(2));third=1/(2*math.sqrt(2))
    return {3000:np.array([-1j*first,0j]),3030:np.array([0j,-1j*first]),
            9000:np.array([-1j*third,0j]),9090:np.array([0j,-1j*third])}


class RotationDriveRatioScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rotation_drive_ratio_scout_tested',ROOT/'tools/task1_rotation_drive_ratio_scout.py')
        cls.scout=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.scout)

    def test_truncated_square_true_vpp_differs_from_fundamental_amplitude_and_rms(self):
        first=3/(2*math.sqrt(2));third=1/(2*math.sqrt(2))
        phase=np.linspace(0,2*np.pi,65536,endpoint=False)
        voltage=.5*(first*np.sin(phase)+third*np.sin(3*phase))
        self.assertAlmostEqual(.5*(first*math.sin(math.pi/4)+third*math.sin(3*math.pi/4)),.5,places=15)
        self.assertAlmostEqual(float(np.ptp(voltage)),1.,places=14)
        rms=.5*math.sqrt((first**2+third**2)/2)
        self.assertAlmostEqual(rms,math.sqrt(5/32),places=15)
        self.assertAlmostEqual(math.sqrt(float(np.mean(voltage**2))),rms,places=15)
        self.assertNotAlmostEqual(first,1.,places=3)
        self.assertNotAlmostEqual(2*math.sqrt(2)*rms,1.,places=3)

    def test_output_vector_scales_all_four_frequency_coefficients_with_phase_preserved(self):
        base=square_coefficients()
        for vector in ([.5,1.],[2**-.5,1.],[1.,2**-.5],[1.,.5]):
            actual=self.scout.drive.scaled_coefficients(base,vector)
            self.assertEqual(set(actual),{3000,3030,9000,9090})
            for frequency in base:
                np.testing.assert_allclose(actual[frequency],base[frequency]*vector,rtol=0,atol=1e-15)
                np.testing.assert_array_equal(actual[frequency].real,[0.,0.])
            self.assertAlmostEqual(abs(actual[9000][0]/actual[3000][0]),1/3)
            self.assertAlmostEqual(abs(actual[9090][1]/actual[3030][1]),1/3)
            self.assertEqual(actual[3000][1],0j);self.assertEqual(actual[3030][0],0j)

    def test_coefficient_scaling_keeps_input_and_result_storage_independent(self):
        base=square_coefficients();before=copy.deepcopy(base)
        actual=self.scout.drive.scaled_coefficients(base,[.5,1.])
        for frequency in base:
            np.testing.assert_array_equal(base[frequency],before[frequency])
            self.assertFalse(np.shares_memory(actual[frequency],base[frequency]))
        actual[3000][0]=100j
        np.testing.assert_array_equal(base[3000],before[3000])

    def test_five_modes_preserve_actual_declared_output_voltage_vector(self):
        candidate={key:.5**degree for key,degree in DEGREES.items()};baseline={key:1. for key in DEGREES}
        for vector in ([.5,1.],[2**-.5,1.],[1.,2**-.5],[1.,.5]):
            modes=self.scout.drive.normalization_adapter(candidate,baseline,.5,1.,vector)
            self.assertEqual(set(modes),{'raw_declared_Vpp','equal_total_source_output_RMS_sum','equal_total_power',
                'skin_contact_only','legacy_composite_full_skin'})
            self.assertEqual(modes['raw_declared_Vpp']['source_Vpp_by_output'],list(vector))
            for name,mode in modes.items():
                scale=mode['amplitude_scale'];self.assertNotIn('source_Vpp_per_output',mode)
                np.testing.assert_allclose(mode['source_Vpp_by_output'],np.asarray(vector)*scale,rtol=0,atol=1e-15)
                self.assertEqual(mode['raw_declared_source_Vpp_by_output'],list(vector))
                self.assertAlmostEqual(mode['sum_source_output_RMS_mA'],.5*scale)
                for key,degree in DEGREES.items():self.assertAlmostEqual(mode['normalized_burdens'][key],candidate[key]*scale**degree)
            legacy=modes['legacy_composite_full_skin']
            self.assertEqual(legacy['amplitude_scale'],1.)
            self.assertLessEqual(max(legacy['source_Vpp_by_output']),1.)
            self.assertEqual(modes['skin_contact_only']['amplitude_scale'],2.)

    def test_scaled_output_waveform_rms_and_full_vpp_both_follow_declared_amplitude(self):
        base=square_coefficients()
        for vector in ([.5,1.],[2**-.5,1.],[1.,2**-.5],[1.,.5]):
            actual=self.scout.drive.scaled_coefficients(base,vector)
            for output in range(2):
                phasors=np.array([.5*actual[f][output]for f in(3000,3030,9000,9090)])
                rms=float(np.sqrt(np.sum(abs(phasors)**2)/2))
                self.assertAlmostEqual(rms,vector[output]*math.sqrt(5/32),places=15)
                self.assertNotAlmostEqual(2*math.sqrt(2)*rms,vector[output],places=3)


    class FakeSamplingLimits:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)

    def test_reused_coefficient_and_normalization_aliases_are_exact_pure_helpers(self):
        self.assertIs(self.scout.scaled_coefficients,self.scout.drive.scaled_coefficients)
        self.assertIs(self.scout.normalization_adapter,self.scout.drive.normalization_adapter)
        self.assertIs(self.scout.scaled_probe_rows,self.scout.drive.scaled_probe_rows)

    def test_source_waveform_evidence_matches_actual_carrier_third_and_half_peak_basis(self):
        base=square_coefficients();vector=[.5,1.];actual=self.scout.scaled_coefficients(base,vector)
        before=copy.deepcopy((base,actual,vector));calls=[]
        def statistics(frequencies,phasors,fundamentals,*,sampling):
            output=len(calls);carrier=(3000,3030)[output]
            self.assertEqual(list(frequencies),[carrier,3*carrier]);self.assertEqual(list(fundamentals),[carrier])
            self.assertEqual(sampling.samples_per_highest_cycle,128)
            np.testing.assert_allclose(phasors,.5*np.array([actual[f][output]for f in frequencies]),rtol=0,atol=1e-15)
            calls.append((list(frequencies),np.asarray(phasors).copy()))
            return dict(Vpp_lower_V=vector[output]-1e-5,Vpp_upper_V=vector[output]+1e-5)
        proof=self.scout.source_waveform_evidence(base,actual,vector,statistics,self.FakeSamplingLimits)
        self.assertTrue(proof['source_waveform_check_passed'])
        self.assertEqual(proof['actual_source_Vpp_by_output'],vector)
        self.assertEqual(proof['source_peak_basis_V'],.5)
        self.assertEqual(proof['analytic_waveform_peak_factor'],1.)
        self.assertFalse(proof['normalization_performed']);self.assertFalse(proof['hardware_waveform_calibration_validated'])
        self.assertEqual(len(proof['sampled_outputs']),2)
        self.assertEqual(len(calls),2)
        for output,row in enumerate(proof['sampled_outputs']):
            self.assertEqual(row['output_index'],output)
            self.assertEqual(row['analytic_source_Vpp_V'],vector[output])
            self.assertLessEqual(row['numerical_Vpp_lower_V'],vector[output])
            self.assertGreaterEqual(row['numerical_Vpp_upper_V'],vector[output])
        for old,new in zip(before[:2],(base,actual)):
            for frequency in old:np.testing.assert_array_equal(new[frequency],old[frequency])
        self.assertEqual(vector,before[2])

    def test_analytic_exact_vpp_is_not_replaced_by_independent_numerical_or_tone_normalization(self):
        base=square_coefficients();vector=[2**-.5,1.];actual=self.scout.scaled_coefficients(base,vector);calls=[]
        def statistics(*args,**kwargs):
            output=len(calls);calls.append(output)
            return dict(Vpp_lower_V=vector[output]-.001,Vpp_upper_V=vector[output]+.001)
        proof=self.scout.source_waveform_evidence(base,actual,vector,statistics,self.FakeSamplingLimits)
        self.assertTrue(proof['source_waveform_check_passed'])
        self.assertEqual(proof['actual_source_Vpp_by_output'],vector)
        for frequency in base:np.testing.assert_array_equal(actual[frequency],base[frequency]*vector)
        self.assertGreater(proof['sampled_outputs'][0]['numerical_Vpp_upper_V']-proof['sampled_outputs'][0]['numerical_Vpp_lower_V'],1e-6)

    def test_sampled_source_bracket_must_contain_analytic_declared_vpp(self):
        base=square_coefficients();actual=self.scout.scaled_coefficients(base,[.5,1.])
        for lower,upper in ((.1,.2),(.6,.7),(1.1,1.2),(float('nan'),1.),(1.,.5)):
            def bad(*args,**kwargs):return dict(Vpp_lower_V=lower,Vpp_upper_V=upper)
            with self.subTest(lower=lower,upper=upper),self.assertRaises(ValueError):
                self.scout.source_waveform_evidence(base,actual,[.5,1.],bad,self.FakeSamplingLimits)

    def test_base_square_amplitude_harmonic_phase_and_exclusive_source_activity_are_fixed(self):
        original=square_coefficients()
        for change in ('fundamental','third','phase','cross_output','missing_frequency'):
            base=copy.deepcopy(original)
            if change=='fundamental':base[3000][0]*=.9
            elif change=='third':base[9000][0]*=.9
            elif change=='phase':base[9000][0]*=-1
            elif change=='cross_output':base[3000][1]=.01j
            else:base.pop(9090)
            actual={f:values*np.array([.5,1.])for f,values in base.items()}
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):
                self.scout.source_waveform_evidence(base,actual,[.5,1.],lambda *a,**k:dict(Vpp_lower_V=.4,Vpp_upper_V=1.1),self.FakeSamplingLimits)

    def test_actual_coefficients_must_match_declared_output_vector_and_phase(self):
        base=square_coefficients()
        for change in ('amplitude','phase','cross_output'):
            actual=self.scout.scaled_coefficients(base,[.5,1.])
            if change=='amplitude':actual[3000][0]*=2
            elif change=='phase':actual[9090][1]*=-1
            else:actual[3030][0]=.01j
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.scout.source_waveform_evidence(base,actual,[.5,1.],lambda *a,**k:dict(Vpp_lower_V=.4,Vpp_upper_V=1.1),self.FakeSamplingLimits)

    def test_ratio_source_vectors_and_coefficient_abi_are_finite_positive_two_outputs(self):
        for vector in ([1.],[1.,1.,1.],[0.,1.],[-.5,1.],[float('nan'),1.],[1.,float('inf')]):
            with self.subTest(vector=vector),self.assertRaises(ValueError):self.scout.scaled_coefficients(square_coefficients(),vector)
        for values in (np.ones(3),np.full(2,np.nan+0j)):
            base=square_coefficients();base[9000]=values
            with self.assertRaises(ValueError):self.scout.scaled_coefficients(base,[.5,1.])


    def test_exact_four_declared_ratios_use_rotation_source_and_square_canonical_reference(self):
        expected=[dict(id=identifier,source_Vpp_by_output=vector)for identifier,vector in(
            ('rotation-ratio-o0-half',[.5,1.]),('rotation-ratio-o0-sqrt-half',[2**-.5,1.]),
            ('rotation-ratio-o1-sqrt-half',[1.,2**-.5]),('rotation-ratio-o1-half',[1.,.5]))]
        self.assertEqual(list(self.scout.CONDITIONS),expected)
        self.assertEqual(self.scout.SOURCE_ID,'asym-return2-rot90-xy80')
        self.assertEqual(self.scout.SOURCE_RUN,'cloud-one-return-rotation-20261021T174000Z')
        self.assertEqual(self.scout.SOURCE_SUMMARY.parent.name,self.scout.SOURCE_ID)
        self.assertEqual(self.scout.BASELINE_SUMMARY.parent.name,'baseline-square15-xy80')
        self.assertNotEqual(self.scout.SOURCE_SUMMARY,self.scout.BASELINE_SUMMARY)

    def test_physical_pad_rms_includes_fundamentals_thirds_and_passive_frequency_currents(self):
        contacts=np.array([(pad,1.)for pad in range(4)],dtype=[('pad','i4'),('area_m2','f8')])
        density=np.array([[1.,-.1,-.3,-.6],[-.1,1.5,-.5,-.9]],dtype=complex)
        source=density[:,:2].T
        factors={3000:1.,3030:1+.2j,9000:3-.1j,9090:.5+.3j}
        basis={'f':{f:dict(contacts=contacts,density=density*factor,source=source*factor)for f,factor in factors.items()}}
        coefficients=self.scout.scaled_coefficients(square_coefficients(),[.5,1.])
        proof=self.scout.physical_pad_currents(basis,coefficients)
        expected=np.stack([coefficients[f]@basis['f'][f]['density']for f in(3000,3030,9000,9090)])
        rms=np.sqrt(np.sum(abs(expected)**2,axis=0)/2)*1000
        np.testing.assert_allclose(proof['physical_pad_current_RMS_mA'],rms,rtol=1e-14,atol=1e-12)
        self.assertEqual([row['frequency_Hz']for row in proof['spectrum']],[3000,3030,9000,9090])
        self.assertGreater(abs(expected[0,1]),0.)
        self.assertGreater(abs(expected[1,0]),0.)
        fundamental_only=np.sqrt(np.sum(abs(expected[:2])**2,axis=0)/2)*1000
        self.assertTrue(np.all(rms>fundamental_only))
        self.assertLessEqual(proof['maximum_groupwise_relative_error'],2e-6)
        basis['f'][9000]['source']=np.zeros((2,2),complex)
        with self.assertRaisesRegex(ValueError,'KCL'):
            self.scout.physical_pad_currents(basis,coefficients)

    def test_saved_signed_source_and_passive_metal_power_remain_distinct(self):
        currents={3000:[.01,-.004],3030:[-.003,.02],9000:[0.,0.],9090:[0.,0.]}
        metals={3000:[.5,.2],3030:[.15,.5],9000:[0.,0.],9090:[0.,0.]}
        metrics=dict(source_current_spectrum=[dict(frequency_Hz=f,real_A=currents[f],imaginary_A=[0.,0.])for f in currents],
            loaded_metal_voltage_spectrum=[dict(frequency_Hz=f,real_V=metals[f],imaginary_V=[0.,0.])for f in metals],
            source_power_W=.02,source_resistor_power_W=.013125,
            source_current_RMS_by_output_mA=[math.sqrt((.01**2+.003**2)/2)*1000,math.sqrt((.004**2+.02**2)/2)*1000])
        proof=self.scout.signed_output_powers(metrics,scale=.5)
        self.assertFalse(proof['requires_source_power_absorption'])
        self.assertTrue(proof['requires_output_power_absorption'])
        self.assertFalse(proof['hardware_absorption_and_compliance_validated'])
        self.assertLess(proof['outputs'][1]['spectrum'][0]['metal_delivered_power_W'],0.)
        self.assertLess(proof['outputs'][0]['spectrum'][1]['metal_delivered_power_W'],0.)
        self.assertAlmostEqual(proof['totals']['ideal_source_power_W'],.02*.25)
        self.assertAlmostEqual(proof['totals']['source_resistor_loss_W'],.013125*.25)
        self.assertAlmostEqual(proof['outputs'][0]['current_RMS_mA'],metrics['source_current_RMS_by_output_mA'][0]*.5)


if __name__=='__main__':unittest.main()
