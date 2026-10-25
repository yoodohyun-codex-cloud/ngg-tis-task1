"""Pure owner accounting for conditional same-physical E13 adjacent-XY study."""
from pathlib import Path

def require(ok,message):
 if not ok:raise ValueError(message)

def fixture_elements(shape,limit=65536):
 dims=(shape,)if type(shape)is int else tuple(shape);require(all(type(n)is int and n>=0 for n in dims),'Manufactured shape uses nonnegative Python integers')
 n=1
 for size in dims:n*=size;require(n<=limit,'Bounded manufactured fixtures; native field/fullQ forbidden')
 return n

def owned_auxiliary_bytes(size,roots_by_base=None):
 """Logical owned bytes in BOTH root-authorized task1 namespaces.

 No deletion or cap change. Injectable listings support source-pure fixtures.
 All scans occur only when actual root owner invokes this after admission.
 """
 roots_by_base={base:list(Path(base).glob('task1-*'))for base in('/dev/shm','/tmp')}if roots_by_base is None else roots_by_base
 require(set(roots_by_base)=={'/dev/shm','/tmp'},'Both task1-owned auxiliary namespaces must be accounted')
 parts={base:sum(size(path)for path in paths)for base,paths in roots_by_base.items()}
 return dict(total_bytes=sum(parts.values()),by_namespace_bytes=parts,namespace_roots=['/dev/shm/task1-*','/tmp/task1-*'],historical_auxiliary_omission_bytes_reported_by_root=14341,physical_cap_unchanged=True)

def validate_summary(s):
 require(s.get('status')=='two_E13_matched97_metric_cases_and_physical_overlap_computed_unadopted','Exact completed E13 adjacent-grid study')
 for key,num in dict(actual_new_driven_RHS=2,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=2,actual_full_angular_evaluations=1,actual_SC4_only_angular_evaluations=1,actual_repeated_original_bulk_angular_evaluations=0,actual_duplicate_full_coarse_scalar_archives=0,actual_immutable_fine_B0_aliases=1,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0).items():require(type(s.get(key))is int and s[key]==num,'Exact new/reused/scalar accounting '+key)
 rows=s.get('candidates',[]);require(len(rows)==3 and len(s.get('new_E13_metric_cases',[]))==2,'Two grid representations plus exactly one full fineB0 immutable alias')
 require({r.get('grid_variant')for r in s['new_E13_metric_cases']}=={'XY102-Z97','XY100-Z97'},'Explicit fine/coarse common97 representations')
 for key in('Q_resident_during_postprocessing','originals_overwritten','candidate_adopted'):require(s.get(key)is False,'No Q leak/overwrite/adoption '+key)
 holds=s.get('holds',{});require(holds.get('old_independent_5percent_interface_failures_preserved')is True and holds.get('prior_fine14_of18_and16_of18_failures_preserved')is True,'All original failed diagnostics preserved')
 require(all(holds.get(k)is False for k in('full_convergence','physiological_activation_or_safety_claim','experimental_validation','candidate_adopted')),'No new convergence/activation/safety/experimental claim')
 require(s.get('same_grid_fine_design_comparisons',{}),'FineB0 primary/secondary comparisons must remain explicit')
 return dict(passed=True,actual_new_driven_RHS=2,new_coarse_RHS=0,new_eigen_solves=0,full_angular_evaluations=1,SC4_only_angular_evaluations=1,repeated_old93_bulk_angular_evaluations=0,immutable_fine_B0_aliases=1,candidate_adopted=False)

def validate_physical_proof(p,new_rhs):
 require(type(new_rhs)is int and new_rhs in(0,1),'Predeclared fine or cached-coarse RHS role')
 require(p.get('passed')is True and p.get('passivity_passed')is True and p.get('physical_gates',{}).get('passed')is True,'Unchanged five current/power circuit gates and passivity')
 limits=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
 metrics=p['physical_gates'].get('metrics',{});require(set(metrics)==set(limits),'All five original numerical circuit metrics retained')
 for key,limit in limits.items():require(metrics[key].get('passed')is True and metrics[key].get('limit')==limit,'Gate not relaxed '+key)
 require(type(p.get('actual_new_RHS'))is int and p['actual_new_RHS']==new_rhs,'Actual per-response new/cached count')
 if not new_rhs:
  require(p.get('reused_published_baseline_surface')is True and p.get('iterations')==0 and p.get('matvec_count')==0 and p.get('new_Krylov_calls')==0,'Cached coarse response never falls back to Krylov')
  require(type(p.get('modal_restore_relative_error'))in(int,float)and 0<=p['modal_restore_relative_error']<=2e-7 and p.get('modal_restore_limit')==2e-7,'Fresh coarse modal restore')
 return dict(passed=True,new_RHS=new_rhs,coarse_new_Krylov_calls=0 if not new_rhs else None)

def validate_MFG(r,sources,model_count,owner_count):
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0,'Dynamic positive source-AST test counts')
 require(r.get('status')=='passed'and r.get('model_source_sha256')==sources and r.get('model_source_test_count')==model_count,'Actual source-bound local manufactured PASS')
 for key,num in dict(model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0).items():require(type(r.get(key))is int and r[key]==num,'Actual local test count '+key)
 require(r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('native_field_reads')==0 and r.get('field_admission_granted')is False and r.get('scientific_API_spy_calls')==[],'No actual native data/Q/PDE in protected tiny fixtures')
 return dict(passed=True,model_tests=model_count,owner_tests=owner_count)
