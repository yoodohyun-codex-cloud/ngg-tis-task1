"""Synthetic adjacent-drive admission/search checks; no native data, PDE or preparation."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('adjacent_cached_drive_tested',ROOT/'tools/task1_adjacent_cached_drive.py')
tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tool;spec.loader.exec_module(tool)


def configs():
    adjacent={'mask.path':'new-mask','mask.sha256':'new-hash','sc.sigma':'.0002','z.3000.re':'.00004452','h_mm':'.625'}
    for i,xy in enumerate(((-10,-10),(10,-10),(10,10),(-10,10))):
        for name,value in dict(shape='rectangle',width_mm='15',height_mm='15',rotation_deg='0',analytic_area_mm2='225',
            represented_area_m2='.00022499999999999999',x_mm=str(xy[0]),y_mm=str(xy[1])).items():adjacent[f'pad.{i}.{name}']=value
    canonical=adjacent.copy();canonical.update({'mask.path':'old-mask','mask.sha256':'old-hash','pad.1.y_mm':'10','pad.2.y_mm':'-10'})
    return canonical,adjacent


class AdjacentCachedDriveTests(unittest.TestCase):
    def record(self,g):return dict(objective=[sum(abs(v)for v in g[:4])+abs(g[4]-1),0.,-1.])

    def test_contract_is_distinct_source_cosine_and_finite(self):
        self.assertEqual(tool.SOURCE_ID,'adjacent-square15-xy80')
        self.assertEqual(tool.SOURCE_RUN,'cloud-finite-loop-20261020T002600Z-fine')
        self.assertEqual(tool.BOUNDS,((-1.,1.),)*4+((.5,1.5),))
        self.assertEqual(tool.STEPS,(.25,.1,.05))
        self.assertEqual(tool.SEEDS,((0.,0.,0.,0.,1.),(.5,0.,.5,0.,1.),(-.5,0.,-.5,0.,1.)))
        self.assertEqual(tool.SEARCH_CONTRACT['maximum_proxy_evaluations'],96)
        self.assertEqual(tool.SEARCH_CONTRACT['maximum_final_candidates'],2)
        self.assertEqual(tool.SEARCH_CONTRACT['total_seconds'],540)
        self.assertEqual(tool.SEARCH_CONTRACT['proxy_seconds'],240)
        self.assertEqual(tool.SEARCH_CONTRACT['per_condition_seconds'],120)
        self.assertEqual(tool.OUTPUT_BOUND_BYTES,64*1024**2)
        self.assertIn('cosine',tool.SEARCH_CONTRACT['command_gauge'])

    def test_complex_ratio_sign_and_zero_harmonics_cosine_gauge(self):
        gene=[.3,-.7,-.2,.4,1.25];before=gene.copy();c=tool.gene_coefficients(gene)
        np.testing.assert_array_equal(c[3000],[1.,.3-.7j]);np.testing.assert_array_equal(c[3030],[-.2+.4j,1.25])
        np.testing.assert_array_equal(c[9000],[0,0]);np.testing.assert_array_equal(c[9090],[0,0]);self.assertEqual(gene,before)
        self.assertEqual(tool.free_family_evidence({f:v*.7 for f,v in c.items()},gene)['global_scale'],.7)
        with self.assertRaises(ValueError):tool.free_family_evidence({f:v*(-1j)for f,v in c.items()},gene)

    def test_invalid_bounds_nonfinite_and_no_clipping(self):
        self.assertTrue(tool.valid_gene([-1,1,-1,1,.5]));self.assertTrue(tool.valid_gene([1,-1,1,-1,1.5]))
        for g in([1.00001,0,0,0,1],[0,0,0,0,.49999],[0,0,0,0,1.50001],[float('nan'),0,0,0,1],np.zeros(5)):
            self.assertFalse(tool.valid_gene(g))
            with self.assertRaises(ValueError):tool.gene_key(g)

    def test_source_and_metric_cache_namespaces_preserve_nearby_floats(self):
        g=[0.,0.,0.,0.,1.];h=g.copy();h[0]=float(np.nextafter(0.,1.))
        self.assertNotEqual(tool.gene_key(g,'adjacent','metric'),tool.gene_key(g,'rounded','metric'))
        self.assertNotEqual(tool.gene_key(g,'adjacent','metric'),tool.gene_key(g,'adjacent','different'))
        self.assertNotEqual(tool.gene_key(g),tool.gene_key(h))

    def test_actual_rectangle_property_schema_admits_only_expected_assignment(self):
        canonical,adjacent=configs();before=copy.deepcopy((canonical,adjacent));proof=tool.validate_adjacent_configs(canonical,adjacent)
        self.assertTrue(proof['same_tissue_contact_grid_source_properties']);self.assertEqual(proof['area_mm2_per_pad'],225)
        self.assertEqual((canonical,adjacent),before)
        for key,value in(('sc.sigma','.002'),('z.3000.re','.1'),('h_mm','1.25'),('pad.0.width_mm','16'),('pad.3.rotation_deg','5')):
            changed=adjacent.copy();changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):tool.validate_adjacent_configs(canonical,changed)

    def test_equal_wrong_shapes_rejected_not_only_contrast_keys(self):
        canonical,adjacent=configs()
        for conf in(canonical,adjacent):conf['pad.0.shape']='circle'
        with self.assertRaises(ValueError):tool.validate_adjacent_configs(canonical,adjacent)
        canonical,adjacent=configs();adjacent['extra']='anything'
        with self.assertRaises(ValueError):tool.validate_adjacent_configs(canonical,adjacent)

    def test_existing_cosine_tau_gene_and_positive_global_scale_exact_alias(self):
        q0=-.444+.0599j;q1=-.443+.0594j
        for tau in(0.,.5,1.):
            seed={3000:np.array([1,tau*q0]),3030:np.array([tau*q1,1]),9000:np.zeros(2),9090:np.zeros(2)}
            genes=tool.canonical_gene_from_seed(seed);self.assertEqual(genes[-1],1.)
            proof=tool.free_family_evidence({f:v*.816 for f,v in seed.items()},genes)
            self.assertEqual(proof['global_scale'],.816)
            if not tau:self.assertEqual(genes,[0.,0.,0.,0.,1.])
        bad={f:v*(-1j)for f,v in seed.items()}
        with self.assertRaises(ValueError):tool.canonical_gene_from_seed(bad)

    def test_duplicate_search_nodes_are_evaluated_once_and_cap_is_hard(self):
        calls=[]
        def evaluate(g):calls.append(g);return self.record(g)
        result=tool.bounded_pattern_search(evaluate,deadline=10,clock=lambda:0,max_evaluations=16)
        self.assertEqual(len(calls),16);self.assertEqual(len(set(calls)),16)
        self.assertEqual(result['evaluation_attempts'],16);self.assertEqual(result['stop_reason'],'evaluation_cap')
        self.assertEqual(result['status'],'proxy_budget_exhausted_partial');self.assertFalse(result['global_optimum_claimed'])
        self.assertEqual(calls[:3],list(tool.SEEDS))

    def test_deadline_and_incomplete_level_preserve_anchor(self):
        result=tool.bounded_pattern_search(self.record,deadline=0,clock=lambda:0)
        self.assertEqual(result['completed_evaluations'],0);self.assertEqual(result['stop_reason'],'proxy_wall_deadline')
        result=tool.bounded_pattern_search(lambda g:dict(objective=[g[0]+1,0,-1]),deadline=10,clock=lambda:0,max_evaluations=5)
        level=result['levels'][0];self.assertFalse(level['completed']);self.assertFalse(level['anchor_updated_once'])
        self.assertEqual(level['next_anchor_genes'],level['anchor_genes'])

    def test_old_tau_full_alias_never_selected_and_max_two_novel_finals(self):
        genes=[[0,0,0,0,1],[.1,0,.1,0,1],[.2,0,.2,0,1],[.3,0,.3,0,1]]
        rows=[dict(genes=g,key=tool.gene_key(g,'A','M'),evaluation_index=i,objective=[3-i,0,-1])for i,g in enumerate(genes)]
        result=tool.select_final_candidates(dict(evaluations=rows,seed_evaluation_indices=[0]),[dict(genes=genes[3])],'A','M')
        self.assertEqual(len(result),2);self.assertNotIn(rows[3],result);self.assertEqual(result,[rows[2],rows[1]])

    def test_cached_pure_regression_uses_exact_target2074_not_offtarget_proxy(self):
        target=dict(mean=3.,p10=2.5)
        saved=dict(normalizations={'skin_contact_only':dict(amplitude_scale=.9,regions={tool.volume.PRIMARY:dict(maxTIS=target)})})
        self.assertTrue(tool.validate_seed_regression(target,.9,saved)['passed'])
        with self.assertRaises(ValueError):tool.validate_seed_regression(dict(mean=3.01,p10=2.5),.9,saved)


if __name__=='__main__':unittest.main()
