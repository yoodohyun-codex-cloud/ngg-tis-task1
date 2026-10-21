import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_candidate_xy_registration as r


def condition(ident,wave):
    special={'roi_mean_TIS_V_m','roi_p10_TIS_V_m','roi_mean_RMS_V_m','target_superficial_p95_ratio'}
    return dict(id=ident+'-'+wave,waveform=wave,actual_fundamental_Hz=[3000,3030],phase_deg=[0.,0.],
        source_Vpp_per_output=1.,metrics={name:1. for name in r.GATE_PERCENT if name not in special},
        volume_metrics=dict(regions=dict(target=dict(statistics=dict(maxTIS=dict(mean=1.,p10=1.),RMS=dict(mean=1.))),
            surface_0_5=dict(statistics=dict(maxTIS=dict(p95=1.))))))


def summary(ident,h,cells):
    return dict(id=ident,status='complete',mesh_metadata=dict(h_xy_mm=h,cells=cells,sc_cells=2,
        bulk_layer_counts=[14,14,40],radius_mm=25,total_depth_mm=25.1,
        tissue_boundaries_mm=[0,.1,5.1,10.1,25.1],z_faces_mm=[0,.05,.1,5.1,10.1,25.1],
        field_reconstruction='same',source_resistance_ohm=50,source_peak_V=.5,channels=2),
        conditions=[condition(ident,w) for w in ('square_3h','sine','triangle_3h')])


class CandidateXYTests(unittest.TestCase):
    def setUp(self):
        self.previous=summary(r.HISTORY_ID,.625,351680)
        self.old=summary(r.TEMPLATE_ID,.5,550200)
        self.new=summary(r.CASE_ID,r.H_MM,791280)
        self.case=dict(id=r.CASE_ID,candidate_coarser_xy_reference=dict(postprocess_path='/tmp/coarser',postprocess_sha256='pin'),
            candidate_xy80_history_reference=dict(postprocess_path='/tmp/history',postprocess_sha256='pin'))
        designs=json.loads((r.core.HIST/'inputs/designs.json').read_text())
        self.design=next(d for d in designs if d['id']==r.DESIGN_ID)

    def compare(self,new=None):
        with patch.object(r.core,'sha',return_value='pin'),patch.object(r.core,'read',side_effect=[self.old,self.previous]):
            return r.compare_candidate_xy(Path('/tmp/cloud-test'),self.case,new or self.new)

    def test_integer_mask_has2304_full_faces_and100mm2_per_pad(self):
        rows,areas,receipt=r.aligned_full_face_mask(self.design)
        face=(r.H_MM/1000)**2
        self.assertEqual(2304,len(rows));self.assertEqual(2304,len({(i,j)for _,i,j,_ in rows}))
        self.assertTrue(all(a==face for _,_,_,a in rows))
        for pad in range(4):
            self.assertEqual(576,sum(p==pad for p,_,_,_ in rows))
            self.assertAlmostEqual(100.,areas[pad]*1e6)
        self.assertEqual({18,42,78,102},set(receipt['grid_edge_indices']))
        self.assertFalse(receipt['renormalization']);self.assertEqual(0,receipt['discarded_slivers'])
        self.assertEqual(set(range(18,42)),{i for p,i,_,_ in rows if p==0})
        self.assertEqual(set(range(78,102)),{j for p,_,j,_ in rows if p==1})

    def test_mask_rejects_shift_rotation_and225mm2_baseline(self):
        for field,value in [('center_mm',[-12.4,-12.5]),('rotation_deg',5),('width_mm',15)]:
            changed=copy.deepcopy(self.design);changed['pads'][0][field]=value
            with self.assertRaises(ValueError):r.aligned_full_face_mask(changed)

    def test_only_registered_xy_mask_area_fields_change(self):
        source=r.core.HIST/'configs'/(r.TEMPLATE_ID+'.properties');original=source.read_bytes()
        changed,changes=r.changed_xy_config(original,Path('/tmp/new-mask'),'a'*64)
        a,b=r._properties(original),r._properties(changed)
        permitted={'h_mm','mask.path','mask.sha256',*(f'pad.{p}.represented_area_m2'for p in range(4))}
        self.assertEqual(permitted,set(changes))
        self.assertTrue({k for k in a if a[k]!=b[k]}<=permitted)
        self.assertEqual(r.H_MM,float(b['h_mm']))
        self.assertTrue(all(abs(float(b[f'pad.{p}.represented_area_m2'])/.0001-1)<1e-14 for p in range(4)))
        self.assertEqual(original,source.read_bytes())

    def test_cell_cap_and_exact_raw_bound(self):
        case=dict(h_xy_mm=r.H_MM,sc_cells=2,bulk_counts=[14,14,40])
        mesh=r._mesh(case)
        self.assertEqual(791280,mesh['cells']);self.assertEqual(474768000,mesh['cells']*600)
        case['sc_cells']=4
        with self.assertRaises(ValueError):r._mesh(case)

    def test_all36_pair_gates_do_not_clear_prior_failure_or_enable_normalization(self):
        self.old['conditions'][0]['metrics']['surface_J_RMS_max_A_m2']=1.050946
        self.new['conditions'][0]['metrics']['surface_J_RMS_max_A_m2']=1.050946*1.01
        result=self.compare()
        self.assertTrue(result['all_registered_comparison_gates_passed'])
        self.assertEqual(36,result['gate_count'])
        previous=result['preceding_XY_comparison'][0]['changes']['surface_J_RMS_max_A_m2']
        self.assertFalse(previous['passed']);self.assertAlmostEqual(5.0946,previous['relative_change_percent'])
        for flag in ('candidate_adopted','XY_convergence_hold_resolved','matched_burden_evaluated',
                     'across_mesh_normalization_performed','continuum_convergence_validated','experimental_validation'):
            self.assertFalse(result[flag])
        self.assertEqual('held_no_eligible_reference',result['same_grid_original_four_pad_reference_status'])
        self.assertEqual([1.25,1.2],result['grid_step_ratios'])

    def test_unchanged5percent_failure_and_wrong_mesh_or_wave_rejected(self):
        changed=copy.deepcopy(self.new);changed['conditions'][0]['metrics']['contact_voltage_RMS_max_V']=1.05001
        result=self.compare(changed)
        self.assertFalse(result['all_registered_comparison_gates_passed'])
        self.assertEqual(5.,result['waveform_comparisons'][0]['changes']['contact_voltage_RMS_max_V']['limit_percent'])
        for mutate in (lambda x:x['mesh_metadata'].__setitem__('sc_cells',8),lambda x:x['conditions'].pop(),
                       lambda x:x['conditions'][0].__setitem__('source_Vpp_per_output',2.)):
            changed=copy.deepcopy(self.new);mutate(changed)
            with self.assertRaises(ValueError):self.compare(changed)


if __name__=='__main__':
    unittest.main()
