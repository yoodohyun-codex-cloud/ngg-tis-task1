"""Synthetic four-cohort direction contracts; no native arrays or registration."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import numpy as np
import task1_rounded_direction_bounds as audit


def coefficients():
    return {'3000':dict(real=[0.,-.02],imaginary=[-.98,-.01]),
        '3030':dict(real=[-.01,0.],imaginary=[-.015,-.98]),
        '9000':dict(real=[0.,0.],imaginary=[0.,0.]),'9090':dict(real=[0.,0.],imaginary=[0.,0.])}


def selected_fixture():
    caps={k:float(i+1)for i,k in enumerate(audit.screen.CAP_DEGREES)}
    wave=dict(global_scale=.98,source_Vpp_intervals_V=[[.995,.996],[.999,1.]],global_normalization=True)
    selected=dict(id=audit.SELECTED_ID,coefficient_vectors=coefficients(),source_waveform=wave,normalizations={})
    fixed={}
    for i,name in enumerate(audit.screen.MODES):
        scale=1+i*.05;selected['normalizations'][name]=dict(amplitude_scale=scale,baseline_derived_numerical_limits=copy.deepcopy(caps))
        fixed[name]=dict(amplitude_scale=scale,historical_SC2_mode_id=name,SC4_skin_caps_rematched=False,
            normalization_scope='frozen_SC2_amplitude_no_SC4_rematch',original_SC2_eight_caps=copy.deepcopy(caps),
            actual_source_Vpp_intervals_V=(np.asarray(wave['source_Vpp_intervals_V'])*scale).tolist())
    sc4=dict(coefficient_vectors=copy.deepcopy(selected['coefficient_vectors']),source_waveform=copy.deepcopy(wave),
        same_source_coefficients_and_whole_Vpp=True,selected_SC2_condition_id=selected['id'],
        fixed_SC2_amplitude_modes=fixed,supplemental_SC4_rematched_modes={'unrelated':dict(amplitude_scale=9.)})
    return selected,sc4


def mesh_fixture(sc):
    return dict(sc_cells=sc,cells=351680 if sc==2 else 361728,h_xy_mm=.625,radius_mm=25.,total_depth_mm=25.1,
        bulk_layer_counts=[14,14,40],tissue_boundaries_mm=[0,.1,5.1,10.1,25.1],channels=2,n_outputs=2,
        source_peak_V=.5,source_resistance_ohm=50.,phasor_convention='peak,+jomega_t',field_reconstruction='same',
        frequencies_Hz=list(audit.FREQUENCIES),z_faces_mm=([0,.05,.1]if sc==2 else[0,.025,.05,.075,.1])+[1.,5.1,10.1,25.1])


def interval_mode(target=(4.,4.2),off=(8.,8.2),high=(1e-7,2e-7)):
    result=dict(regions={})
    for region in (audit.volume.PRIMARY,'surface_0_5','primary_complement'):
        pair=target if region==audit.volume.PRIMARY else off
        result['regions'][region]=dict(old2074_maxTIS_LB={s:pair[0]for s in ('mean','p10','p95')},
            continuous_direction_UB={s:pair[1]for s in ('mean','p10','p95')},
            continuous_direction_fixed_cutoff_volume_intervals={audit.volume.PRIMARY+'_'+s:
                dict(lower_volume_m3=high[0],upper_volume_m3=high[1])for s in ('mean','p10')})
    return result


class RoundedDirectionBoundsTests(unittest.TestCase):
    def test_exact_four_cohorts_use_existing_nine_lambda_helper(self):
        self.assertEqual(audit.bounds.LAMBDAS,tuple(i/8 for i in range(9)))
        self.assertEqual(audit.PAIR,(3000,3030));self.assertNotEqual(audit.SC4_ID,audit.ROUND_ID)
        self.assertEqual(audit.SOURCE_SUMMARIES,(audit.CONTROL_VOLUME,audit.OPT_SUMMARY,audit.SC4_SUMMARY))

    def test_explicit_SC4_adapter_rejects_fake_SC2_identity_and_model_changes(self):
        c2={'validation.sc_cells':'2','mask.path':'old.csv','mask.sha256':'same','sc.sigma':'.0002'}
        c4=dict(c2,**{'validation.sc_cells':'4','mask.path':'new.csv'})
        result=audit.validate_mesh_identity(mesh_fixture(2),mesh_fixture(4),c2,c4)
        self.assertEqual(result['SC4_cells'],361728)
        wrong=mesh_fixture(4);wrong['cells']=351680
        with self.assertRaisesRegex(ValueError,'Genuine SC2/SC4'):audit.validate_mesh_identity(mesh_fixture(2),wrong,c2,c4)
        wrong=dict(c4,**{'sc.sigma':'.0003'})
        with self.assertRaisesRegex(ValueError,'Only actual SC cell count'):audit.validate_mesh_identity(mesh_fixture(2),mesh_fixture(4),c2,wrong)
        wrong=mesh_fixture(4);wrong['z_faces_mm'][-2]=10.2
        with self.assertRaisesRegex(ValueError,'bulk faces'):audit.validate_mesh_identity(mesh_fixture(2),wrong,c2,c4)

    def test_five_historical_SC2_amplitudes_and_whole_wave_Vpp_preserved(self):
        selected,sc4=selected_fixture();before=copy.deepcopy(sc4)
        result=audit.validate_fixed_modes(selected,sc4)
        self.assertEqual(set(result),set(audit.screen.MODES));self.assertEqual(sc4,before)
        self.assertNotIn('unrelated',result)
        result['raw_1Vpp']['amplitude_scale']=5.;self.assertEqual(sc4,before)

    def test_supplemental_rematch_or_coefficient_renormalization_is_rejected(self):
        selected,sc4=selected_fixture();sc4['fixed_SC2_amplitude_modes']['skin_contact_only']['amplitude_scale']*=1.001
        with self.assertRaisesRegex(ValueError,'historical SC2 amplitude'):audit.validate_fixed_modes(selected,sc4)
        selected,sc4=selected_fixture();sc4['coefficient_vectors']['3000']['imaginary'][0]=-1.
        with self.assertRaisesRegex(ValueError,'Exact selected SC2 coefficients'):audit.validate_fixed_modes(selected,sc4)
        selected,sc4=selected_fixture();sc4['fixed_SC2_amplitude_modes']['skin_contact_only']['actual_source_Vpp_intervals_V'][0][0]*=1.001
        with self.assertRaisesRegex(ValueError,'whole-wave Vpp'):audit.validate_fixed_modes(selected,sc4)

    def test_complex_cross_output_fields_are_coherently_composed_without_new_scale(self):
        source=np.array([[[1+2j,0,1]],[[3-1j,2j,0]]],complex)
        fields={3000:source,3030:source*2j};coef=coefficients()
        result=audit.compose_fundamentals(fields,{str(f):coef[str(f)]for f in audit.PAIR})
        for f in audit.PAIR:
            c=np.asarray(coef[str(f)]['real'])+1j*np.asarray(coef[str(f)]['imaginary'])
            expected=c[0]*fields[f][0]+c[1]*fields[f][1]
            np.testing.assert_array_equal(result[f],expected)
        self.assertNotEqual(result[3000][0,1],0j)
        np.testing.assert_array_equal(source[0,0],[1+2j,0,1])

    def test_selected_coefficient_decoder_rejects_hidden_harmonic_or_nonfinite(self):
        value=dict(coefficient_vectors=coefficients());decoded=audit.decode_coefficients(value)
        self.assertEqual(set(decoded),{'3000','3030'})
        value['coefficient_vectors']['9000']['real'][0]=.01
        with self.assertRaisesRegex(ValueError,'zero harmonics'):audit.decode_coefficients(value)
        value=dict(coefficient_vectors=coefficients());value['coefficient_vectors']['3030']['real'][1]=float('nan')
        with self.assertRaisesRegex(ValueError,'Finite actual complex'):audit.decode_coefficients(value)

    def test_conditional_all_eight_failures_include_actual_high_volume_intervals(self):
        baseline=interval_mode();candidate=interval_mode(target=(3.,3.1),off=(9.,9.1),high=(3e-7,4e-7))
        result=audit.conditional_eight_screen(candidate,baseline)
        self.assertEqual(len(result['checks']),8)
        self.assertTrue(all(c['status']=='conditional_direction_robust_failure'for c in result['checks']))
        self.assertTrue(result['any_conditional_direction_robust_failure']);self.assertFalse(result['old_screen_replaced'])

    def test_original_upper_vs_candidate_lower_required_for_robust_pass(self):
        baseline=interval_mode();candidate=interval_mode(target=(4.5,4.6),off=(7.,7.1),high=(1e-8,2e-8))
        result=audit.conditional_eight_screen(candidate,baseline)
        self.assertTrue(result['all_conditional_direction_robust_pass'])
        self.assertTrue(all(c['status']=='conditional_direction_robust_pass'for c in result['checks']))
        candidate=interval_mode(target=(4.1,4.3),off=(8.1,8.3),high=(1.5e-7,2.5e-7))
        result=audit.conditional_eight_screen(candidate,baseline)
        self.assertEqual(result['inconclusive_count'],8)

    def test_target_loss_cannot_be_hidden_by_surface_ratio_improvement(self):
        baseline=interval_mode();candidate=interval_mode(target=(2.,2.1),off=(1.,1.1),high=(1e-8,2e-8))
        checks=audit.conditional_eight_screen(candidate,baseline)['checks']
        self.assertTrue(all(c['status']=='conditional_direction_robust_failure'for c in checks[:2]))
        self.assertTrue(all(c['status']=='conditional_direction_robust_pass'for c in checks[2:]))

    def test_saved_lower_bounds_and_inclusive_fixed_cutoff_volumes_retained(self):
        e0=np.array([[1.,0.,0.],[2.,0.,0.]],complex);e1=e0.copy()
        result=audit.bounds.field_bounds(e0,e1);lower=np.array([2.,4.]);before=lower.copy()
        audit.bounds.validate_lower_bound(lower,result['continuous_direction_UB_V_m'])
        stats=audit.bounds.weighted_volume_interval(lower,result['continuous_direction_UB_V_m'],np.array([.25,.75]),2.,scale=.5)
        self.assertEqual(stats['lower_volume_m3'],.75);np.testing.assert_array_equal(lower,before)
        self.assertEqual(stats['comparison'],'>=')

    def test_fixed_gate_tolerance_does_not_promote_near_tie_to_robust_failure_or_pass(self):
        base=interval_mode();candidate=interval_mode(target=(4.-1e-11,4.2+1e-11),off=(8.-1e-11,8.2+1e-11),high=(1e-7,2e-7))
        result=audit.conditional_eight_screen(candidate,base)
        self.assertEqual(result['inconclusive_count'],8)

    def test_metadata_artifact_binding_rejects_wrong_completed_status_before_arrays(self):
        refs={};source=dict(conditions=[dict(id='selected',artifacts={'condition.json':dict(path='/fake/condition.json',SHA256='a')})])
        with mock.patch.object(audit,'_json',return_value=dict(schema='expected',status='running',id='selected')):
            with self.assertRaisesRegex(ValueError,'Completed unchanged'):audit._condition_artifacts(source,'selected',refs,'expected')

    def test_failed_main_preserves_originals_and_append_only_actual_cost(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);(root/'docs').mkdir();(root/'runtime').mkdir()
            source=root/'saved-native';source.write_bytes(b'original arrays are never overwritten')
            plan=root/'docs/plan.json';plan.write_text('{}');output=root/'docs/new-output'
            ledger=dict(limit_seconds=13800,spent_seconds=123.,runs=[dict(previous='preserved')]);old=copy.deepcopy(ledger)
            argv=['task1_rounded_direction_bounds.py','--preregistration',str(plan),'--output',str(output)]
            with mock.patch.object(audit,'ROOT',root),mock.patch.object(audit.policy,'load_ledger',return_value=ledger),\
                    mock.patch.object(audit.policy,'remaining_seconds',return_value=1000.),\
                    mock.patch.object(audit,'verify_plan',side_effect=ValueError('deliberate source hash mismatch')),\
                    mock.patch.object(sys,'argv',argv):
                with self.assertRaisesRegex(ValueError,'hash mismatch'):audit.main()
            self.assertEqual(source.read_bytes(),b'original arrays are never overwritten')
            saved=json.loads((root/'runtime/task1-budget.json').read_text())
            self.assertEqual(saved['runs'][:1],old['runs']);self.assertGreater(saved['spent_seconds'],123.)
            self.assertEqual(saved['runs'][-1]['status'],'failed_preserved');self.assertGreater(saved['runs'][-1]['seconds'],0.)
            self.assertTrue((output/'failure.json').exists())
            with mock.patch.object(audit,'ROOT',root),mock.patch.object(sys,'argv',argv):
                with self.assertRaisesRegex(ValueError,'New canonical'):audit.main()


if __name__=='__main__':unittest.main()
