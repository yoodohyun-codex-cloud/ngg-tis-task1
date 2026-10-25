"""Pure accounting for streamed-native cached restoration; no scientific work."""
def require(ok,message):
 if not ok:raise ValueError(message)
def fixture_elements(shape,limit=65536):
 dims=(shape,)if type(shape)is int else tuple(shape);require(all(type(n)is int and n>=0 for n in dims),'Manufactured shape uses nonnegative Python integers')
 n=1
 for size in dims:n*=size;require(n<=limit,'Bounded manufactured arrays before allocation; native field/fullQ forbidden')
 return n
def validate_cached_gates(p):
 require(p.get('passed')is True and p.get('passivity_passed')is True and p.get('physical_gates',{}).get('passed')is True,'Fresh unchanged five circuit/power/passivity gates before E reconstruction')
 limits=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
 metrics=p['physical_gates'].get('metrics',{});require(set(metrics)==set(limits),'All five original numerical metrics retained')
 for key,limit in limits.items():require(metrics[key].get('passed')is True and metrics[key].get('limit')==limit,'Original circuit gate not relaxed '+key)
 require(p.get('actual_new_RHS')==0 and p.get('iterations')==0 and p.get('matvec_count')==0 and p.get('new_Krylov_calls')==0 and p.get('reused_published_baseline_surface')is True,'Cached response only; no solve/Krylov fallback')
 require(p.get('modal_restore_passed')is True and 0<=p.get('modal_restore_relative_error',-1)<=2e-7 and p.get('modal_restore_limit')==2e-7 and p.get('stored_source_current_restore_passed')is True and p.get('stored_power_restore_comparison',{}).get('passed')is True,'Modal/current/signed-power restore gates before field comparison')
 return dict(passed=True,new_PDE_RHS=0,new_Krylov_calls=0)
def validate_summary(s):
 require(s.get('status')=='two_cached_native_carriers_streamed_Q_restore_computed_unadopted','Exact completed cached-native restore status')
 for key,num in dict(completed_cached_native_responses=2,actual_native_E_reconstructions=2,actual_native_field_comparisons=2,actual_new_PDE_RHS=0,actual_new_Krylov_calls=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,new_native_phi_or_E_archives=0,new_Q_archives=0).items():require(type(s.get(key))is int and s[key]==num,'Exact finite restored-work/no-new-solve count '+key)
 require(s.get('frequencies_Hz')==[2000,2010]and s.get('actual_native_Q_read')is True and all(s.get(key)is False for key in('whole_Q_loaded','full_Q_materialized','complex_Q_materialized')),'Actual streamed real nativeQ; no full/complexQ')
 rows=s.get('responses',[]);require(len(rows)==2 and [(r.get('frequency_Hz'),r.get('active_output'))for r in rows]==[(2000,0),(2010,1)],'Exactly original two cached carrier/output responses')
 for r in rows:
  require(r.get('native_Q_read')is True and r.get('whole_Q_loaded')is False and r.get('Q_closed_and_profiles_released_before_error_reduction')is True and r.get('field_reconstruction_saved')is False,'Operator/profile lifetime ended before RAM-only original-field comparison')
  for key in('new_PDE_RHS','new_Krylov_calls','new_eigen_solves','new_angular_evaluations'):require(type(r.get(key))is int and r[key]==0,'No hidden per-carrier solve/search '+key)
  require(type(r.get('field_error',{}).get('passed'))is bool and r.get('candidate_adopted')is False,'Honest retained field-error diagnostic; no adoption')
 expected=all(r['field_error']['passed']for r in rows);require(s.get('native_restore_verification_passed')is expected,'Field-equivalence gate failures remain failed computed results')
 for key in('phase_fit','gauge_fit','original_results_overwritten','full_mesh_convergence','experimental_validation','physiological_activation_or_safety_claim','candidate_adopted','Windows_saved_verified'):require(s.get(key)is False,'No fitted equivalence or unsupported validation/storage/adoption '+key)
 require(s.get('same_physical_coordinates_and_grid_verified')is True and s.get('inherited_holds',{}).get('old_independent_5percent_interface_failures_preserved')is True,'Same physical grid/old failed diagnostics retained')
 return dict(passed=True,completed_cached_native_responses=2,new_PDE_RHS=0,new_Krylov_calls=0,E_reconstructions=2,new_angular_evaluations=0,native_Q_read=True,full_Q_materialized=False,native_field_equivalence_passed=expected,candidate_adopted=False)
def validate_MFG(r,sources,model_count,owner_count):
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0,'Positive prospective source-AST counts')
 require(r.get('status')=='passed'and r.get('model_source_sha256')==sources and r.get('model_source_test_count')==model_count,'Actual successful source-bound local manufactured tests')
 for key,num in dict(model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0).items():require(type(r.get(key))is int and r[key]==num,'Exact actual successful MFG count '+key)
 require(r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('native_field_reads')==0 and r.get('field_admission_granted')is False and r.get('scientific_API_spy_calls')==[],'Small controlled fixtures only, no native/cache/field/solve data in local tests')
 return dict(passed=True,model_tests=model_count,owner_tests=owner_count)
