"""Three pure metadata fixtures; no old file, helper I/O or runtime work."""
import copy,unittest
import prior_source_failure as history

def records():
 owner=dict(status='failed_preserved',failed_phase='source-publication',GUI_generated=False,candidate_adopted=False,new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0)
 attempt=dict(schema='task1-Git-only-attempt-v1',status='failed_preserved',recorded_commit=history.COMMIT,push_attempted=True,push_confirmed=True)
 files={'tools/synthetic/'+str(i)+'.py':dict(SHA256='a'*64,bytes=1)for i in range(61)}
 publication=dict(status='published_readback_verified',commit=history.COMMIT,expected_parent=history.PARENT,transport='supported_Git_HTTPS_readback_only_recovery',verification_source_SHA256=history.RECOVERY_SOURCE_SHA,original_publisher_attempt_preserved=True,no_new_commit_or_push=True,files={k:dict(v,Git_blob_SHA='b'*40,readback_passed=True)for k,v in files.items()})
 common=dict(schema='task1-append-R4-source-readback-recovery-v1',source_commit=history.PARENT,result_commit=history.COMMIT,original_GUI_owner_status='failed_preserved',original_GUI_owner_receipt_SHA256=history.OWNER_SHA,GUI_generated=False,old_owner_rewritten=False,original_GUI_worker_failure_retained=True,finished_utc='actual-terminal-fixture',new_PDE=0,new_native_array_decodes=0,branch_mutations=0)
 recovery=dict(common,status='append_R4_source_readback_recovered',files_verified=61,result_publication_receipt_SHA256=history.PUBLICATION_SHA)
 diagnostic=dict(common,status='failed_preserved',error_type='AssertionError',error='Explicit-no-filter batch request failed')
 planbase=dict(fixed_commit=history.COMMIT,expected_parent=history.PARENT,plan_SHA256=history.PLAN_SHA,original_failed_owner=owner,original_failed_publisher=attempt)
 return dict(owner=owner,attempt=attempt,state=dict(commit=history.COMMIT,parent=history.PARENT,push_confirmed=True),batch=dict(returncode=1,unsupported_fallback=False,unique_blob_count=61),failed_command=dict(returncode=1,stderr='fatal: bad revision'),plan=dict(expected_parent=history.PARENT,files=files),publication=publication,recovery=recovery,diagnostic=diagnostic,recovery_plan=dict(planbase,verifier_source_SHA256=history.RECOVERY_SOURCE_SHA),diagnostic_plan=dict(planbase,verifier_source_SHA256=history.DIAGNOSTIC_SOURCE_SHA),recovery_batch=dict(returncode=0,explicit_no_filter=True,blobs=61),diagnostic_batch=dict(returncode=1,explicit_no_filter=True,stderr='fatal: bad revision'))

class PriorSourceFailureContracts(unittest.TestCase):
 def test_late_source_readback_preserves_original_failure_without_native_success(self):
  value=records();before=copy.deepcopy(value);evidence=history.validate_records(value)
  self.assertEqual(value,before);self.assertEqual(evidence['original_owner_status'],'failed_preserved');self.assertTrue(evidence['late_source_readback_available']);self.assertEqual(evidence['late_source_files_verified'],61);self.assertFalse(evidence['original_MFG_performed']);self.assertFalse(evidence['original_native_work_performed'])
 def test_false_old_success_native_work_or_incomplete_readback_rejects(self):
  for which,key,value in(('owner','status','completed'),('owner','new_PDE_RHS',1),('owner','source_commit',history.COMMIT),('attempt','status','published_readback_verified'),('batch','returncode',0),('publication','commit','0'*40)):
   r=records();r[which][key]=value
   with self.assertRaises(ValueError):history.validate_records(r)
  r=records();r['publication']['files']['tools/synthetic/0.py']['readback_passed']=False
  with self.assertRaises(ValueError):history.validate_records(r)
 def test_failed_recovery_or_relabelled_diagnostic_and_code_mismatch_reject(self):
  for which,key,value in(('recovery','status','failed_preserved'),('recovery','branch_mutations',1),('diagnostic','status','append_R4_source_readback_recovered'),('diagnostic_batch','returncode',0),('recovery_plan','verifier_source_SHA256','0'*64),('diagnostic_plan','plan_SHA256','0'*64)):
   r=records();r[which][key]=value
   with self.assertRaises(ValueError):history.validate_records(r)
if __name__=='__main__':unittest.main()
