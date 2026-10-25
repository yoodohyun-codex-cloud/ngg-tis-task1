"""Synthetic cached-drive search contracts; no native arrays, research or PDE."""
import copy
import importlib.util
import itertools
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


def unit_directions(count=4096):
    output=[np.array(value,dtype=float)/np.linalg.norm(value)for value in itertools.product((-1,0,1),repeat=3)if any(value)]
    for index in range(count):
        z=1-2*(index+.5)/count;angle=index*np.pi*(3-np.sqrt(5));radius=math.sqrt(1-z*z)
        output.append([radius*math.cos(angle),radius*math.sin(angle),z])
    return np.asarray(output)


def sampled_modulation(first,second,directions):
    return np.max(2*np.minimum(abs(np.asarray(first)@directions.T),abs(np.asarray(second)@directions.T)),axis=1)


class PerimeterDriveOptimizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('perimeter_drive_optimization_tested',ROOT/'tools/task1_perimeter_drive_optimization.py')
        cls.tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cls.tool;spec.loader.exec_module(cls.tool)

    def fields(self):
        rng=np.random.default_rng(19)
        return (rng.normal(size=(7,3))+1j*rng.normal(size=(7,3)),
                rng.normal(size=(7,3))+1j*rng.normal(size=(7,3)))

    def baseline(self):
        off={region:dict(p95=1.,high_volume_mean_m3=1e-7,high_volume_p10_m3=2e-7)
            for region in('surface_0_5','primary_complement')}
        return dict(target=dict(mean=1.,p10=.8),**off)

    def test_fixed_five_real_genes_bounds_steps_and_four_seed_family(self):
        self.assertEqual(tuple(self.tool.GENES),('z0_real','z0_imag','z1_real','z1_imag','rho'))
        self.assertEqual(tuple(map(tuple,self.tool.BOUNDS)),((-1,1),)*4+((.5,2),))
        self.assertEqual(tuple(self.tool.STEPS),(.25,.125,.0625))
        np.testing.assert_array_equal(self.tool.SEEDS,[[0,0,0,0,1],[-.05,0,-.05,0,1],[0,.05,0,.05,1],[0,-.05,0,-.05,1]])
        for seed in self.tool.SEEDS:self.assertTrue(self.tool.valid_gene(seed))

    def test_gene_validation_accepts_endpoints_and_rejects_invalid_without_clipping(self):
        for gene in([-1,1,-1,1,.5],[1,-1,1,-1,2]):self.assertTrue(self.tool.valid_gene(gene))
        for gene in([1.00001,0,0,0,1],[0,0,0,0,.499999],[0,0,0,0,2.00001],
                [0,0,0,0],[0,0,0,0,1,1],[0,float('nan'),0,0,1],[0,0,0,0,float('inf')],np.zeros((5,1))):
            before=copy.deepcopy(gene)
            with self.subTest(gene=gene):self.assertFalse(self.tool.valid_gene(gene))
            np.testing.assert_equal(gene,before)

    def test_gene_keys_keep_adjacent_floats_and_source_metric_identities_distinct(self):
        gene=[0.,0.,0.,0.,1.];next_gene=gene.copy();next_gene[0]=float(np.nextafter(0.,1.))
        self.assertNotEqual(self.tool.gene_key(gene),self.tool.gene_key(next_gene))
        self.assertEqual(self.tool.gene_key(gene),self.tool.gene_key(tuple(gene)))
        self.assertNotEqual(self.tool.gene_key(gene,source_identity='source-A'),self.tool.gene_key(gene,source_identity='source-B'))
        self.assertNotEqual(self.tool.gene_key(gene,metric_identity='metric-A'),self.tool.gene_key(gene,metric_identity='metric-B'))

    def test_gene_coefficients_keep_complex_signs_actual_frequencies_and_zero_harmonics(self):
        gene=[.25,-.5,-.75,.125,1.5];before=gene.copy();coefficients=self.tool.gene_coefficients(gene)
        self.assertEqual(set(coefficients),{3000,3030,9000,9090})
        np.testing.assert_allclose(coefficients[3000],[-1j,-.5-.25j],rtol=0,atol=1e-15)
        np.testing.assert_allclose(coefficients[3030],[.125+.75j,-1.5j],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(coefficients[9000],[0j,0j]);np.testing.assert_array_equal(coefficients[9090],[0j,0j])
        self.assertEqual(gene,before)
        second=self.tool.gene_coefficients(gene);coefficients[3000][0]=123
        np.testing.assert_array_equal(second[3000],[-1j,-.5-.25j])
        with self.assertRaises(ValueError):self.tool.gene_coefficients([2,0,0,0,1])

    def test_continuous_direction_upper_bound_exceeds_independent_dense_real_direction_samples(self):
        first,second=self.fields();before=(first.copy(),second.copy())
        upper=self.tool.gershgorin_upper(first,second,chunk_cells=2)
        dense=sampled_modulation(first,second,unit_directions())
        self.assertEqual(upper.shape,(len(first),));self.assertTrue(np.all(np.isfinite(upper)))
        self.assertTrue(np.all(upper>=dense-1e-11))
        np.testing.assert_array_equal(first,before[0]);np.testing.assert_array_equal(second,before[1])

    def test_orthogonal_analytic_carriers_have_sqrt_two_tight_dual_bound(self):
        first=np.array([[1,0,0],[1,0,0]],complex);second=np.array([[0,1,0],[1,0,0]],complex)
        upper=self.tool.gershgorin_upper(first,second)
        np.testing.assert_allclose(upper,[math.sqrt(2),2.],rtol=1e-8,atol=1e-10)
        np.testing.assert_allclose(self.tool.target_lower(first,second),[math.sqrt(2),2.],rtol=1e-14,atol=1e-14)

    def test_bounds_are_invariant_to_each_carrier_global_phase_and_swap_and_scale(self):
        first,second=self.fields();upper=self.tool.gershgorin_upper(first,second);lower=self.tool.target_lower(first,second)
        np.testing.assert_allclose(self.tool.gershgorin_upper(first*np.exp(.3j),second*np.exp(-.7j)),upper,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(self.tool.target_lower(first*np.exp(.3j),second*np.exp(-.7j)),lower,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(self.tool.gershgorin_upper(second,first),upper,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(self.tool.gershgorin_upper(first*3,second*3),upper*3,rtol=1e-10,atol=1e-10)

    def test_target_static_26_direction_lower_bound_is_not_promoted_to_continuous_maximum(self):
        first,second=self.fields();lower=self.tool.target_lower(first,second)
        directions=unit_directions();expected=sampled_modulation(first,second,directions[:26])
        np.testing.assert_allclose(lower,expected,rtol=1e-14,atol=1e-14)
        self.assertTrue(np.all(lower<=sampled_modulation(first,second,directions)+1e-12))
        self.assertTrue(np.any(lower<sampled_modulation(first,second,directions)-1e-4))

    def test_bounds_reject_invalid_shapes_and_nonfinite_fields_and_handle_zero_modulation(self):
        first,second=self.fields()
        for bad in(first[:,:2],first[:-1],np.full(first.shape,np.nan+0j)):
            for function in(self.tool.gershgorin_upper,self.tool.target_lower):
                with self.subTest(shape=bad.shape,function=function.__name__),self.assertRaises(ValueError):function(bad,second)
        zero=np.zeros((2,3),complex)
        upper=self.tool.gershgorin_upper(zero,zero);lower=self.tool.target_lower(zero,zero)
        self.assertTrue(np.isfinite(upper).all());self.assertTrue(np.all(upper>=0))
        np.testing.assert_array_equal(lower,np.zeros(2))

    def test_proxy_objective_respects_eight_screen_directions_then_target_p10(self):
        baseline=self.baseline();off={key:copy.deepcopy(baseline[key])for key in('surface_0_5','primary_complement')}
        self.assertEqual(self.tool.proxy_objective(copy.deepcopy(baseline['target']),off,baseline),(0.,0.,-.8))
        good_target=dict(mean=1.1,p10=.9);good_off={r:{k:v*.9 for k,v in stats.items()}for r,stats in off.items()}
        good=self.tool.proxy_objective(good_target,good_off,baseline)
        self.assertEqual(good,(0.,0.,-.9))
        bad_off=copy.deepcopy(off);bad_off['primary_complement']['p95']=1.2
        bad=self.tool.proxy_objective(good_target,bad_off,baseline)
        self.assertGreater(bad[0],0.);self.assertGreater(bad[1],0.)
        self.assertLess(good,bad)

    def test_proxy_objective_keeps_existing_arithmetic_tolerance_not_a_new_percent_gate(self):
        baseline=self.baseline();target=copy.deepcopy(baseline['target']);off={key:copy.deepcopy(baseline[key])for key in('surface_0_5','primary_complement')}
        target['mean']-=.5*(1e-12+1e-10)
        off['surface_0_5']['p95']+=.5*(1e-12+1e-10)
        self.assertEqual(self.tool.proxy_objective(target,off,baseline)[:2],(0.,0.))
        off['surface_0_5']['p95']=1+2*(1e-12+1e-10)
        self.assertGreater(self.tool.proxy_objective(target,off,baseline)[0],0.)


    def test_upper_bound_uses_no_eigensolver_and_expired_chunk_deadline_cannot_return_partial_array(self):
        first,second=self.fields()
        with patch.object(np.linalg,'eig',side_effect=AssertionError('No eigensolver')),             patch.object(np.linalg,'eigh',side_effect=AssertionError('No eigensolver')),             patch.object(np.linalg,'eigvals',side_effect=AssertionError('No eigensolver')),             patch.object(np.linalg,'eigvalsh',side_effect=AssertionError('No eigensolver')):
            self.assertTrue(np.isfinite(self.tool.gershgorin_upper(first,second)).all())
        with self.assertRaises(self.tool.ProxyDeadline):self.tool.gershgorin_upper(first,second,deadline=-1.)
        for dirs in(np.array([[2.,0.,0.]]),np.array([1.,0.,0.]),np.empty((0,3)),np.array([[float('nan'),0.,0.]])):
            with self.assertRaises(ValueError):self.tool.target_lower(first,second,dirs=dirs)

    def evaluator(self,gene):
        return dict(objective=(sum(abs(value)for value in gene[:4])+abs(gene[4]-1),0.,-1.),sentinel='synthetic')

    def test_search_is_deterministic_bounded_and_never_labels_ranked_proxy_as_global_optimum(self):
        calls=[]
        def evaluate(gene):calls.append(gene);return self.evaluator(gene)
        first=self.tool.bounded_pattern_search(evaluate,deadline=100.,clock=lambda:0.)
        second=self.tool.bounded_pattern_search(self.evaluator,deadline=100.,clock=lambda:0.)
        self.assertEqual(first,second)
        self.assertEqual(first['status'],'proxy_search_complete_ranked_only')
        self.assertLessEqual(first['evaluation_attempts'],124)
        self.assertEqual(first['completed_evaluations'],len(first['evaluations']))
        self.assertEqual(len(calls),first['evaluation_attempts'])
        self.assertTrue(first['ranked_only_not_full2074_validation'])
        self.assertFalse(first['global_optimum_claimed']);self.assertFalse(first['all124_evaluations_promised'])
        self.assertTrue(all(self.tool.valid_gene(gene)for gene in calls))
        self.assertTrue(all(row['completed']and row['anchor_updated_once']for row in first['levels']))

    def test_search_evaluates_all_ten_neighbors_from_fixed_anchor_before_moving(self):
        calls=[]
        def evaluate(gene):
            calls.append(gene)
            return dict(objective=(gene[0]+1.,0.,-1.))
        result=self.tool.bounded_pattern_search(evaluate,deadline=100.,max_evaluations=14,clock=lambda:0.)
        self.assertEqual(result['status'],'proxy_budget_exhausted_partial')
        self.assertEqual(result['completed_evaluations'],14)
        self.assertEqual(calls[:4],[tuple(map(float,seed))for seed in self.tool.SEEDS])
        anchor=list(self.tool.SEEDS[0]);expected=[]
        for dim in range(5):
            for sign in(-1,1):
                gene=list(anchor);gene[dim]+=sign*.25;expected.append(tuple(map(float,gene)))
        self.assertEqual(calls[4:14],expected)
        level=result['levels'][0]
        self.assertEqual(level['anchor_genes'],list(map(float,anchor)))
        self.assertTrue(level['completed']);self.assertTrue(level['anchor_updated_once'])
        self.assertEqual(level['returned_neighbor_records'],10)

    def test_search_exact_dedup_and_bounds_skip_avoid_duplicate_or_clipped_evaluations(self):
        seed=(1.,0.,0.,0.,1.);calls=[]
        def evaluate(gene):calls.append(gene);return dict(objective=(0.,0.,-1.))
        with patch.object(self.tool,'SEEDS',(seed,)*4):
            result=self.tool.bounded_pattern_search(evaluate,deadline=100.,clock=lambda:0.)
        self.assertTrue(result['aliases']);self.assertTrue(result['skipped'])
        self.assertEqual(len(calls),len(set(calls)))
        self.assertEqual(len({row['key']for row in result['evaluations']}),result['completed_evaluations'])
        self.assertTrue(all(self.tool.valid_gene(gene)for gene in calls))
        self.assertTrue(all(row['reason']=='out_of_bounds_no_clipping'for row in result['skipped']))
        self.assertTrue(any(row['genes'][0]>1. for row in result['skipped']))
        for alias in result['aliases']:
            self.assertEqual(result['evaluations'][alias['alias_of']]['key'],alias['key'])

    def test_search_deadline_or_typed_evaluator_timeout_preserves_partial_without_retry(self):
        calls=[]
        def timed_out(gene):calls.append(gene);raise self.tool.ProxyDeadline('synthetic interrupted bound')
        partial=self.tool.bounded_pattern_search(timed_out,deadline=100.,clock=lambda:0.)
        self.assertEqual(len(calls),1);self.assertEqual(partial['evaluation_attempts'],1)
        self.assertEqual(partial['completed_evaluations'],0)
        self.assertEqual(partial['status'],'proxy_budget_exhausted_partial')
        self.assertIn('synthetic interrupted bound',partial['stop_reason'])
        calls.clear()
        def forbidden(gene):calls.append(gene);raise RuntimeError('synthetic data corruption')
        with self.assertRaisesRegex(RuntimeError,'data corruption'):
            self.tool.bounded_pattern_search(forbidden,deadline=100.,clock=lambda:0.)
        self.assertEqual(len(calls),1)
        expired=self.tool.bounded_pattern_search(forbidden,deadline=0.,clock=lambda:0.)
        self.assertEqual(expired['evaluation_attempts'],0);self.assertEqual(expired['completed_evaluations'],0)
        self.assertEqual(expired['status'],'proxy_budget_exhausted_partial')


if __name__=='__main__':unittest.main()
