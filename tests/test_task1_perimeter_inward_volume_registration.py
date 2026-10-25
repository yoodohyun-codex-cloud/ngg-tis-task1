"""Pure registered-outline fixtures; no native arrays, preparation or PDE."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_perimeter_inward_volume_registration as r
import task1_perimeter_inward_registration as geometry


class PerimeterInwardVolumeRegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline=next(d for d in json.loads((geometry.core.HIST/'inputs/designs.json').read_text())
            if d['id']=='baseline-square15')
        cls.parent_design,_,_,_=geometry.parent.shell_design(baseline)
        cls.design,cls.rows,_,cls.proof=geometry.inward_design(cls.parent_design)
        cls.parent=dict(design=cls.parent_design)
        cls.current=dict(design=cls.design)
        for key in ('geometry_kind','native_full_face_contact','physical_total_contact_area_mm2',
            'minimum_physical_gap_mm','minimum_gap_XY_cells','maximum_physical_vertex_radius_squared_mm2',
            'rim_clearance_mm','physical_geometry_frozen','future_grid_reranking_allowed','position_only_contrast',
            'translated_parent_outline','placement_offset_per_coordinate_mm','physical_translation_mm_by_pad',
            'source_parent_case_id','combined_geometry_and_placement','new_geometry_shape_unchanged',
            'placement_and_gap_jointly_changed','isolated_rim_effect_claimed','isolated_shape_effect_claimed'):
            cls.current[key]=cls.design[key]
        source=(geometry.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        parent,_=geometry.parent.changed_shell_config(source,cls.parent_design,Path('/tmp/parent-mask.csv'),'a'*64)
        current,_=geometry.changed_inward_config(parent,cls.design,Path('/tmp/inward-mask.csv'),'b'*64)
        cls.parent_config=geometry._properties(parent);cls.current_config=geometry._properties(current)

    def test_three_case_cohort_keeps_square_as_only_baseline_and_shell_as_placement_control(self):
        self.assertEqual(('cloud-mesh-c1-20261019T190000Z','baseline-square15-xy80'),r.CASE_TABLE[0])
        self.assertEqual((r.PARENT_RUN,r.PARENT_ID),r.CASE_TABLE[1])
        self.assertEqual((r.NEW_RUN,r.CASE_ID),r.CASE_TABLE[2])
        self.assertEqual(3,len(set(r.CASE_TABLE)))
        self.assertEqual(2304,len(self.rows));self.assertEqual([576]*4,self.proof['faces_per_pad'])
        self.assertEqual(583.203125,r.RIM_RADIUS_SQUARED)
        self.assertAlmostEqual(.8504011420479287,r.RIM_CLEARANCE,places=14)

    def test_exact_rigid_outline_and_index_translation_is_accepted_without_mutating_inputs(self):
        before=copy.deepcopy((self.parent,self.current,self.proof))
        r.validate_inward_provenance(self.parent,self.current,self.proof)
        self.assertEqual(before,(self.parent,self.current,self.proof))
        for p,(dx,dy)in enumerate(r.TRANSLATIONS):
            old=self.parent_design['pads'][p];new=self.design['pads'][p]
            self.assertEqual([[x+dx,y+dy]for x,y in old['polygon_mm']],new['polygon_mm'])
            self.assertEqual(old['shape'],new['shape']);self.assertEqual(old['role'],new['role'])
        self.assertTrue(self.current['position_only_contrast'])
        self.assertTrue(self.current['placement_and_gap_jointly_changed'])
        self.assertFalse(self.current['isolated_rim_effect_claimed'])
        self.assertFalse(self.current['isolated_shape_effect_claimed'])

    def test_face_reranking_outline_wiring_and_intrinsic_dimensions_are_rejected(self):
        for edit in ('index','outline','role','width','primitive'):
            bad=copy.deepcopy(self.current);pad=bad['design']['pads'][0]
            if edit=='index':pad['native_face_indices'][0][0]+=1
            elif edit=='outline':pad['boundary_loops_mm'][0][0][0]+=.625
            elif edit=='role':pad['role']='return'
            elif edit=='width':pad['width_mm']-=.625
            else:pad['union_rectangles_mm'][0]['center_mm'][0]+=.625
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                r.validate_inward_provenance(self.parent,bad,self.proof)

    def test_area_connectivity_rim_proof_and_claim_changes_are_rejected(self):
        for edit in ('area','hole','partial','rim','rerank','isolated','combined'):
            bad=copy.deepcopy(self.current);proof=copy.deepcopy(self.proof)
            if edit=='area':proof['represented_pad_areas_m2'][1]*=.99
            elif edit=='hole':proof['holes_per_pad'][2]=1
            elif edit=='partial':proof['partial_faces']=1
            elif edit=='rim':bad['rim_clearance_mm']+=.1
            elif edit=='rerank':bad['design']['future_grid_reranking_allowed']=True
            elif edit=='isolated':bad['isolated_rim_effect_claimed']=True
            else:bad['combined_geometry_and_placement']=True
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                r.validate_inward_provenance(self.parent,bad,proof)

    def test_config_allowlist_preserves_contact_circuit_carriers_mesh_area_and_shape(self):
        before=copy.deepcopy((self.parent_config,self.current_config))
        r.validate_inward_configs(self.parent_config,self.current_config,self.design)
        self.assertEqual(before,(self.parent_config,self.current_config))
        changes={k for k in self.parent_config if self.parent_config[k]!=self.current_config[k]}
        self.assertEqual(r.ALLOWED_CONFIG_CHANGES,changes)
        for key,value in [('channels','4'),('frequencies','2000,2010'),('h_mm','0.5'),
            ('pad.0.width_mm','21.875'),('pad.1.rotation_deg','90'),('pad.2.x_mm','0')]:
            bad=dict(self.current_config);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                r.validate_inward_configs(self.parent_config,bad,self.design)
        bad=dict(self.current_config);bad['mask.sha256']=self.parent_config['mask.sha256']
        with self.assertRaisesRegex(ValueError,'distinct mask SHA'):
            r.validate_inward_configs(self.parent_config,bad,self.design)

    def test_output_overwrite_or_nonplan_path_fails_before_any_source_or_array_read(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);docs=root/'docs';docs.mkdir();output=docs/'inward-plan.json';output.write_text('preserved')
            with mock.patch.object(r,'_committed_sources')as sources:
                for destination in (output,docs/'report.json'):
                    with self.subTest(path=destination),self.assertRaisesRegex(ValueError,'New canonical docs'):
                        r.make_preregistration(destination,root=root,decision_path=docs/'decision.json',feedback_path=docs/'feedback.json')
                sources.assert_not_called()
            self.assertEqual('preserved',output.read_text())


if __name__=='__main__':unittest.main()
