"""Pure fixed native-face geometry/context fixtures; no native fields or PDE."""
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_perimeter_shell_registration as r
import task1_perimeter_shell_volume_registration as volume


class ShellGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=next(d for d in json.loads((r.core.HIST/'inputs/designs.json').read_text())if d['id']=='baseline-square15')
        cls.design,cls.rows,cls.areas,cls.proof=r.shell_design(cls.baseline)

    def test_exact_full_face_count_area_hash_and_original_d50(self):
        self.assertEqual([576]*4,[sum(p==q for p,i,j,a in self.rows)for q in range(4)])
        self.assertEqual(2304,len({(i,j)for p,i,j,a in self.rows}))
        for a in self.areas:self.assertAlmostEqual(.000225,a,places=16)
        for p,i,j,a in self.rows:
            self.assertEqual((.625/1000)**2,a)
            self.assertTrue(all((-25+ii*.625)**2+(-25+jj*.625)**2<625 for ii in(i,i+1)for jj in(j,j+1)))
        encoded=r._mask_bytes(self.rows)
        self.assertEqual('875179a89b1f7f0f77d9c7973121363db89a49bad61c6f41fa4c4d8babca363e',hashlib.sha256(encoded).hexdigest())
        self.assertEqual(70900,len(encoded));self.assertEqual([576]*4,self.proof['faces_per_pad'])
        self.assertFalse(self.proof['clipping']);self.assertFalse(self.proof['renormalization'])

    def test_canonical_quadrant_orientation_rotation_reflection_and_exact_notch(self):
        faces=[set(p)for p in r.shell_faces()];sw,ne,se,nw=faces
        self.assertEqual(nw,r.rotate90(ne));self.assertEqual(sw,r.rotate90(nw));self.assertEqual(se,r.rotate90(sw))
        self.assertEqual(ne,r.rotate90(se));self.assertEqual(ne,{(j,i)for i,j in ne})
        self.assertNotIn((67,67),ne)
        ties={(44,66),(48,65),(58,59),(59,58),(65,48),(66,44)}
        self.assertTrue(ties<=ne);self.assertTrue(all(i>=43 and j>=43 for i,j in ne))
        self.assertEqual(989,self.proof['construction']['quarter_candidate_count'])
        self.assertFalse(self.proof['strict_outermost576_claimed'])

    def test_one_component_no_hole_and_rejected_inner_notch_is_a_real_closed_hole(self):
        for cells in r.shell_faces():
            self.assertEqual([576],r.components(cells));self.assertEqual(set(),r.hole_cells(cells))
        ne=set(r.shell_faces()[1]);wrong=(ne|{(67,67)})-{(59,59)}
        self.assertEqual(576,len(wrong));self.assertEqual({(59,59)},r.hole_cells(wrong))
        with self.assertRaises(ValueError):r.boundary_loop(wrong)

    def test_boundary_is_exact_nonconvex_face_union_instead_of_bounding_box_or_hull(self):
        for pad in self.design['pads']:
            loop=pad['boundary_loops_mm'][0]
            self.assertEqual(loop,pad['polygon_mm']);self.assertGreater(len(loop),4)
            area=sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(loop,loop[1:]+loop[:1]))/2
            self.assertEqual(225.,area);self.assertLess(area,pad['width_mm']*pad['height_mm'])
            self.assertEqual(576,len(pad['union_rectangles_mm']))
            self.assertEqual('masked_face_union',pad['shape']);self.assertFalse(pad['convex_hull_used'])
            self.assertTrue(pad['physical_outline_frozen']);self.assertFalse(pad['smooth_annular_arc_claimed'])
        self.assertFalse(self.design['future_grid_reranking_allowed'])

    def test_centroid_bbox_contact_gap_and_near_rim_hold_are_distinct(self):
        for pad,(sx,sy)in zip(self.design['pads'],((-1,-1),(1,1),(1,-1),(-1,1))):
            self.assertEqual([sx*13.125,sy*13.125],pad['bounding_box_center_mm'])
            self.assertAlmostEqual(sx*13.638237847222221,pad['center_mm'][0],places=12)
            self.assertAlmostEqual(sy*13.638237847222221,pad['center_mm'][1],places=12)
            self.assertNotEqual(pad['center_mm'],pad['bounding_box_center_mm'])
            self.assertEqual(22.5,pad['width_mm']);self.assertEqual(0.,pad['rotation_deg'])
        self.assertEqual(3.75,min(g['gap_mm']for g in self.proof['verified_physical_gaps_mm']))
        self.assertEqual(6,self.proof['minimum_gap_XY_cells'])
        self.assertEqual(623.828125,self.proof['maximum_physical_vertex_radius_squared_mm2'])
        self.assertAlmostEqual(.02344849663989379,self.proof['rim_clearance_mm'],places=14)
        self.assertFalse(self.proof['mesh_convergence_claimed'])

    def test_config_changes_only_shape_bbox_centroid_and_mask_preserving_originalphysics(self):
        source=(r.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        output,changes=r.changed_shell_config(source,self.design,Path('/tmp/shell-mask'),'a'*64)
        before,after=r._properties(source),r._properties(output)
        allowed={'mask.path','mask.sha256'}|{f'pad.{p}.{key}'for p in range(4)for key in('shape','width_mm','height_mm','x_mm','y_mm')}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(before),set(after))
        self.assertEqual({k:v for k,v in before.items()if k not in allowed},{k:v for k,v in after.items()if k not in allowed})
        volume.validate_shell_configs(before,after,self.design)
        case={k:self.design[k]for k in('geometry_kind','combined_geometry_and_placement','isolated_shape_effect_claimed',
            'native_full_face_contact','physical_total_contact_area_mm2','minimum_physical_gap_mm','minimum_gap_XY_cells',
            'maximum_physical_vertex_radius_squared_mm2','rim_clearance_mm')};case['design']=self.design
        volume.validate_shell_provenance(case,self.proof)

    def test_source_identity_wiring_and_single_condition_resource_contract_reject_drift(self):
        wrong=copy.deepcopy(self.baseline);wrong['source_outputs']=4
        with self.assertRaises(ValueError):r.shell_design(wrong)
        wrong=copy.deepcopy(self.baseline);wrong['pads'][2]['shape']='ellipse'
        with self.assertRaises(ValueError):r.shell_design(wrong)
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1320,r.MIN_REMAINING_SECONDS);self.assertEqual(120,r.PREPARATION_SECONDS)


class ContextAndFailureTests(unittest.TestCase):
    def context(self,root):
        paths={}
        for relative,(schema,status)in r.REQUIRED_CONTEXT.items():
            p=root/relative;p.parent.mkdir(parents=True,exist_ok=True)
            obj={'schema':schema,'status':status,'inputs_unchanged':True,'new_PDE':0}
            if schema=='task1-candidate-screen-v1':
                target=root/'docs/cloud-tangential-return-context-20261021T183000Z/volume.json'
                obj.pop('inputs_unchanged');obj['input_volume_report']=dict(path=str(target),SHA256=paths[str(target)])
            if 'coherent-'in relative:obj['conditions']=[{'status':'calculated_unadopted','canonical_screen_all_passed':False}for _ in range(5)]
            r.core.write(p,obj);paths[str(p)]=r.core.sha(p)
        comment={'id':6321929825,'author':'yoodohyun-codex-cloud','body':'fixture public feedback',
                 'html_url':'https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825'}
        comment['body_sha256']=hashlib.sha256(comment['body'].encode()).hexdigest()
        receipts=[]
        for pull in(1,2):
            for kind in('head','comments'):
                endpoint='repos/yoodohyun-codex-cloud/ngg-tis-task1/'+(f'pulls/{pull}'if kind=='head'else f'issues/{pull}/comments')
                receipts.append(dict(pull=pull,kind=kind,endpoint=endpoint,evidence={'head_sha':'a'*40}if kind=='head'else([comment]if pull==2 else[])))
        fp=root/'feedback.json';r.core.write(fp,dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,receipts=receipts,observed_utc='2026-10-21T17:57:02+00:00'))
        d=dict(schema='task1-perimeter-shell-root-decision-v1',status='selected_not_executed',case_id=r.CASE_ID,
            source_run_id=r.SOURCE_RUN,source_case_id=r.SOURCE_ID,question='Finite geometry question',
            selected_variant='radial_prefix_all_cutoff_ties_minus_outermost_diagonal',removed_Q1_face=[67,67],
            cutoff_center_radius_squared_integer=2890,minimum_gap_mm=3.75,maximum_corner_radius_squared_mm2=623.828125,new_PDE=1,new_native_RHS=8,independent_outputs=2,physical_pads=4,
            fixed_total_area_mm2=900,candidate_adopted=False,root_selected=True,peer_endorsed=False,
            feedback=dict(path=str(fp),SHA256=r.core.sha(fp)),input_sha256=paths)
        dp=root/'decision.json';r.core.write(dp,d);return dp,fp,d

    def test_completed_hashed_context_passes_and_source_drift_or_extra_output_blocks(self):
        with tempfile.TemporaryDirectory()as td,mock.patch.object(r.core,'REPO',Path(td)):
            root=Path(td);dp,fp,d=self.context(root)
            decision,feedback,pins=r.verify_context(dp,fp)
            self.assertTrue(decision['root_selected']);self.assertFalse(decision['peer_endorsed'])
            self.assertEqual(r.core.sha(dp),pins[str(dp)])
            d['independent_outputs']=4;r.core.write(dp,d)
            with self.assertRaises(ValueError):r.verify_context(dp,fp)
            d['independent_outputs']=2;r.core.write(dp,d)
            path=Path(next(iter(d['input_sha256'])));path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'SHA'):r.verify_context(dp,fp)

    def test_preparation_context_failure_preserves_evidence_and_debits_without_reset_or_run(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'data-native').mkdir();(root/'runtime').mkdir();run=root/'data-native/cloud-synthetic-tangent'
            ledger=dict(limit_seconds=13800,spent_seconds=7.,runs=[dict(stage='earlier',seconds=7.)])
            r.core.write(root/'runtime/task1-budget.json',ledger)
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r,'_caller_owns_execution_lock'),\
                 mock.patch.object(r.os,'sched_setaffinity'),mock.patch.object(r.policy,'load_ledger',return_value=copy.deepcopy(ledger)),\
                 mock.patch.object(r.policy,'effective_limit',return_value=13800),\
                 mock.patch.object(r,'verify_context',side_effect=ValueError('synthetic context drift')),\
                 mock.patch.object(r.subprocess,'Popen')as popen:
                with self.assertRaisesRegex(ValueError,'context drift'):r.prepare_perimeter_shell(run,root/'decision',root/'feedback')
            self.assertFalse(run.exists());popen.assert_not_called()
            self.assertEqual('preparation_failed_preserved',r.core.read(run.with_name(run.name+'.preparation-failure.json'))['status'])
            after=r.core.read(root/'runtime/task1-budget.json')
            self.assertEqual(ledger['runs'],after['runs'][:1]);self.assertGreater(after['spent_seconds'],7)
            self.assertEqual('preparation_failed_preserved',after['runs'][-1]['status'])
            before_bytes=(root/'runtime/task1-budget.json').read_bytes()
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r.policy,'load_ledger')as load:
                with self.assertRaisesRegex(ValueError,'failed run IDs'):
                    r.prepare_perimeter_shell(run,root/'decision',root/'feedback')
            load.assert_not_called();self.assertEqual(before_bytes,(root/'runtime/task1-budget.json').read_bytes())

    def test_bounded_java_timeout_kills_only_its_owned_group_and_never_retries(self):
        child=mock.Mock(pid=987654);child.wait.side_effect=[subprocess.TimeoutExpired(['java'],5),0];child.poll.return_value=None
        guard=mock.Mock(side_effect=[10.,ValueError('synthetic timeout')])
        with mock.patch.object(r.subprocess,'Popen',return_value=child)as popen,mock.patch.object(r.core,'rss',return_value=100),\
             mock.patch.object(r.os,'killpg')as killpg:
            with self.assertRaisesRegex(ValueError,'synthetic timeout'):r.bounded_command(['java'],io.StringIO(),guard)
        self.assertEqual(1,popen.call_count);self.assertTrue(popen.call_args.kwargs['start_new_session'])
        killpg.assert_called_once_with(987654,r.signal.SIGTERM)


if __name__=='__main__':unittest.main()
