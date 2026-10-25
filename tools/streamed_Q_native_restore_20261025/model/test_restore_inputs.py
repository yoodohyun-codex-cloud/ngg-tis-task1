"""Pure deferred-admission/provenance fixtures; author did not run them."""
import copy,unittest
from unittest.mock import patch
import restore_inputs as subject

def admission():
 return dict(schema='task1-streamed-Q-native-B0-restore-root-admission-v1',status='admitted_cached_native_B0_restore_after_published_MFG',root_review_positive=True,sole_NUM_owner=True,
  new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,expected_cached_restored_carriers=2,physical_pads=4,independent_outputs=2,frequencies_Hz=[2000,2010],fine_layer_counts=[4,19,18,56],fine_evaluation_cells=793848,max_physical_evaluation_cells=800000,Q_rows=8184,cache_name='xy102',CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,candidate_adopted=False,source_sha256={'synthetic.py':'a'*64},decision_basis='Synthetic contract only',
  MFG_review=dict(run=str(subject.MFG),publication_path=str(subject.MFG/'result-publication/result-publication.json'),publication_SHA256='b'*64,publication_commit='c'*40,root_reviewed=True,decision_basis='Synthetic scope fixture only'))
def mfg():
 return dict(status='passed',kind='actual_tiny_streamed_real_Q_operator_fixtures_only',source_publication_commit='c'*40,model_source_sha256={'fixture.py':'a'*64},source_sha256={'fixture.py':'a'*64},model_source_test_count=12,tests_run=20,expected_total_tests=20,model_tests_run=12,owner_tests_run=8,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_file_reads=0,native_eigen_solves=0,native_full_field_exports=0,native_field_angular_work=0,native_Q_loaded=False,native_eigen_performed=False,native_restore_performed=False,field_admission_granted=False,candidate_adopted=False,forbidden_field_calls=[],native_IO_attempts=[],IO_audit_installed=True,synthetic_metadata_proofs_are_fixture_values=True,test_events=[dict(test_id='synthetic_method_'+str(i),outcome='passed')for i in range(20)],manufactured_work_counts={k:1 for k in('operator_constructors','metadata_validation_calls','forward_attempts','transpose_attempts','slice_attempts','chunk_visits_started','chunk_visits_completed','operator_receipts')})
def qproof():
 target='data-native/retained-eigen-cache-20261025/xy102/Q-test.f64'
 row=dict(path='/synthetic-Q/Q-test.f64',SHA256='e'*64,bytes=32,row_start=0,row_stop=2,column_start=0,column_stop=2,dtype='<f8',order='F')
 manifest=dict(shape=[2,2],dtype='<f8',order='F',remote_verified=False,chunks=[row])
 proof=dict(SHA256='e'*64,bytes=32,Git_blob_SHA='f'*40,readback_passed=True)
 normalized=dict(status='published_readback_verified',commit=subject.REMOTE_Q_COMMIT,original_public_receipt_SHA256=subject.ORIGINAL_Q_RECEIPT_SHA,files={target:proof})
 original=dict(schema='task1-retained-cache-public-readback-receipt-v1',commit=subject.REMOTE_Q_COMMIT,files=[dict(proof,repo_relative_path=target,commit=subject.REMOTE_Q_COMMIT)])
 return manifest,normalized,original,target

class RestoreInputContracts(unittest.TestCase):
 def test_incomplete_admission_does_not_touch_any_metadata(self):
  with patch.object(subject,'metadata',side_effect=AssertionError('No actual metadata')),patch.object(subject,'source_inventory',side_effect=AssertionError('No actual source map')):
   with self.assertRaises(ValueError):subject.make_spec({})
 def test_exact_published_MFG_run_is_mandatory(self):
  a=admission();self.assertIs(subject.validate_admission(a),a)
  for key,value in(('run','/dev/shm/task1-other-MFG-run'),('publication_path','/dev/shm/task1-fixture/result-publication/result-publication.json'),('root_reviewed',False)):
   a=admission();a['MFG_review'][key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_restore_cannot_become_new_PDE_or_another_grid(self):
  for key,value in(('new_driven_RHS',1),('new_eigen_solves',True),('new_angular_metric_evaluations',1),('Q_rows',7860),('cache_name','xy100'),('fine_evaluation_cells',800001)):
   a=admission();a[key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_actual_MFG_status_counts_and_native_scope_are_required(self):
  value=mfg();self.assertTrue(subject.validate_mfg(value,value['model_source_sha256'],'c'*40))
  for key,x in(('status','source_only'),('tests_run',True),('tests_run',19),('tests_skipped',1),('native_file_reads',1),('native_Q_loaded',True),('native_restore_performed',True),('field_admission_granted',True)):
   value=mfg();value[key]=x
   with self.assertRaises(ValueError):subject.validate_mfg(value,value['model_source_sha256'],'c'*40)
 def test_MFG_cannot_hide_missing_events_calls_or_caught_violations(self):
  for change in('duplicate_event','failed_event','missing_call','forbidden','source_mismatch'):
   value=mfg()
   if change=='duplicate_event':value['test_events'][-1]=dict(value['test_events'][0])
   elif change=='failed_event':value['test_events'][-1]['outcome']='failed'
   elif change=='missing_call':value['manufactured_work_counts']['chunk_visits_completed']=0
   elif change=='forbidden':value['forbidden_field_calls']=['native_attempt']
   else:value['source_sha256']={}
   with self.assertRaises(ValueError):subject.validate_mfg(value,value['model_source_sha256'],'c'*40)
 def test_descriptor_requires_full_unskipped_actual_readback(self):
  target='data-native/fixture/archive.npz';pub=dict(status='published_readback_verified',commit='c'*40,files={target:dict(SHA256='d'*64,bytes=123,readback_passed=True)})
  result=subject.direct(pub,'/synthetic/restore/archive.npz',target,'d'*64);self.assertFalse(result['decoded_here'])
  for key,x in(('readback_passed',False),('SHA256',None),('bytes',True)):
   bad=copy.deepcopy(pub);bad['files'][target][key]=x
   with self.assertRaises(ValueError):subject.direct(bad,'/synthetic/restore/archive.npz',target,'d'*64)
 def test_every_Q_chunk_has_original_and_normalized_proof(self):
  manifest,normalized,original,target=qproof();before=copy.deepcopy(manifest)
  rows=subject.validate_chunk_receipts(manifest,normalized,original,n=2,grid_name='xy102');self.assertEqual(len(rows),1);self.assertEqual(manifest,before);self.assertFalse(manifest['remote_verified'])
  original['files'][0]['Git_blob_SHA']='0'*40
  with self.assertRaises(ValueError):subject.validate_chunk_receipts(manifest,normalized,original,n=2,grid_name='xy102')
 def test_MFG_only_success_does_not_claim_a_native_restore(self):
  value=mfg();self.assertTrue(subject.validate_mfg(value,value['model_source_sha256'],'c'*40))
  self.assertFalse(value['native_restore_performed']);self.assertFalse(value['field_admission_granted'])

if __name__=='__main__':unittest.main()
