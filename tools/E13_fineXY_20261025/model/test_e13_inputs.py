"""Prospective pure proof contracts; no arrays/data/Q/imported science."""
import copy,unittest
from unittest.mock import patch
import e13_inputs as subject

def admission():
 return dict(schema='task1-E13-fineXY-root-admission-v1',status='admitted_after_published_native_streamed_B0_PASS',root_review_positive=True,sole_NUM_owner=True,new_fine_driven_RHS=2,new_coarse_driven_RHS=0,cached_coarse_SC4_responses=2,new_eigen_solves=0,new_fine_full_angular_evaluations=1,new_coarse_SC4_angular_evaluations=1,repeated_original93_bulk_angular_evaluations=0,fine_B0_PDE_or_angular_repeats=0,physical_pads=4,independent_outputs=2,frequencies_Hz=[2000,2010],fine_evaluation_cells=793848,coarse_common97_cells=762420,max_physical_evaluation_cells=800000,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,candidate_adopted=False,source_sha256={'fixture.py':'a'*64},decision_basis='Synthetic contract only',native_restore_review=dict(run=str(subject.NATIVE),publication_path=str(subject.NATIVE/'result-publication/result-publication.json'),publication_SHA256='b'*64,publication_commit='c'*40,root_reviewed=True,decision_basis='Synthetic status only, not an execution',terminal_owner_receipt=dict(path=str(subject.NATIVE/'receipt.json'),SHA256='d'*64,bytes=123)))
def summary():
 rows=[]
 for f,out in((2000,0),(2010,1)):
  rows.append(dict(frequency_Hz=f,active_output=out,native_Q_read=True,whole_Q_loaded=False,Q_closed_and_profiles_released_before_error_reduction=True,field_reconstruction_saved=False,new_PDE_RHS=0,new_Krylov_calls=0,new_eigen_solves=0,new_angular_evaluations=0,field_error=dict(passed=True,pointwise_passed=True,component_passed=True,vector_passed=True),candidate_adopted=False))
 return dict(status='two_cached_native_carriers_streamed_Q_restore_computed_unadopted',completed_cached_native_responses=2,actual_native_E_reconstructions=2,actual_native_field_comparisons=2,actual_new_PDE_RHS=0,actual_new_Krylov_calls=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,new_native_phi_or_E_archives=0,new_Q_archives=0,frequencies_Hz=[2000,2010],actual_native_Q_read=True,whole_Q_loaded=False,full_Q_materialized=False,complex_Q_materialized=False,responses=rows,native_restore_verification_passed=True,phase_fit=False,gauge_fit=False,original_results_overwritten=False,full_mesh_convergence=False,experimental_validation=False,physiological_activation_or_safety_claim=False,candidate_adopted=False,Windows_saved_verified=False,same_physical_coordinates_and_grid_verified=True,inherited_holds={'old_independent_5percent_interface_failures_preserved':True})
def gates():
 limits=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
 return dict(passed=True,passivity_passed=True,physical_gates=dict(passed=True,metrics={k:dict(value=0.,limit=v,passed=True)for k,v in limits.items()}),actual_new_RHS=0,iterations=0,matvec_count=0,new_Krylov_calls=0,reused_published_baseline_surface=True,modal_restore_passed=True,modal_restore_relative_error=0.,modal_restore_limit=2e-7,stored_source_current_restore_passed=True,stored_power_restore_comparison={'passed':True})

class E13InputContracts(unittest.TestCase):
 def test_incomplete_decision_stops_before_any_metadata(self):
  with patch.object(subject,'metadata',side_effect=AssertionError('No input reads')),patch.object(subject,'source_inventory',side_effect=AssertionError('No input reads')):
   with self.assertRaises(ValueError):subject.make_spec({})
 def test_only_exact_actual_native_result_can_be_reviewed(self):
  a=admission();self.assertIs(subject.validate_admission(a),a)
  for key,value in(('run',str(subject.MFG)),('publication_path',str(subject.MFG/'result-publication/result-publication.json')),('root_reviewed',False)):
   a=admission();a['native_restore_review'][key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_no_extra_solve_or_bulk_angular_or_baseline_repeat(self):
  for key,value in(('new_fine_driven_RHS',3),('new_coarse_driven_RHS',1),('new_eigen_solves',True),('repeated_original93_bulk_angular_evaluations',1),('fine_B0_PDE_or_angular_repeats',1),('physical_pads',8)):
   a=admission();a[key]=value
   with self.assertRaises(ValueError):subject.validate_admission(a)
 def test_native_computed_with_failed_field_gate_is_not_PASS(self):
  good=summary();self.assertTrue(subject.require_native_PASS(good)['native_field_equivalence_passed'])
  bad=summary();bad['responses'][1]['field_error'].update(passed=False,pointwise_passed=False,component_passed=False,vector_passed=False);bad['native_restore_verification_passed']=False
  self.assertFalse(subject.validate_summary(bad)['native_field_equivalence_passed'])
  with self.assertRaises(ValueError):subject.require_native_PASS(bad)
 def test_native_full_Q_or_fitted_coordinates_cannot_admit(self):
  for key,value in(('whole_Q_loaded',True),('full_Q_materialized',True),('complex_Q_materialized',True),('phase_fit',True),('gauge_fit',True),('actual_new_PDE_RHS',1)):
   bad=summary();bad[key]=value
   with self.assertRaises(ValueError):subject.require_native_PASS(bad)
 def test_every_component_vector_pointwise_gate_is_required(self):
  for key in('component_passed','vector_passed','pointwise_passed'):
   bad=summary();bad['responses'][0]['field_error'][key]=False
   with self.assertRaises(ValueError):subject.require_native_PASS(bad)
 def test_five_cached_physics_modal_and_power_gates_cannot_relax(self):
  self.assertTrue(subject.validate_cached_gates(gates())['passed'])
  for key,value in(('actual_new_RHS',1),('new_Krylov_calls',1),('passivity_passed',False),('modal_restore_passed',False),('stored_source_current_restore_passed',False)):
   bad=gates();bad[key]=value
   with self.assertRaises(ValueError):subject.validate_cached_gates(bad)
  bad=gates();bad['physical_gates']['metrics']['relative_complex_power_error']['limit']=1e-3
  with self.assertRaises(ValueError):subject.validate_cached_gates(bad)
 def test_original_interface_failure_hold_must_remain(self):
  bad=summary();bad['inherited_holds']['old_independent_5percent_interface_failures_preserved']=False
  with self.assertRaises(ValueError):subject.require_native_PASS(bad)
 def test_direct_descriptor_rejects_skipped_readback_and_changed_SHA(self):
  target='data-native/fixture/a.npz';pub=dict(status='published_readback_verified',commit='c'*40,files={target:dict(SHA256='d'*64,bytes=12,readback_passed=True)})
  self.assertFalse(subject.direct(pub,'/synthetic/fixture/a.npz',target,'d'*64)['decoded_here'])
  for key,value in(('SHA256','e'*64),('readback_passed',False),('bytes',True)):
   bad=copy.deepcopy(pub);bad['files'][target][key]=value
   with self.assertRaises(ValueError):subject.direct(bad,'/synthetic/fixture/a.npz',target,'d'*64)
 def test_synthetic_or_pending_summary_never_counts_as_native_PASS(self):
  for status in('passed','source_prepared','synthetic_tests_executed','failed_preserved'):
   bad=summary();bad['status']=status
   with self.assertRaises(ValueError):subject.require_native_PASS(bad)
 def test_postbuild_worker_stage_source_or_terminal_failure_blocks_candidate(self):
  account=dict(native_field_equivalence_passed=True,new_PDE_RHS=0)
  verification=dict(before_tests_and_build=dict(passed=True,count=9),after_build=dict(passed=True,count=10))
  worker=dict(status='streamed_Q_cached_native_restore_computed',summary_SHA256='a'*64,native_restore_accounting=account,input_verification=verification,manufactured_test_receipt_SHA256='f'*64)
  stage=dict(status='streamed_Q_native_restore_computed',worker_exit_code=0,source_commit='b'*40,accounting=account)
  terminal=dict(status='streamed_Q_native_restore_computed_published',source_commit='b'*40,result_commit='c'*40,postprocess_accounting=account,finished_utc='synthetic-terminal-time')
  kwargs=dict(summary_SHA256='a'*64,source_commit='b'*40,result_commit='c'*40,local_MFG_receipt_SHA256='f'*64)
  self.assertTrue(subject.validate_native_completion(worker,stage,verification,terminal,**kwargs))
  for which,key,value in(('worker','status','failed_preserved'),('stage','worker_exit_code',1),('terminal','error_type','LatePublicationFailure'),('terminal','result_commit','e'*40)):
   records={name:copy.deepcopy(obj)for name,obj in(('worker',worker),('stage',stage),('terminal',terminal))};records[which][key]=value
   with self.assertRaises(ValueError):subject.validate_native_completion(records['worker'],records['stage'],verification,records['terminal'],**kwargs)
  bad=copy.deepcopy(verification);bad['after_build']['passed']=False
  with self.assertRaises(ValueError):subject.validate_native_completion(worker,stage,bad,terminal,**kwargs)
  bad=copy.deepcopy(verification);bad['after_build']['count']=9;changed=copy.deepcopy(worker);changed['input_verification']=bad
  with self.assertRaises(ValueError):subject.validate_native_completion(changed,stage,bad,terminal,**kwargs)
  changed=copy.deepcopy(worker);changed['manufactured_test_receipt_SHA256']='0'*64
  with self.assertRaises(ValueError):subject.validate_native_completion(changed,stage,verification,terminal,**kwargs)

if __name__=='__main__':unittest.main()
