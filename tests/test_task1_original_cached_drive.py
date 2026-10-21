"""Synthetic original-drive contracts; no native arrays, research or preparation."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('original_cached_drive_tested',ROOT/'tools/task1_original_cached_drive.py')
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)


def config():
    result={'mask.path':'canonical-mask','mask.sha256':'canonical-hash','sc.sigma':'.0002','z.3000.re':'.00004452','h_mm':'.625'}
    for i,xy in enumerate(((-10,-10),(10,10),(10,-10),(-10,10))):
        for name,value in dict(shape='rectangle',width_mm='15',height_mm='15',rotation_deg='0',analytic_area_mm2='225',
            represented_area_m2='.00022499999999999999',x_mm=str(xy[0]),y_mm=str(xy[1])).items():result[f'pad.{i}.{name}']=value
    return result


def actual_commands(z0,z1,rho=1.,scale=.8):
    return {3000:-1j*np.array([1,z0])*scale,3030:-1j*np.array([z1,rho])*scale,
        9000:np.zeros(2,complex),9090:np.zeros(2,complex)}


class OriginalCachedDriveTests(unittest.TestCase):
    def record(self,g):return dict(objective=[sum(abs(v)for v in g[:4])+abs(g[4]-1),0.,-1.])

    def test_distinct_original_source_sine_contract_finite_budget(self):
        self.assertEqual(tool.SOURCE_ID,'baseline-square15-xy80')
        self.assertEqual(tool.SOURCE_RUN,'cloud-mesh-c1-20261019T190000Z')
        self.assertEqual(tool.SOURCE_SUMMARY,tool.BASELINE_SUMMARY)
        self.assertEqual(tool.BOUNDS,((-.15,.15),)*4+((.9,1.1),))
        self.assertEqual(tool.STEPS,(.03,.015,.005))
        self.assertEqual(tool.SEEDS[:2],((0.,0.,0.,0.,1.),(-.03,0.,-.03,0.,1.)))
        self.assertEqual(tool.SEARCH_CONTRACT['maximum_proxy_evaluations'],72)
        self.assertEqual(tool.SEARCH_CONTRACT['maximum_final_candidates'],1)
        self.assertEqual(tool.SEARCH_CONTRACT['total_seconds'],360)
        self.assertEqual(tool.SEARCH_CONTRACT['proxy_seconds'],180)
        self.assertEqual(tool.SEARCH_CONTRACT['per_condition_seconds'],120)
        self.assertEqual(tool.OUTPUT_BOUND_BYTES,32*1024**2)
        self.assertIn('-j',tool.SEARCH_CONTRACT['command_gauge'])

    def test_exact_weak_seed_preserves_phase_terms_and_rho_drift(self):
        self.assertEqual(tool.SEEDS[2],(-3.0616341296444263e-18,.050000279783135114,
            3.061616997868383e-18,.05,1.000005595662702))
        self.assertNotEqual(tool.SEEDS[2],(0.,.05,0.,.05,1.))
        self.assertTrue(all(tool.valid_gene(g)for g in tool.SEEDS))

    def test_complex_sine_sign_and_explicit_zero_harmonics(self):
        genes=[.1,-.12,-.04,.03,1.05];before=genes.copy();c=tool.gene_coefficients(genes)
        np.testing.assert_allclose(c[3000],[-1j,-.12-.1j],rtol=0,atol=1e-15)
        np.testing.assert_allclose(c[3030],[.03+.04j,-1.05j],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(c[9000],[0,0]);np.testing.assert_array_equal(c[9090],[0,0]);self.assertEqual(genes,before)
        self.assertEqual(tool.free_family_evidence({f:v*.7 for f,v in c.items()},genes)['global_scale'],.7)
        with self.assertRaises(ValueError):tool.free_family_evidence({f:v*1j for f,v in c.items()},genes)

    def test_invalid_bounds_and_nonfinite_are_rejected_without_clipping(self):
        self.assertTrue(tool.valid_gene([-.15,.15,-.15,.15,.9]));self.assertTrue(tool.valid_gene([.15,-.15,.15,-.15,1.1]))
        for g in([.150001,0,0,0,1],[0,0,0,0,.89999],[0,0,0,0,1.10001],[float('nan'),0,0,0,1],np.zeros(5)):
            self.assertFalse(tool.valid_gene(g))
            with self.assertRaises(ValueError):tool.gene_key(g)

    def test_keys_preserve_geometry_metric_and_nearby_float_identity(self):
        g=list(tool.SEEDS[2]);h=g.copy();h[0]=float(np.nextafter(g[0],1.))
        self.assertNotEqual(tool.gene_key(g,'original','metric'),tool.gene_key(g,'rounded','metric'))
        self.assertNotEqual(tool.gene_key(g,'original','metric'),tool.gene_key(g,'original','different'))
        self.assertNotEqual(tool.gene_key(g),tool.gene_key(h))

    def test_selfsame_canonical_config_does_not_require_adjacent_difference(self):
        c=config();before=copy.deepcopy(c);proof=tool.validate_original_config(c,c.copy())
        self.assertEqual(proof['changed_properties'],[]);self.assertTrue(proof['self_same_canonical_source']);self.assertEqual(c,before)
        for key,value in(('sc.sigma','.002'),('z.3000.re','.1'),('h_mm','1.25'),('pad.0.width_mm','16'),('pad.1.y_mm','-10')):
            changed=c.copy();changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):tool.validate_original_config(changed,c)

    def test_equal_unsupported_shape_is_rejected(self):
        c=config();c['pad.0.shape']='circle'
        with self.assertRaises(ValueError):tool.validate_original_config(c,c.copy())

    def test_actual_old_column_normalization_becomes_exact_one_scale_genes(self):
        # Physical outputs had independently chosen historical scales. Extracting
        # ratios from ACTUAL commands must keep both cross ratio and rho changes.
        c=actual_commands(.05j,.05j,scale=1.)
        for f in c:c[f]*=np.array([.8,.800004])
        before=copy.deepcopy(c);proof=tool.decode_existing_commands(c);g=proof['genes']
        self.assertTrue(proof['within_registered_domain']);self.assertAlmostEqual(g[1],.05000025,places=15)
        self.assertAlmostEqual(g[3],.05,places=15);self.assertAlmostEqual(g[4],1.000005,places=15)
        self.assertEqual(proof['actual_primary_global_scale'],.8)
        for f,v in tool.gene_coefficients(g).items():np.testing.assert_allclose(v*.8,c[f],rtol=1e-14,atol=1e-16)
        for f in c:np.testing.assert_array_equal(c[f],before[f])

    def test_out_of_domain_historical_alias_is_preserved_without_clipping(self):
        p=tool.decode_existing_commands(actual_commands(-.5,.5,rho=1.00003,scale=.66))
        self.assertFalse(p['within_registered_domain']);self.assertEqual(p['genes'][0],-.5)
        self.assertAlmostEqual(p['genes'][4],1.00003,places=14)
        with self.assertRaises(ValueError):tool.gene_key(p['genes'])

    def test_phase_harmonic_and_nonfinite_aliases_cannot_masquerade_as_same_commands(self):
        for mode in('cosine','wrongrho','harmonic','nan'):
            c=actual_commands(.05j,.05j)
            if mode=='cosine':c={f:v*1j for f,v in c.items()}
            elif mode=='wrongrho':c[3030][1]*=1j
            elif mode=='harmonic':c[9000][0]=.01
            else:c[3000][1]=float('nan')
            with self.subTest(mode=mode),self.assertRaises(ValueError):tool.decode_existing_commands(c)

    def test_cached_pure_regression_selects_original_cap_cohort(self):
        target=dict(mean=4.,p10=3.6)
        saved=dict(id=tool.PURE_ID,schema='saved-pure',source_provenance=dict(source_summary=str(tool.SOURCE_SUMMARY)),cohorts={
            'cached_original_square_3000_3030_caps':dict(normalizations={'skin_contact_only':dict(amplitude_scale=1.07,
                regions={tool.volume.PRIMARY:dict(maxTIS=target)})}),
            'fresh_sine_3000_3030_caps':dict(normalizations={'skin_contact_only':dict(amplitude_scale=1.,
                regions={tool.volume.PRIMARY:dict(maxTIS=dict(mean=1.,p10=1.))})})})
        before=copy.deepcopy(saved);proof=tool.validate_pure_seed_regression(target,1.07,saved)
        self.assertTrue(proof['passed']);self.assertEqual(saved,before);self.assertFalse(proof['old_JSON_mutated'])
        self.assertEqual(proof['selected_cap_cohort'],'cached_original_square_3000_3030_caps')
        with self.assertRaises(ValueError):tool.validate_pure_seed_regression(target,1.,saved)

    def test_historical_source_config_and_commit_identity_cannot_be_swapped(self):
        row=dict(source_run_id=tool.SOURCE_RUN,source_case_id=tool.SOURCE_ID,source_commit='canonical-commit',
            configuration_sha256='canonical-config')
        before=copy.deepcopy(row)
        self.assertTrue(tool.validate_existing_source_identity(row,'canonical-commit','canonical-config')['passed'])
        self.assertEqual(row,before)
        for key in('source_commit','configuration_sha256','source_case_id','source_run_id'):
            bad=row.copy();bad[key]='different'
            with self.subTest(key=key),self.assertRaises(ValueError):
                tool.validate_existing_source_identity(bad,'canonical-commit','canonical-config')
        pure=dict(source_provenance=dict(run_id=tool.SOURCE_RUN,case_id=tool.SOURCE_ID,source_commit='canonical-commit',
            configuration_sha256='canonical-config',source_summary=str(tool.SOURCE_SUMMARY)))
        self.assertTrue(tool.validate_existing_source_identity(pure,'canonical-commit','canonical-config',pure=True)['passed'])
        pure['source_provenance']['source_summary']='other-summary'
        with self.assertRaises(ValueError):tool.validate_existing_source_identity(pure,'canonical-commit','canonical-config',pure=True)

    def test_duplicate_nodes_are_not_rerun_and_72_cap_is_hard(self):
        calls=[]
        def evaluate(g):calls.append(g);return self.record(g)
        result=tool.bounded_pattern_search(evaluate,deadline=10,clock=lambda:0,max_evaluations=72)
        self.assertLessEqual(len(calls),72);self.assertEqual(len(calls),len(set(calls)))
        self.assertEqual(calls[:3],list(tool.SEEDS));self.assertFalse(result['global_optimum_claimed'])
        self.assertFalse(result['all72_evaluations_promised'])

    def test_deadline_and_partial_level_preserve_anchor(self):
        result=tool.bounded_pattern_search(self.record,deadline=0,clock=lambda:0)
        self.assertEqual(result['completed_evaluations'],0);self.assertEqual(result['stop_reason'],'proxy_wall_deadline')
        result=tool.bounded_pattern_search(lambda g:dict(objective=[g[0]+1,0,-1]),deadline=10,clock=lambda:0,max_evaluations=5)
        level=result['levels'][0];self.assertFalse(level['completed']);self.assertFalse(level['anchor_updated_once'])
        self.assertEqual(level['next_anchor_genes'],level['anchor_genes'])

    def test_eligible_old_full_alias_excluded_outside_alias_never_keyed_and_one_final(self):
        genes=[[0,0,0,0,1],[.01,0,.01,0,1],[.02,0,.02,0,1],[.03,0,.03,0,1]]
        rows=[dict(genes=g,key=tool.gene_key(g,'A','M'),evaluation_index=i,objective=[3-i,0,-1])for i,g in enumerate(genes)]
        aliases=[dict(genes=genes[3],within_registered_domain=True),dict(genes=[.5,0,.5,0,1],within_registered_domain=False)]
        result=tool.select_final_candidates(dict(evaluations=rows,seed_evaluation_indices=[0]),aliases,'A','M')
        self.assertEqual(result,[rows[2]])


if __name__=='__main__':unittest.main()
