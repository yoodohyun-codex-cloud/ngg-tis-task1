"""Small fixed-outline/context fixtures; no native arrays, JVM, prepare or PDE."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_perimeter_inward_registration as r


class InwardGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline=next(d for d in json.loads((r.core.HIST/'inputs/designs.json').read_text())if d['id']=='baseline-square15')
        cls.parent,cls.oldrows,_,_=r.parent.shell_design(baseline)
        cls.design,cls.rows,cls.areas,cls.proof=r.inward_design(cls.parent)

    def test_rigid_face_permutation_preserves_exact_area_outline_and_all_four_identities(self):
        self.assertEqual(2304,len(self.rows));self.assertEqual(2304,len({(i,j)for p,i,j,a in self.rows}))
        self.assertEqual([576]*4,self.proof['faces_per_pad'])
        for p,(di,dj)in enumerate(r.INDEX_SHIFTS):
            old={(i,j,a)for q,i,j,a in self.oldrows if q==p};new={(i-di,j-dj,a)for q,i,j,a in self.rows if q==p}
            self.assertEqual(old,new);self.assertAlmostEqual(.000225,self.areas[p],places=16)
            pad,before=self.design['pads'][p],self.parent['pads'][p];dx,dy=r.TRANSLATIONS[p]
            self.assertEqual([[x+dx,y+dy]for x,y in before['polygon_mm']],pad['polygon_mm'])
            for key in ('shape','width_mm','height_mm','rotation_deg','role','source_output','analytic_area_mm2','native_face_count'):
                self.assertEqual(before[key],pad[key])
        self.assertEqual(r._mask_bytes(self.rows),r._mask_bytes(r.inward_design(copy.deepcopy(self.parent))[1]))

    def test_clearance_gaps_connectivity_and_holds_are_explicit_without_mesh_promotion(self):
        self.assertEqual(583.203125,self.proof['maximum_physical_vertex_radius_squared_mm2'])
        self.assertAlmostEqual(.8504011420479287,self.proof['rim_clearance_mm'],places=14)
        self.assertEqual(2.5,min(g['gap_mm']for g in self.proof['verified_physical_gaps_mm']))
        self.assertEqual(4,self.proof['minimum_gap_XY_cells']);self.assertEqual([0]*4,self.proof['holes_per_pad'])
        self.assertTrue(self.proof['placement_and_gap_jointly_changed']);self.assertFalse(self.proof['isolated_rim_effect_claimed'])
        self.assertFalse(self.proof['mesh_convergence_claimed']);self.assertFalse(self.proof['future_grid_reranking_allowed'])
        for p,i,j,a in self.rows:
            self.assertEqual((.625/1000)**2,a)
            self.assertTrue(all((-25+ii*.625)**2+(-25+jj*.625)**2<625 for ii in(i,i+1)for jj in(j,j+1)))

    def test_source_drift_or_ground_output_reassignment_is_rejected(self):
        for edit in ('face','area','output','parent_id'):
            source=copy.deepcopy(self.parent)
            if edit=='face':source['pads'][0]['native_face_indices'][0][0]+=1
            if edit=='area':source['pads'][2]['analytic_area_mm2']=224
            if edit=='output':source['pads'][3]['source_output']=2
            if edit=='parent_id':source['id']='other-shell'
            with self.subTest(edit=edit),self.assertRaises(ValueError):r.inward_design(source)

    def test_config_changes_only_mask_and_translated_positions_not_contact_physics_or_mesh(self):
        source=(r.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        data,_=r.parent.changed_shell_config(source,self.parent,Path('/tmp/old-mask.csv'),'a'*64)
        updated,changes=r.changed_inward_config(data,self.design,Path('/tmp/new-mask.csv'),'b'*64)
        a,b=r._properties(data),r._properties(updated)
        allowed={'mask.path','mask.sha256'}|{f'pad.{p}.{k}'for p in range(4)for k in ('x_mm','y_mm')}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},{k:v for k,v in b.items()if k not in allowed})
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1320,r.MIN_REMAINING_SECONDS);self.assertEqual(120,r.PREPARATION_SECONDS)


class ContextTests(unittest.TestCase):
    def fixture(self,root):
        comment=dict(id=6321929825,author='yoodohyun-codex-cloud',body='signed power fixture',
            html_url='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825')
        comment['body_sha256']=hashlib.sha256(comment['body'].encode()).hexdigest();receipts=[]
        for p in (1,2):
            for k in ('head','comments'):
                receipts.append(dict(pull=p,kind=k,endpoint='repos/yoodohyun-codex-cloud/ngg-tis-task1/'+(f'pulls/{p}'if k=='head'else f'issues/{p}/comments'),
                    evidence={'head_sha':'a'*40}if k=='head'else([comment]if p==2 else[])))
        fp=root/'feedback.json';r.core.write(fp,dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,observed_utc='2026-10-21T19:00:00+00:00',receipts=receipts))
        op=root/'optimization.json';r.core.write(op,dict(schema='task1-perimeter-drive-optimization-v1',status='calculated_unadopted',
            inputs_unchanged=True,new_PDE=0,candidate_adopted=False,global_optimum_claimed=False,conditions=[],
            source_geometry=dict(source_run_id=r.SOURCE_RUN,source_case_id=r.SOURCE_ID)))
        d=dict(schema='task1-perimeter-inward-root-decision-v1',status='selected_not_executed',case_id=r.CASE_ID,
            source_run_id=r.SOURCE_RUN,source_case_id=r.SOURCE_ID,question='Rigid same-outline placement diagnostic',
            placement_offset_per_coordinate_mm=.625,new_PDE=1,new_native_RHS=8,independent_outputs=2,physical_pads=4,
            fixed_total_area_mm2=900,candidate_adopted=False,root_selected=True,peer_endorsed=False,
            feedback=dict(path=str(fp),SHA256=r.core.sha(fp)),optimization_result=dict(path=str(op),SHA256=r.core.sha(op)),
            input_sha256={str(op):r.core.sha(op)})
        dp=root/'decision.json';r.core.write(dp,d);return dp,fp,op,d

    def test_completed_optimization_feedback_hash_required_without_global_infeasibility_claim(self):
        with tempfile.TemporaryDirectory()as td,mock.patch.object(r.core,'REPO',Path(td)):
            dp,fp,op,d=self.fixture(Path(td));decision,feedback,pins=r.verify_context(dp,fp)
            self.assertFalse(decision['peer_endorsed']);self.assertEqual(r.core.sha(op),pins[str(op)])
            o=r.core.read(op);o['status']='running';r.core.write(op,o)
            d['optimization_result']['SHA256']=r.core.sha(op);d['input_sha256'][str(op)]=r.core.sha(op);r.core.write(dp,d)
            with self.assertRaisesRegex(ValueError,'optimization evidence'):r.verify_context(dp,fp)
            o['status']='calculated_unadopted';o['conditions']=[dict(canonical_screen_all_passed=True)];r.core.write(op,o)
            d['optimization_result']['SHA256']=r.core.sha(op);d['input_sha256'][str(op)]=r.core.sha(op);r.core.write(dp,d)
            with self.assertRaises(ValueError):r.verify_context(dp,fp)

    def test_failed_context_preserves_failure_and_charges_ledger_without_jvm_or_output_reuse(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'data-native').mkdir();(root/'runtime').mkdir();run=root/'data-native/cloud-synthetic-inward'
            ledger=dict(limit_seconds=13800,spent_seconds=7.,runs=[dict(stage='past',seconds=7.)]);r.core.write(root/'runtime/task1-budget.json',ledger)
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r,'_caller_owns_execution_lock'),mock.patch.object(r.os,'sched_setaffinity'),\
                mock.patch.object(r.policy,'load_ledger',return_value=copy.deepcopy(ledger)),mock.patch.object(r.policy,'effective_limit',return_value=13800),\
                mock.patch.object(r,'verify_context',side_effect=ValueError('synthetic context drift')),mock.patch.object(r.subprocess,'Popen')as popen:
                with self.assertRaisesRegex(ValueError,'context drift'):r.prepare_perimeter_inward(run,root/'decision',root/'feedback')
            popen.assert_not_called();self.assertFalse(run.exists());self.assertTrue(run.with_name(run.name+'.preparation-failure.json').is_file())
            after=r.core.read(root/'runtime/task1-budget.json');self.assertGreater(after['spent_seconds'],7);self.assertEqual(ledger['runs'],after['runs'][:1])
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r.policy,'load_ledger')as load:
                with self.assertRaisesRegex(ValueError,'failed run IDs'):r.prepare_perimeter_inward(run,root/'decision',root/'feedback')
                load.assert_not_called()

if __name__=='__main__':unittest.main()
