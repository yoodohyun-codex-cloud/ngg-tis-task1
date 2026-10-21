"""Synthetic rounded full-face display contracts; no native inputs or rendering."""
import ast
import copy
import importlib.util
import inspect
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
GATE_NAMES=('primary_maxTIS_mean','primary_maxTIS_p10','surface_0_5_maxTIS_p95',
    'surface_0_5_high_volume_at_primary_r5_depth15_20_mean','surface_0_5_high_volume_at_primary_r5_depth15_20_p10',
    'primary_complement_maxTIS_p95','primary_complement_high_volume_at_primary_r5_depth15_20_mean',
    'primary_complement_high_volume_at_primary_r5_depth15_20_p10')


class RoundedFullfaceMapsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rounded_maps_tested',ROOT/'tools/task1_rounded_fullface_maps.py')
        cls.maps=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.maps)
        pads=[dict(pad=p,role='signal'if p<2 else'common_gnd_return',source_output=p if p<2 else None,
            center_mm=list(centre),shape='rectangle',width_mm=15.,height_mm=15.,rotation_deg=0.,analytic_area_mm2=225.)
            for p,centre in enumerate(cls.maps.geometry.CENTRES)]
        baseline=dict(id='baseline-square15',phantom_diameter_mm=50,contact_plane_z_mm=0,total_pads=4,source_outputs=2,
            return_connection='all_return_pads_ideal_common_GND',pads=pads)
        # The constructor receives only this in-memory synthetic baseline, never historical files.
        with patch.object(Path,'read_text',side_effect=AssertionError('No research input reads')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('No research input reads')):
            rounded,_,_,_=cls.maps.geometry.rounded_design(baseline)
        cls.contact_fixture=[dict(id=cls.maps.IDS[0],design=baseline),
            dict(id=cls.maps.IDS[1],design=rounded,**copy.deepcopy(cls.maps.geometry.COMMON))]

    def rows(self):
        limits={key:float(i+1)for i,key in enumerate(sorted(self.maps.base.CAPS))}
        return [dict(case_id=identifier,adopted=False,calculation_status='cached_native_scalar_audit_complete',
            summary_path=f'/synthetic/{identifier}/postprocess/{identifier}/summary.json',normalizations={
                name:dict(amplitude_scale=scale,source_Vpp_per_output=scale,baseline_derived_numerical_limits=copy.deepcopy(limits),
                    includes_source_power_cap=False,includes_1Vpp_ceiling=False)
                for name,scale in(('raw_1Vpp',1.),('skin_contact_only',value))})
            for identifier,value in zip(self.maps.IDS,(1.,.8))]

    def audit(self):return dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',inputs_unchanged=True,
        selected_for_adoption=[],cases=self.rows(),inputs_sha256={})

    def screen(self,path):return dict(schema='task1-candidate-screen-v1',status='screen_complete_not_adopted',candidate_adopted=False,
        input_volume_report=dict(path=str(Path(path).resolve()),SHA256='a'*64),cases=[dict(case_id=self.maps.IDS[1],candidate_adopted=False,
            checks=[dict(name=name,passed=index>=2)for index,name in enumerate(GATE_NAMES)])])

    def test_exact_two_ordered_completed_unadopted_cases_and_input_state(self):
        self.assertEqual(self.maps.IDS,('baseline-square15-xy80','rounded-fullface225-xy80'))
        audit=self.audit();before=copy.deepcopy(audit);self.assertIs(self.maps.validate_audit(audit),audit['cases']);self.assertEqual(audit,before)
        for mutation in('reverse','missing','adopted','running','changed','selected','wrongid'):
            value=self.audit()
            if mutation=='reverse':value['cases'].reverse()
            elif mutation=='missing':value['cases'].pop()
            elif mutation=='adopted':value['cases'][1]['adopted']=True
            elif mutation=='running':value['status']='running'
            elif mutation=='changed':value['inputs_unchanged']=False
            elif mutation=='selected':value['selected_for_adoption']=[self.maps.IDS[1]]
            else:value['cases'][1]['case_id']='a-smooth-circle'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_audit(value)

    def test_original_square_eight_caps_and_fixed_d50_sc2_mesh_are_inherited(self):
        self.assertIs(self.maps.validate_modes,self.maps.previous.validate_modes)
        self.assertIs(self.maps.validate_grid_contract,self.maps.previous.validate_grid_contract)
        self.assertEqual(self.maps.validate_modes(self.rows()),[{'raw_1Vpp':1.,'skin_contact_only':1.},{'raw_1Vpp':1.,'skin_contact_only':.8}])
        rows=self.rows();rows[1]['normalizations']['skin_contact_only']['includes_source_power_cap']=True
        with self.assertRaises(ValueError):self.maps.validate_modes(rows)
        meta=dict(cells=351680,h_xy_mm=.625,radius_mm=25,total_depth_mm=25.1,channels=2,sc_cells=2,
            bulk_layer_counts=[14,14,40],frequencies_Hz=[3000,3030,9000,9090],tissue_boundaries_mm=[0,.1,5.1,10.1,25.1])
        self.maps.validate_grid_contract(meta)
        for key,value in(('radius_mm',30),('sc_cells',4),('h_xy_mm',1.25)):
            bad=copy.deepcopy(meta);bad[key]=value
            with self.assertRaises(ValueError):self.maps.validate_grid_contract(bad)

    def test_saved_screen_preserves_two_target_failures_six_offtarget_passes_and_exact_volume_sha(self):
        path=Path('/synthetic/context/volume.json');screen=self.screen(path);before=copy.deepcopy(screen)
        self.maps.validate_screen(screen,path,'a'*64);self.assertEqual(screen,before)
        for mutation in('target','offtarget','duplicate','sha','id','adopted','status'):
            bad=self.screen(path)
            if mutation=='target':bad['cases'][0]['checks'][0]['passed']=True
            elif mutation=='offtarget':bad['cases'][0]['checks'][2]['passed']=False
            elif mutation=='duplicate':bad['cases'][0]['checks'][1]['name']=GATE_NAMES[0]
            elif mutation=='sha':bad['input_volume_report']['SHA256']='b'*64
            elif mutation=='id':bad['cases'][0]['case_id']=self.maps.IDS[0]
            elif mutation=='adopted':bad['candidate_adopted']=True
            else:bad['status']='running'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_screen(bad,path,'a'*64)

    def test_actual_576_full_face_contour_has_all_sixteen_ties_d4_and_seventy_mm_perimeter(self):
        cases=copy.deepcopy(self.contact_fixture);before=copy.deepcopy(cases)
        shapes=[self.maps.validate_contact_shapes(case)for case in cases]
        self.maps.validate_same_centres(*shapes);self.assertEqual(cases,before)
        for p,(square,rounded)in enumerate(zip(*shapes)):
            self.assertEqual(square['area_mm2'],225.);self.assertEqual(rounded['area_mm2'],225.)
            self.assertEqual(square['perimeter_mm'],60.);self.assertEqual(rounded['perimeter_mm'],70.)
            self.assertEqual(square['centroid_mm'],rounded['centroid_mm'])
            self.assertGreater(len(rounded['polygon_mm']),4)
            pad=cases[1]['design']['pads'][p];cx,cy=rounded['centroid_mm'];ic,jc=round((cx+25)/.625),round((cy+25)/.625)
            local={(2*(i-ic)+1,2*(j-jc)+1)for i,j in pad['native_face_indices']}
            self.assertEqual(len(local),576);self.assertEqual(sum(u*u+v*v<730 for u,v in local),560)
            self.assertEqual(sum(u*u+v*v==730 for u,v in local),16)
            self.assertTrue(all((-v,u)in local and(-u,v)in local and(v,u)in local for u,v in local))
            self.assertEqual(pad['width_mm']*pad['height_mm'],306.25)
            self.assertNotEqual(pad['width_mm']*pad['height_mm'],rounded['area_mm2'])

    def test_wrong_faces_ties_circle_hull_or_bbox_outline_are_not_displayed_as_physical_contact(self):
        for mutation in('faces','ties','circle','hull','bbox','wiring','perimeter'):
            case=copy.deepcopy(self.contact_fixture[1]);pad=case['design']['pads'][0]
            if mutation=='faces':pad['native_face_indices'][0]=pad['native_face_indices'][1]
            elif mutation=='ties':case['all_cutoff_ties_included']=False;case['design']['all_cutoff_ties_included']=False
            elif mutation=='circle':pad['smooth_circle_claimed']=True
            elif mutation=='hull':pad['convex_hull_used']=True
            elif mutation=='bbox':
                x0,y0,x1,y1=pad['bounding_box_mm'];pad['polygon_mm']=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];pad['boundary_loops_mm']=[pad['polygon_mm']]
            elif mutation=='wiring':pad['source_output']=1
            else:pad['physical_outline_perimeter_mm']=60.
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_contact_shapes(case)

    def test_same_centres_area_and_source_return_identity_cannot_silently_become_placement_change(self):
        square,rounded=[self.maps.validate_contact_shapes(copy.deepcopy(case))for case in self.contact_fixture]
        for mutation in('centre','area','role','perimeter'):
            bad=copy.deepcopy(rounded)
            if mutation=='centre':bad[0]['centroid_mm'][0]+=.625
            elif mutation=='area':bad[0]['area_mm2']=224.
            elif mutation=='role':bad[0]['source_output']=1
            else:bad[0]['perimeter_mm']=60.
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_same_centres(square,bad)

    def test_global_and_deep_ranges_share_both_cases_and_keep_three_field_metrics_distinct(self):
        cases=[]
        for values,scale in zip(([100.,2.,3.],[50.,4.,5.]),(1.,.8)):
            values=np.array(values);cases.append(dict(arrays=dict(maxTIS=values,fixedTIS=values*.5,RMS=values*2,
                region_target_m3=np.array([0.,.5,1.])),scales={'raw_1Vpp':1.,'skin_contact_only':scale}))
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','raw_1Vpp'),(0.,100.))
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','skin_contact_only',deep_roi=True),(0.,4.))
        self.assertEqual(self.maps.shared_color_limits(cases,'fixedTIS','raw_1Vpp'),(0.,50.))
        self.assertEqual(self.maps.shared_color_limits(cases,'RMS','raw_1Vpp'),(0.,200.))

    def test_native_xy_xz_keep_actual_planes_cell_faces_and_uninterpolated_scalars(self):
        grid=np.array([(x,y,z)for z in(.5,2.)for y in(-.3125,.3125)for x in(-.3125,.3125)])
        values=np.arange(1.,9.);before=(grid.copy(),values.copy())
        result=self.maps.native_slices(grid,dict(cells=8,h_xy_mm=.625,z_faces_mm=[0.,1.,3.]),values,xy_depth_mm=1.8)
        np.testing.assert_array_equal(result['xy'],[[5.,6.],[7.,8.]])
        np.testing.assert_array_equal(result['xz'],[[1.,2.],[5.,6.]])
        np.testing.assert_array_equal(result['z_edges_mm'],[0.,1.,3.])
        self.assertEqual(result['xy_actual_depth_mm'],2.);self.assertEqual(result['xz_actual_y_mm'],-.3125)
        np.testing.assert_array_equal(grid,before[0]);np.testing.assert_array_equal(values,before[1])

    def test_source_artifact_must_be_bound_before_any_scalar_npz_or_grid_read(self):
        volume=Path('/synthetic/context/volume.json');screen_path=volume.parent/'screen.json';audit=self.audit();screen=self.screen(volume)
        def bound(path,pins,expected=None):
            path=Path(path).resolve();pins[str(path)]='a'*64
            if path==volume:return audit
            if path==screen_path:return screen
            raise AssertionError('Unbound source must not be opened')
        with patch.object(self.maps.base,'bound_json',side_effect=bound),\
             patch.object(self.maps.base,'load_scalars',side_effect=AssertionError('No NPZ read')),\
             patch.object(self.maps.np,'loadtxt',side_effect=AssertionError('No grid read')):
            with self.assertRaisesRegex(ValueError,'artifact binding'):self.maps.load_model(volume,screen_path)

    def test_renderer_declares_fat_at_true_layer_boundaries_and_twelve_heatmap_combinations_without_running_it(self):
        tree=ast.parse(inspect.getsource(self.maps.render_model))
        spans=[call for call in ast.walk(tree)if isinstance(call,ast.Call)and isinstance(call.func,ast.Attribute)and call.func.attr=='axhspan']
        self.assertTrue(any([ast.literal_eval(arg)for arg in call.args[:2]]==[5.1,10.1]and
            any(item.arg=='hatch'and ast.literal_eval(item.value)=='///'for item in call.keywords)for call in spans))
        self.assertEqual(len(self.maps.base.MODES)*len(self.maps.base.METRICS)*2,12)
        self.assertIn('no_E_phi_decode',inspect.getsource(self.maps.render_model))


if __name__=='__main__':unittest.main()
