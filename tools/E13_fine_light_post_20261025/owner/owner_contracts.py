"""Pure source-bound accounting and resource contracts; no dataset access."""
from pathlib import Path
CANDIDATE_ID='E13-tangent-P23-centroids-225-XY102-Z97'
def require(ok,message):
 if not ok:raise ValueError(message)
def fixture_elements(shape,limit=65536):
 dims=(shape,)if type(shape)is int else tuple(shape);require(all(type(n)is int and n>=0 for n in dims),'Manufactured array shape uses nonnegative Python integers')
 total=1
 for n in dims:total*=n;require(total<=limit,'Bounded manufactured arrays before allocation; native graph/field/Q shapes forbidden')
 return total
def owned_auxiliary_bytes(size,roots_by_base=None):
 roots_by_base={base:list(Path(base).glob('task1-*'))for base in('/dev/shm','/tmp')}if roots_by_base is None else roots_by_base
 require(set(roots_by_base)=={'/dev/shm','/tmp'},'Both actual task1 owned auxiliary namespaces')
 parts={base:sum(size(path)for path in paths)for base,paths in roots_by_base.items()}
 return dict(total_bytes=sum(parts.values()),by_namespace_bytes=parts,namespace_roots=['/dev/shm/task1-*','/tmp/task1-*'],historical_auxiliary_correction_bytes_reported_by_root=14341,physical_cap_unchanged=True)
def validate_summary(s,expected_geometries=1):
 require(type(expected_geometries)is int and expected_geometries==1,'Exactly one E13fine geometry; no old-case repeat')
 require(s.get('status')=='E13_fine_cached_highvolume_and40probe_postbatch_computed_unadopted','Exact E13 fine stored-native postbatch status')
 for key in('actual_new_PDE_RHS','actual_new_Q_loads','actual_new_eigen_solves','actual_new_angular_evaluations','old_case_repeats'):require(type(s.get(key))is int and s[key]==0,'Zero hidden scientific recompute/repeat '+key)
 require(type(s.get('completed_native_geometries'))is int and s['completed_native_geometries']==1 and len(s.get('candidates',[]))==1,'Exactly one retained E13 fine case')
 rows=s['candidates'];require(rows[0].get('candidate_id')==CANDIDATE_ID,'No substituted old/coarse case')
 keys=('requested_probes','calculated_probes','unavailable_probes','strict_same_layer_bracket_available_probes','same_layer_extrapolated_probes')
 for r in rows:
  require(all(type(r.get(k))is int and r[k]>=0 for k in keys)and r['requested_probes']==40 and r['calculated_probes']+r['unavailable_probes']==40 and r['strict_same_layer_bracket_available_probes']+r['same_layer_extrapolated_probes']==r['calculated_probes'],'All forty actual requests retain unavailable and strict/extrapolated counts separately')
  for k in('new_PDE_RHS','new_Q_loads','new_eigen_solves','new_angular_evaluations'):require(type(r.get(k))is int and r[k]==0,'No per-case hidden scientific recompute '+k)
  require(type(r.get('actual_threshold_subsets'))is int and r['actual_threshold_subsets']==48 and r.get('candidate_adopted')is False,'Actual forty-eight classifications and no per-case adoption')
 for k in keys:require(type(s.get(k))is int and s[k]==sum(r[k]for r in rows),'Exact actual retained-row aggregate '+k)
 require(type(s.get('actual_threshold_subsets'))is int and s['actual_threshold_subsets']==48 and s.get('expected_threshold_subsets_per_geometry')==48,'Four separate modes bytwo cutoffs bysix fixed ROI')
 require(s.get('original_statistics_recomputed')is False and s.get('original_results_overwritten')is False and s.get('old600probe_predictions_preserved')is True,'Original results/statistics/predictions preserved')
 for k in('hardware_loading_validated','experimental_validation','full_convergence','physiological_activation_or_safety_claim','candidate_adopted','Windows_saved_verified'):require(s.get(k)is False,'No unsupported validation/storage/adoption claim '+k)
 holds=s.get('inherited_holds',{})
 for k in('old_independent_5percent_interface_failures_preserved','prior_fine14_of18_and16_of18_failures_preserved','SC_XY_contact_edge_material_uncertainty_preserved'):require(holds.get(k)is True,'Actual inherited failed diagnostics remain held '+k)
 recovery=s.get('E13_publication_recovery',{});require(recovery.get('original_numerical_owner_status')=='failed_preserved'and recovery.get('old_numerical_owner_rewritten')is False and recovery.get('recovery_only_not_new_numerical_success')is True,'Late transport recovery never relabels original failed owner as numerical success')
 return dict(passed=True,completed_native_geometries=1,actual_threshold_subsets=48,old_case_repeats=0,**{k:s[k]for k in keys},new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,candidate_adopted=False)
def validate_MFG(r,sources,model_count,owner_count):
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0,'Positive prospective source-AST test counts')
 require(r.get('status')=='passed'and r.get('model_source_sha256')==sources and r.get('model_source_test_count')==model_count,'Actual successful prospective tests bound to exact canonical model')
 for key,value in dict(model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0).items():require(type(r.get(key))is int and r[key]==value,'Exact successful actual test count '+key)
 require(r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('native_field_reads')==0 and r.get('field_admission_granted')is False and r.get('scientific_API_spy_calls')==[],'Bounded manufactured arrays/FFT only; no actual native/cache/scientific work in tests')
 return dict(passed=True,model_tests=model_count,owner_tests=owner_count,actual_tests=model_count+owner_count)
