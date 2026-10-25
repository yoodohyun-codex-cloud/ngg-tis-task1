"""Pure partial-payload proof fixtures; no actual files, helpers or arrays."""
import copy,hashlib,unittest
from unittest.mock import patch
import append_inputs as subject

def admission():
 return dict(schema='task1-native-GUI-append-E13fine-root-admission-v4',status='selected_partial_payload_append_after_GUI5_readback_recovery',root_authorized=True,safe_boundary_confirmed=True,base_version=subject.BASE_VERSION,base_outcome=subject.BASE_OUTCOME,publication_outcome=subject.PUBLICATION_OUTCOME,prior_owner_terminal_dead_confirmed=True,prior_recovery_terminal_dead_confirmed=True,candidate_ids=[subject.CID],new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0,old_native_extractions=0,new_native_extractions=1,CPU_limit=4,physical_cap_bytes=8000000000,max_cells=800000,candidate_adopted=False,browser_authorized=False,old_GUI_pointers_modified=False,source_sha256={'synthetic/source.py':'a'*64},decision_basis='Synthetic metadata fixture, not actual admission',previous_GUI=dict(base_version=subject.BASE_VERSION,base_outcome=subject.BASE_OUTCOME,publication_outcome=subject.PUBLICATION_OUTCOME,readback_recovery=copy.deepcopy(subject.RECOVERY_RECORDS),run=str(subject.GUI),source_publication=dict(path=str(subject.GUI/'source-publication/result-publication.json'),SHA256=subject.GUI5_SOURCE_RECEIPT_SHA,commit=subject.GUI5_SOURCE_COMMIT),result_publication=dict(path=str(subject.GUI/'result-publication/result-publication.json'),SHA256=subject.GUI5_RESULT_RECEIPT_SHA,commit=subject.GUI5_RESULT_COMMIT),terminal_owner=dict(path=str(subject.GUI/'receipt.json'),SHA256=subject.ORIGINAL_FAILED_OWNER_SHA256,bytes=961)))
def partial():
 S=dict(commit=subject.GUI5_SOURCE_COMMIT);R=dict(commit=subject.GUI5_RESULT_COMMIT);sources={'synthetic/source.py':'c'*64};model={'synthetic/model.py':'d'*64}
 methods={'model':{'test_model':['Synthetic.m'+str(i)for i in range(16)]},'owner':{'test_owner':['Synthetic.o'+str(i)for i in range(27)]}};inventory={}
 for ns,modules in methods.items():inventory[ns+'_methods']=modules;inventory[ns+'_counts']={k:len(v)for k,v in modules.items()};inventory[ns+'_total']=sum(inventory[ns+'_counts'].values())
 inventory['total']=43;event_ids=[module+'.'+method for modules in methods.values()for module,rows in modules.items()for method in rows]
 verification={k:dict(passed=True,count=n,native_bytes_opened_by_verifier=False)for k,n in(('before_MFG_metadata_only',2),('after_MFG_before_native_bytes',3))}
 worker=dict(schema='task1-native-GUI-lite-worker-v1',status='failed_preserved',error_type='ValueError',error=subject.FUNCTIONAL_LIMIT_ERROR,GUI_generated=False,stored_native_phase_started=True,actual_native_bytes_may_have_been_read=True,actual_tests_run=43,MFG_boundary=dict(manufactured_phase=False,scientific_API_spy_calls=[],native_IO_attempts=[]),new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0,candidate_adopted=False,browser_validation_performed=False,input_verification=verification)
 account=dict(passed=False,summary_present=False,partial_results_preserved=True)
 stage=dict(status='native_GUI_lite_failed_or_partial_preserved',worker_exit_code=1,source_commit=S['commit'],accounting=account)
 mfg=dict(schema='task1-native-GUI-lite-manufactured-tests-v1',status='passed',source_publication_commit=S['commit'],model_source_test_count=16,model_tests_run=16,owner_tests_run=27,tests_run=43,expected_total_tests=43,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0,scientific_API_spy_calls=[],native_IO_attempts=[],field_admission_granted=False,dependencies_initialized_before_mocks=True,IO_audit_installed=True,negative_fixture_counts={'native_suffix_rejection_before_open':1},owner_source_sha256=sources,source_sha256=sources,model_source_sha256=model,test_events=[dict(test_id=x,outcome='passed')for x in event_ids])
 pre=dict(source_sha256=sources,model_source_sha256=model,expected_synthetic_tests=43,expected_model_tests=16,expected_owner_tests=27)
 registration=dict(supervisor_pid=1,proc_start_ticks=2,controller_path=str(subject.GUI_SOURCE/'guardian.py'),source_sha256=sources)
 terminal=dict(schema='task1-native-GUI-lite-owner-v1',status='failed_preserved',failed_phase='result-publication',error_type='ValueError',error='Finite child failed result-publication; preserve log '+str(subject.GUI/'logs/195-result-publication.log'),GUI_generated=False,resources=dict(peak_accounted=7850267549),finished_utc='synthetic',pid=1,proc_start_ticks=2,candidate_adopted=False,browser_validation_performed=False)
 missing=dict(status='actual_outputs_and_absences_preserved',missing=['index.html','summary.json','gui-build-receipt.json'])
 payload=dict(path=str(subject.GUI/'payload.json'),bytes=5242129,SHA256='e'*64,readback_passed=True)
 cases=[];proofs=[];checkpoints=[];stats={}
 for i,cid in enumerate(subject.OLD_CASE_IDS):
  row=dict(candidate_id=cid,geometry=dict(kind='rectangles'))
  for key in('grid','scalars','E2000')+(('probe_arrays',)if i<3 else())+(('mask',)if i<2 else()):
   d=dict(path='/synthetic/'+str(i)+'-'+key+'.npz',SHA256='f'*64,bytes=123,publication_commit='a'*40,publication_target='data-native/synthetic/'+str(i)+'-'+key+'.npz',readback_passed=True);row[key]=d;stats[d['path']]=[1,i,123,4,5]
  expected=[v for k,v in row.items()if k in('grid','scalars','E2000','probe_arrays','mask')]
  proofs.append(dict(candidate_id=cid,large_native_arrays_released_before_next_case=True,original_statistics_recomputed=False,native_quantitative_metrics_recomputed=False,actual_new_PDE_RHS=0,actual_new_Q_loads=0,actual_new_angular_evaluations=0,native_cells=1,stored_grid_SHA256=row['grid']['SHA256'],stored_scalar_SHA256=row['scalars']['SHA256'],stored_E2000_SHA256=row['E2000']['SHA256'],native_file_proofs=[dict(d,full_SHA_before_verified=True,full_SHA_after_verified=True)for d in expected]));cases.append(row);checkpoints.append(dict(completed_cases=i+1,candidate_id=cid,native_arrays_released=True))
 return worker,stage,mfg,terminal,registration,pre,S,R,inventory,missing,proofs,cases,dict(native_bytes_opened=False,files=stats),payload,checkpoints

def certificate():
 pads=[];support=[]
 for i,signs in enumerate(((-1,-1),(1,1),(1,-1),(-1,1))):
  pads.append(dict(physical_pad_id=i,analytic_area_mm2=225.0,tangential_semimajor_mm=13.0,analytic_centroid_exact=[dict(numerator=n*5647,denominator=450)for n in signs]));support.append(dict(physical_pad_id=i,omitted_unresolved_area_upper_bound_m2=0.,minimum_positive_fraction=.001))
 return dict(schema='task1-certified-centroid-ellipse-contact-v1',passed=True,area_rescaled=False,analytic_centres_adjusted=False,unresolved_potential_positive_support_omitted=False,exact_h_mm=dict(numerator=25,denominator=51),injected_graph_node_count=8184,physical_pads=4,independent_outputs=2,physical_area_total_mm2=900.,pads=support,preflight=dict(passed=True,no_resize=True,no_centre_adjustment=True,node_mapping=['out0','out1','GND','GND'],pads=pads))
class AppendInputContracts(unittest.TestCase):
 def test_invalid_admission_stops_before_metadata_source_or_native_access(self):
  with patch.object(subject,'metadata',side_effect=AssertionError('No metadata')),patch.object(subject,'source_inventory',side_effect=AssertionError('No source')):
   with self.assertRaises(ValueError):subject.make_spec({})
 def test_only_typed_particular_partial_branch_and_dead_terminal_qualify(self):
  self.assertTrue(subject.validate_admission(admission())['root_authorized'])
  for key,value in(('base_outcome','complete_success'),('base_version','native-GUI-lite-r4-20261025'),('prior_owner_terminal_dead_confirmed',False),('publication_outcome','original_success'),('prior_recovery_terminal_dead_confirmed',False)):
   a=admission();a[key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_exact_valueerror_with43PASS_and_full_seven_proofs_is_allowed(self):self.assertTrue(subject.validate_partial_GUI_evidence(*partial()))
 def test_memory_deadline_field_or_test_failure_never_uses_partial_payload_branch(self):
  for index,key,value in((0,'error_type','MemoryError'),(0,'error','Other size or field error'),(0,'stored_native_phase_started',False),(2,'tests_errors',1),(2,'status','failed'),(3,'status','native_GUI_lite_failed_or_partial_published')):
   rows=list(copy.deepcopy(partial()));rows[index][key]=value
   with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
 def test_incomplete_six_or_wrong_native_SHA_proof_cannot_resume(self):
  rows=list(copy.deepcopy(partial()));rows[10].pop()
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
  rows=list(copy.deepcopy(partial()));rows[10][0]['native_file_proofs'][0]['SHA256']='0'*64
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
  rows=list(copy.deepcopy(partial()));rows[10][0]['native_file_proofs'][0]['full_SHA_after_verified']=False
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
 def test_uncreated_index_summary_and_GUIreceipt_are_honest_not_success(self):
  for index,key,value in((0,'GUI_generated',True),(1,'status','native_GUI_lite_built'),(3,'GUI_generated',True),(9,'missing',['index.html'])):
   rows=list(copy.deepcopy(partial()));rows[index][key]=value
   with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
 def test_payload_size_and_source_identity_are_fixed_actual_evidence(self):
  rows=list(copy.deepcopy(partial()));rows[13]['bytes']-=1
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
  rows=list(copy.deepcopy(partial()));rows[6]['commit']='0'*40
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
 def test_root_pin_of_unpublished_failed_terminal_needs_full_SHA_and_bytes(self):
  for key,value in(('SHA256',None),('bytes',0),('path','/synthetic/owner.json')):
   a=admission();a['previous_GUI']['terminal_owner'][key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_actual_complete_unique_passed_events_and_source_inventory_required(self):
  rows=list(copy.deepcopy(partial()));rows[2]['test_events'][1]['test_id']=rows[2]['test_events'][0]['test_id']
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
  rows=list(copy.deepcopy(partial()));rows[8]['owner_total']=26
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
 def test_native_stat_guards_and_all_seven_sequential_checkpoints_required(self):
  rows=list(copy.deepcopy(partial()));rows[12]['files'].pop(next(iter(rows[12]['files'])))
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
  rows=list(copy.deepcopy(partial()));rows[14][6]['completed_cases']=6
  with self.assertRaises(ValueError):subject.validate_partial_GUI_evidence(*rows)
 def test_new_native_descriptor_full_correct_direct_SHA_and_bytes(self):
  target='data-native/synthetic/a.npz';pub=dict(status='published_readback_verified',commit='a'*40,files={target:dict(SHA256='b'*64,bytes=123,readback_passed=True)})
  self.assertFalse(subject.direct(pub,'/synthetic/a.npz',target)['bytes_opened_here'])
  pub['files'][target]['readback_passed']=False
  with self.assertRaises(ValueError):subject.direct(pub,'/synthetic/a.npz',target)
 def test_actual_fine_area_centroid_and_four_normalizations_unchanged(self):
  self.assertTrue(subject.validate_geometry(certificate())['passed']);v=dict(status='complete',comparisons={m:dict(amplitude_scale=.5)for m in subject.MODES});self.assertEqual(subject.normalization_rows(v),v['comparisons'])
  c=certificate();c['preflight']['pads'][0]['analytic_centroid_exact'][0]['numerator']=-5646
  with self.assertRaises(ValueError):subject.validate_geometry(c)
 def test_canonical_source_keys_do_not_change_with_frozen_deployment_file(self):
  fake=subject.SOURCE/'append_inputs.py'
  with patch.object(subject.Path,'iterdir',return_value=iter([fake])),patch.object(subject.Path,'is_file',return_value=True),patch.object(subject.Path,'is_symlink',return_value=False),patch.object(subject.Path,'stat')as st,patch.object(subject,'digest',return_value='a'*64):
   st.return_value.st_size=100
   with patch.object(subject,'__file__','/synthetic/frozen/append_inputs.py'):a=subject.source_inventory()
  self.assertEqual(a,{str(fake):'a'*64})
 def test_separate_actual_readback_does_not_rewrite_publication_failed_old_owner(self):
  old=partial()[3];raw=b'x'*10739;codeSHA=hashlib.sha256(raw).hexdigest()
  R=dict(status='published_readback_verified',commit=subject.GUI5_RESULT_COMMIT,expected_parent=subject.GUI5_SOURCE_COMMIT,transport='supported_Git_HTTPS_readback_only_recovery',verification_source_SHA256=codeSHA,original_publisher_attempt_preserved=True,no_new_commit_or_push=True,files={str(i):dict(readback_passed=True,SHA256='a'*64)for i in range(230)})
  record=dict(schema='task1-GUI5-readback-recovery-v1',status='GUI5_partial_result_readback_recovered',source_commit=subject.GUI5_SOURCE_COMMIT,result_commit=subject.GUI5_RESULT_COMMIT,original_GUI_owner_status='failed_preserved',original_GUI_owner_receipt_SHA256=subject.ORIGINAL_FAILED_OWNER_SHA256,result_publication_receipt_SHA256=subject.GUI5_RESULT_RECEIPT_SHA,original_GUI_worker_failure_retained=True,old_owner_rewritten=False,GUI_generated=False,Windows_saved_verified=False,new_PDE=0,new_native_array_decodes=0,branch_mutations=0,pid=2,proc_start_ticks=3,finished_utc='synthetic',files_verified=230)
  pre=dict(schema='task1-GUI5-readback-recovery-plan-v1',fixed_commit=subject.GUI5_RESULT_COMMIT,expected_parent=subject.GUI5_SOURCE_COMMIT,original_failed_owner=copy.deepcopy(old),original_failed_publisher=dict(schema='task1-Git-only-attempt-v1',status='failed_preserved',attempt=1,push_confirmed=True,recorded_commit=subject.GUI5_RESULT_COMMIT),new_PDE=0,branch_mutations=0,verifier_source_SHA256=codeSHA,verifier_source_UTF8=raw.decode())
  with patch.object(subject,'RECOVERY_SOURCE_SHA',codeSHA):
   self.assertTrue(subject.validate_readback_recovery(record,pre,old,R,subject.GUI5_RESULT_RECEIPT_SHA,raw))
   for key,value in(('status','failed_preserved'),('old_owner_rewritten',True),('GUI_generated',True),('branch_mutations',1),('files_verified',229),('original_GUI_owner_receipt_SHA256','0'*64)):
    bad=copy.deepcopy(record);bad[key]=value
    with self.assertRaises(ValueError):subject.validate_readback_recovery(bad,pre,old,R,subject.GUI5_RESULT_RECEIPT_SHA,raw)
if __name__=='__main__':unittest.main()
