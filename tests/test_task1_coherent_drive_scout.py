"""Synthetic coherent-drive contracts; no native fields, PDE or research runs."""
import copy
import importlib.util
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


class CoherentDriveScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('coherent_drive_scout_tested',ROOT/'tools/task1_coherent_drive_scout.py')
        cls.scout=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.scout)

    def test_seed_preserves_actual_frequencies_and_zero_harmonics(self):
        for ratio in (.5,1.):
            for phase in (0,90,180,270):
                coefficients=self.scout.seed_coefficients(ratio,phase)
                self.assertEqual(set(coefficients),{3000,3030,9000,9090})
                for frequency,value in coefficients.items():
                    self.assertEqual(np.asarray(value).shape,(2,))
                    self.assertTrue(np.all(np.isfinite(value)))
                    self.assertTrue(np.iscomplexobj(value))
                np.testing.assert_array_equal(coefficients[9000],np.zeros(2,dtype=complex))
                np.testing.assert_array_equal(coefficients[9090],np.zeros(2,dtype=complex))

    def test_seed_exact_complex_phase_matrix(self):
        for ratio in (.5,1.):
            for phase in (0,90,180,270):
                angle=np.deg2rad(phase)
                expected=-1j/np.sqrt(1+ratio**2)*np.array([[1,-ratio*np.exp(-1j*angle)],
                                                                      [ratio*np.exp(1j*angle),1]])
                actual=self.scout.seed_coefficients(ratio,phase)
                np.testing.assert_allclose(np.stack([actual[3000],actual[3030]]),expected,rtol=0,atol=1e-15)

    def test_seed_is_unitary_per_output_and_per_frequency(self):
        for ratio in (.5,1.):
            for phase in (0,90,180,270):
                coefficients=self.scout.seed_coefficients(ratio,phase)
                matrix=np.stack([coefficients[3000],coefficients[3030]])
                np.testing.assert_allclose(matrix.conj().T@matrix,np.eye(2),rtol=0,atol=6e-16)
                np.testing.assert_allclose(matrix@matrix.conj().T,np.eye(2),rtol=0,atol=6e-16)
                np.testing.assert_allclose(np.sum(abs(matrix)**2,axis=0),[1.,1.],rtol=0,atol=5e-16)

    def test_seed_preserves_distinct_cross_output_phase_signs(self):
        coefficients=self.scout.seed_coefficients(1.,90)
        np.testing.assert_allclose(coefficients[3000],[-1j/np.sqrt(2),1/np.sqrt(2)],rtol=0,atol=1e-15)
        np.testing.assert_allclose(coefficients[3030],[1/np.sqrt(2),-1j/np.sqrt(2)],rtol=0,atol=1e-15)
        self.assertNotEqual(coefficients[3000][1],coefficients[3030][1])

    def test_seed_returns_independent_arrays_and_calls(self):
        first=self.scout.seed_coefficients(.5,180);before=copy.deepcopy(first)
        second=self.scout.seed_coefficients(.5,180)
        first[3000][0]=123+7j;first[9000][0]=8j
        for frequency in second:
            np.testing.assert_array_equal(second[frequency],before[frequency])
        np.testing.assert_array_equal(first[9090],np.zeros(2,dtype=complex))

    def test_seed_rejects_unregistered_ratio_and_phase(self):
        for ratio in (0.,-1.,2.,float('nan'),float('inf')):
            with self.subTest(ratio=ratio),self.assertRaises((ValueError,TypeError)):
                self.scout.seed_coefficients(ratio,0)
        for phase in (45,360,float('nan'),float('inf')):
            with self.subTest(phase=phase),self.assertRaises((ValueError,TypeError)):
                self.scout.seed_coefficients(.5,phase)

    def test_unitary_seed_rms_does_not_equal_full_waveform_vpp(self):
        coefficients=self.scout.seed_coefficients(.5,0)
        t=np.arange(65536)/65536/30.
        voltage=sum(np.real(.5*coefficients[f][0]*np.exp(2j*np.pi*f*t)) for f in (3000,3030))
        sampled_vpp=np.ptp(voltage)
        output_rms=math.sqrt(sum(abs(.5*coefficients[f][0])**2/2 for f in (3000,3030)))
        self.assertAlmostEqual(output_rms,1/np.sqrt(8),places=15)
        self.assertGreater(sampled_vpp,1.3)
        self.assertLess(sampled_vpp,1.35)
        self.assertNotAlmostEqual(sampled_vpp,1.,places=2)
        self.assertNotAlmostEqual(sampled_vpp,2*np.sqrt(2)*output_rms,places=2)


    class FakeSamplingLimits:
        def __init__(self,**kwargs):
            self.__dict__.update(kwargs)

    def test_source_normalization_uses_half_peak_actual_frequency_and_distinct_columns(self):
        coefficients=self.scout.seed_coefficients(.5,90);before=copy.deepcopy(coefficients);calls=[]
        def statistics(frequencies,phasors,fundamentals,*,sampling):
            self.assertEqual(list(frequencies),[3000,3030]);self.assertEqual(list(fundamentals),[3000,3030])
            phasors=np.asarray(phasors);calls.append((phasors.copy(),sampling))
            upper=2. if abs(phasors[0])>abs(phasors[1]) else 4.
            return {'Vpp_lower_V':upper*(1-5e-7),'Vpp_upper_V':upper}
        normalized,proof=self.scout.normalize_source(coefficients,statistics,self.FakeSamplingLimits)
        np.testing.assert_allclose(proof['column_scales'],[.5,.25],rtol=0,atol=1e-15)
        np.testing.assert_allclose(proof['source_Vpp_intervals_V'],[[1-5e-7,1],[1-5e-7,1]],rtol=0,atol=1e-15)
        self.assertIs(proof['unitary_after_Vpp_normalization'],False)
        self.assertLessEqual(proof['maximum_bracket_width_V'],1e-6)
        self.assertEqual(len(calls),2)
        for column,(phasors,sampling) in enumerate(calls):
            np.testing.assert_allclose(phasors,.5*np.array([coefficients[3000][column],coefficients[3030][column]]),rtol=0,atol=1e-15)
            self.assertEqual(sampling.samples_per_highest_cycle,128)
            self.assertEqual(sampling.max_statistics_samples,262144)
            self.assertAlmostEqual(sampling.plot_duration_s,min(.002,4000/(3030*128)))
        for frequency in normalized:
            np.testing.assert_allclose(normalized[frequency],coefficients[frequency]*[.5,.25],rtol=0,atol=1e-15)
            np.testing.assert_array_equal(coefficients[frequency],before[frequency])

    def test_source_normalization_refines_each_output_until_one_microvolt_bracket(self):
        coefficients=self.scout.seed_coefficients(1.,0);levels=[]
        def statistics(frequencies,phasors,fundamentals,*,sampling):
            level=sampling.samples_per_highest_cycle;levels.append(level)
            width={128:1e-3,256:1e-5,512:5e-7}[level]
            return {'Vpp_lower_V':1-width,'Vpp_upper_V':1.}
        normalized,proof=self.scout.normalize_source(coefficients,statistics,self.FakeSamplingLimits)
        self.assertEqual(sorted(levels),[128,128,256,256,512,512])
        self.assertLessEqual(proof['maximum_bracket_width_V'],1e-6)
        self.assertEqual(len(proof['outputs']),2)
        for frequency in normalized:np.testing.assert_array_equal(normalized[frequency],coefficients[frequency])

    def test_source_normalization_holds_instead_of_accepting_unresolved_vpp(self):
        levels=[]
        def unresolved(frequencies,phasors,fundamentals,*,sampling):
            levels.append(sampling.samples_per_highest_cycle)
            return {'Vpp_lower_V':.99,'Vpp_upper_V':1.}
        with self.assertRaisesRegex(ValueError,'1uV'):
            self.scout.normalize_source(self.scout.seed_coefficients(.5,180),unresolved,self.FakeSamplingLimits)
        self.assertIn(2560,levels)
        self.assertTrue(set(levels)<={128,256,512,1024,2048,2560})

    def test_source_normalization_rejects_invalid_or_nonfinite_statistics(self):
        for lower,upper in ((1.,.5),(-1.,1.),(.5,float('nan')),(float('inf'),2.),(0.,0.)):
            def invalid(*args,**kwargs):return {'Vpp_lower_V':lower,'Vpp_upper_V':upper}
            with self.subTest(lower=lower,upper=upper),self.assertRaises(ValueError):
                self.scout.normalize_source(self.scout.seed_coefficients(.5,270),invalid,self.FakeSamplingLimits)

    def test_source_normalization_rejects_nonphysical_coefficient_abi(self):
        def statistics(*args,**kwargs):return {'Vpp_lower_V':1.,'Vpp_upper_V':1.}
        seed=self.scout.seed_coefficients(.5,0)
        cases=[]
        missing=copy.deepcopy(seed);del missing[3030];cases.append(missing)
        wrong=copy.deepcopy(seed);wrong[3000]=np.ones(3,dtype=complex);cases.append(wrong)
        harmonic=copy.deepcopy(seed);harmonic[9000][0]=1;cases.append(harmonic)
        nonfinite=copy.deepcopy(seed);nonfinite[3030][1]=np.nan;cases.append(nonfinite)
        inactive=copy.deepcopy(seed);inactive[3000][1]=0;cases.append(inactive)
        for coefficients in cases:
            with self.subTest(keys=list(coefficients)),self.assertRaises(ValueError):
                self.scout.normalize_source(coefficients,statistics,self.FakeSamplingLimits)


    def burden_fixture(self):
        degrees={'surface_J_RMS_max_A_m2':1,'surface_J_RMS_p95_A_m2':1,'contact_voltage_RMS_max_V':1,
            'SC_power_W':2,'contact_power_W':2,'source_power_W':2,'bulk_skin_J_vector_RMS_max_A_m2':1,
            'bulk_skin_J_vector_RMS_p95_A_m2':1,'skin_SC_plus_dermis_power_W':2}
        return degrees,{key:.5**degree for key,degree in degrees.items()},{key:1. for key in degrees}

    def test_normalization_modes_scale_current_linearly_and_power_quadratically(self):
        degrees,candidate,baseline=self.burden_fixture();before=copy.deepcopy(candidate)
        intervals=[[1-5e-7,1.],[1-7e-7,1.]]
        modes=self.scout.normalization_modes(candidate,baseline,.5,1.,intervals)
        self.assertEqual(set(modes),{'raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power',
            'skin_contact_only','legacy_composite_full_skin'})
        self.assertEqual(candidate,before)
        for name in ('equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only'):
            mode=modes[name];self.assertEqual(mode['amplitude_scale'],2.)
            self.assertEqual(mode['sum_source_output_RMS_mA'],1.)
            self.assertNotIn('source_Vpp_per_output',mode)
            for key in degrees:self.assertAlmostEqual(mode['normalized_burdens'][key],1.)
            np.testing.assert_allclose(mode['actual_source_Vpp_intervals_V'],np.array(intervals)*2,rtol=0,atol=1e-15)
            self.assertEqual(mode['source_Vpp_upper_by_output_V'],[2.,2.])
        self.assertEqual(modes['raw_1Vpp']['normalized_burdens']['SC_power_W'],.25)
        self.assertEqual(modes['skin_contact_only']['includes_source_power_cap'],False)
        self.assertEqual(modes['skin_contact_only']['includes_1Vpp_ceiling'],False)

    def test_legacy_ceiling_caps_actual_full_waveform_upper_at_one_volt(self):
        _,candidate,baseline=self.burden_fixture()
        intervals=[[1-5e-7,1.],[1-2e-7,1.]]
        modes=self.scout.normalization_modes(candidate,baseline,.5,1.,intervals)
        legacy=modes['legacy_composite_full_skin']
        self.assertEqual(legacy['amplitude_scale'],1.)
        self.assertEqual(legacy['source_Vpp_upper_by_output_V'],[1.,1.])
        np.testing.assert_array_equal(legacy['actual_source_Vpp_intervals_V'],intervals)
        self.assertTrue(legacy['includes_source_power_cap']);self.assertTrue(legacy['includes_1Vpp_ceiling'])
        self.assertEqual(legacy['normalized_burdens']['source_power_W'],.25)

    def test_normalization_modes_reject_unresolved_or_invalid_source_intervals(self):
        _,candidate,baseline=self.burden_fixture()
        invalid=([1.,1.],[[.9999999,1.,1.],[.9999999,1.,1.]],
            [[.9,1.],[.9999999,1.]],[[1.,1.1],[1.,1.]],
            [[1.,.99],[1.,1.]],[[0.,0.],[1.,1.]],[[float('nan'),1.],[1.,1.]])
        for intervals in invalid:
            with self.subTest(intervals=intervals),self.assertRaises(ValueError):
                self.scout.normalization_modes(candidate,baseline,.5,1.,intervals)

    def test_physical_pad_currents_integrate_complex_returns_before_rms(self):
        coefficients=self.scout.seed_coefficients(.5,90)
        contacts=np.array([(p,1.)for p in range(4)],dtype=[('pad','i4'),('area_m2','f8')])
        density=np.array([[1,0,-.5,-.5],[0,1,-.5,-.5]],dtype=complex)
        basis={'f':{f:{'contacts':contacts,'density':density.copy(),'source':np.eye(2,dtype=complex)}
            for f in (3000,3030)}}
        result=self.scout.physical_pad_currents(basis,coefficients)
        expected=np.array([coefficients[f]@density for f in (3000,3030)])
        np.testing.assert_allclose(result['physical_pad_current_RMS_mA'],np.sqrt(np.sum(abs(expected)**2,axis=0)/2)*1000,
            rtol=1e-14,atol=1e-12)
        self.assertLessEqual(result['maximum_groupwise_relative_error'],1e-15)
        self.assertEqual(result['physical_pads'],4);self.assertEqual(result['independent_outputs'],2)
        self.assertEqual(result['common_GND_return_pads'],[2,3])
        wrong_return=np.sqrt(sum(np.abs(coefficients[f])**2/2 for f in (3000,3030))).sum()/2*1000
        self.assertNotAlmostEqual(result['physical_pad_current_RMS_mA'][2],wrong_return,places=6)
        basis['f'][3000]['density'][0,2]=.5
        with self.assertRaisesRegex(ValueError,'KCL'):
            self.scout.physical_pad_currents(basis,coefficients)


    def context_fixture(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name)
        evidence=root/'scientific-evidence.json';evidence.write_text('{"status":"calculated_unadopted"}')
        decision=dict(schema='task1-coherent-drive-root-decision-v1',status='selected_not_executed',
            root_selected=True,peer_endorsed=False,conditions=[dict(c)for c in self.scout.CONDITIONS],
            input_sha256={str(evidence):hashlib.sha256(evidence.read_bytes()).hexdigest()})
        body='Public peer comment: continue a bounded diagnostic; no endorsement inferred.'
        feedback=dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,peer_agreement_inferred=False,
            new_feedback_automatically_adopted=False,observed_utc='2026-10-21T17:00:00Z',
            receipts=[dict(kind='comments',evidence=[dict(id=123,author='public-peer',updated_at='2026-10-21T16:00:00Z',
                body=body,body_sha256=hashlib.sha256(body.encode()).hexdigest(),html_url='https://github.com/example/issues/1#issuecomment-123')])])
        dp=root/'root-decision.json';fp=root/'feedback.json'
        dp.write_text(json.dumps(decision));fp.write_text(json.dumps(feedback))
        return root,evidence,dp,fp,decision,feedback

    def test_context_requires_root_selection_and_actual_sha_bound_public_comment(self):
        root,evidence,dp,fp,_,_=self.context_fixture();pins={}
        with patch.object(self.scout,'ROOT',root):result=self.scout.context_metadata(dp,fp,pins)
        self.assertTrue(result['root_selected']);self.assertFalse(result['peer_endorsed'])
        self.assertEqual(result['feedback_comment_evidence'][0]['id'],123)
        self.assertEqual(set(pins),{str(dp),str(fp),str(evidence)})
        for path,digest in pins.items():self.assertEqual(digest,hashlib.sha256(Path(path).read_bytes()).hexdigest())

    def test_context_rejects_changed_comment_body_sha_and_missing_comments(self):
        root,_,dp,fp,_,feedback=self.context_fixture()
        for change in ('body','missing'):
            bad=copy.deepcopy(feedback)
            if change=='body':bad['receipts'][0]['evidence'][0]['body']+=' changed'
            else:bad['receipts']=[]
            fp.write_text(json.dumps(bad))
            with self.subTest(change=change),patch.object(self.scout,'ROOT',root),self.assertRaises(ValueError):
                self.scout.context_metadata(dp,fp,{})

    def test_context_rejects_peer_endorsement_seed_change_or_changed_evidence(self):
        root,evidence,dp,fp,decision,_=self.context_fixture()
        for change in ('endorsement','seeds'):
            bad=copy.deepcopy(decision)
            if change=='endorsement':bad['peer_endorsed']=True
            else:bad['conditions'][0]['phase_deg']=45
            dp.write_text(json.dumps(bad))
            with self.subTest(change=change),patch.object(self.scout,'ROOT',root),self.assertRaises(ValueError):
                self.scout.context_metadata(dp,fp,{})
        dp.write_text(json.dumps(decision));evidence.write_text('{"changed":true}')
        with patch.object(self.scout,'ROOT',root),self.assertRaisesRegex(ValueError,'evidence changed'):
            self.scout.context_metadata(dp,fp,{})

    def test_context_rejects_sent_messages_automatic_adoption_or_inferred_agreement(self):
        root,_,dp,fp,_,feedback=self.context_fixture()
        for key,value in (('messages_sent',1),('new_PDE',1),('public_GitHub_only',False),
                ('peer_agreement_inferred',True),('new_feedback_automatically_adopted',True),('error','failed GET')):
            bad=copy.deepcopy(feedback);bad[key]=value;fp.write_text(json.dumps(bad))
            with self.subTest(key=key),patch.object(self.scout,'ROOT',root),self.assertRaises(ValueError):
                self.scout.context_metadata(dp,fp,{})
        with patch.object(self.scout,'ROOT',root),self.assertRaises(ValueError):
            self.scout.context_metadata(None,fp,{})

    def test_signed_powers_preserve_negative_tones_even_when_output_totals_positive(self):
        metrics=dict(source_current_spectrum=[dict(frequency_Hz=f,real_A=[.01,.01],imaginary_A=[0.,0.])for f in(3000,3030)],
            loaded_metal_voltage_spectrum=[dict(frequency_Hz=3000,real_V=[1.,-.8],imaginary_V=[0.,0.]),
                dict(frequency_Hz=3030,real_V=[-.8,1.],imaginary_V=[0.,0.])],
            source_power_W=.012,source_resistor_power_W=.01,source_current_RMS_by_output_mA=[10.,10.])
        result=self.scout.signed_output_powers(metrics,scale=.5)
        self.assertTrue(result['requires_source_power_absorption']);self.assertTrue(result['requires_output_power_absorption'])
        self.assertTrue(result['has_negative_per_frequency_ideal_source_power'])
        self.assertFalse(result['has_negative_metal_delivered_power'])
        self.assertFalse(result['hardware_absorption_and_compliance_validated'])
        self.assertGreater(result['outputs'][0]['ideal_source_power_W'],0.)
        self.assertLess(result['outputs'][0]['spectrum'][1]['ideal_source_power_W'],0.)
        self.assertAlmostEqual(result['totals']['ideal_source_power_W'],.012*.25)
        self.assertAlmostEqual(result['outputs'][0]['current_RMS_mA'],5.)

    def test_passive_output_absorption_is_signed_and_not_source_absorption(self):
        metrics=dict(source_current_spectrum=[dict(frequency_Hz=3000,real_A=[.01,.01],imaginary_A=[0.,0.])],
            loaded_metal_voltage_spectrum=[dict(frequency_Hz=3000,real_V=[1.,-.5],imaginary_V=[0.,0.])],
            source_power_W=.0075,source_resistor_power_W=.005,
            source_current_RMS_by_output_mA=[10/math.sqrt(2),10/math.sqrt(2)])
        result=self.scout.signed_output_powers(metrics)
        self.assertFalse(result['requires_source_power_absorption'])
        self.assertFalse(result['has_negative_per_frequency_ideal_source_power'])
        self.assertTrue(result['requires_output_power_absorption']);self.assertTrue(result['has_negative_metal_delivered_power'])
        self.assertAlmostEqual(result['outputs'][1]['metal_delivered_power_W'],-.0025)
        self.assertAlmostEqual(result['outputs'][1]['ideal_source_power_W'],0.)

    def test_generic_source_receipt_does_not_claim_nonunitary_input_is_unitary(self):
        coefficients=self.scout.seed_coefficients(.5,0)
        coefficients[3000][0]*=2;coefficients[3030][0]*=2
        def statistics(*args,**kwargs):return {'Vpp_lower_V':1.,'Vpp_upper_V':1.}
        _,proof=self.scout.normalize_source(coefficients,statistics,self.FakeSamplingLimits)
        self.assertIs(proof['seed_unitary'],False)
        self.assertIs(proof['unitary_after_Vpp_normalization'],False)


    def test_positive_phi90_coherent_complex_field_passes_actual_waveform_audit(self):
        coefficients=self.scout.seed_coefficients(.5,90)
        basis={3000:np.array([[1+.2j,-.1+.3j,.5-.4j],[-.3+.4j,.8+.1j,.1+.2j]]),
            3030:np.array([[.7-.2j,.2+.6j,-.4+.1j],[.1+.5j,-.6+.2j,.9-.3j]])}
        effective=np.stack([coefficients[f]@basis[f]for f in(3000,3030)])
        self.assertTrue(np.any(abs(effective.real)>0));self.assertTrue(np.any(abs(effective.imag)>0))
        direction_set=self.scout.waveform.directions(2048)
        expected_modulation=float(np.max(2*np.min(abs(effective@direction_set.T),axis=0)))
        expected_vector_rms=float(np.sqrt(np.sum(abs(effective)**2)/2))
        condition=dict(id='synthetic-coherent-positive-phi90',waveform='coherent_two_tone_sine',
            actual_fundamental_Hz=[3000,3030],metrics=dict(target20_modulation_V_m=expected_modulation,
                target20_total_E_RMS_V_m=expected_vector_rms,centre_field_spectrum=[
                    dict(frequency_Hz=f,real_V_m=field.real.tolist(),imaginary_V_m=field.imag.tolist())
                    for f,field in zip((3000,3030),effective)]))
        before=copy.deepcopy(condition)
        report=self.scout.waveform.field_check(condition)
        self.assertTrue(report['passed']);self.assertEqual(report['direction_count'],2074)
        self.assertAlmostEqual(report['saved_direction_max_TIS_V_m'],expected_modulation,places=14)
        self.assertTrue(report['vector_waveform']['passed'])
        self.assertAlmostEqual(report['vector_waveform']['reconstructed_RMS'],expected_vector_rms,places=14)
        self.assertAlmostEqual(report['vector_waveform']['common_period_s'],1/30)
        self.assertTrue(report['winning_direction_fundamental_envelope']['passed'])
        self.assertAlmostEqual(report['winning_direction_fundamental_envelope']['exact_width'],expected_modulation,places=14)
        self.assertTrue(report['winning_direction_actual_signed_waveform']['passed'])
        convergence=report['actual_harmonic_waveform_temporal_convergence']
        self.assertTrue(convergence['passed']);self.assertEqual(convergence['status'],'converged_temporal_diagnostic')
        self.assertEqual([row['samples_per_highest_cycle']for row in convergence['levels']],[64,128,256])
        self.assertFalse(convergence['physical_mesh_and_instrument_convergence'])
        self.assertEqual(condition,before)


if __name__=='__main__':unittest.main()
