"""Pure fixed-contour metadata tests; no native arrays, preparation or PDE."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_rounded_fullface_volume_registration as r


class RoundedFullfaceVolumeRegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import task1_rounded_fullface_registration as geometry
        cls.geometry=geometry
        baseline=next(d for d in json.loads((geometry.core.HIST/'inputs/designs.json').read_text())
            if d['id']=='baseline-square15')
        cls.design,cls.rows,_,cls.proof=geometry.rounded_design(baseline)
        cls.case=dict(design=cls.design)
        for key in ('geometry_kind','geometry_revision','native_full_face_contact','physical_total_contact_area_mm2',
            'minimum_physical_gap_mm','minimum_gap_XY_cells','maximum_physical_vertex_radius_squared_mm2','rim_clearance_mm',
            'physical_geometry_frozen','future_grid_reranking_allowed','shape_only_contrast','centres_unchanged','area_unchanged',
            'smooth_circle_claimed','perimeter_reduction_claimed','isolated_edge_effect_claimed',
            'physical_outline_perimeter_mm_per_pad','source_square_perimeter_mm_per_pad','strict_radial_prefix_face_count',
            'cutoff_tie_face_count','all_cutoff_ties_included','cutoff_local_odd_radius_squared'):
            cls.case[key]=cls.design[key]
        source=(geometry.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        current,_=geometry.changed_rounded_config(source,cls.design,Path('/tmp/rounded-mask.csv'),'b'*64)
        cls.parent_config=geometry._properties(source);cls.current_config=geometry._properties(current)

    def test_two_case_cohort_and_complete_radial_tie_set_keep_original_square_baseline(self):
        self.assertEqual((('cloud-mesh-c1-20261019T190000Z','baseline-square15-xy80'),(r.NEW_RUN,r.CASE_ID)),r.CASE_TABLE)
        self.assertEqual(2304,len(self.rows));self.assertEqual([576]*4,self.proof['faces_per_pad'])
        for p,(cx,cy)in enumerate(r.CENTRES):
            ix,iy=round((cx+25)/.625),round((cy+25)/.625)
            radii=[(2*(i-ix)+1)**2+(2*(j-iy)+1)**2 for i,j in r.expected_native_faces(p)]
            self.assertEqual(560,sum(v<730 for v in radii));self.assertEqual(16,sum(v==730 for v in radii))
            self.assertEqual(r.expected_native_faces(p),self.design['pads'][p]['native_face_indices'])
        self.assertEqual(528.90625,r.RIM_RADIUS_SQUARED)
        self.assertAlmostEqual(2.002038133782378,r.RIM_CLEARANCE,places=13)

    def test_registered_outline_preserves_centres_area_wiring_and_honest_larger_perimeter(self):
        before=copy.deepcopy((self.case,self.proof));r.validate_rounded_provenance(self.case,self.proof)
        self.assertEqual(before,(self.case,self.proof))
        self.assertEqual(70.,self.case['physical_outline_perimeter_mm_per_pad'])
        self.assertEqual(60.,self.case['source_square_perimeter_mm_per_pad'])
        self.assertFalse(self.case['smooth_circle_claimed']);self.assertFalse(self.case['perimeter_reduction_claimed'])
        self.assertFalse(self.case['isolated_edge_effect_claimed'])
        for p,centre in enumerate(r.CENTRES):
            self.assertEqual(list(centre),self.design['pads'][p]['center_mm'])
            self.assertEqual(225.,self.design['pads'][p]['analytic_area_mm2'])

    def test_wrong_cutoff_native_indices_centres_wiring_dimensions_or_boundary_rejected(self):
        for edit in ('face','tie','centre','role','width','boundary'):
            bad=copy.deepcopy(self.case);proof=copy.deepcopy(self.proof);pad=bad['design']['pads'][0]
            if edit=='face':pad['native_face_indices'][0][0]+=1
            elif edit=='tie':bad['cutoff_tie_face_count']=15
            elif edit=='centre':pad['center_mm'][0]+=.625
            elif edit=='role':pad['source_output']=1
            elif edit=='width':pad['width_mm']=15.
            else:pad['boundary_loops_mm'][0][0][0]=float('nan')
            with self.subTest(edit=edit),self.assertRaises(ValueError):r.validate_rounded_provenance(bad,proof)

    def test_partial_area_holes_rim_and_unjustified_claims_rejected(self):
        for edit in ('area','hole','partial','rim','circle','perimeter','edge','rerank'):
            bad=copy.deepcopy(self.case);proof=copy.deepcopy(self.proof)
            if edit=='area':proof['represented_pad_areas_m2'][1]*=.99
            elif edit=='hole':proof['holes_per_pad'][0]=1
            elif edit=='partial':proof['partial_faces']=1
            elif edit=='rim':bad['rim_clearance_mm']+=.1
            elif edit=='circle':bad['smooth_circle_claimed']=True
            elif edit=='perimeter':bad['perimeter_reduction_claimed']=True
            elif edit=='edge':bad['isolated_edge_effect_claimed']=True
            else:bad['future_grid_reranking_allowed']=True
            with self.subTest(edit=edit),self.assertRaises(ValueError):r.validate_rounded_provenance(bad,proof)

    def test_config_changes_only_mask_shape_and_extent_while_physics_positions_and_area_stay_fixed(self):
        before=copy.deepcopy((self.parent_config,self.current_config))
        r.validate_rounded_configs(self.parent_config,self.current_config,self.design)
        self.assertEqual(before,(self.parent_config,self.current_config))
        self.assertEqual(r.ALLOWED_CONFIG_CHANGES,{k for k in self.parent_config if self.parent_config[k]!=self.current_config[k]})
        for key,value in [('channels','4'),('frequencies','2000,2010'),('h_mm','0.5'),('pad.0.x_mm','-9.375'),
            ('pad.2.rotation_deg','90'),('pad.3.analytic_area_mm2','224')]:
            bad=dict(self.current_config);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):r.validate_rounded_configs(self.parent_config,bad,self.design)

    def test_context_delegation_and_fail_before_read_output_guard(self):
        sentinel=({'conditional':'actual inward volume and screen required'},{'SHA256':'a'*64},{'/tmp/context.json':'b'*64})
        old_root=Path('/original');core=SimpleNamespace(REPO=old_root)
        verify=mock.Mock(return_value=sentinel);module=SimpleNamespace(core=core,verify_context=verify)
        with mock.patch.object(r.importlib,'import_module',return_value=module):
            self.assertIs(sentinel,r._context(Path('/tmp/decision.json'),Path('/tmp/feedback.json'),Path('/tmp/test-root')))
        verify.assert_called_once_with(Path('/tmp/decision.json'),Path('/tmp/feedback.json'));self.assertEqual(old_root,core.REPO)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);docs=root/'docs';docs.mkdir();output=docs/'rounded-plan.json';output.write_text('preserved')
            with mock.patch.object(r,'_committed_sources')as sources:
                for target in (output,docs/'report.json'):
                    with self.subTest(target=target),self.assertRaisesRegex(ValueError,'New canonical docs'):
                        r.make_preregistration(target,root=root,decision_path=docs/'decision.json',feedback_path=docs/'feedback.json')
                sources.assert_not_called()
            self.assertEqual('preserved',output.read_text())


if __name__=='__main__':unittest.main()
