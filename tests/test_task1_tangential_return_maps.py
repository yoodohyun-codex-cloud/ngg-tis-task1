"""Synthetic tangential-return scalar display contracts; no native files or plots."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


class TangentialReturnMapsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('tangential_return_maps_tested',ROOT/'tools/task1_tangential_return_maps.py')
        cls.maps=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.maps)

    def rows(self):
        limits={key:float(index+1)for index,key in enumerate(sorted(self.maps.base.CAPS))}
        return [dict(case_id=identifier,adopted=False,calculation_status='cached_native_scalar_audit_complete',
            summary_path=f'/synthetic/{identifier}/postprocess/{identifier}/summary.json',normalizations={
                name:dict(amplitude_scale=value,source_Vpp_per_output=value,includes_source_power_cap=False,
                    includes_1Vpp_ceiling=False,baseline_derived_numerical_limits=copy.deepcopy(limits))
                for name,value in(('raw_1Vpp',1.),('skin_contact_only',scale))})
                for identifier,scale in zip(self.maps.IDS,(1.,.5,.8))]

    def audit(self):
        return dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',inputs_unchanged=True,
            selected_for_adoption=[],cases=self.rows(),inputs_sha256={})

    def metadata(self):
        boundaries=[0.,.1,5.1,10.1,25.1];faces=[0.]
        for lo,hi,count in zip(boundaries,boundaries[1:],(2,14,14,40)):
            faces.extend(lo+(hi-lo)*index/count for index in range(1,count+1))
        return dict(cells=351680,h_xy_mm=.625,radius_mm=25.,total_depth_mm=25.1,channels=2,sc_cells=2,
            bulk_layer_counts=[14,14,40],frequencies_Hz=[3000,3030,9000,9090],source_peak_V=.5,
            source_resistance_ohm=50.,z_faces_mm=faces,tissue_boundaries_mm=boundaries)

    def cases(self):
        output=[]
        for values,scale in zip(([100.,2.,3.],[50.,4.,5.],[25.,6.,7.]),(1.,.5,.8)):
            values=np.array(values)
            output.append(dict(arrays=dict(maxTIS=values.copy(),fixedTIS=values*.5,RMS=values*2,
                region_target_m3=np.array([0.,.5,1.])),scales={'raw_1Vpp':1.,'skin_contact_only':scale}))
        return output

    def test_exact_three_ordered_terminal_unadopted_volume_rows(self):
        audit=self.audit();before=copy.deepcopy(audit)
        self.assertEqual(len(self.maps.IDS),3)
        self.assertEqual(self.maps.IDS,('baseline-square15-xy80','asym-cross281p25-return168p75-xy80','asym-return-tangent4p375-xy80'))
        self.assertNotEqual(self.maps.IDS[2],self.maps.IDS[1])
        self.assertEqual([row['case_id']for row in self.maps.validate_audit(audit)],list(self.maps.IDS))
        self.assertEqual(audit,before)

    def test_case_identity_order_adoption_and_failed_or_changed_inputs_are_rejected(self):
        for mutation in('schema','status','changed','adoption','adoptedrow','reverse','missing','wrongid'):
            audit=self.audit()
            if mutation=='schema':audit['schema']='different'
            elif mutation=='status':audit['status']='running'
            elif mutation=='changed':audit['inputs_unchanged']=False
            elif mutation=='adoption':audit['selected_for_adoption']=[self.maps.IDS[2]]
            elif mutation=='adoptedrow':audit['cases'][2]['adopted']=True
            elif mutation=='reverse':audit['cases'].reverse()
            elif mutation=='missing':audit['cases'].pop()
            else:audit['cases'][2]['case_id']='other-case'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_audit(audit)

    def test_saved_scales_retain_canonical_square_eight_caps_without_recalculation(self):
        rows=self.rows();before=copy.deepcopy(rows)
        self.assertEqual(self.maps.validate_modes(rows),[{'raw_1Vpp':1.,'skin_contact_only':scale}for scale in(1.,.5,.8)])
        self.assertEqual(rows,before)
        for mode in('raw_1Vpp','skin_contact_only'):
            self.assertFalse(rows[2]['normalizations'][mode]['includes_source_power_cap'])
            self.assertFalse(rows[2]['normalizations'][mode]['includes_1Vpp_ceiling'])

    def test_mode_or_cap_mutation_cannot_silently_use_other_normalization(self):
        for mutation in('zero','nan','raw','sourcepower','ceiling','cap','sourcevpp','baselinescale','missing'):
            rows=self.rows();mode=rows[2]['normalizations']['skin_contact_only']
            if mutation=='zero':mode['amplitude_scale']=0.
            elif mutation=='nan':mode['amplitude_scale']=float('nan')
            elif mutation=='raw':rows[2]['normalizations']['raw_1Vpp']['amplitude_scale']=.5
            elif mutation=='sourcepower':mode['includes_source_power_cap']=True
            elif mutation=='ceiling':mode['includes_1Vpp_ceiling']=True
            elif mutation=='cap':mode['baseline_derived_numerical_limits']['SC_power_W']=999.
            elif mutation=='sourcevpp':mode['source_Vpp_per_output']=5.
            elif mutation=='baselinescale':rows[0]['normalizations']['skin_contact_only'].update(amplitude_scale=.8,source_Vpp_per_output=.8)
            else:rows[2]['normalizations'].pop('raw_1Vpp')
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):self.maps.validate_modes(rows)

    def test_native_mesh_contract_preserves_d50_layers_and_fine_sc2_grid(self):
        self.maps.validate_grid_contract(self.metadata())
        for key,value in(('cells',351681),('h_xy_mm',1.25),('radius_mm',30.),('total_depth_mm',30.1),
                ('channels',4),('sc_cells',4),('bulk_layer_counts',[18,18,56]),('frequencies_Hz',[3000,3030]),
                ('tissue_boundaries_mm',[0.,.2,5.2,10.2,25.2])):
            meta=self.metadata();meta[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.maps.validate_grid_contract(meta)

    def test_all_three_cases_share_global_and_explicit_frozen_roi_display_ranges(self):
        cases=self.cases();before=copy.deepcopy(cases)
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','raw_1Vpp'),(0.,100.))
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','skin_contact_only'),(0.,100.))
        self.assertEqual(self.maps.shared_color_limits(cases,'maxTIS','raw_1Vpp',deep_roi=True),(0.,7.))
        self.assertAlmostEqual(self.maps.shared_color_limits(cases,'maxTIS','skin_contact_only',deep_roi=True)[1],5.6,places=14)
        self.assertEqual(self.maps.shared_color_limits(cases,'fixedTIS','raw_1Vpp'),(0.,50.))
        self.assertEqual(self.maps.shared_color_limits(cases,'RMS','raw_1Vpp'),(0.,200.))
        for new,old in zip(cases,before):
            for key in old['arrays']:np.testing.assert_array_equal(new['arrays'][key],old['arrays'][key])
            self.assertEqual(new['scales'],old['scales'])

    def test_native_xy_and_xz_are_actual_cell_planes_with_faces_and_no_interpolation(self):
        grid=np.array([(x,y,z)for z in(.5,2.)for y in(-.3125,.3125)for x in(-.3125,.3125)])
        values=np.arange(1.,9.);before=(grid.copy(),values.copy())
        meta=dict(cells=8,h_xy_mm=.625,z_faces_mm=[0.,1.,3.])
        result=self.maps.native_slices(grid,meta,values,xy_depth_mm=1.8)
        np.testing.assert_array_equal(result['xy'],[[5.,6.],[7.,8.]])
        np.testing.assert_array_equal(result['xz'],[[1.,2.],[5.,6.]])
        np.testing.assert_array_equal(result['x_edges_mm'],[-.625,0.,.625])
        np.testing.assert_array_equal(result['z_edges_mm'],[0.,1.,3.])
        self.assertEqual(result['xy_actual_depth_mm'],2.);self.assertEqual(result['xz_actual_y_mm'],-.3125)
        np.testing.assert_array_equal(grid,before[0]);np.testing.assert_array_equal(values,before[1])

    def test_empty_frozen_roi_or_nonfinite_saved_scale_cannot_invent_deep_range(self):
        for mutation in('empty','scale','negative'):
            cases=self.cases()
            if mutation=='empty':cases[2]['arrays']['region_target_m3'][:]=0
            elif mutation=='scale':cases[2]['scales']['skin_contact_only']=float('inf')
            else:cases[2]['arrays']['maxTIS'][1]=-1.
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                self.maps.shared_color_limits(cases,'maxTIS','skin_contact_only',deep_roi=True)


    def screen(self,volume_path,volume_sha='a'*64):
        return dict(schema='task1-candidate-screen-v1',status='screen_complete_not_adopted',candidate_adopted=False,
            input_volume_report=dict(path=str(Path(volume_path).resolve()),SHA256=volume_sha),
            cases=[dict(case_id=identifier,candidate_adopted=False,all_screen_checks_passed=False,
                failed_checks=['saved-off-target-check'])for identifier in self.maps.IDS[1:]])

    def test_saved_failed_screen_is_bound_without_inventing_success_or_new_gates(self):
        path=Path('/synthetic/context/volume.json');screen=self.screen(path);before=copy.deepcopy(screen)
        self.maps.validate_screen(screen,path,'a'*64)
        self.assertEqual(screen,before)
        only_new=copy.deepcopy(screen);only_new['cases']=only_new['cases'][1:]
        self.maps.validate_screen(only_new,path,'a'*64)
        self.assertFalse(only_new['cases'][0]['all_screen_checks_passed'])
        self.assertFalse(screen['cases'][1]['all_screen_checks_passed'])
        self.assertIs(self.maps.validate_modes,self.maps.previous.validate_modes)
        self.assertIs(self.maps.validate_grid_contract,self.maps.previous.validate_grid_contract)
        self.assertIs(self.maps.native_slices,self.maps.base.native_slices)

    def test_screen_status_case_identity_adoption_or_volume_sha_mismatch_is_rejected(self):
        path=Path('/synthetic/context/volume.json')
        for mutation in('schema','status','adopted','rowadopted','sha','path','order','missing','wrongid'):
            screen=self.screen(path)
            if mutation=='schema':screen['schema']='different'
            elif mutation=='status':screen['status']='running'
            elif mutation=='adopted':screen['candidate_adopted']=True
            elif mutation=='rowadopted':screen['cases'][1]['candidate_adopted']=True
            elif mutation=='sha':screen['input_volume_report']['SHA256']='b'*64
            elif mutation=='path':screen['input_volume_report']['path']='/synthetic/other/volume.json'
            elif mutation=='order':screen['cases'].reverse()
            elif mutation=='missing':screen['cases'].pop()
            else:screen['cases'][1]['case_id']='another-case'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_screen(screen,path,'a'*64)

    def properties_text(self,centres):
        lines=['# Synthetic operative four-pad config']
        lines.extend(f'pad.{pad}.{axis}_mm={centres[pad][column]}'for pad in range(4)for column,axis in enumerate(('x','y')))
        return chr(10).join(lines)

    def test_pad_projection_markers_use_finite_operative_centres_and_exact_tangential_translation(self):
        parent=np.array([[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]])
        new=np.array([[-10.,-10.],[10.,10.],[14.375,-5.625],[-14.375,5.625]])
        before=(parent.copy(),new.copy())
        np.testing.assert_array_equal(self.maps.pad_centres_from_properties(self.properties_text(parent)),parent)
        np.testing.assert_array_equal(self.maps.pad_centres_from_properties(self.properties_text(new)),new)
        self.maps.validate_pad_translation(parent,new)
        np.testing.assert_array_equal(parent,before[0]);np.testing.assert_array_equal(new,before[1])
        for bad in(np.array([[25.,0.],[10.,10.],[10.,-10.],[-10.,10.]]),
                np.array([[float('nan'),0.],[10.,10.],[10.,-10.],[-10.,10.]])):
            with self.assertRaises(ValueError):self.maps.pad_centres_from_properties(self.properties_text(bad))

    def test_unregistered_return_motion_or_any_source_pad_change_is_not_labelled_tangential(self):
        parent=np.array([[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]])
        correct=np.array([[-10.,-10.],[10.,10.],[14.375,-5.625],[-14.375,5.625]])
        for mutation in('source','return','swap','nonfinite','shape'):
            new=correct.copy()
            if mutation=='source':new[0,0]+=.625
            elif mutation=='return':new[2,0]+=.625
            elif mutation=='swap':new[[2,3]]=new[[3,2]]
            elif mutation=='nonfinite':new[2,1]=float('inf')
            else:new=new[:3]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.maps.validate_pad_translation(parent,new)

    def test_missing_source_artifact_binding_blocks_before_native_scalar_or_grid_reads(self):
        volume=Path('/synthetic/context/volume.json');screen_path=volume.parent/'screen.json';audit=self.audit()
        screen=self.screen(volume)
        def bound(path,pins,expected=None):
            path=Path(path).resolve();pins[str(path)]='a'*64
            if path==volume:return audit
            if path==screen_path:return screen
            raise AssertionError('Unbound scientific source must not be opened')
        with patch.object(self.maps.base,'bound_json',side_effect=bound),             patch.object(self.maps.base,'load_scalars',side_effect=AssertionError('NPZ read forbidden')) ,             patch.object(self.maps.np,'loadtxt',side_effect=AssertionError('grid read forbidden')):
            with self.assertRaisesRegex(ValueError,'artifact binding'):self.maps.load_model(volume,screen_path)


if __name__=='__main__':unittest.main()
