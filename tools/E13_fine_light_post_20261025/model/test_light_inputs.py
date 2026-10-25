"""Pure prospective producer/provenance contracts; author did not run tests."""
import copy,unittest
from unittest.mock import patch
import light_inputs as subject

def admission():
 return dict(schema='task1-E13-fine-light-post-root-admission-v1',status='admitted_finite_E13_fine_cached_post',root_review_positive=True,sole_NUM_owner=True,candidate_ids=[subject.CANDIDATE_ID],completed_native_geometries=1,requested_probes=40,threshold_subsets=48,new_driven_RHS=0,new_eigen_solves=0,new_angular_metric_evaluations=0,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,child_RSS_forecast_bytes=170000000,new_output_forecast_bytes=10000000,native_Q_loaded=False,fields_reconstructed=False,old_statistics_recomputed=False,candidate_adopted=False,owned_auxiliary_namespaces=['/dev/shm/task1-*','/tmp/task1-*'],source_sha256={'synthetic/source.py':'a'*64},decision_basis='Synthetic metadata fixture only')
def producer():
 summary=dict(status='two_E13_matched97_metric_cases_and_physical_overlap_computed_unadopted',actual_new_driven_RHS=2,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=2,actual_full_angular_evaluations=1,actual_SC4_only_angular_evaluations=1,actual_repeated_original_bulk_angular_evaluations=0,actual_immutable_fine_B0_aliases=1,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0,candidate_adopted=False,Q_resident_during_postprocessing=False)
 verify=dict(before_tests_and_build=dict(passed=True,count=2),after_build=dict(passed=True,count=3));account=dict(passed=True,actual_new_driven_RHS=2)
 worker=dict(status='E13_fineXY_computed',summary_SHA256='b'*64,input_verification=verify,manufactured_test_receipt_SHA256='c'*64,E13_fineXY_accounting=account,actual_new_fine_RHS=2,actual_new_coarse_RHS=0)
 stage=dict(status='E13_fineXY_computed',worker_exit_code=0,source_commit=subject.PUBLICATIONS['E13_S'][2],accounting=account)
 sources={'synthetic/source.py':'a'*64};spec=dict(inputs=dict(source_sha256=sources));local=dict(status='passed',source_publication_commit=subject.PUBLICATIONS['E13_S'][2],model_source_sha256=sources,model_source_test_count=40,model_tests_run=40,owner_tests_run=5,tests_run=45,expected_total_tests=45,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_Q_loaded=False,field_admission_granted=False,scientific_API_spy_calls=[])
 return summary,worker,stage,verify,local,spec,'b'*64,'c'*64

class E13FineInputContracts(unittest.TestCase):
 def test_invalid_admission_stops_before_all_metadata_or_source_access(self):
  with patch.object(subject,'metadata',side_effect=AssertionError('No metadata access')),patch.object(subject,'source_inventory',side_effect=AssertionError('No source access')):
   with self.assertRaises(ValueError):subject.make_spec({})
 def test_only_full_E13fine_single_case_is_selected(self):
  self.assertIs(subject.validate_admission(admission())['root_review_positive'],True)
  for ids in([],(subject.CANDIDATE_ID,),[subject.E13],[subject.B0],[subject.CANDIDATE_ID,subject.CANDIDATE_ID],[True]):
   a=admission();a['candidate_ids']=ids
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_exact_zero_work_counts_and_forecasts_cannot_be_relaxed(self):
  for key,value in(('requested_probes',39),('threshold_subsets',47),('completed_native_geometries',2),('new_driven_RHS',True),('new_angular_metric_evaluations',1),('new_eigen_solves',1),('CPU_limit',True),('total_RSS_plus_all_owned_tmpfs_bytes',9000000000),('child_RSS_forecast_bytes',170000001),('new_output_forecast_bytes',10000001),('native_Q_loaded',True),('fields_reconstructed',True),('old_statistics_recomputed',True),('owned_auxiliary_namespaces',['/dev/shm/task1-*'])):
   a=admission();a[key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_original_four_normalizations_are_finite_and_unmodified(self):
  n=dict(status='complete',comparisons={mode:dict(amplitude_scale=.5)for mode in subject.MODES});original=copy.deepcopy(n)
  self.assertIs(subject.validate_normalizations(n),n);self.assertEqual(n,original)
  for x in(-1.,float('nan'),True):
   bad=copy.deepcopy(n);bad['comparisons'][subject.MODES[-1]]['amplitude_scale']=x
   with self.assertRaises(ValueError):subject.validate_normalizations(bad)
  bad=copy.deepcopy(n);bad['comparisons'].pop(subject.MODES[-1])
  with self.assertRaises(ValueError):subject.validate_normalizations(bad)
 def test_completed_numerical_stage_accepts_exact_extra_local_MFG_pin(self):
  rows=producer();before=copy.deepcopy(rows);self.assertTrue(subject.validate_completed_producer(*rows));self.assertEqual(rows,before)
 def test_numerical_partial_or_late_failed_worker_does_not_supply_fields(self):
  for index,key,value in((0,'actual_new_driven_RHS',1),(1,'status','failed_preserved'),(1,'error_type','SyntheticLateFailure'),(2,'worker_exit_code',1),(4,'tests_skipped',1),(4,'model_source_sha256',{})):
   rows=list(copy.deepcopy(producer()));rows[index][key]=value
   with self.assertRaises(ValueError):subject.validate_completed_producer(*rows)
  rows=list(copy.deepcopy(producer()));rows[3]['after_build']['count']=rows[3]['before_tests_and_build']['count']
  with self.assertRaises(ValueError):subject.validate_completed_producer(*rows)
 def test_actual_transfer_descriptor_coverage_is_exact_not_a_Windows_claim(self):
  d=dict(path='/synthetic/a.npz',publication_commit='d'*40,publication_target='data-native/fixture/a.npz',SHA256='e'*64,bytes=123)
  row=dict(fixed_commit=d['publication_commit'],repo_relative_path=d['publication_target'],SHA256=d['SHA256'],bytes=d['bytes'])
  m=dict(schema='task1-safe-windows-transfer-manifest-v1',public_reference_commit=subject.PUBLICATIONS['E13_M'][2],Windows_backup_complete=False,OneDrive_sync_verified=False,files=[],logical_file_aliases=[row])
  result=subject.validate_manifest_coverage(m,[d]);self.assertFalse(result['Windows_saved_verified']);self.assertEqual(result['used_native_artifacts'],1)
  for key,value in(('SHA256','f'*64),('bytes',124),('fixed_commit','0'*40),('repo_relative_path','data-native/fixture/other.npz')):
   bad=copy.deepcopy(m);bad['logical_file_aliases'][0][key]=value
   with self.assertRaises(ValueError):subject.validate_manifest_coverage(bad,[d])
  bad=copy.deepcopy(m);bad['Windows_backup_complete']=True
  with self.assertRaises(ValueError):subject.validate_manifest_coverage(bad,[d])
 def test_direct_artifact_proof_needs_full_SHA_bytes_and_actual_readback(self):
  target='data-native/synthetic/a.npz';p=dict(status='published_readback_verified',commit='d'*40,files={target:dict(SHA256='e'*64,bytes=123,readback_passed=True)})
  self.assertFalse(subject.direct(p,'/synthetic/a.npz',target,'e'*64)['arrays_decoded_here'])
  for key,value in(('SHA256','short'),('bytes',True),('readback_passed',False)):
   bad=copy.deepcopy(p);bad['files'][target][key]=value
   with self.assertRaises(ValueError):subject.direct(bad,'/synthetic/a.npz',target,'e'*64)
 def test_recovery_alias_preserves_original_and_alias_addresses(self):
  source=subject.FINE/'receipt.json';alias=subject.RECOVERY/'original-numerical-owner-failure.json';d=dict(original_path=str(source),alias_path=str(alias),alias_only=True,SHA256='a'*64,bytes=123)
  self.assertIs(subject.recovery_contracts.validate_recovery_alias(d,source,alias),d)
  for key,value in(('original_path','/synthetic/other.json'),('alias_path','/synthetic/other.json'),('alias_only',False)):
   bad=copy.deepcopy(d);bad[key]=value
   with self.assertRaises(ValueError):subject.recovery_contracts.validate_recovery_alias(bad,source,alias)

if __name__=='__main__':unittest.main()
