"""Metadata-only recovery fixtures; earlier failures and arrays stay intact."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
import task1_grouped_fine_volume_recovery_registration as reg
import test_task1_grouped_fine_volume_registration as fixtures

REAL_FEEDBACK=ROOT/'docs/cloud-grouped-fine-recovery-20261021T161000Z/feedback-before.json'
COMMENT_IDS={6312627319,6314921372}


def contexts(value):
    if isinstance(value,dict):
        return [value]+[row for child in value.values()for row in contexts(child)]
    if isinstance(value,list):return [row for child in value for row in contexts(child)]
    return []


class GroupedFineVolumeRecoveryRegistrationTest(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.GroupedFineVolumeRegistrationTest(methodName='runTest');fixture.setUp()
        self.addCleanup(fixture.doCleanups);self.fixture=fixture;self.root=fixture.root
        self.write=fixture.write;self.output=self.root/'docs/grouped-fine-recovery-plan.json'
        self.feedback=self.root/'docs/explicit-queue-feedback.json'
        self.write(self.feedback,json.loads(REAL_FEEDBACK.read_text()))
        self.decision=self.root/'docs/grouped-fine-root-decision.json'
        self.write(self.decision,dict(schema='task1-grouped-fine-root-decision-v1',status='selected_not_executed',
            question='Root-selected fixed fine grouped-pad volume comparison',new_PDE=4,new_native_RHS=32,
            reuse_original4squarefine=True,no_duplicate_baseline=True,independent_outputs=2,
            physical_pads=[4,8,12,16],fixed_total_area_mm2=900.,
            coarse_to_fine_each_case_geometry_unchanged=True,candidate_adopted=False,input_sha256={}))
        self.pre_path=self.root/'data-native'/reg.NEW_RUN/'preregistration.json'
        pre=json.loads(self.pre_path.read_text());pre.pop('source_feedback',None)
        pre['created_utc']='2026-10-21T15:57:25+00:00'
        pre['root_selection_decision']=dict(path=str(self.decision),SHA256=reg.sha(self.decision))
        self.write(self.pre_path,pre);self.rebind_audits()

    def rebind_audits(self):
        for path in (self.pre_path.parent/'audit').glob('*.json'):
            audit=json.loads(path.read_text());audit['registration_sha256']=reg.sha(self.pre_path);self.write(path,audit)

    def generate(self,feedback=None):
        with (mock.patch.object(reg,'_committed_sources',return_value=('implementation-commit',{})),
              mock.patch.object(reg.inherited.policy,'load_ledger',return_value=self.fixture.fixture.expanded),
              mock.patch.object(reg.inherited.policy,'effective_limit',return_value=13800),
              mock.patch.object(reg.inherited.policy,'remaining_seconds',return_value=7800),
              mock.patch.object(reg.inherited.policy,'policy_refs',return_value={})):
            return reg.make_preregistration(self.output,self.feedback if feedback is None else feedback,root=self.root)

    def test_explicit_feedback_and_root_selection_register_five_rows_without_array_reads(self):
        old_failure=self.root/'docs/grouped-fine-plan.failure.json';old_failure.write_text('preserved original failure\n')
        failure_sha=reg.sha(old_failure);feedback_sha=reg.sha(self.feedback);pre_sha=reg.sha(self.pre_path)
        self.assertNotIn('source_feedback',json.loads(self.pre_path.read_text()))
        original=Path.read_bytes
        def guarded(path):
            if path.name=='volume.npz'or path.name.startswith(('grid.','field-','potential-','density-','contacts-','source-','loss-')):
                raise AssertionError('Metadata recovery attempted native-array byte read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):plan=self.generate()
        self.assertEqual(5,plan['initial_case_count'])
        self.assertEqual([4,4,8,12,16],[row['n_pads']for row in plan['cases']])
        self.assertEqual([2]*5,[row['n_outputs']for row in plan['cases']])
        self.assertEqual('baseline-square15-xy80',plan['baseline_case_id'])
        self.assertEqual([plan['cases'][0]['summary']],plan['baseline_summary_paths'])
        self.assertEqual(feedback_sha,plan['input_sha256'][str(self.feedback)])
        self.assertEqual(reg.sha(self.decision),plan['input_sha256'][str(self.decision)])
        evidence=plan['new_feedback_context']['source']
        incoming={row['source_comment_id'] for row in evidence['stable_incoming_sources']}
        self.assertEqual({6280443738,6297472037,6308380231,6308699569,6309148063,6312627319,6314921372,
            6319669306,6320375305},incoming)
        self.assertNotIn(6320024448,incoming)
        self.assertFalse(evidence['latest_review_scope']['numerical_or_target_feasibility_endorsement'])
        self.assertFalse(evidence['latest_review_scope']['existing_volume_registration_blocked_by_separate_new_hotspot_audit'])
        self.assertEqual(failure_sha,reg.sha(old_failure));self.assertEqual(feedback_sha,reg.sha(self.feedback))
        self.assertEqual(pre_sha,reg.sha(self.pre_path))
        self.assertTrue(plan['metadata_recovery']['original_stage_failure_preserved'])
        self.assertFalse(plan['metadata_recovery']['original_preregistration_modified'])
        self.assertEqual(0,plan['metadata_recovery']['new_PDE'])
        recovery=[row for row in contexts(plan)if 'root_selected_fine_comparison'in row]
        self.assertTrue(recovery)
        self.assertTrue(all(row['root_selected_fine_comparison']is True for row in recovery))
        self.assertTrue(all(row.get('peer_requested_specific_geometry')is False for row in recovery))

    def test_missing_explicit_feedback_does_not_fall_back_to_old_preregistration_feedback(self):
        pre=json.loads(self.pre_path.read_text())
        pre['source_feedback']=dict(path=str(self.fixture.fixture.feedback),
            SHA256=reg.sha(self.fixture.fixture.feedback),stable_source_keys=['old-stage'])
        self.write(self.pre_path,pre);self.rebind_audits()
        with self.assertRaises(ValueError):self.generate(self.root/'docs/missing-feedback.json')
        self.assertFalse(self.output.exists())

    def test_failed_or_nonreadonly_feedback_and_mismatched_comment_body_hash_are_rejected(self):
        original=json.loads(self.feedback.read_text())
        for mutation in ('failed','messaged','bodyhash'):
            snapshot=copy.deepcopy(original)
            if mutation=='failed':snapshot.update(status='failed_preserved',error='synthetic GET failure')
            elif mutation=='messaged':snapshot['messages_sent']=1
            else:
                comments=[comment for receipt in snapshot['receipts']if receipt['kind']=='comments'
                          for comment in receipt['evidence']if comment['id']in COMMENT_IDS]
                self.assertTrue(comments);comments[0]['body_sha256']='0'*64
            self.write(self.feedback,snapshot)
            with self.assertRaises(ValueError):self.generate()
            self.assertFalse(self.output.exists())

    def test_expected_incoming_body_cannot_be_replaced_even_with_a_consistent_new_hash(self):
        snapshot=json.loads(self.feedback.read_text())
        comment=next(comment for receipt in snapshot['receipts']if receipt['kind']=='comments'
                     for comment in receipt['evidence']if comment['id']in COMMENT_IDS)
        comment['body']+='\nsynthetic changed content'
        comment['body_sha256']=hashlib.sha256(comment['body'].encode()).hexdigest()
        self.write(self.feedback,snapshot)
        with self.assertRaises(ValueError):self.generate()
        self.assertFalse(self.output.exists())

    def test_missing_or_changed_mandatory_root_decision_is_rejected(self):
        original=self.decision.read_bytes()
        for absent in (True,False):
            try:
                if absent:self.decision.unlink()
                else:self.decision.write_bytes(original+b'\n')
                with self.assertRaises(ValueError):self.generate()
                self.assertFalse(self.output.exists())
            finally:self.decision.write_bytes(original)

    def test_recovery_never_overwrites_an_existing_plan(self):
        self.output.write_text('preserved prior plan\n')
        with self.assertRaises(ValueError):self.generate()
        self.assertEqual('preserved prior plan\n',self.output.read_text())


if __name__=='__main__':
    unittest.main()
