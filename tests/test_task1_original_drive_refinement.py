"""Synthetic exact-cache/compact contracts; no native data/PDE/research preparation."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('original_drive_refinement_tested',ROOT/'tools/task1_original_drive_refinement.py')
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)


class OriginalRefinementTests(unittest.TestCase):
    def record(self,g):return dict(objective=[sum(abs(v)for v in g[:4])+abs(g[4]-1),0.,-1.])

    def cached(self,g,source='A',metric='M',index=31):
        record=self.record(g)
        return dict(evaluation_index=index,genes=list(g),key=tool.gene_key(g,source,metric),objective=record['objective'].copy(),record=record)

    def fixture(self):
        source=dict(summary_path=str(tool.SOURCE_SUMMARY),configuration_sha256='config',mask_sha256='mask',native_input_sha256={'native':'hash'})
        identity=tool._hash_json(source)
        metric=tool._hash_json(dict(proxy=tool.PROXY_DEFINITION,canonical_summary_SHA256='baseline',source_scalar_archive_SHA256='scalars'))
        plan=dict(schema=tool.previous.SCHEMA,proxy_definition=copy.deepcopy(tool.PROXY_DEFINITION),source_geometry=source,
            input_sha256={str(tool.SOURCE_SUMMARY.parent/'volume.npz'):'scalars'},baseline_summary_sha256='baseline',source_identity=identity,metric_identity=metric)
        rows=[];individual={};pure_regression=dict(passed=True,selected_cap_cohort='cached_original_square_3000_3030_caps',actual_source_primary_global_scale=1.)
        for i in range(72):
            gene=[float(i)*.0001,0.,0.,0.,1.];record=dict(objective=[float(i),0.,-1.],status='ranked_only_not_full2074_validation',
                target_direction_count=2074,target_is_continuous_maximum=False,proxy_whole_source_Vpp_normalized=False,raw_1Vpp_claimed=False)
            if i==0:record['cached_pure_seed_regression']=copy.deepcopy(pure_regression)
            row=dict(evaluation_index=i,genes=gene,key=tool.gene_key(gene,identity,metric),objective=record['objective'].copy(),record=record)
            rows.append(row);individual[i]={k:copy.deepcopy(row[k])for k in('genes','key','record')}
        direction=dict(count=2074,dtype='float64',SHA256='d'*64)
        search=dict(proxy_definition=copy.deepcopy(tool.PROXY_DEFINITION),source_identity=identity,metric_identity=metric,
            evaluations=rows,completed_evaluations=72,ranked_only_not_full2074_validation=True,actual_target_direction_set=direction)
        summary=dict(schema='task1-original-cached-drive-v1',status='calculated_unadopted',inputs_unchanged=True,new_PDE=0,
            proxy_definition=copy.deepcopy(tool.PROXY_DEFINITION),proxy_completed_evaluations=72,
            actual_target_direction_set=copy.deepcopy(direction),cached_pure_seed_regression=copy.deepcopy(pure_regression))
        return summary,plan,search,individual

    def test_registered_local_seeds_and_limits_same_source_domain_metric(self):
        self.assertEqual(tool.SOURCE_SUMMARY,tool.previous.SOURCE_SUMMARY)
        self.assertEqual(tool.BOUNDS,tool.previous.BOUNDS)
        self.assertEqual(tool.PROXY_DEFINITION,tool.previous.PROXY_DEFINITION)
        self.assertEqual(tool.SEEDS,((.03,0.,.005,0.,.985),(0.,0.,0.,0.,1.),tool.previous.SEEDS[2]))
        self.assertEqual(tool.STEPS,(.01,.005,.0025))
        self.assertEqual(tool.SEARCH_CONTRACT['maximum_new_proxy_evaluations'],72)
        self.assertEqual(tool.SEARCH_CONTRACT['maximum_final_candidates'],1)
        self.assertEqual(tool.SEARCH_CONTRACT['total_seconds'],360)
        self.assertEqual(tool.SEARCH_CONTRACT['proxy_seconds'],180)
        self.assertEqual(tool.SEARCH_CONTRACT['per_condition_seconds'],120)
        self.assertEqual(tool.OUTPUT_BOUND_BYTES,8*1024**2)
        self.assertEqual(tool.SEARCH_CONTRACT['output_bound_bytes'],tool.OUTPUT_BOUND_BYTES)
        self.assertEqual(tool.SEARCH_CONTRACT['derivative_export'],'compact_float64_metrics_and_probes_no_new_scalar_NPZ')

    def test_exact_original_coefficient_gauge_and_gene_keys_preserved(self):
        g=tool.SEEDS[0]
        for f,c in tool.gene_coefficients(g).items():np.testing.assert_array_equal(c,tool.previous.gene_coefficients(g)[f])
        self.assertEqual(tool.gene_key(g,'A','M'),tool.previous.gene_key(g,'A','M'))
        self.assertNotEqual(tool.gene_key(g,'A','M'),tool.gene_key(g,'rounded','M'))

    def test_all72_exact_immutable_rows_accepted_without_mutation(self):
        fixture=self.fixture();before=copy.deepcopy(fixture);rows=tool.validate_cached_proxy(*fixture)
        self.assertEqual(len(rows),72);self.assertEqual(fixture,before);rows[0]['record']['objective'][0]=999
        self.assertEqual(fixture,before)

    def test_incomplete_duplicate_individual_or_objective_cache_rejected(self):
        for failure in('short','duplicate','individual','objective','key','direction','pure'):
            s,p,x,individual=self.fixture()
            if failure=='short':x['evaluations'].pop()
            elif failure=='duplicate':x['evaluations'][1]['key']=x['evaluations'][0]['key']
            elif failure=='individual':individual[1]['record']['objective']=[99,0,-1]
            elif failure=='objective':x['evaluations'][1]['objective']=[99,0,-1]
            elif failure=='key':x['evaluations'][1]['key']='foreign-source-metric'
            elif failure=='direction':s['actual_target_direction_set']['SHA256']='e'*64
            else:x['evaluations'][0]['record']['cached_pure_seed_regression']['passed']=False;individual[0]=copy.deepcopy({k:x['evaluations'][0][k]for k in('genes','key','record')})
            with self.subTest(failure=failure),self.assertRaises(ValueError):tool.validate_cached_proxy(s,p,x,individual)

    def test_rounded_source_or_different_proxy_namespace_rejected(self):
        for failure in('rounded','metric','proxy'):
            s,p,x,individual=self.fixture()
            if failure=='rounded':p['source_geometry']['summary_path']=str(tool.ROOT/'data-native/rounded/postprocess/rounded/summary.json')
            elif failure=='metric':x['metric_identity']='different'
            else:p['proxy_definition']['target']='another metric'
            with self.subTest(failure=failure),self.assertRaises(ValueError):tool.validate_cached_proxy(s,p,x,individual)

    def test_cached_seeds_not_recomputed_and72_new_cap_excludes_reused_count(self):
        cache=[self.cached(g,index=50+i)for i,g in enumerate(tool.SEEDS)];before=copy.deepcopy(cache);calls=[]
        def evaluate(g):calls.append(g);return self.record(g)
        x=tool.bounded_pattern_search(evaluate,deadline=10,clock=lambda:0,max_evaluations=2,source_identity='A',metric_identity='M',initial_cache=cache)
        self.assertEqual(len(calls),2);self.assertEqual(x['completed_new_evaluations'],2);self.assertEqual(x['reused_previous_evaluations'],3)
        self.assertEqual(x['completed_evaluations'],5);self.assertEqual(x['stop_reason'],'new_evaluation_cap');self.assertEqual(cache,before)
        for g in tool.SEEDS:self.assertNotIn(g,calls)
        self.assertTrue(all(not row['new_evaluation']for row in x['evaluations'][:3]));self.assertTrue(all(row['new_evaluation']for row in x['evaluations'][3:]))

    def test_cache_wrong_namespace_duplicates_or_objective_rejected_before_evaluator(self):
        for failure in('namespace','duplicate','objective'):
            row=self.cached(tool.SEEDS[0]);cache=[row]
            if failure=='namespace':row['key']=tool.gene_key(row['genes'],'other','M')
            elif failure=='duplicate':cache.append(copy.deepcopy(row))
            else:row['objective']=[99,0,0]
            with self.subTest(failure=failure),self.assertRaises(ValueError):
                tool.bounded_pattern_search(lambda g:self.fail('should not evaluate'),deadline=10,clock=lambda:0,
                    source_identity='A',metric_identity='M',initial_cache=cache)

    def test_deadline_reuses_cache_without_fabricating_new_completion(self):
        cache=[self.cached(g)for g in tool.SEEDS]
        x=tool.bounded_pattern_search(lambda g:self.fail('deadline'),deadline=0,clock=lambda:0,
            source_identity='A',metric_identity='M',initial_cache=cache)
        self.assertEqual(x['completed_new_evaluations'],0);self.assertEqual(x['reused_previous_evaluations'],3)
        self.assertEqual(x['status'],'proxy_budget_exhausted_partial');self.assertEqual(x['stop_reason'],'proxy_wall_deadline')

    def test_pure_source_bound_regression_reused_instead_of_new_claim(self):
        row=self.cached(tool.SEEDS[1]);row['record']['cached_pure_seed_regression']={'passed':True,'source':'old actual immutable evaluation'}
        before=copy.deepcopy(row)
        x=tool.bounded_pattern_search(self.record,deadline=10,clock=lambda:0,max_evaluations=1,
            source_identity='A',metric_identity='M',initial_cache=[row])
        reused=next(r for r in x['evaluations']if r['genes']==list(tool.SEEDS[1]))
        self.assertFalse(reused['new_evaluation']);self.assertEqual(reused['record'],before['record']);self.assertEqual(row,before)

    def test_old_full_aliases_excluded_and_at_most_one_strict_novel_final(self):
        genes=[[0,0,0,0,1],[.01,0,.01,0,1],[.02,0,.02,0,1],[.03,0,.03,0,1]]
        rows=[dict(genes=g,key=tool.gene_key(g,'A','M'),evaluation_index=i,objective=[3-i,0,-1])for i,g in enumerate(genes)]
        old=[dict(genes=genes[3],within_registered_domain=True),dict(genes=[.5,0,.5,0,1],within_registered_domain=False)]
        chosen=tool.select_final_candidates(dict(evaluations=rows,seed_evaluation_indices=[0]),old,'A','M')
        self.assertEqual(chosen,[rows[2]])
        self.assertEqual(tool.select_final_candidates(dict(evaluations=rows[:1],seed_evaluation_indices=[0]),old,'A','M'),[])

    def test_compact_manifest_requires_actual_metric_probe_files_and_no_unwritten_NPZ_reference(self):
        self.assertEqual(set(tool.COMPACT_ARTIFACT_FILENAMES),{'condition.json','probes.json','native-volume-metrics.json'})
        seen=[]
        def sha(path):seen.append(Path(path).name);return 'synthetic-'+Path(path).name
        with patch.object(tool.view,'sha',side_effect=sha):manifest=tool.compact_artifact_manifest(Path('/synthetic'))
        self.assertEqual(set(manifest),set(tool.COMPACT_ARTIFACT_FILENAMES));self.assertNotIn('volume.npz',manifest)
        self.assertEqual(set(seen),set(tool.COMPACT_ARTIFACT_FILENAMES))
        with patch.object(tool.view,'sha',side_effect=FileNotFoundError('missing metric/probe')):
            with self.assertRaises(FileNotFoundError):tool.compact_artifact_manifest(Path('/synthetic'))

    def test_compact_reconstruction_recipe_pins_actual_inputs_coeffs_and_does_not_claim_export(self):
        basis=dict(hashes={'source-E':'e-hash','source-phi':'p-hash'},metadata={'config_sha256':'config-hash'})
        coefficients=tool.gene_coefficients(tool.SEEDS[0]);source={'artifacts':{'files':{'volume.npz':{'SHA256':'roi-weight-hash'}}}}
        with patch.object(tool.view,'read',return_value=source):recipe=tool.reconstruction_recipe(basis,coefficients)
        self.assertEqual(recipe['native_input_sha256'],basis['hashes']);self.assertEqual(recipe['native_grid_configuration_sha256'],'config-hash')
        self.assertEqual(recipe['source_ROI_weight_archive']['SHA256'],'roi-weight-hash')
        self.assertEqual(recipe['actual_coefficients']['3000']['imaginary'],coefficients[3000].imag.tolist())
        self.assertFalse(recipe['new_scalar_archive_written']);self.assertFalse(recipe['executable_scalar_export_command_registered'])
        self.assertTrue(recipe['old_scalar_archives_preserved']);self.assertIn('float64',recipe['scalar_dtype'])


if __name__=='__main__':unittest.main()
