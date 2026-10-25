"""Synthetic weak-drive source contracts; no native data, PDE or preparation."""
import ast
import copy
import importlib.util
import hashlib
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


class CoherentDriveWeakScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name,file in (('weak','task1_coherent_drive_weak_scout.py'),('strong','task1_coherent_drive_scout.py')):
            spec=importlib.util.spec_from_file_location('tested_'+name+'_scout',ROOT/'tools'/file)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);setattr(cls,name,module)

    def test_exact_six_registered_conditions(self):
        expected=[dict(id=f'coherent-weak-r{label}-p{phase:03d}',mix_ratio=ratio,phase_deg=phase)
            for ratio,label in ((.05,'0p05'),(.1,'0p1'),(.2,'0p2'))for phase in (90,270)]
        self.assertEqual(list(self.weak.CONDITIONS),expected)
        self.assertEqual(len({item['id']for item in self.weak.CONDITIONS}),6)

    def test_weak_seed_complex_matrix_matches_registered_ratios_and_phases(self):
        for ratio in (.05,.1,.2):
            for phase in (90,270):
                angle=np.deg2rad(phase)
                expected=-1j/np.sqrt(1+ratio**2)*np.array([[1,-ratio*np.exp(-1j*angle)],
                    [ratio*np.exp(1j*angle),1]],dtype=complex)
                coefficients=self.weak.seed_coefficients(ratio,phase)
                np.testing.assert_allclose(np.stack([coefficients[3000],coefficients[3030]]),expected,rtol=0,atol=1e-15)

    def test_weak_seeds_preserve_unitarity_and_equal_column_spectral_norm(self):
        for declaration in self.weak.CONDITIONS:
            coefficients=self.weak.seed_coefficients(declaration['mix_ratio'],declaration['phase_deg'])
            matrix=np.stack([coefficients[3000],coefficients[3030]])
            np.testing.assert_allclose(matrix.conj().T@matrix,np.eye(2),rtol=0,atol=5e-16)
            np.testing.assert_allclose(matrix@matrix.conj().T,np.eye(2),rtol=0,atol=5e-16)
            self.assertTrue(np.all(abs(matrix)>0))

    def test_actual_frequency_and_zero_harmonic_contract(self):
        for declaration in self.weak.CONDITIONS:
            coefficients=self.weak.seed_coefficients(declaration['mix_ratio'],declaration['phase_deg'])
            self.assertEqual(set(coefficients),{3000,3030,9000,9090})
            for frequency,value in coefficients.items():
                self.assertEqual(value.shape,(2,));self.assertTrue(np.iscomplexobj(value));self.assertTrue(np.isfinite(value).all())
            np.testing.assert_array_equal(coefficients[9000],np.zeros(2,dtype=complex))
            np.testing.assert_array_equal(coefficients[9090],np.zeros(2,dtype=complex))

    def test_weak_quadrature_phase_signs_are_distinct(self):
        ratio=.1;scale=math.sqrt(1+ratio**2)
        positive=self.weak.seed_coefficients(ratio,90);negative=self.weak.seed_coefficients(ratio,270)
        np.testing.assert_allclose(positive[3000],[-1j/scale,ratio/scale],rtol=0,atol=1e-15)
        np.testing.assert_allclose(positive[3030],[ratio/scale,-1j/scale],rtol=0,atol=1e-15)
        np.testing.assert_allclose(negative[3000],[-1j/scale,-ratio/scale],rtol=0,atol=1e-15)
        np.testing.assert_allclose(negative[3030],[-ratio/scale,-1j/scale],rtol=0,atol=1e-15)

    def test_weak_seed_arrays_and_calls_are_independent(self):
        first=self.weak.seed_coefficients(.05,90);before=copy.deepcopy(first);second=self.weak.seed_coefficients(.05,90)
        first[3000][0]=99j;first[9000][0]=123
        for frequency in second:np.testing.assert_array_equal(second[frequency],before[frequency])
        np.testing.assert_array_equal(first[9090],np.zeros(2,dtype=complex))

    def test_strong_ratios_nonquadrature_phases_and_nonfinite_inputs_rejected(self):
        for ratio in (0.,-.05,.3,.5,1.,float('nan'),float('inf')):
            with self.subTest(ratio=ratio),self.assertRaises((ValueError,TypeError)):
                self.weak.seed_coefficients(ratio,90)
        for phase in (0,180,360,45,float('nan'),float('inf')):
            with self.subTest(phase=phase),self.assertRaises((ValueError,TypeError)):
                self.weak.seed_coefficients(.1,phase)

    def test_frozen_numerical_and_waveform_helper_function_asts_match_parent(self):
        def functions(path):
            tree=ast.parse(path.read_text())
            class CanonicalSchema(ast.NodeTransformer):
                def visit_Constant(self,node):
                    if node.value=='task1-coherent-drive-weak-condition-v1':
                        node.value='task1-coherent-drive-condition-v1'
                    return node
            tree=CanonicalSchema().visit(tree)
            return {node.name:ast.dump(node,include_attributes=False)for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
        weak=functions(Path(self.weak.__file__));strong=functions(Path(self.strong.__file__))
        for name in ('validated_coefficients','normalize_source','normalization_modes','signed_output_powers',
                     'physical_pad_currents','derive'):
            with self.subTest(function=name):self.assertEqual(weak[name],strong[name])

    def test_cached_exclusive_control_and_fixed_physics_preserved(self):
        self.assertEqual(self.weak.CONTROL_ID,self.strong.CONTROL_ID)
        self.assertEqual(self.weak.CONTROL_ID,'sine-3000-3030-beat30')
        self.assertEqual(self.weak.CONTROL_SUMMARY,self.strong.CONTROL_SUMMARY)
        self.assertEqual(self.weak.BASELINE_SUMMARY,self.strong.BASELINE_SUMMARY)
        self.assertEqual(self.weak.FREQUENCIES,self.strong.FREQUENCIES)
        self.assertEqual(self.weak.PAIR,(3000,3030))
        self.assertEqual(self.weak.VPP_WIDTH,1e-6)
        self.assertEqual(self.weak.LEVELS,self.strong.LEVELS)
        self.assertEqual(self.weak.screen.GATE_DEFINITIONS,self.strong.screen.GATE_DEFINITIONS)


    class FakeSamplingLimits:
        def __init__(self,**kwargs):self.__dict__.update(kwargs)

    def test_weak_source_full_wave_upper_normalization_preserves_one_microvolt_bound(self):
        for declaration in self.weak.CONDITIONS:
            seed=self.weak.seed_coefficients(declaration['mix_ratio'],declaration['phase_deg']);before=copy.deepcopy(seed);calls=[]
            def statistics(frequencies,phasors,fundamentals,*,sampling):
                self.assertEqual(list(frequencies),[3000,3030]);self.assertEqual(list(fundamentals),[3000,3030])
                self.assertEqual(sampling.max_statistics_samples,262144)
                upper=float(2*np.sum(abs(phasors)));calls.append(np.asarray(phasors).copy())
                return dict(Vpp_lower_V=upper*(1-5e-7),Vpp_upper_V=upper)
            normalized,proof=self.weak.normalize_source(seed,statistics,self.FakeSamplingLimits)
            self.assertTrue(proof['seed_unitary']);self.assertFalse(proof['unitary_after_Vpp_normalization'])
            self.assertEqual(len(calls),2);self.assertLessEqual(proof['maximum_bracket_width_V'],1e-6)
            for output in range(2):
                np.testing.assert_allclose(calls[output],.5*np.array([seed[f][output]for f in(3000,3030)]),atol=1e-15,rtol=0)
                self.assertEqual(proof['source_Vpp_intervals_V'][output][1],1.)
                self.assertGreaterEqual(proof['source_Vpp_intervals_V'][output][0],1-1e-6)
            for f in seed:
                np.testing.assert_array_equal(seed[f],before[f])
                np.testing.assert_allclose(normalized[f],seed[f]*proof['column_scales'],rtol=0,atol=1e-15)

    def test_weak_source_unresolved_bracket_holds_without_relaxation(self):
        def unresolved(*args,**kwargs):return dict(Vpp_lower_V=.999,Vpp_upper_V=1.)
        with self.assertRaisesRegex(ValueError,'1uV'):
            self.weak.normalize_source(self.weak.seed_coefficients(.05,270),unresolved,self.FakeSamplingLimits)

    def test_actual_source_intervals_current_and_power_scaling_inherited(self):
        degrees={'surface_J_RMS_max_A_m2':1,'surface_J_RMS_p95_A_m2':1,'contact_voltage_RMS_max_V':1,
            'SC_power_W':2,'contact_power_W':2,'source_power_W':2,'bulk_skin_J_vector_RMS_max_A_m2':1,
            'bulk_skin_J_vector_RMS_p95_A_m2':1,'skin_SC_plus_dermis_power_W':2}
        candidate={key:.5**degree for key,degree in degrees.items()};baseline={key:1. for key in degrees}
        intervals=[[1-5e-7,1.],[1-3e-7,1.]]
        modes=self.weak.normalization_modes(candidate,baseline,.5,1.,intervals)
        self.assertEqual(len(modes),5)
        for name in ('equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only'):
            mode=modes[name];self.assertEqual(mode['amplitude_scale'],2.)
            self.assertEqual(mode['sum_source_output_RMS_mA'],1.)
            self.assertNotIn('source_Vpp_per_output',mode)
            np.testing.assert_allclose(mode['actual_source_Vpp_intervals_V'],np.asarray(intervals)*2,rtol=0,atol=1e-15)
            self.assertEqual(mode['normalized_burdens'],baseline)
        self.assertEqual(modes['legacy_composite_full_skin']['amplitude_scale'],1.)
        self.assertEqual(modes['legacy_composite_full_skin']['source_Vpp_upper_by_output_V'],[1.,1.])

    def parent_evidence_mocks(self,source_sha=None,test_sha=None,expected=None):
        source=Path(self.weak.PARENT_SOURCE_PATH).read_bytes()
        expected=source if expected is None else expected
        source_sha=self.weak.PARENT_SOURCE_SHA256 if source_sha is None else source_sha
        test_sha=self.weak.PARENT_TEST_SHA256 if test_sha is None else test_sha
        def sha(path):
            if Path(path)==self.weak.PARENT_SOURCE_PATH:return source_sha
            if Path(path)==self.weak.PARENT_TEST_PATH:return test_sha
            raise AssertionError('Unexpected parent evidence path')
        return source,patch.object(self.weak.subprocess,'check_output',return_value=expected),patch.object(self.weak.view,'sha',side_effect=sha)

    def test_parent_evidence_preserves_executed_commit_and_source_test_hashes(self):
        source,gitmock,shamock=self.parent_evidence_mocks()
        self.assertEqual(hashlib.sha256(source).hexdigest(),self.weak.PARENT_SOURCE_SHA256)
        with gitmock as git,shamock:proof=self.weak.parent_implementation_evidence()
        self.assertEqual(proof['parent_commit'],'9e81df26605155e2f1b31e063ed236340f2c71dd')
        self.assertEqual(proof['source_SHA256'],self.weak.PARENT_SOURCE_SHA256)
        self.assertEqual(proof['tests_SHA256'],self.weak.PARENT_TEST_SHA256)
        self.assertEqual(proof['source_path'],str(self.weak.PARENT_SOURCE_PATH))
        self.assertEqual(proof['tests_path'],str(self.weak.PARENT_TEST_PATH))
        self.assertTrue(proof['changed_scope'])
        self.assertEqual(git.call_args.args[0],['git','show',self.weak.PARENT_COMMIT+':tools/task1_coherent_drive_scout.py'])

    def test_parent_evidence_rejects_source_test_and_commit_content_mismatch(self):
        for arguments in (dict(source_sha='0'*64),dict(test_sha='0'*64),dict(expected=b'changed frozen parent source')):
            _,gitmock,shamock=self.parent_evidence_mocks(**arguments)
            with self.subTest(arguments=arguments),gitmock,shamock,self.assertRaises(ValueError):
                self.weak.parent_implementation_evidence()

    def screen_row_from_values(self,values):
        primary=self.weak.screen.PRIMARY
        regions={primary:{'maxTIS':dict(mean=values['primary_maxTIS_mean'],p10=values['primary_maxTIS_p10'])}}
        for region in ('surface_0_5','primary_complement'):
            regions[region]={'maxTIS':dict(p95=values[region+'_maxTIS_p95'],fixed_baseline_threshold_volume={
                primary+'_'+stat:dict(volume_m3=values[region+'_high_volume_at_'+primary+'_'+stat])for stat in('mean','p10')})}
        return dict(normalizations={'skin_contact_only':dict(regions=regions)})

    def test_cached_exclusive_control_target_gain_is_not_assumed_non_target_headroom(self):
        definitions=self.weak.screen.GATE_DEFINITIONS
        baseline_values={definition['name']:1e-7 if definition['unit']=='m3' else 1. for definition in definitions}
        candidate_values={name:value*1.1 for name,value in baseline_values.items()}
        baseline=self.screen_row_from_values(baseline_values);candidate=self.screen_row_from_values(candidate_values)
        condition=dict(cohorts={'cached_original_square_3000_3030_caps':candidate})
        before=copy.deepcopy((condition,baseline));proof=self.weak.cached_control_screen(condition,baseline)
        self.assertEqual(len(proof['checks']),8)
        self.assertEqual([row['passed']for row in proof['checks']],[True,True,False,False,False,False,False,False])
        self.assertEqual(proof['failed_checks'],[definition['name']for definition in definitions[2:]])
        self.assertFalse(proof['all_screen_checks_passed']);self.assertFalse(proof['headroom_assumed'])
        self.assertFalse(proof['candidate_adopted']);self.assertEqual(proof['normalization'],'skin_contact_only')
        self.assertEqual((condition,baseline),before)

    def test_cached_control_equality_passes_same_eight_gates_and_missing_mode_rejected(self):
        values={definition['name']:1e-7 if definition['unit']=='m3' else 1. for definition in self.weak.screen.GATE_DEFINITIONS}
        baseline=self.screen_row_from_values(values)
        proof=self.weak.cached_control_screen(dict(cohorts={'cached_original_square_3000_3030_caps':copy.deepcopy(baseline)}),baseline)
        self.assertTrue(proof['all_screen_checks_passed']);self.assertEqual(proof['failed_checks'],[])
        self.assertFalse(proof['headroom_assumed'])
        with self.assertRaisesRegex(ValueError,'mode required'):
            self.weak.cached_control_screen(dict(cohorts={'cached_original_square_3000_3030_caps':{'normalizations':{}}}),baseline)


if __name__=='__main__':unittest.main()
