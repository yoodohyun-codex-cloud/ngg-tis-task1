"""Integer geometry and context fixtures only; no actual native or PDE work."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_rounded_fullface_registration as r


class RoundedGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=next(d for d in json.loads((r.core.HIST/'inputs/designs.json').read_text())if d['id']=='baseline-square15')
        cls.design,cls.rows,cls.areas,cls.proof=r.rounded_design(cls.baseline)

    def test_all_ties_exact_D4_local_mirrors_and_closed_holefree_576_faces(self):
        self.assertEqual(2304,len(self.rows));self.assertEqual(2304,len({(i,j)for p,i,j,a in self.rows}))
        for p,(cx,cy)in enumerate(r.CENTRES):
            ic,jc=round((cx+25)/r.H),round((cy+25)/r.H)
            local={(2*(i-ic)+1,2*(j-jc)+1)for q,i,j,a in self.rows if p==q}
            self.assertEqual(576,len(local));self.assertEqual(560,sum(u*u+v*v<730 for u,v in local))
            self.assertEqual(16,sum(u*u+v*v==730 for u,v in local))
            self.assertTrue(all((-v,u)in local and(-u,v)in local and(v,u)in local for u,v in local))
            self.assertAlmostEqual(.000225,self.areas[p],places=16)
            self.assertEqual(list(r.CENTRES[p]),self.design['pads'][p]['center_mm'])
        self.assertEqual([1]*4,self.proof['components_per_pad']);self.assertEqual([0]*4,self.proof['holes_per_pad'])
        self.assertEqual([576]*4,self.proof['faces_per_pad']);self.assertTrue(self.proof['all_cutoff_ties_included'])

    def test_exact_fullface_geometry_rim_gap_perimeter_and_nonpromotion(self):
        self.assertEqual(528.90625,self.proof['maximum_physical_vertex_radius_squared_mm2'])
        self.assertAlmostEqual(2.002038133782378,self.proof['rim_clearance_mm'],places=14)
        self.assertEqual(2.5,min(g['gap_mm']for g in self.proof['verified_physical_gaps_mm']))
        self.assertEqual(4,self.proof['minimum_gap_XY_cells']);self.assertEqual(70.,self.proof['physical_outline_perimeter_mm_per_pad'])
        self.assertGreater(self.proof['physical_outline_perimeter_mm_per_pad'],self.proof['source_square_perimeter_mm_per_pad'])
        for key in ('smooth_circle_claimed','perimeter_reduction_claimed','isolated_edge_effect_claimed','mesh_convergence_claimed','future_grid_reranking_allowed'):
            self.assertFalse(self.proof[key])
        for p,i,j,a in self.rows:
            self.assertEqual((r.H/1000)**2,a)
            self.assertTrue(all((-25+ii*r.H)**2+(-25+jj*r.H)**2<625 for ii in(i,i+1)for jj in(j,j+1)))
        self.assertEqual(r._mask_bytes(self.rows),r._mask_bytes(r.rounded_design(copy.deepcopy(self.baseline))[1]))

    def test_original_centres_areas_roles_and_shape_are_required(self):
        for change in ('centre','area','role','shape'):
            baseline=copy.deepcopy(self.baseline)
            if change=='centre':baseline['pads'][0]['center_mm'][0]-=.625
            if change=='area':baseline['pads'][1]['analytic_area_mm2']=224
            if change=='role':baseline['pads'][2]['source_output']=2
            if change=='shape':baseline['pads'][3]['shape']='circle'
            with self.subTest(change=change),self.assertRaises(ValueError):r.rounded_design(baseline)

    def test_config_only_changes_mask_shape_and_bbox_preserving_mesh_centres_rotation_and_all_physics(self):
        source=(r.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        updated,changes=r.changed_rounded_config(source,self.design,Path('/tmp/synthetic-mask.csv'),'b'*64)
        a,b=r._properties(source),r._properties(updated)
        allowed={'mask.path','mask.sha256'}|{f'pad.{p}.{k}'for p in range(4)for k in ('shape','width_mm','height_mm')}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},{k:v for k,v in b.items()if k not in allowed})
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1320,r.MIN_REMAINING_SECONDS);self.assertEqual(120,r.PREPARATION_SECONDS)


class RoundedContextTests(unittest.TestCase):
    def fixture(self,root):
        comment=dict(id=6321929825,author='yoodohyun-codex-cloud',body='signed source-power fixture',
            html_url='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825')
        comment['body_sha256']=hashlib.sha256(comment['body'].encode()).hexdigest();receipts=[]
        for p in (1,2):
            for k in ('head','comments'):
                receipts.append(dict(pull=p,kind=k,endpoint='repos/yoodohyun-codex-cloud/ngg-tis-task1/'+(f'pulls/{p}'if k=='head'else f'issues/{p}/comments'),
                    evidence={'head_sha':'a'*40}if k=='head'else([comment]if p==2 else[])))
        fp=root/'feedback.json';r.core.write(fp,dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,observed_utc='2026-10-21T19:00:00+00:00',receipts=receipts))
        vp=root/'volume.json';r.core.write(vp,dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',inputs_unchanged=True,
            selected_for_adoption=[],cases=[dict(case_id=r.INWARD_ID,adopted=False)]))
        vr=dict(path=str(vp),SHA256=r.core.sha(vp));sp=root/'screen.json'
        r.core.write(sp,dict(schema='task1-candidate-screen-v1',status='screen_complete_not_adopted',input_volume_report=vr,
            baseline_case_id=r.BASE_ID,candidate_adopted=False,cases=[dict(case_id=r.INWARD_ID,all_screen_checks_passed=False,
                checks=[dict(passed=False)]+[dict(passed=True)for _ in range(7)])]))
        d=dict(schema='task1-rounded-fullface-root-decision-v1',status='selected_not_executed',case_id=r.CASE_ID,
            source_run_id=r.SOURCE_RUN,source_case_id=r.SOURCE_ID,question='Same-centre area fullface SHAPE diagnostic',
            new_PDE=1,new_native_RHS=8,independent_outputs=2,physical_pads=4,fixed_total_area_mm2=900,candidate_adopted=False,
            root_selected=True,peer_endorsed=False,feedback=dict(path=str(fp),SHA256=r.core.sha(fp)),inward_volume=vr,
            inward_screen=dict(path=str(sp),SHA256=r.core.sha(sp)),input_sha256={str(vp):r.core.sha(vp),str(sp):r.core.sha(sp)})
        dp=root/'decision.json';r.core.write(dp,d);return dp,fp,sp,d

    def test_completed_same_volume_failed_eight_screen_and_exact_hashes_required(self):
        with tempfile.TemporaryDirectory()as td,mock.patch.object(r.core,'REPO',Path(td)):
            dp,fp,sp,d=self.fixture(Path(td));decision,feedback,pins=r.verify_context(dp,fp)
            self.assertFalse(decision['peer_endorsed']);self.assertEqual(r.core.sha(sp),pins[str(sp)])
            s=r.core.read(sp);s['cases'][0]['all_screen_checks_passed']=True;r.core.write(sp,s)
            d['inward_screen']['SHA256']=r.core.sha(sp);d['input_sha256'][str(sp)]=r.core.sha(sp);r.core.write(dp,d)
            with self.assertRaisesRegex(ValueError,'inward8screen'):r.verify_context(dp,fp)
            s['cases'][0]['all_screen_checks_passed']=False;s['input_volume_report']['SHA256']='f'*64;r.core.write(sp,s)
            d['inward_screen']['SHA256']=r.core.sha(sp);d['input_sha256'][str(sp)]=r.core.sha(sp);r.core.write(dp,d)
            with self.assertRaises(ValueError):r.verify_context(dp,fp)

    def test_context_failure_preserves_evidence_and_finally_charges_without_jvm_or_reuse(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'data-native').mkdir();(root/'runtime').mkdir();run=root/'data-native/cloud-synthetic-rounded'
            ledger=dict(limit_seconds=13800,spent_seconds=7.,runs=[dict(stage='past',seconds=7.)]);r.core.write(root/'runtime/task1-budget.json',ledger)
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r,'_caller_owns_execution_lock'),mock.patch.object(r.os,'sched_setaffinity'),\
                mock.patch.object(r.policy,'load_ledger',return_value=copy.deepcopy(ledger)),mock.patch.object(r.policy,'effective_limit',return_value=13800),\
                mock.patch.object(r,'verify_context',side_effect=ValueError('synthetic context drift')),mock.patch.object(r.subprocess,'Popen')as popen:
                with self.assertRaisesRegex(ValueError,'context drift'):r.prepare_rounded_fullface(run,root/'decision',root/'feedback')
            popen.assert_not_called();self.assertFalse(run.exists());self.assertTrue(run.with_name(run.name+'.preparation-failure.json').exists())
            after=r.core.read(root/'runtime/task1-budget.json');self.assertGreater(after['spent_seconds'],7);self.assertEqual(ledger['runs'],after['runs'][:1])
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r.policy,'load_ledger')as load:
                with self.assertRaisesRegex(ValueError,'failed run IDs'):r.prepare_rounded_fullface(run,root/'decision',root/'feedback')
                load.assert_not_called()

if __name__=='__main__':unittest.main()
